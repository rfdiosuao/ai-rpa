"""Parse Robot Framework execution results into user-friendly summaries."""

from __future__ import annotations

from ai_rpa.executor.suite_runner import ExecutionResult


def parse_result(exec_result: ExecutionResult) -> ExecutionResult:
    """Parse and return the execution result as-is (already structured).

    This function exists for future enhancement: extracting more details,
    formatting messages in Chinese, generating human-readable summaries, etc.
    """
    # Clean up error messages for display
    if exec_result.message and not exec_result.success:
        # Truncate very long error messages
        msg = exec_result.message
        if len(msg) > 200:
            msg = msg[:200] + "..."
        exec_result.message = msg

    return exec_result
