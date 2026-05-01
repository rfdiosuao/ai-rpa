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
from ai_rpa.pattern_store import PatternStore

logger = logging.getLogger(__name__)


@dataclass
class GeneratedScript:
    """Result of script generation."""

    robot_text: str
    suite: object  # TestSuite instance
    libraries_needed: list[str] = field(default_factory=list)
    explanation: str = ""
    categories: list[str] = field(default_factory=list)
    from_pattern: bool = False   # True if reused from pattern store (free!)
    pattern_id: str = ""         # Pattern ID if reused


class ScriptGenerator:
    """Generate Robot Framework scripts from natural language task descriptions.

    Flow:
    1. Search pattern store first (free, instant)
    2. If no match → AI intent classification (cheap)
    3. AI script generation with targeted keyword context (expensive)
    4. On success → save to pattern store for future reuse
    """

    def __init__(self, config: AirPaConfig, registry: KeywordRegistry,
                 pattern_store: PatternStore | None = None):
        self._config = config
        self._registry = registry
        self._pattern_store = pattern_store or PatternStore()
        self._ai = AIClient(
            api_key=config.openai_api_key,
            model=config.openai_model,
            base_url=config.openai_base_url,
        )

    def generate(self, task: str) -> GeneratedScript:
        """Generate a Robot Framework script from a natural language task."""
        # Step 1: Search pattern store (free!)
        match = self._search_patterns(task)
        if match:
            return match

        # Step 2: AI intent classification
        print("[分析意图...]", end=" ", flush=True)
        categories = self._classify_intent(task)
        category_str = ", ".join(categories)
        print(f"→ {category_str}")

        # Step 3: Search pattern store with categories
        match = self._search_patterns(task, categories=categories)
        if match:
            return match

        # Step 4: Get keyword context and generate via AI
        keyword_context = self._registry.get_compact_context(categories)
        print(f"[加载关键字...] → 来自相关库的 {len(keyword_context.splitlines())} 个关键字")

        print("[生成脚本...]", end=" ", flush=True)
        script_result = self._generate_script(task, keyword_context, categories)
        print("完成")

        return script_result

    def _search_patterns(self, task: str, categories: list[str] | None = None) -> GeneratedScript | None:
        """Search pattern store for a matching reusable pattern."""
        results = self._pattern_store.search(task, categories=categories, min_similarity=0.6)

        if not results:
            return None

        best_pattern, score = results[0]

        # High-confidence match: reuse directly
        if score >= 0.75:
            print(f"[模式复用] 找到相似模式 (相似度 {score:.0%}) → {best_pattern.explanation}")
            try:
                suite = TestSuite.from_string(best_pattern.robot_text)
            except DataError:
                # Pattern has syntax errors, remove it
                self._pattern_store.delete(best_pattern.id)
                return None

            self._pattern_store.record_success(best_pattern.id)
            return GeneratedScript(
                robot_text=best_pattern.robot_text,
                suite=suite,
                libraries_needed=best_pattern.libraries_needed,
                explanation=best_pattern.explanation,
                categories=best_pattern.categories,
                from_pattern=True,
                pattern_id=best_pattern.id,
            )

        # Medium-confidence match: show as suggestion, still generate new
        if score >= 0.6:
            print(f"[模式参考] 找到相似模式 (相似度 {score:.0%}): {best_pattern.task_description}")
            print(f"           → 仍将生成新脚本，但参考历史模式")

        return None

    def save_pattern(self, task: str, script: GeneratedScript) -> str:
        """Save a successful script as a reusable pattern."""
        pattern = self._pattern_store.add(
            task=task,
            categories=script.categories,
            robot_text=script.robot_text,
            libraries_needed=script.libraries_needed,
            explanation=script.explanation,
        )
        return pattern.id

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
            # Fallback: use local pattern matching
            from ai_rpa.scenarios.scenario_matcher import match_categories
            return match_categories(task)

    def _generate_script(self, task: str, keyword_context: str,
                         categories: list[str]) -> GeneratedScript:
        """Use AI to generate a Robot Framework script."""
        system, user = build_generation_prompt(task, keyword_context)

        try:
            result = self._ai.chat_json(system, user, temperature=0.1)
        except json.JSONDecodeError:
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
            categories=categories,
        )

    def regenerate_with_error(
        self, task: str, original_script: str,
        error_message: str, failed_keyword: str = "",
        test_name: str = "RPA Task", error_type: str = "RuntimeError",
    ) -> GeneratedScript:
        """Regenerate a script after execution failure, using error context."""
        from ai_rpa.engine.prompt_builder import build_recovery_prompt

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
            categories=categories,
        )

    def _auto_fix_structure(self, robot_text: str, error: str) -> str:
        """Attempt to fix common structural issues in generated scripts."""
        text = robot_text.strip()

        if "*** Settings ***" not in text:
            text = "*** Settings ***\n\n" + text

        if "*** Test Cases ***" not in text:
            text += "\n\n*** Test Cases ***\nRPA Task\n    No Operation\n"

        return text
