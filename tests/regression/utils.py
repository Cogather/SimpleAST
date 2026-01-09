"""
回归测试工具函数

提供 TXT 文件对比、差异报告生成等功能。
"""
import json
import difflib
import re
from typing import Dict, Any, List, Tuple, Set
from pathlib import Path
from datetime import datetime


class ComparisonResult:
    """对比结果"""
    def __init__(self):
        self.passed = True
        self.differences = []
        self.metrics = {}
        self.file_diffs = {}  # 存储文件级别的差异

    def add_difference(self, path: str, expected: Any, actual: Any):
        """添加差异"""
        self.passed = False
        self.differences.append({
            'path': path,
            'expected': expected,
            'actual': actual
        })

    def add_metric(self, name: str, expected: Any, actual: Any):
        """添加指标对比"""
        self.metrics[name] = {
            'expected': expected,
            'actual': actual,
            'match': expected == actual
        }
        if expected != actual:
            self.passed = False

    def add_file_diff(self, filename: str, diff_lines: List[str]):
        """添加文件差异"""
        self.file_diffs[filename] = diff_lines
        if diff_lines:
            self.passed = False


def compare_json_structures(baseline: Dict[str, Any], actual: Dict[str, Any],
                            path: str = "root") -> ComparisonResult:
    """
    深度对比两个 JSON 结构

    Args:
        baseline: 基准 JSON
        actual: 实际 JSON
        path: 当前路径（用于错误报告）

    Returns:
        ComparisonResult 对象
    """
    result = ComparisonResult()

    # 对比关键指标
    _compare_metrics(baseline, actual, result)

    # 深度对比结构
    _deep_compare(baseline, actual, path, result)

    return result


def _compare_metrics(baseline: Dict[str, Any], actual: Dict[str, Any],
                     result: ComparisonResult):
    """对比关键指标"""

    # 函数数量
    baseline_funcs = baseline.get('function_signatures', {})
    actual_funcs = actual.get('function_signatures', {})
    result.add_metric('function_count', len(baseline_funcs), len(actual_funcs))

    # 调用链数量
    baseline_chains = baseline.get('call_chains', {})
    actual_chains = actual.get('call_chains', {})
    result.add_metric('call_chain_count', len(baseline_chains), len(actual_chains))

    # 数据结构数量
    baseline_structs = baseline.get('data_structures', {})
    actual_structs = actual.get('data_structures', {})
    result.add_metric('data_structure_count', len(baseline_structs), len(actual_structs))

    # 文件边界信息（如果存在）
    if 'file_boundary' in baseline and 'file_boundary' in actual:
        baseline_boundary = baseline['file_boundary']
        actual_boundary = actual['file_boundary']

        baseline_internal = baseline_boundary.get('internal_functions', [])
        actual_internal = actual_boundary.get('internal_functions', [])
        result.add_metric('internal_function_count',
                         len(baseline_internal), len(actual_internal))

        baseline_external = baseline_boundary.get('external_functions', [])
        actual_external = actual_boundary.get('external_functions', [])
        result.add_metric('external_function_count',
                         len(baseline_external), len(actual_external))


def _deep_compare(baseline: Any, actual: Any, path: str, result: ComparisonResult):
    """深度对比数据结构"""

    # 类型不匹配
    if type(baseline) != type(actual):
        result.add_difference(path, type(baseline).__name__, type(actual).__name__)
        return

    # 字典对比
    if isinstance(baseline, dict):
        # 检查键是否一致
        baseline_keys = set(baseline.keys())
        actual_keys = set(actual.keys())

        missing_keys = baseline_keys - actual_keys
        extra_keys = actual_keys - baseline_keys

        if missing_keys:
            result.add_difference(f"{path}.missing_keys", list(missing_keys), None)
        if extra_keys:
            result.add_difference(f"{path}.extra_keys", None, list(extra_keys))

        # 递归对比共同的键
        for key in baseline_keys & actual_keys:
            _deep_compare(baseline[key], actual[key], f"{path}.{key}", result)

    # 列表对比
    elif isinstance(baseline, list):
        if len(baseline) != len(actual):
            result.add_difference(f"{path}.length", len(baseline), len(actual))

        # 对比每个元素
        for i, (b_item, a_item) in enumerate(zip(baseline, actual)):
            _deep_compare(b_item, a_item, f"{path}[{i}]", result)

    # 基本类型对比
    else:
        if baseline != actual:
            result.add_difference(path, baseline, actual)


