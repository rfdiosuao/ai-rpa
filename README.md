# AI-RPA

AI驱动的傻瓜式RPA自动化系统，基于 Robot Framework。

只需用自然语言描述你想做的自动化任务，AI 自动生成脚本并执行。出错自动修复。

## 特性

- **自然语言驱动** — 用中文或英文描述任务，AI 自动理解意图
- **自动生成脚本** — 基于 Robot Framework 的 .robot 脚本，自动选择正确的关键字
- **自动修复** — 执行失败时自动将错误反哺 AI，修复后重试
- **多场景支持** — 文件操作、浏览器自动化、Excel/PDF/邮件等办公自动化
- **关键字注册表** — 自动扫描内置库关键字，外部库未安装时提供降级支持

## 安装

```bash
pip install -e .
```

## 配置

设置 OpenAI API Key（三选一）：

```bash
# 方式1: 环境变量
export AIRPA_OPENAI_API_KEY=sk-xxx

# 方式2: 配置文件 (.airpa.toml)
openai_api_key = "sk-xxx"

# 方式3: 命令行参数
airpa --api-key sk-xxx "你的任务"
```

## 使用

```bash
# 一次性模式
airpa "创建一个文件test.txt并写入Hello World"

# 交互式 REPL
airpa

# 只生成脚本不执行
airpa --dry-run "打开百度搜索今天的新闻并截图"

# 指定额外库
airpa --libs SeleniumLibrary "打开网页并截图"

# 自定义重试次数
airpa --max-retries 5 "读取Excel文件中的数据"

# 切换AI模型
airpa --model gpt-4o-mini "创建目录结构"
```

## 交互式示例

```
$ airpa
AI-RPA v0.1.0 | Model: gpt-4o
输入你的自动化任务，输入 quit 退出

airpa> 创建一个文件/tmp/test.txt并写入Hello AI-RPA

[分析意图...] → file
[加载关键字...] → 来自相关库的 56 个关键字
[生成脚本...] 完成
[验证脚本...] 通过
[执行中...]
  ✓ Create File
  ✓ File Should Exist
  ✓ Remove File

结果: 通过 (3个步骤, 0.1秒)
```

## 架构

```
用户自然语言
    ↓
[意图分类] ← AI Phase 1: 识别操作类别 (file/browser/excel/email/...)
    ↓
[关键字筛选] ← 从注册表筛选相关关键字 (40-80个，非全部500+)
    ↓
[脚本生成] ← AI Phase 2: 生成 .robot 脚本
    ↓
[语法验证] ← TestSuite.from_string()
    ↓
[执行] ← suite.run() + ListenerV2 实时监控
    ↓
  成功 → 返回结果
  失败 → [自动修复] → 错误反哺AI → 重新生成 → 重试 (最多3次)
```

## 关键字支持

### 内置库（开箱即用）

| 库 | 关键字数 | 用途 |
|----|---------|------|
| BuiltIn | 107 | 通用断言、变量、流程控制 |
| OperatingSystem | 56 | 文件/目录/环境变量 |
| Collections | 43 | 列表/字典操作 |
| String | 32 | 字符串处理 |
| XML | 37 | XML解析 |
| Process | 15 | 进程执行 |
| DateTime | 8 | 日期时间 |
| Screenshot | 3 | 截图 |

### 外部库（需 pip 安装，或使用降级关键字）

| 库 | 安装命令 |
|----|---------|
| SeleniumLibrary | `pip install robotframework-seleniumlibrary` |
| RPA.Excel.Files | `pip install rpaframework` |
| RPA.PDF | `pip install rpaframework` |
| RPA.Email.ImapSmtp | `pip install rpaframework` |

## 开发

```bash
# 安装开发模式
pip install -e .

# 测试关键字注册表
python -c "
from ai_rpa.registry.keyword_registry import KeywordRegistry
from ai_rpa.config import AirPaConfig
registry = KeywordRegistry()
registry.load(AirPaConfig.load(openai_api_key='test'))
print(f'{len(registry._keywords)} keywords loaded')
"
```

## License

Apache License 2.0
