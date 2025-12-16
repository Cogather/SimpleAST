"""
C++ 代码分析工具 - 直接输出结果（带日志）
"""
import sys
import io
import os
from pathlib import Path
from datetime import datetime
from cpp_analyzer import CppProjectAnalyzer

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
        print("用法: python analyze.py <项目根目录> <目标CPP文件> [追踪深度] [函数名]")
        print()
        print("参数说明:")
        print("  项目根目录  - C++项目的根目录")
        print("  目标CPP文件 - 要分析的.cpp文件（相对或绝对路径）")
        print("  追踪深度    - 可选，函数调用链追踪深度（默认10）")
        print("  函数名      - 可选，只分析指定的函数（默认分析文件中所有函数）")
        print()
        print("示例:")
        print("  # 分析整个文件")
        print("  python analyze.py ./example_project ./example_project/src/main.cpp")
        print()
        print("  # 分析整个文件，追踪深度15")
        print("  python analyze.py D:\\my_project src\\main.cpp 15")
        print()
        print("  # 只分析指定函数")
        print("  python analyze.py ./project main.cpp 10 MyFunction")
        sys.exit(1)

    project_root = sys.argv[1]
    target_file = sys.argv[2]
    trace_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    target_function = sys.argv[4] if len(sys.argv) > 4 else None

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
    log(f"追踪深度: {trace_depth}")
    if target_function:
        log(f"目标函数: {target_function}")
    else:
        log(f"分析范围: 文件中所有函数")
    log("")

    try:
        # 创建分析器
        log("步骤 1/4: 初始化分析器...")
        analyzer = CppProjectAnalyzer(project_root)
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

        # 输出文件路径
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
