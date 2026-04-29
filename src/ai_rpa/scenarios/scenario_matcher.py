"""Match natural language intent to scenario categories."""

from __future__ import annotations

# Keywords in natural language that map to categories
CATEGORY_PATTERNS = {
    "browser": [
        "浏览器", "网页", "打开网页", "网站", "点击按钮", "输入文字",
        "截图", "网页截图", "页面", "url", "html",
        "selenium", "chrome", "firefox", "browser",
        "open browser", "click", "navigate", "网页操作",
    ],
    "excel": [
        "excel", "表格", "工作簿", "工作表", "单元格", "xlsx", "xls",
        "电子表格", "读取表格", "写入表格", "数据表",
    ],
    "email": [
        "邮件", "发送邮件", "收邮件", "email", "smtp", "imap",
        "附件", "邮箱", "抄送",
    ],
    "pdf": [
        "pdf", "读取pdf", "生成pdf", "pdf文件",
    ],
    "file": [
        "文件", "创建文件", "读取文件", "写入文件", "删除文件",
        "复制文件", "移动文件", "目录", "文件夹",
        "file", "directory", "folder", "path",
    ],
    "string": [
        "字符串", "替换", "分割", "拼接", "正则",
        "string", "replace", "split", "concat",
    ],
    "datetime": [
        "日期", "时间", "当前时间", "格式化日期",
        "date", "time", "datetime", "timestamp",
    ],
    "process": [
        "进程", "命令", "执行命令", "运行程序", "脚本执行",
        "process", "command", "shell", "cmd",
    ],
    "xml": [
        "xml", "解析xml", "xml文件",
    ],
    "system": [
        "环境变量", "系统", "系统信息", "环境",
        "environment", "system", "env",
    ],
    "network": [
        "http", "请求", "api", "接口", "url请求",
        "request", "rest", "get", "post",
    ],
    "database": [
        "数据库", "sql", "查询", "mysql", "postgres",
        "database", "db", "query",
    ],
    "desktop": [
        "桌面", "窗口", "鼠标", "键盘", "自动化操作桌面",
        "desktop", "window", "mouse", "keyboard",
    ],
}


def match_categories(task: str) -> list[str]:
    """Match a task description to likely scenario categories.

    This is a lightweight fallback when AI classification is unavailable.
    Returns a list of matching category names.
    """
    task_lower = task.lower()
    scores: dict[str, int] = {}

    for category, patterns in CATEGORY_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if pattern in task_lower:
                score += 1
        if score > 0:
            scores[category] = score

    # Sort by score descending
    sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Return top categories (at least 1, at most 3)
    if not sorted_categories:
        return ["general"]
    return [cat for cat, _ in sorted_categories[:3]]
