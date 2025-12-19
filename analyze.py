"""
C++ 代码分析工具 - 直接输出结果（带日志）
"""
import sys
import io
import os
from pathlib import Path
from datetime import datetime
from simple_ast import CppProjectAnalyzer, AnalysisMode, get_mode_from_string
from simple_ast.analysis_modes import get_mode_config

# 设置标准输出为 UTF-8 编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 日志文件
log_file = None

def log(message):
    """同时输出到控制台和日志文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    if log_file:
        log_file.write(log_msg + "\n")
        log_file.flush()


def main():
    global log_file

    if len(sys.argv) < 3:
        print("用法: python analyze.py <项目根目录> <目标CPP文件> [模式] [追踪深度] [函数名] [--output <输出目录>]")
        print()
        print("参数说明:")
        print("  项目根目录  - C++项目的根目录")
        print("  目标CPP文件 - 要分析的.cpp文件（相对或绝对路径）")
        print("  模式        - 可选，分析模式（默认: single）")
        print("  追踪深度    - 可选，函数调用链追踪深度（默认: 根据模式）")
        print("  函数名      - 可选，只分析指定的函数（默认分析文件中所有函数）")
        print("  --output    - 可选，输出目录（默认: ./output）")
        print()
        print("可用模式:")
        print("  single / boundary  - 单文件边界模式：快速分析单个文件，外部调用标记但不深入")
        print("  full               - 完整项目模式：索引整个项目，全局分析（较慢）")
        print()
        print("示例:")
        print("  # 单文件边界分析（推荐，快速）")
        print("  python analyze.py . main.cpp")
        print("  python analyze.py . main.cpp single")
        print()
        print("  # 指定输出目录")
        print("  python analyze.py . main.cpp --output /path/to/output")
        print("  python analyze.py . main.cpp single 50 --output ./results")
        print()
        print("  # 单文件分析，指定追踪深度和函数")
        print("  python analyze.py . main.cpp single 50 MyFunction")
        print()
        print("  # 完整项目模式分析")
        print("  python analyze.py ./project src/main.cpp full 15")
        sys.exit(1)

    project_root = sys.argv[1]
    target_file = sys.argv[2]

    # 解析参数：模式、追踪深度、函数名、输出目录
    mode_str = "single"  # 默认单文件模式
    trace_depth = None
    target_function = None
    output_dir_str = "output"  # 默认输出目录

    # 处理 --output 参数
    args = sys.argv[3:]
    if "--output" in args:
        output_idx = args.index("--output")
        if output_idx + 1 < len(args):
            output_dir_str = args[output_idx + 1]
            # 移除 --output 及其值
            args = args[:output_idx] + args[output_idx + 2:]
        else:
            print("错误：--output 需要指定目录路径")
            sys.exit(1)

    # 处理其他参数
    if len(args) > 0:
        # 第1个参数：可能是模式或追踪深度
        try:
            trace_depth = int(args[0])
        except ValueError:
            mode_str = args[0]

    if len(args) > 1:
        # 第2个参数：可能是追踪深度或函数名
        try:
            if trace_depth is None:
                trace_depth = int(args[1])
            else:
                target_function = args[1]
        except ValueError:
            target_function = args[1]

    if len(args) > 2:
        # 第3个参数：函数名
        target_function = args[2]

    # 解析模式
    try:
        mode = get_mode_from_string(mode_str)
        mode_config = get_mode_config(mode)
    except ValueError as e:
        print(f"错误: {e}")
        sys.exit(1)

    # 如果没有指定追踪深度，使用模式默认值
    if trace_depth is None:
        trace_depth = mode_config.max_trace_depth

    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 创建日志文件
    log_filename = log_dir / f"analyze_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_file = open(log_filename, 'w', encoding='utf-8')

    # 配置 simple_ast 库的日志也使用同一个文件
    import simple_ast.logger as logger_module
    lib_logger = logger_module.setup_logger(name="simple_ast", log_file_path=str(log_filename))
    # 设置为全局默认logger，确保所有 get_logger() 调用都使用这个配置
    logger_module._default_logger = lib_logger

    log(f"日志文件: {log_filename}")
    log("=" * 80)

    # 验证路径
    if not os.path.exists(project_root):
        log(f"错误：项目目录不存在: {project_root}")
        sys.exit(1)

    # 规范化文件路径
    target_path = Path(target_file)
    if not target_path.is_absolute():
        full_path = Path(project_root) / target_file
    else:
        full_path = target_path

    if not full_path.exists():
        log(f"错误：文件不存在: {full_path}")
        sys.exit(1)

    log(f"项目根目录: {project_root}")
    log(f"目标文件: {target_file}")
    log(f"分析模式: {mode.value} - {mode_config.description}")
    log(f"追踪深度: {trace_depth}")
    if target_function:
        log(f"目标函数: {target_function}")
    else:
        log(f"分析范围: 文件中所有函数")
    log("")

    try:
        # 创建分析器（根据模式）
        log("步骤 1/4: 初始化分析器...")
        analyzer = CppProjectAnalyzer(project_root, mode=mode)
        log("✓ 分析器初始化完成")
        log("")

        # 分析文件
        log("步骤 2/4: 开始分析目标文件...")
        result = analyzer.analyze_file(str(target_file), trace_depth=trace_depth, target_function=target_function)
        log("✓ 文件分析完成")
        log("")

        # 创建输出目录
        log("步骤 3/4: 生成输出文件...")
        output_dir = Path(output_dir_str)
        output_dir.mkdir(parents=True, exist_ok=True)
        log(f"  输出目录: {output_dir.resolve()}")

        # 生成文件名
        project_name = Path(project_root).name
        file_name = Path(target_file).stem  # 不带扩展名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 统一创建输出目录
        base_name = f"_{file_name}_{timestamp}"
        result_dir = output_dir / base_name
        result_dir.mkdir(exist_ok=True)
        log(f"  输出目录: {result_dir.resolve()}")

        # 统一使用分层输出（无论函数数量多少）
        use_structured_output = False
        if mode.value == "single_file_boundary" and result.file_boundary:
            func_count = len(result.file_boundary.internal_functions)
            use_structured_output = True
            log(f"  使用分层输出模式（共 {func_count} 个函数）")

        if use_structured_output:
            # 分层输出模式
            # 1. 生成摘要报告（无分类信息）
            summary_file = result_dir / "summary.txt"
            log(f"  - 写入摘要报告: {summary_file}")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(result.generate_simple_summary_report())

            # 2. 生成边界分析
            boundary_file = result_dir / "boundary.txt"
            log(f"  - 写入边界分析: {boundary_file}")
            with open(boundary_file, 'w', encoding='utf-8') as f:
                f.write(result.generate_boundary_report())

            # 3. 生成每个函数的独立文件
            functions_dir = result_dir / "functions"
            functions_dir.mkdir(exist_ok=True)

            # 如果指定了目标函数，只生成目标函数及其依赖的文件
            if target_function:
                # 从调用链中收集所有相关函数
                all_functions = set()
                if target_function in result.call_chains:
                    all_functions.add(target_function)
                    # 递归收集内部依赖
                    def collect_internal_funcs(node):
                        if node and not node.is_external:
                            all_functions.add(node.function_name)
                            for child in node.children:
                                collect_internal_funcs(child)
                    collect_internal_funcs(result.call_chains[target_function])
                all_functions = sorted(all_functions)
                log(f"  - 生成 {len(all_functions)} 个函数文件（目标函数及依赖）到: {functions_dir}/")
            else:
                # 生成所有函数的文件
                all_functions = sorted(result.file_boundary.internal_functions) if result.file_boundary else sorted(result.function_signatures.keys())
                log(f"  - 生成 {len(all_functions)} 个函数文件到: {functions_dir}/")

            for idx, func_name in enumerate(all_functions, 1):
                func_file = functions_dir / f"{func_name}.txt"
                print(f"\n[文件输出] 生成函数报告 ({idx}/{len(all_functions)}): {func_name}", file=sys.stderr)
                report = result.generate_single_function_report(func_name)
                with open(func_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"[文件输出] ✓ 写入文件: {func_file.name} ({len(report)} 字符)", file=sys.stderr)

            # 4. 生成调用链和数据结构报告（仅在多函数时）
            # 注意：单函数分析时，functions/ 已包含所有信息，无需额外文件
            if len(all_functions) > 1:
                call_chains_file = result_dir / "call_chains.txt"
                log(f"  - 写入调用链: {call_chains_file}")
                with open(call_chains_file, 'w', encoding='utf-8') as f:
                    f.write(result.generate_call_chains_report())

                data_structures_file = result_dir / "data_structures.txt"
                log(f"  - 写入数据结构: {data_structures_file}")
                with open(data_structures_file, 'w', encoding='utf-8') as f:
                    f.write(result.generate_data_structures_report())

            # 6. JSON 输出
            json_file = result_dir / "analysis.json"
            log(f"  - 写入JSON数据: {json_file}")
            with open(json_file, 'w', encoding='utf-8') as f:
                f.write(result.to_json())

            log("✓ 输出文件生成完成")
            log("")
            log("=" * 80)
            log("✅ 分析完成!")
            log(f"📁 输出目录: {result_dir}")
            log(f"📊 摘要报告: {summary_file}")
            log(f"📋 边界分析: {boundary_file}")
            log(f"📁 函数文件: {functions_dir}/ ({len(all_functions)} 个)")
            log(f"📝 执行日志: {log_filename}")
            log("=" * 80)

        else:
            # 小文件输出模式 - 也使用目录结构
            # 保存文本报告
            txt_file = result_dir / "analysis.txt"
            log(f"  - 写入文本报告: {txt_file}")
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(result.format_report())

            # 保存 JSON
            json_file = result_dir / "analysis.json"
            log(f"  - 写入JSON数据: {json_file}")
            with open(json_file, 'w', encoding='utf-8') as f:
                f.write(result.to_json())

            log("✓ 输出文件生成完成")
            log("")
            log("=" * 80)
            log("✅ 分析完成!")
            log(f"📁 输出目录: {result_dir}")
            log(f"📄 文本报告: {txt_file}")
            log(f"📊 JSON数据: {json_file}")
            log(f"📝 执行日志: {log_filename}")
            log("=" * 80)

        if log_file:
            log_file.close()

    except Exception as e:
        log(f"❌ 分析失败: {e}")
        import traceback
        error_trace = traceback.format_exc()
        log(error_trace)
        if log_file:
            log_file.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
