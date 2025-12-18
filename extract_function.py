"""
提取指定函数的完整上下文信息，用于生成单元测试或文档
"""
import sys
import io
import json
from pathlib import Path

# 设置标准输出为 UTF-8 编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def extract_function_context(analysis_dir: str, function_name: str) -> str:
    """
    从分析结果中提取指定函数的完整信息

    Args:
        analysis_dir: 分析结果目录（如 output/_imgui_draw_20251218_161024）
        function_name: 函数名

    Returns:
        格式化的函数上下文信息
    """
    analysis_path = Path(analysis_dir)

    # 读取 JSON 数据
    json_file = analysis_path / "analysis.json"
    if not json_file.exists():
        return f"错误：找不到分析结果文件 {json_file}"

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 查找函数
    function_sig = data['function_signatures'].get(function_name)
    if not function_sig:
        return f"错误：函数 '{function_name}' 不存在\n可用函数：{', '.join(list(data['function_signatures'].keys())[:10])}..."

    # 提取源文件路径和行号
    target_file = data['target_file']
    file_line = function_sig.split('//')[-1].strip()
    file_path, line_number = file_line.rsplit(':', 1)
    line_number = int(line_number)

    lines = []
    lines.append("=" * 80)
    lines.append(f"📋 函数上下文：{function_name}")
    lines.append("=" * 80)
    lines.append("")

    # 1. 函数签名
    lines.append("## 1️⃣ 函数签名")
    lines.append("")
    lines.append(f"```cpp")
    lines.append(function_sig.split('//')[0].strip())
    lines.append("```")
    lines.append("")
    lines.append(f"📍 位置：`{file_path}:{line_number}`")
    lines.append("")

    # 2. 函数实现（如果可以读取）
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_lines = f.readlines()

        # 尝试提取函数体（简单策略：从定义行开始，到下一个空行或函数定义）
        start_idx = line_number - 1
        end_idx = start_idx + 1

        # 找到函数体结束位置（简单策略：找到对应的右大括号）
        brace_count = 0
        started = False
        for i in range(start_idx, min(start_idx + 100, len(source_lines))):
            line = source_lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    started = True
                elif char == '}':
                    brace_count -= 1
                    if started and brace_count == 0:
                        end_idx = i + 1
                        break
            if started and brace_count == 0:
                break

        lines.append("## 2️⃣ 函数实现")
        lines.append("")
        lines.append("```cpp")
        for i in range(start_idx, end_idx):
            lines.append(source_lines[i].rstrip())
        lines.append("```")
        lines.append("")
    except Exception as e:
        lines.append(f"⚠️ 无法读取源文件：{e}")
        lines.append("")

    # 3. 调用关系
    call_tree = data['call_chains'].get(function_name)
    if call_tree:
        lines.append("## 3️⃣ 函数调用关系")
        lines.append("")
        lines.append("### 直接调用的函数：")
        lines.append("")

        children = call_tree.get('children', [])
        if children:
            internal_calls = [c for c in children if not c.get('is_external')]
            external_calls = [c for c in children if c.get('is_external')]

            if internal_calls:
                lines.append("**内部函数：**")
                for child in internal_calls:
                    child_name = child['function_name']
                    child_loc = f"{child['file_path']}:{child['line_number']}"
                    lines.append(f"  - `{child_name}` - {child_loc}")
                lines.append("")

            if external_calls:
                lines.append("**外部依赖：**")
                for child in external_calls:
                    child_name = child['function_name']
                    lines.append(f"  - `{child_name}` [EXTERNAL]")
                lines.append("")
        else:
            lines.append("  （无函数调用）")
            lines.append("")

        # 计算调用深度
        def get_depth(node, current=0):
            if not node.get('children'):
                return current
            return max(get_depth(c, current + 1) for c in node['children'])

        depth = get_depth(call_tree)
        lines.append(f"**调用深度：** {depth} 层")
        lines.append("")

    # 4. 相关数据结构
    lines.append("## 4️⃣ 使用的数据结构")
    lines.append("")

    # 从函数签名中提取类型
    sig_str = function_sig.split('//')[0]
    used_types = []
    for ds_name in data['data_structures'].keys():
        if ds_name in sig_str:
            used_types.append(ds_name)

    # 从调用链中提取
    if call_tree:
        def extract_types(node):
            types = []
            sig = node.get('signature', '')
            for ds_name in data['data_structures'].keys():
                if ds_name in sig and ds_name not in types:
                    types.append(ds_name)
            for child in node.get('children', []):
                types.extend(extract_types(child))
            return types

        used_types.extend(extract_types(call_tree))

    used_types = list(set(used_types))

    if used_types:
        for ds_name in used_types:
            ds_info = data['data_structures'][ds_name]
            lines.append(f"### {ds_name}")
            lines.append(f"  - 类型：{ds_info['type']}")
            lines.append(f"  - 定义：`{ds_info['file_path']}:{ds_info['line_number']}`")
            lines.append("")
    else:
        lines.append("  （未使用自定义数据结构）")
        lines.append("")

    # 5. 生成测试建议
    lines.append("## 5️⃣ 单元测试建议")
    lines.append("")
    lines.append("### 测试要点：")
    lines.append("")

    # 根据函数名和调用关系提供建议
    if "Draw" in function_name or "Add" in function_name:
        lines.append("- ✅ 测试基本绘图功能")
        lines.append("- ✅ 验证顶点和索引数据正确性")
        lines.append("- ✅ 测试边界条件（空输入、极大值）")
    elif "Push" in function_name or "Pop" in function_name:
        lines.append("- ✅ 测试栈操作的正确性")
        lines.append("- ✅ 验证多次 Push/Pop 的配对")
        lines.append("- ✅ 测试边界条件（空栈、栈溢出）")
    elif "Calc" in function_name or "Compute" in function_name:
        lines.append("- ✅ 测试计算结果的准确性")
        lines.append("- ✅ 测试边界值（0、负数、极大值）")
        lines.append("- ✅ 验证精度和舍入问题")
    else:
        lines.append("- ✅ 测试正常输入场景")
        lines.append("- ✅ 测试边界条件")
        lines.append("- ✅ 验证返回值正确性")

    lines.append("")

    if children and len(children) > 0:
        lines.append("### Mock 建议：")
        lines.append("")
        external_calls = [c for c in children if c.get('is_external')]
        if external_calls:
            lines.append("需要 Mock 的外部依赖：")
            for child in external_calls[:5]:
                lines.append(f"  - `{child['function_name']}`")
            if len(external_calls) > 5:
                lines.append(f"  - ... 还有 {len(external_calls) - 5} 个")
        lines.append("")

    lines.append("=" * 80)
    lines.append("💡 提示：将以上信息提供给 AI 工具，可生成更准确的单元测试")
    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("用法: python extract_function.py <分析结果目录> <函数名>")
        print()
        print("示例:")
        print("  python extract_function.py output/_imgui_draw_20251218_161024 PrimRect")
        print("  python extract_function.py output/_imgui_draw_20251218_161024 PushClipRect")
        sys.exit(1)

    analysis_dir = sys.argv[1]
    function_name = sys.argv[2]

    result = extract_function_context(analysis_dir, function_name)
    print(result)

    # 可选：保存到文件
    if len(sys.argv) > 3 and sys.argv[3] == "--save":
        output_file = Path(analysis_dir) / f"function_{function_name}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"\n💾 已保存到：{output_file}")


if __name__ == "__main__":
    main()
