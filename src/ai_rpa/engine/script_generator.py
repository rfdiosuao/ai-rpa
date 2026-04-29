"""Generate Robot Framework scripts from natural language via AI."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from robot.api import TestSuite
from robot.errors import DataError

from ai_rpa.config import AirPaConfig
from ai_rpa.engine.ai_client import AIClient
from ai_rpa.engine.prompt_builder import (
    build_classification_prompt,
    build_generation_prompt,
)
from ai_rpa.registry.keyword_registry import KeywordRegistry

logger = logging.getLogger(__name__)


@dataclass
class GeneratedScript:
    """Result of script generation."""

    robot_text: str
    suite: object  # TestSuite instance
    libraries_needed: list[str] = field(default_factory=list)
    explanation: str = ""
    categories: list[str] = field(default_factory=list)


class ScriptGenerator:
    """Generate Robot Framework scripts from natural language task descriptions."""

    def __init__(self, config: AirPaConfig, registry: KeywordRegistry):
        self._config = config
        self._registry = registry
        self._ai = AIClient(
            api_key=config.openai_api_key,
            model=config.openai_model,
            base_url=config.openai_base_url,
        )

    def generate(self, task: str) -> GeneratedScript:
        """Generate a Robot Framework script from a natural language task.

        Two-stage process:
        1. Classify intent → determine categories
        2. Generate script with targeted keyword context
        """
        # Stage 1: Intent classification
        print("[分析意图...]", end=" ", flush=True)
        categories = self._classify_intent(task)
        category_str = ", ".join(categories)
        print(f"→ {category_str}")

        # Stage 2: Get keyword context for relevant categories
        keyword_context = self._registry.get_compact_context(categories)
        print(f"[加载关键字...] → 来自相关库的 {len(keyword_context.splitlines())} 个关键字")

        # Stage 3: Generate script
        print("[生成脚本...]", end=" ", flush=True)
        script_result = self._generate_script(task, keyword_context)
        print("完成")

        return script_result

    def _classify_intent(self, task: str) -> list[str]:
        """Use AI to classify the task into operation categories."""
        system, user = build_classification_prompt(task)

        try:
            result = self._ai.chat_json(system, user, temperature=0.0)
            categories = result.get("categories", ["general"])
            logger.info("Intent classified: %s -> %s", task[:50], categories)
            return categories
        except Exception as e:
            logger.warning("Intent classification failed, using general: %s", e)
            return ["general"]

    def _generate_script(self, task: str, keyword_context: str) -> GeneratedScript:
        """Use AI to generate a Robot Framework script."""
        system, user = build_generation_prompt(task, keyword_context)

        try:
            result = self._ai.chat_json(system, user, temperature=0.1)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract script from raw response
            logger.warning("JSON parsing failed, attempting raw extraction")
            raw = self._ai.chat(system, user, json_mode=False, temperature=0.1)
            result = {"script": raw, "libraries_needed": [], "explanation": ""}

        robot_text = result.get("script", "")
        libraries = result.get("libraries_needed", [])
        explanation = result.get("explanation", "")

        # Validate: try to parse into TestSuite
        try:
            suite = TestSuite.from_string(robot_text)
        except DataError as e:
            logger.warning("Generated script has syntax error: %s", e)
            # Attempt auto-fix: add minimal structure if missing
            robot_text = self._auto_fix_structure(robot_text, str(e))
            try:
                suite = TestSuite.from_string(robot_text)
            except DataError as e2:
                raise ValueError(f"生成的脚本语法无效且无法自动修复: {e2}") from e2

        return GeneratedScript(
            robot_text=robot_text,
            suite=suite,
            libraries_needed=libraries,
            explanation=explanation,
        )

    def regenerate_with_error(
        self, task: str, original_script: str,
        error_message: str, failed_keyword: str = "",
        test_name: str = "RPA Task", error_type: str = "RuntimeError",
    ) -> GeneratedScript:
        """Regenerate a script after execution failure, using error context."""
        from ai_rpa.engine.prompt_builder import build_recovery_prompt

        # Get keyword context (use all categories to give AI more options)
        categories = self._classify_intent(task)
        keyword_context = self._registry.get_compact_context(categories, max_keywords=100)

        system, user = build_recovery_prompt(
            keyword_context=keyword_context,
            original_script=original_script,
            test_name=test_name,
            failed_keyword=failed_keyword,
            error_message=error_message,
            error_type=error_type,
        )

        result = self._ai.chat_json(system, user, temperature=0.1)

        robot_text = result.get("script", "")
        libraries = result.get("libraries_needed", [])
        explanation = result.get("explanation", "")

        try:
            suite = TestSuite.from_string(robot_text)
        except DataError as e:
            robot_text = self._auto_fix_structure(robot_text, str(e))
            suite = TestSuite.from_string(robot_text)

        return GeneratedScript(
            robot_text=robot_text,
            suite=suite,
            libraries_needed=libraries,
            explanation=explanation,
        )

    def _auto_fix_structure(self, robot_text: str, error: str) -> str:
        """Attempt to fix common structural issues in generated scripts."""
        text = robot_text.strip()

        # If missing *** Settings *** section, add it
        if "*** Settings ***" not in text:
            text = "*** Settings ***\n\n" + text

        # If missing *** Test Cases *** section, wrap content
        if "*** Test Cases ***" not in text:
            text += "\n\n*** Test Cases ***\nRPA Task\n    No Operation\n"

        return text
