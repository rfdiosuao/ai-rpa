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

    sub = parser.add_subparsers(dest="command")
    pat = sub.add_parser("patterns", help="查看已积累的自动化模式")
    pat.add_argument("--detail", action="store_true", help="显示脚本详情")
    pat.add_argument("--delete", metavar="ID", help="删除指定模式")

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

    # Handle subcommands
    if args.command == "patterns":
        return cmd_patterns(args)

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


def cmd_patterns(args) -> int:
    """Handle `airpa patterns` subcommand."""
    from ai_rpa.pattern_store import PatternStore

    store = PatternStore()

    # Delete pattern
    if args.delete:
        if store.delete(args.delete):
            print(f"已删除模式: {args.delete}")
        else:
            print(f"未找到模式: {args.delete}")
        return 0

    patterns = store.list_all()

    if not patterns:
        print("还没有积累任何自动化模式。")
        print("使用 airpa 执行任务后，成功的脚本会自动保存为模式。")
        return 0

    print(f"已积累 {len(patterns)} 个自动化模式:\n")
    print(f"{'ID':<12} {'成功次数':<8} {'可靠度':<8} {'任务描述':<40}")
    print("-" * 72)
    for p in patterns:
        desc = p.task_description[:38] + ".." if len(p.task_description) > 40 else p.task_description
        print(f"{p.id:<12} {p.success_count:<8} {p.reliability:.0%}     {desc}")

        if args.detail:
            print(f"  分类: {', '.join(p.categories)}")
            print(f"  说明: {p.explanation}")
            print(f"  库:   {', '.join(p.libraries_needed)}")
            print(f"  脚本:")
            for line in p.robot_text.splitlines():
                print(f"    {line}")
            print()

    return 0


def run_one_shot(task: str, config, refresh_registry: bool = False) -> int:
    """Execute a single task description."""
    from ai_rpa.registry.keyword_registry import KeywordRegistry
    from ai_rpa.engine.script_generator import ScriptGenerator
    from ai_rpa.executor.suite_runner import SuiteRunner
    from ai_rpa.executor.result_parser import parse_result
    from ai_rpa.pattern_store import PatternStore

    # 1. Build keyword registry
    registry = KeywordRegistry()
    registry.load(config, refresh=refresh_registry)

    # 2. Generate script (with pattern store)
    pattern_store = PatternStore()
    generator = ScriptGenerator(config, registry, pattern_store)
    result = generator.generate(task)

    if config.dry_run:
        source = "[模式复用]" if result.from_pattern else "[AI生成]"
        print(f"\n{source} 生成的脚本:")
        print("=" * 50)
        print(result.robot_text)
        print("=" * 50)
        print(f"\n说明: {result.explanation}")
        if result.from_pattern:
            print(f"模式ID: {result.pattern_id}")
        print("(dry-run 模式，未执行)")
        return 0

    source = "模式复用" if result.from_pattern else "AI生成"
    print(f"\n来源: {source} | 说明: {result.explanation}")
    if result.libraries_needed:
        print(f"需要的库: {', '.join(result.libraries_needed)}")
    print()

    # 3. Execute with error recovery
    runner = SuiteRunner(config)
    exec_result = runner.run_with_recovery(result, generator, task)

    # 4. Display results
    summary = parse_result(exec_result)
    if summary.success:
        # Save successful pattern (if not already from pattern store)
        if not result.from_pattern:
            pid = generator.save_pattern(task, result)
            print(f"\n结果: 通过 ({summary.keywords_executed}个步骤, {summary.elapsed_seconds:.1f}秒)")
            print(f"[模式积累] 已保存为可复用模式 (id: {pid})")
        else:
            print(f"\n结果: 通过 ({summary.keywords_executed}个步骤, {summary.elapsed_seconds:.1f}秒)")
            print(f"[模式复用] 来自历史模式 (id: {result.pattern_id})")
    else:
        # Record failure on pattern if it was reused
        if result.from_pattern and result.pattern_id:
            pattern_store.record_failure(result.pattern_id)
        print(f"\n结果: 失败 - {summary.message}")
        if config.verbose and exec_result.robot_text:
            print("\n执行的脚本:")
            print(exec_result.robot_text)

    return 0 if summary.success else 1


def run_interactive(config, refresh_registry: bool = False) -> int:
    """Interactive REPL mode."""
    from ai_rpa.registry.keyword_registry import KeywordRegistry
    from ai_rpa.pattern_store import PatternStore

    pattern_store = PatternStore()
    print(f"AI-RPA v{__version__} | Model: {config.openai_model} | 模式库: {pattern_store.count()}个")
    print("输入你的自动化任务，输入 quit 退出，输入 patterns 查看模式库\n")

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
        if task.lower() == "patterns":
            # Inline pattern listing
            patterns = pattern_store.list_all()
            if not patterns:
                print("模式库为空。执行任务后成功的脚本会自动积累。\n")
                continue
            print(f"已积累 {len(patterns)} 个模式:\n")
            for p in patterns[:10]:
                desc = p.task_description[:40]
                print(f"  {p.id}  {p.success_count}次成功  {desc}")
            print()
            continue

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