def generate_diff_report(result: ComparisonResult, test_name: str) -> str:
    """
    生成差异报告

    Args:
        result: 对比结果
        test_name: 测试名称

    Returns:
        格式化的报告文本
    """
    lines = []
    lines.append("=" * 80)
    lines.append(f"回归测试报告: {test_name}")
    lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    lines.append("")

    # 总体结果
    if result.passed:
        lines.append("✅ 测试通过 - 无差异")
    else:
        lines.append("❌ 测试失败 - 发现差异")
    lines.append("")

    # 关键指标对比
    if result.metrics:
        lines.append("## 关键指标对比")
        lines.append("")
        for metric_name, metric_data in result.metrics.items():
            status = "✅" if metric_data['match'] else "❌"
            lines.append(f"{status} {metric_name}:")
            lines.append(f"   预期: {metric_data['expected']}")
            lines.append(f"   实际: {metric_data['actual']}")
            lines.append("")

    # 详细差异
    if result.differences:
        lines.append("## 结构差异")
        lines.append("")
        for i, diff in enumerate(result.differences, 1):
            lines.append(f"{i}. 路径: {diff['path']}")
            lines.append(f"   预期: {diff['expected']}")
            lines.append(f"   实际: {diff['actual']}")
            lines.append("")

    # 文件差异
    if result.file_diffs:
        lines.append("## 文件内容差异")
        lines.append("")
        lines.append(f"发现 {len(result.file_diffs)} 个文件有差异:")
        lines.append("")

        for filename, diff_lines in result.file_diffs.items():
            lines.append(f"### {filename}")
            lines.append("")
            # 只显示前 50 行差异，避免报告过长
            max_lines = 50
            if len(diff_lines) > max_lines:
                lines.extend(diff_lines[:max_lines])
                lines.append(f"... (还有 {len(diff_lines) - max_lines} 行差异，已省略)")
            else:
                lines.extend(diff_lines)
            lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


