"""
回归测试主文件

运行方式:
    # 首次运行，生成基准
    python tests/regression/test_regression.py --update-baseline

    # 后续运行，对比差异
    python tests/regression/test_regression.py

    # 运行特定测试
    python tests/regression/test_regression.py --test simple_call_chain
"""
import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from simple_ast import CppProjectAnalyzer, AnalysisMode
from tests.regression.utils import (
    compare_txt_files,
    compare_summary_files,
    generate_diff_report,
    get_test_fixtures
)


# 测试配置
FIXTURES_DIR = Path(__file__).parent / "fixtures"
BASELINES_DIR = Path(__file__).parent / "baselines"
REPORTS_DIR = Path(__file__).parent / "reports"
TEMP_OUTPUT_DIR = Path(__file__).parent / "temp_output"


def run_analysis(cpp_file: Path, output_dir: Path) -> Path:
    """
    运行分析并返回输出目录

    Args:
        cpp_file: C++ 文件路径
        output_dir: 输出根目录

    Returns:
        实际输出目录路径
    """
    # 创建分析器
    analyzer = CppProjectAnalyzer(str(FIXTURES_DIR), mode=AnalysisMode.SINGLE_FILE_BOUNDARY)

    # 运行分析
    result = analyzer.analyze_file(str(cpp_file), trace_depth=50)

    # 生成输出
    test_name = cpp_file.stem
    result_dir = output_dir / test_name
    result_dir.mkdir(parents=True, exist_ok=True)

    # 生成 summary.txt
    summary_file = result_dir / "summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(result.generate_simple_summary_report())

    # 生成 boundary.txt
    boundary_file = result_dir / "boundary.txt"
    with open(boundary_file, 'w', encoding='utf-8') as f:
        f.write(result.generate_boundary_report())

    # 生成 functions/ 目录
    functions_dir = result_dir / "functions"
    functions_dir.mkdir(exist_ok=True)

    # 获取所有函数
    if result.file_boundary:
        all_functions = sorted(result.file_boundary.internal_functions)
    else:
        all_functions = sorted(result.function_signatures.keys())

    # 生成每个函数的文件
    for func_name in all_functions:
        func_file = functions_dir / f"{func_name}.txt"
        report = result.generate_single_function_report(func_name)
        with open(func_file, 'w', encoding='utf-8') as f:
            f.write(report)

    return result_dir


def run_regression_test(cpp_file: Path, update_baseline: bool = False) -> bool:
    """
    运行单个回归测试

    Args:
        cpp_file: C++ 测试文件
        update_baseline: 是否更新基准

    Returns:
        测试是否通过
    """
    test_name = cpp_file.stem
    baseline_dir = BASELINES_DIR / test_name

    print(f"\n{'='*80}")
    print(f"测试: {test_name}")
    print(f"文件: {cpp_file}")
    print(f"{'='*80}")

    # 运行分析
    print("运行分析...")
    actual_dir = run_analysis(cpp_file, TEMP_OUTPUT_DIR)
    print(f"✓ 分析完成: {actual_dir}")

    # 更新基准模式
    if update_baseline:
        print(f"更新基准: {baseline_dir}")
        if baseline_dir.exists():
            shutil.rmtree(baseline_dir)
        shutil.copytree(actual_dir, baseline_dir)
        print("✅ 基准已更新")
        return True

    # 对比模式
    if not baseline_dir.exists():
        print(f"❌ 基准目录不存在: {baseline_dir}")
        print(f"请先运行: python {__file__} --update-baseline")
        return False

    print("对比差异...")

    # 对比 functions/ 目录
    func_result = compare_txt_files(baseline_dir, actual_dir)

    # 对比 summary 和 boundary 文件
    summary_result = compare_summary_files(baseline_dir, actual_dir)

    # 合并结果
    combined_result = func_result
    for filename, diff in summary_result.file_diffs.items():
        combined_result.add_file_diff(filename, diff)
    for metric_name, metric_data in summary_result.metrics.items():
        combined_result.add_metric(metric_name, metric_data['expected'], metric_data['actual'])

    # 生成报告
    report = generate_diff_report(combined_result, test_name)

    # 保存报告
    REPORTS_DIR.mkdir(exist_ok=True)
    report_file = REPORTS_DIR / f"{test_name}_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n报告已保存: {report_file}")
    print("\n" + report)

    if combined_result.passed:
        print("✅ 测试通过")
        return True
    else:
        print("❌ 测试失败")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='SimpleAST 回归测试')
    parser.add_argument('--update-baseline', action='store_true',
                       help='更新基准数据（首次运行或功能改进后使用）')
    parser.add_argument('--test', type=str,
                       help='只运行指定的测试（测试名称，不含 .cpp 扩展名）')
    args = parser.parse_args()

    # 确保目录存在
    FIXTURES_DIR.mkdir(exist_ok=True)
    BASELINES_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
    TEMP_OUTPUT_DIR.mkdir(exist_ok=True)

    # 获取测试文件
    all_fixtures = get_test_fixtures(FIXTURES_DIR)

    if not all_fixtures:
        print(f"❌ 没有找到测试文件: {FIXTURES_DIR}")
        print("请在 fixtures/ 目录中添加 .cpp 测试文件")
        return 1

    # 过滤测试
    if args.test:
        all_fixtures = [f for f in all_fixtures if f.stem == args.test]
        if not all_fixtures:
            print(f"❌ 找不到测试: {args.test}")
            return 1

    print(f"\n找到 {len(all_fixtures)} 个测试用例")
    print("=" * 80)

    # 运行测试
    passed = 0
    failed = 0

    for cpp_file in all_fixtures:
        try:
            if run_regression_test(cpp_file, args.update_baseline):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    # 清理临时目录
    if TEMP_OUTPUT_DIR.exists():
        shutil.rmtree(TEMP_OUTPUT_DIR)

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"总计: {passed + failed}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print("=" * 80)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
