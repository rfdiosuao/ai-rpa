"""Real-time execution listener for AI-RPA."""

from __future__ import annotations

from typing import Callable, Optional


class AirPaListener:
    """ListenerV2 implementation that reports keyword-level execution status.

    Reports events via a callback for real-time CLI feedback.
    """

    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, callback: Optional[Callable[[str, dict], None]] = None):
        self._callback = callback
        self._keyword_stack: list[str] = []
        self._log_messages: list[str] = []
        self._current_test: str = ""

    def start_suite(self, name, attrs):
        self._notify("suite_start", {"suite": name})

    def end_suite(self, name, attrs):
        self._notify("suite_end", {"suite": name, "stats": attrs.get("statistics", "")})

    def start_test(self, name, attrs):
        self._current_test = name
        self._notify("test_start", {"test": name})

    def end_test(self, name, attrs):
        self._notify("test_end", {
            "test": name,
            "status": attrs.get("status", "UNKNOWN"),
            "message": attrs.get("message", ""),
        })

    def start_keyword(self, name, attrs):
        kw_name = attrs.get("kwname", name)
        self._keyword_stack.append(kw_name)
        self._notify("keyword_start", {
            "keyword": kw_name,
            "args": attrs.get("args", []),
        })

    def end_keyword(self, name, attrs):
        kw_name = self._keyword_stack.pop() if self._keyword_stack else name
        status = attrs.get("status", "UNKNOWN")
        self._notify("keyword_end", {
            "keyword": kw_name,
            "status": status,
        })

    def log_message(self, message):
        msg_text = message.get("message", "") if isinstance(message, dict) else str(message)
        self._log_messages.append(msg_text)
        self._notify("log_message", {"message": msg_text})

    def message(self, message):
        pass  # Ignore console messages

    def close(self):
        self._notify("close", {})

    def _notify(self, event_type: str, data: dict):
        if self._callback:
            self._callback(event_type, data)

    @property
    def log_messages(self) -> list[str]:
        return self._log_messages


# Default CLI callback for printing execution status
def cli_status_callback(event_type: str, data: dict):
    """Print execution status to terminal with rich formatting."""
    if event_type == "keyword_end":
        status = data.get("status", "")
        keyword = data.get("keyword", "")
        if status == "PASS":
            print(f"  ✓ {keyword}")
        elif status == "FAIL":
            print(f"  ✗ {keyword}")
        else:
            print(f"  · {keyword} ({status})")
    elif event_type == "test_end":
        status = data.get("status", "")
        if status == "PASS":
            pass  # Will be summarized at the end
        else:
            message = data.get("message", "")
            print(f"  错误: {message}")