def save_baseline(data: Dict[str, Any], baseline_path: Path):
    """
    保存基准数据

    Args:
        data: 要保存的数据
        baseline_path: 基准文件路径
    """
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    with open(baseline_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_baseline(baseline_path: Path) -> Dict[str, Any]:
    """
    加载基准数据

    Args:
        baseline_path: 基准文件路径

    Returns:
        基准数据字典
    """
    with open(baseline_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_test_fixtures(fixtures_dir: Path) -> List[Path]:
    """
    获取所有测试夹具文件

    Args:
        fixtures_dir: 夹具目录

    Returns:
        C++ 文件路径列表
    """
    return sorted(fixtures_dir.glob("*.cpp"))


def normalize_json_for_comparison(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化 JSON 数据用于对比

    移除时间戳、路径等可变字段

    Args:
        data: 原始数据

    Returns:
        标准化后的数据
    """
    import copy
    normalized = copy.deepcopy(data)

    # 移除时间戳字段
    if 'timestamp' in normalized:
        del normalized['timestamp']

    # 移除绝对路径，只保留文件名
    if 'target_file' in normalized:
        normalized['target_file'] = Path(normalized['target_file']).name

    if 'project_root' in normalized:
        normalized['project_root'] = '<project_root>'

    return normalized


def normalize_txt_content(content: str) -> str:
    """
    标准化 TXT 内容用于对比

    移除绝对路径、时间戳等可变内容

    Args:
        content: 原始文本内容

    Returns:
        标准化后的文本
    """
    lines = content.split('\n')
    normalized_lines = []

    for line in lines:
        # 移除绝对路径，只保留文件名和行号
        # 例如: // D:\work\code\...\file.cpp:123 -> // file.cpp:123
        line = re.sub(r'//\s+[A-Za-z]:[^\s]+[/\\]([^/\\]+\.(?:cpp|h)):', r'// \1:', line)
        line = re.sub(r'//\s+/[^\s]+/([^/]+\.(?:cpp|h)):', r'// \1:', line)

        # 移除 "来自:" 后的绝对路径
        line = re.sub(r'// 来自:\s+[A-Za-z]:[^\s]+[/\\]([^/\\]+\.(?:cpp|h)):', r'// 来自: \1:', line)
        line = re.sub(r'// 来自:\s+/[^\s]+/([^/]+\.(?:cpp|h)):', r'// 来自: \1:', line)

        normalized_lines.append(line)

    return '\n'.join(normalized_lines)


def compare_txt_files(baseline_dir: Path, actual_dir: Path) -> ComparisonResult:
    """
    对比两个输出目录中的 functions/ 文件夹

    Args:
        baseline_dir: 基准输出目录
        actual_dir: 实际输出目录

    Returns:
        ComparisonResult 对象
    """
    result = ComparisonResult()

    baseline_funcs_dir = baseline_dir / "functions"
    actual_funcs_dir = actual_dir / "functions"

    # 检查目录是否存在
    if not baseline_funcs_dir.exists():
        result.add_difference("functions_dir", "exists", "missing")
        return result

    if not actual_funcs_dir.exists():
        result.add_difference("functions_dir", "exists", "missing")
        return result

    # 获取所有函数文件
    baseline_files = {f.name for f in baseline_funcs_dir.glob("*.txt")}
    actual_files = {f.name for f in actual_funcs_dir.glob("*.txt")}

    # 对比文件列表
    result.add_metric('function_file_count', len(baseline_files), len(actual_files))

    missing_files = baseline_files - actual_files
    extra_files = actual_files - baseline_files

    if missing_files:
        result.add_difference('missing_files', list(missing_files), None)

    if extra_files:
        result.add_difference('extra_files', None, list(extra_files))

    # 对比共同的文件
    common_files = baseline_files & actual_files

    for filename in sorted(common_files):
        baseline_file = baseline_funcs_dir / filename
        actual_file = actual_funcs_dir / filename

        # 读取并标准化内容
        baseline_content = normalize_txt_content(baseline_file.read_text(encoding='utf-8'))
        actual_content = normalize_txt_content(actual_file.read_text(encoding='utf-8'))

        # 生成差异
        if baseline_content != actual_content:
            diff = list(difflib.unified_diff(
                baseline_content.splitlines(keepends=True),
                actual_content.splitlines(keepends=True),
                fromfile=f'baseline/{filename}',
                tofile=f'actual/{filename}',
                lineterm=''
            ))
            result.add_file_diff(filename, diff)

    return result


def compare_summary_files(baseline_dir: Path, actual_dir: Path) -> ComparisonResult:
    """
    对比 summary.txt 和 boundary.txt 文件

    Args:
        baseline_dir: 基准输出目录
        actual_dir: 实际输出目录

    Returns:
        ComparisonResult 对象
    """
    result = ComparisonResult()

    for filename in ['summary.txt', 'boundary.txt']:
        baseline_file = baseline_dir / filename
        actual_file = actual_dir / filename

        if not baseline_file.exists() or not actual_file.exists():
            continue

        baseline_content = normalize_txt_content(baseline_file.read_text(encoding='utf-8'))
        actual_content = normalize_txt_content(actual_file.read_text(encoding='utf-8'))

        if baseline_content != actual_content:
            diff = list(difflib.unified_diff(
                baseline_content.splitlines(keepends=True),
                actual_content.splitlines(keepends=True),
                fromfile=f'baseline/{filename}',
                tofile=f'actual/{filename}',
                lineterm=''
            ))
            result.add_file_diff(filename, diff)

    return result
