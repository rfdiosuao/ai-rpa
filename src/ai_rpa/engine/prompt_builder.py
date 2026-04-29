"""Build AI prompts with keyword context for two-stage generation."""

from __future__ import annotations

from ai_rpa.registry.keyword_registry import KeywordRegistry

# --- Stage 1: Intent Classification ---

INTENT_CLASSIFICATION_SYSTEM = """你是一个RPA任务分类器。根据用户的任务描述，判断需要哪些操作类别。

可用类别:
- file: 文件/目录操作 (创建、复制、移动、删除、读写)
- browser: 浏览器自动化 (打开网页、点击、输入、截图)
- excel: Excel操作 (读取、写入、创建工作簿)
- email: 邮件操作 (发送、读取、搜索)
- string: 字符串处理和验证
- datetime: 日期和时间操作
- collection: 列表/字典操作
- process: 运行外部进程/命令
- xml: XML解析和操作
- system: 系统级操作 (环境变量、路径)
- pdf: PDF操作
- image: 图片操作 (截图)
- network: 网络请求 (HTTP API)
- database: 数据库操作
- desktop: 桌面应用操作

请用JSON回复:
{
  "categories": ["类别1", "类别2"],
  "task_summary": "用英文简述任务内容",
  "requires_browser": true/false,
  "requires_external_lib": true/false,
  "external_libs_needed": ["SeleniumLibrary", "RPA.Excel.Files"]
}"""

# --- Stage 2: Script Generation ---

SCRIPT_GENERATION_SYSTEM = """你是一个Robot Framework RPA脚本生成专家。

你需要生成一个合法的Robot Framework .robot文件来完成用户的任务。

可用关键字（格式: 库名: 关键字名(参数) - 说明）:
{keyword_context}

规则:
1. 只使用上面列出的关键字，不要编造关键字
2. 必须包含 *** Settings *** 部分来导入需要的库
3. 使用 *** Test Cases *** 部分，创建一个名为 "RPA Task" 的测试用例
4. 使用Robot Framework变量语法: ${{variable_name}}
5. 使用 ${{EMPTY}} 表示空字符串
6. 对于浏览器自动化，始终在teardown中关闭浏览器
7. 生成简洁、聚焦的脚本

请用JSON回复:
{{
  "script": "完整的.robot文件内容",
  "libraries_needed": ["需要的库列表"],
  "explanation": "简要说明脚本做了什么"
}}"""

# --- Stage 3: Error Recovery ---

ERROR_RECOVERY_SYSTEM = """你是一个Robot Framework脚本修复专家。

你之前生成的脚本执行失败了，请根据错误信息修复脚本。

可用关键字（格式: 库名: 关键字名(参数) - 说明）:
{keyword_context}

原始脚本:
{original_script}

执行错误:
- 测试: {test_name}
- 失败关键字: {failed_keyword}
- 错误消息: {error_message}
- 错误类型: {error_type}

常见修复方式:
- 关键字名称错误: 使用上面列表中的精确关键字名
- 参数数量错误: 检查关键字的参数规格
- 缺少库导入: 在Settings中添加所需的Library导入
- 变量引用错误: 确保变量已正确定义
- 浏览器元素未找到: 添加Wait Until关键字等待元素

请用JSON回复修正后的脚本:
{{
  "script": "修正后的完整.robot文件内容",
  "libraries_needed": ["需要的库列表"],
  "explanation": "简要说明做了什么修改"
}}"""


def build_classification_prompt(task: str) -> tuple[str, str]:
    """Build prompts for Stage 1: intent classification."""
    return INTENT_CLASSIFICATION_SYSTEM, task


def build_generation_prompt(task: str, keyword_context: str) -> tuple[str, str]:
    """Build prompts for Stage 2: script generation."""
    system = SCRIPT_GENERATION_SYSTEM.format(keyword_context=keyword_context)
    return system, task


def build_recovery_prompt(
    keyword_context: str,
    original_script: str,
    test_name: str,
    failed_keyword: str,
    error_message: str,
    error_type: str = "RuntimeError",
) -> tuple[str, str]:
    """Build prompts for Stage 3: error recovery."""
    system = ERROR_RECOVERY_SYSTEM.format(
        keyword_context=keyword_context,
        original_script=original_script,
        test_name=test_name,
        failed_keyword=failed_keyword,
        error_message=error_message,
        error_type=error_type,
    )
    # User message for recovery is just "请修复脚本"
    return system, "请修复上面的脚本"
