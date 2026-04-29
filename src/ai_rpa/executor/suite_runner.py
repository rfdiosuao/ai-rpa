"""Suite runner: execute Robot Framework suites with monitoring and error recovery."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from io import StringIO
from typing import Optional

from robot.api import TestSuite
from robot.errors import DataError

from ai_rpa.config import AirPaConfig
from ai_rpa.engine.script_generator import GeneratedScript, ScriptGenerator
from ai_rpa.executor.listener import AirPaListener, cli_status_callback

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a suite execution."""

    success: bool
    return_code: int = 0
    status: str = "PASS"  # PASS / FAIL
    message: str = ""
    failed_keyword: str = ""
    robot_text: str = ""
    elapsed_seconds: float = 0.0
    keywords_executed: int = 0
    log_messages: list[str] = field(default_factory=list)
    retries_used: int = 0


class SuiteRunner:
    """Execute Robot Framework suites with monitoring and error recovery."""

    def __init__(self, config: AirPaConfig):
        self._config = config

    def run(self, suite: TestSuite, listener: Optional[AirPaListener] = None) -> ExecutionResult:
        """Execute a TestSuite and return structured results."""
        # Capture stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        captured_out = StringIO()
        captured_err = StringIO()

        if not self._config.verbose:
            sys.stdout = captured_out
            sys.stderr = captured_err

        listener_instance = listener or AirPaListener(cli_status_callback)

        try:
            result = suite.run(
                output=None,   # Don't write output.xml
                log=None,     # Don't generate log.html
                report=None,  # Don't generate report.html
                listener=listener_instance,
                stdout=captured_out,
                stderr=captured_err,
            )
        except DataError as e:
            return ExecutionResult(
                success=False,
                return_code=255,
                status="FAIL",
                message=str(e),
                robot_text="",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                return_code=255,
                status="FAIL",
                message=f"执行异常: {e}",
                robot_text="",
            )
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        # Parse results
        return_code = result.return_code if result else 1
        success = return_code == 0

        # Extract test results
        message = ""
        failed_keyword = ""
        keywords_executed = 0
        elapsed = 0.0

        if result and result.suite:
            for test in result.suite.tests:
                if test.status == "FAIL":
                    message = test.message
                    # Try to extract failed keyword name from message
                    if "Keyword" in message:
                        parts = message.split("'")
                        if len(parts) >= 2:
                            failed_keyword = parts[1]
                keywords_executed += len(list(test.body))
                elapsed += test.elapsed_time.total_seconds() if test.elapsed_time else 0

        return ExecutionResult(
            success=success,
            return_code=return_code,
            status="PASS" if success else "FAIL",
            message=message,
            failed_keyword=failed_keyword,
            elapsed_seconds=elapsed,
            keywords_executed=keywords_executed,
            log_messages=listener_instance.log_messages,
        )

    def dry_run_validate(self, suite: TestSuite) -> ExecutionResult:
        """Validate a suite using Robot Framework's dry-run mode.

        Checks: keyword names exist, argument counts match, imports resolve.
        """
        try:
            result = suite.run(
                output=None,
                log=None,
                report=None,
                dryrun=True,
                stdout=StringIO(),
                stderr=StringIO(),
            )
            success = result.return_code == 0
            message = ""
            if not success and result.suite:
                for test in result.suite.tests:
                    if test.status == "FAIL":
                        message = test.message
                        break
            return ExecutionResult(
                success=success,
                return_code=result.return_code,
                status="PASS" if success else "FAIL",
                message=message,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                return_code=255,
                status="FAIL",
                message=str(e),
            )

    def run_with_recovery(
        self, generated: GeneratedScript, generator: ScriptGenerator, task: str
    ) -> ExecutionResult:
        """Execute a script with automatic error recovery.

        If execution fails, feed the error back to AI for repair and retry.
        """
        # First, try dry-run validation
        print("[验证脚本...]", end=" ", flush=True)
        dry_result = self.dry_run_validate(generated.suite)
        if not dry_result.success:
            print("脚本验证失败，尝试自动修复")
            logger.info("Dry-run validation failed: %s", dry_result.message)
        else:
            print("通过")

        # Execute
        print("[执行中...]")
        exec_result = self.run(generated.suite)

        if exec_result.success:
            return exec_result

        # Error recovery loop
        max_retries = self._config.max_retries
        for retry in range(max_retries):
            print(f"\n[自动修复] 第 {retry + 1} 次重试...", end=" ", flush=True)
            try:
                fixed = generator.regenerate_with_error(
                    task=task,
                    original_script=generated.robot_text,
                    error_message=exec_result.message,
                    failed_keyword=exec_result.failed_keyword,
                )
                print("重新执行...")
                exec_result = self.run(fixed.suite)
                exec_result.robot_text = fixed.robot_text
                exec_result.retries_used = retry + 1
                if exec_result.success:
                    print("[自动修复成功!]")
                    return exec_result
            except Exception as e:
                logger.warning("Recovery attempt %d failed: %s", retry + 1, e)
                print(f"修复失败: {e}")

        # All retries exhausted
        exec_result.retries_used = max_retries
        return exec_result
