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
        print("用法: python analyze.py <项目根目录> <目标CPP文件> [模式] [追踪深度] [函数名]")
        print()
        print("参数说明:")
        print("  项目根目录  - C++项目的根目录")
        print("  目标CPP文件 - 要分析的.cpp文件（相对或绝对路径）")
        print("  模式        - 可选，分析模式（默认: single）")
        print("  追踪深度    - 可选，函数调用链追踪深度（默认: 根据模式）")
        print("  函数名      - 可选，只分析指定的函数（默认分析文件中所有函数）")
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
        print("  # 单文件分析，指定追踪深度和函数")
        print("  python analyze.py . main.cpp single 50 MyFunction")
        print()
        print("  # 完整项目模式分析")
        print("  python analyze.py ./project src/main.cpp full 15")
        sys.exit(1)

    project_root = sys.argv[1]
    target_file = sys.argv[2]

    # 解析参数：模式、追踪深度、函数名
    # 需要智能判断第3个参数是模式还是数字
    mode_str = "single"  # 默认单文件模式
    trace_depth = None
    target_function = None

    if len(sys.argv) > 3:
        # 第3个参数：可能是模式或追踪深度
        try:
            trace_depth = int(sys.argv[3])
            # 如果成功转换为数字，说明是追踪深度，使用默认模式
        except ValueError:
            # 不是数字，当作模式处理
            mode_str = sys.argv[3]

    if len(sys.argv) > 4:
        # 第4个参数：可能是追踪深度或函数名
        try:
            if trace_depth is None:
                trace_depth = int(sys.argv[4])
            else:
                # 已经有trace_depth了，这是函数名
                target_function = sys.argv[4]
        except ValueError:
            # 不是数字，当作函数名
            target_function = sys.argv[4]

    if len(sys.argv) > 5:
        # 第5个参数：函数名
        target_function = sys.argv[5]

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

        # 创建 output 目录
        log("步骤 3/4: 生成输出文件...")
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # 生成文件名
        project_name = Path(project_root).name
        file_name = Path(target_file).stem  # 不带扩展名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 检查是否需要分层输出（单文件边界模式且函数数量 > 50）
        use_structured_output = False
        if mode.value == "single_file_boundary" and result.file_boundary:
            func_count = len(result.file_boundary.internal_functions)
            if func_count > 50:
                use_structured_output = True
                log(f"  检测到大型文件（{func_count} 个函数），使用分层输出模式")

        if use_structured_output:
            # 分层输出模式
            base_name = f"{project_name}_{file_name}_{timestamp}"
            structured_dir = output_dir / base_name
            structured_dir.mkdir(exist_ok=True)

            # 1. 生成摘要报告
            summary_file = structured_dir / "summary.txt"
            log(f"  - 写入摘要报告: {summary_file}")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(result.generate_summary_report())

            # 2. 生成边界分析
            boundary_file = structured_dir / "boundary.txt"
            log(f"  - 写入边界分析: {boundary_file}")
            with open(boundary_file, 'w', encoding='utf-8') as f:
                f.write(result.generate_boundary_report())

            # 3. 生成按模块分类的函数报告
            functions_dir = structured_dir / "functions"
            functions_dir.mkdir(exist_ok=True)

            modules = result.classify_functions_by_module()
            for module, functions in modules.items():
                module_file = functions_dir / f"{module}.txt"
                log(f"  - 写入模块函数: {module_file}")
                with open(module_file, 'w', encoding='utf-8') as f:
                    f.write(result.generate_functions_by_module_report(module, functions))

            # 4. 生成调用链报告
            call_chains_file = structured_dir / "call_chains.txt"
            log(f"  - 写入调用链: {call_chains_file}")
            with open(call_chains_file, 'w', encoding='utf-8') as f:
                f.write(result.generate_call_chains_report())

            # 5. 生成数据结构报告
            data_structures_file = structured_dir / "data_structures.txt"
            log(f"  - 写入数据结构: {data_structures_file}")
            with open(data_structures_file, 'w', encoding='utf-8') as f:
                f.write(result.generate_data_structures_report())

            # 6. JSON 输出
            json_file = structured_dir / "analysis.json"
            log(f"  - 写入JSON数据: {json_file}")
            with open(json_file, 'w', encoding='utf-8') as f:
                f.write(result.to_json())

            log("✓ 输出文件生成完成")
            log("")
            log("=" * 80)
            log("✅ 分析完成!")
            log(f"📁 输出目录: {structured_dir}")
            log(f"📊 摘要报告: {summary_file}")
            log(f"📋 边界分析: {boundary_file}")
            log(f"📁 函数详情: {functions_dir}/")
            log(f"📝 执行日志: {log_filename}")
            log("=" * 80)

        else:
            # 传统单文件输出模式
            txt_file = output_dir / f"{project_name}_{file_name}_{timestamp}.txt"
            json_file = output_dir / f"{project_name}_{file_name}_{timestamp}.json"

            # 保存文本报告
            log(f"  - 写入文本报告: {txt_file}")
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(result.format_report())

            # 保存 JSON
            log(f"  - 写入JSON数据: {json_file}")
            with open(json_file, 'w', encoding='utf-8') as f:
                f.write(result.to_json())

            log("✓ 输出文件生成完成")
            log("")
            log("=" * 80)
            log("✅ 分析完成!")
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
