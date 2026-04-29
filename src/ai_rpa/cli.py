"""CLI entry point for AI-RPA."""

from __future__ import annotations

import argparse
import sys

from ai_rpa import __version__


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="airpa",
        description="AI-RPA: AI驱动的傻瓜式RPA自动化系统",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("task", nargs="?", help="要执行的自动化任务描述")
    parser.add_argument("--dry-run", action="store_true", help="只生成脚本不执行")
    parser.add_argument("--api-key", help="OpenAI API Key")
    parser.add_argument("--model", help="AI模型 (默认: gpt-4o)")
    parser.add_argument("--base-url", help="OpenAI API Base URL (用于代理)")
    parser.add_argument("--max-retries", type=int, help="错误修复最大重试次数")
    parser.add_argument("--libs", help="额外库，逗号分隔 (如: SeleniumLibrary,RPA.Excel.Files)")
    parser.add_argument("--verbose", action="store_true", help="显示详细输出")
    parser.add_argument("--refresh-registry", action="store_true", help="强制刷新关键字注册表缓存")
    return parser


def main(argv=None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    # Import here to avoid slow startup for --help / --version
    from ai_rpa.config import AirPaConfig

    overrides = {}
    if args.api_key:
        overrides["openai_api_key"] = args.api_key
    if args.model:
        overrides["openai_model"] = args.model
    if args.base_url:
        overrides["openai_base_url"] = args.base_url
    if args.max_retries is not None:
        overrides["max_retries"] = args.max_retries
    if args.verbose:
        overrides["verbose"] = True
    if args.dry_run:
        overrides["dry_run"] = True
    if args.libs:
        overrides["extra_libraries"] = [l.strip() for l in args.libs.split(",")]

    config = AirPaConfig.load(**overrides)

    if not config.openai_api_key:
        print("错误: 未设置 OpenAI API Key")
        print("  设置环境变量: export AIRPA_OPENAI_API_KEY=sk-xxx")
        print("  或使用参数:    airpa --api-key sk-xxx ...")
        print("  或配置文件:    创建 .airpa.toml 并写入 openai_api_key = \"sk-xxx\"")
        return 1

    if args.task:
        return run_one_shot(args.task, config, args.refresh_registry)
    else:
        return run_interactive(config, args.refresh_registry)


def run_one_shot(task: str, config, refresh_registry: bool = False) -> int:
    """Execute a single task description."""
    from ai_rpa.registry.keyword_registry import KeywordRegistry
    from ai_rpa.engine.script_generator import ScriptGenerator
    from ai_rpa.executor.suite_runner import SuiteRunner
    from ai_rpa.executor.result_parser import parse_result

    # 1. Build keyword registry
    registry = KeywordRegistry()
    registry.load(config, refresh=refresh_registry)

    # 2. Generate script
    generator = ScriptGenerator(config, registry)
    result = generator.generate(task)

    if config.dry_run:
        print("\n生成的脚本:")
        print("=" * 50)
        print(result.robot_text)
        print("=" * 50)
        print(f"\n说明: {result.explanation}")
        print("(dry-run 模式，未执行)")
        return 0

    print(f"\n说明: {result.explanation}")
    print(f"需要的库: {', '.join(result.libraries_needed)}")
    print()

    # 3. Execute with error recovery
    runner = SuiteRunner(config)
    exec_result = runner.run_with_recovery(result, generator, task)

    # 4. Display results
    summary = parse_result(exec_result)
    if summary.success:
        print(f"\n结果: 通过 ({summary.keywords_executed}个步骤, {summary.elapsed_seconds:.1f}秒)")
    else:
        print(f"\n结果: 失败 - {summary.message}")
        if config.verbose and exec_result.robot_text:
            print("\n执行的脚本:")
            print(exec_result.robot_text)

    return 0 if summary.success else 1


def run_interactive(config, refresh_registry: bool = False) -> int:
    """Interactive REPL mode."""
    from ai_rpa.registry.keyword_registry import KeywordRegistry

    print(f"AI-RPA v{__version__} | Model: {config.openai_model}")
    print("输入你的自动化任务，输入 quit 退出\n")

    # Pre-load registry
    registry = KeywordRegistry()
    registry.load(config, refresh=refresh_registry)

    while True:
        try:
            task = input("airpa> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if not task:
            continue
        if task.lower() in ("quit", "exit", "q"):
            print("再见!")
            break

        # Run the task
        from ai_rpa.config import AirPaConfig

        task_config = AirPaConfig.load(
            openai_api_key=config.openai_api_key,
            openai_model=config.openai_model,
            openai_base_url=config.openai_base_url,
            max_retries=config.max_retries,
            registry_cache_path=config.registry_cache_path,
            extra_libraries=config.extra_libraries,
            language=config.language,
            verbose=config.verbose,
            dry_run=False,
        )

        run_one_shot(task, task_config)

    return 0
