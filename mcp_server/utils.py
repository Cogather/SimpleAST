"""
结果转换工具

将 SimpleAST 的 AnalysisResult 转换为 MCP 友好的 JSON 格式
"""
from typing import Dict, List, Any, Optional
from pathlib import Path


def extract_function_test_context(result, function_name: str) -> Dict[str, Any]:
    """
    从 AnalysisResult 提取函数的完整测试上下文

    Args:
        result: AnalysisResult 对象
        function_name: 要提取的函数名

    Returns:
        包含测试上下文的字典
    """
    # 检查函数是否存在
    if function_name not in result.call_chains:
        return {
            "error": f"函数 '{function_name}' 未找到",
            "available_functions": list(result.function_signatures.keys())[:20]
        }

    # 提取基本信息
    context = {
        "function_name": function_name,
        "signature": _get_signature(result, function_name),
        "location": _get_location(result, function_name),
        "source_code": _get_source_code(result, function_name),
    }

    # 提取统计信息
    context["statistics"] = _get_statistics(result, function_name)

    # 提取复杂度信息
    context["complexity"] = _get_complexity(result, function_name)

    # 提取 Mock 清单
    context["mock_list"] = _get_mock_list(result, function_name)

    # 提取内部依赖
    context["internal_dependencies"] = _get_internal_dependencies(result, function_name)

    # 提取数据结构
    context["data_structures"] = _get_data_structures(result, function_name)

    # 提取调用链
    context["call_chain"] = _get_call_chain(result, function_name)

    return context


def _get_signature(result, function_name: str) -> str:
    """获取函数签名"""
    sig = result.function_signatures.get(function_name, "")
    # 签名格式: "signature // file_path:line_number"
    if '//' in sig:
        return sig.split('//')[0].strip()
    return sig


def _get_location(result, function_name: str) -> str:
    """获取函数位置"""
    sig = result.function_signatures.get(function_name, "")
    if '//' in sig:
        return sig.split('//')[-1].strip()
    return ""


def _get_source_code(result, function_name: str) -> str:
    """获取函数源代码"""
    # 从 file_boundary.file_functions 中获取
    if result.file_boundary and result.file_boundary.file_functions:
        if function_name in result.file_boundary.file_functions:
            func_info = result.file_boundary.file_functions[function_name]
            if 'source_code' in func_info:
                return func_info['source_code']

    return ""


def _get_statistics(result, function_name: str) -> Dict[str, int]:
    """获取统计信息"""
    stats = {
        "internal_functions": 0,
        "external_functions": 0,
        "data_structures": 0
    }

    # 统计内部和外部函数
    if function_name in result.call_chains:
        call_node = result.call_chains[function_name]
        internal_funcs = set()
        external_funcs = set()

        def collect_functions(node):
            if node:
                for child in node.children:
                    if child.is_external:
                        external_funcs.add(child.function_name)
                    else:
                        internal_funcs.add(child.function_name)
                    collect_functions(child)

        collect_functions(call_node)
        stats["internal_functions"] = len(internal_funcs)
        stats["external_functions"] = len(external_funcs)

    # 统计数据结构
    # 从 file_boundary 或全局数据结构中统计
    if result.file_boundary and hasattr(result.file_boundary, 'file_data_structures'):
        # 简单统计：使用文件中定义的数据结构数量
        stats["data_structures"] = len(result.file_boundary.file_data_structures)
    elif result.data_structures:
        stats["data_structures"] = len(result.data_structures)

    return stats


def _get_complexity(result, function_name: str) -> Dict[str, Any]:
    """获取复杂度信息"""
    complexity = {
        "cyclomatic": 0,
        "description": "未知"
    }

    # 从 branch_analyses 中获取
    if hasattr(result, 'branch_analyses') and result.branch_analyses and function_name in result.branch_analyses:
        branch_analysis = result.branch_analyses[function_name]

        # 获取圈复杂度
        if hasattr(branch_analysis, 'cyclomatic_complexity'):
            complexity["cyclomatic"] = branch_analysis.cyclomatic_complexity
        elif hasattr(branch_analysis, 'complexity'):
            complexity["cyclomatic"] = branch_analysis.complexity

        # 根据圈复杂度给出描述
        cc = complexity["cyclomatic"]
        if cc <= 5:
            complexity["description"] = "简单"
        elif cc <= 10:
            complexity["description"] = "中等复杂度"
        elif cc <= 20:
            complexity["description"] = "较复杂"
        else:
            complexity["description"] = "非常复杂"

        # 添加分支统计信息
        if hasattr(branch_analysis, 'if_count'):
            complexity["branches"] = {
                "if_else": branch_analysis.if_count if hasattr(branch_analysis, 'if_count') else 0,
                "switch": branch_analysis.switch_count if hasattr(branch_analysis, 'switch_count') else 0,
                "loops": branch_analysis.loop_count if hasattr(branch_analysis, 'loop_count') else 0
            }

    return complexity


def _get_mock_list(result, function_name: str) -> List[str]:
    """获取 Mock 清单（外部函数列表）"""
    mock_list = []

    if function_name in result.call_chains:
        call_node = result.call_chains[function_name]
        external_funcs = set()

        def collect_external(node):
            if node:
                for child in node.children:
                    if child.is_external:
                        external_funcs.add(child.function_name)
                    collect_external(child)

        collect_external(call_node)
        mock_list = sorted(external_funcs)

    return mock_list


def _get_internal_dependencies(result, function_name: str) -> List[Dict[str, str]]:
    """获取内部依赖函数列表"""
    dependencies = []

    if function_name in result.call_chains:
        call_node = result.call_chains[function_name]
        internal_funcs = set()

        def collect_internal(node):
            if node:
                for child in node.children:
                    if not child.is_external:
                        internal_funcs.add(child.function_name)
                    collect_internal(child)

        collect_internal(call_node)

        # 为每个内部函数提取详细信息
        for func_name in sorted(internal_funcs):
            dep = {
                "name": func_name,
                "signature": _get_signature(result, func_name),
                "location": _get_location(result, func_name),
                "source_code": _get_source_code(result, func_name)
            }
            dependencies.append(dep)

    return dependencies


def _get_data_structures(result, function_name: str) -> List[Dict[str, str]]:
    """获取数据结构列表"""
    structures = []

    # 从 file_boundary 获取函数使用的数据结构
    if result.file_boundary and hasattr(result.file_boundary, 'file_data_structures'):
        # 获取函数使用的数据结构名称列表
        func_data_structures = set()

        # 从调用链中收集数据结构
        if function_name in result.call_chains:
            call_node = result.call_chains[function_name]

            def collect_structures(node):
                if node and hasattr(node, 'data_structures'):
                    func_data_structures.update(node.data_structures)
                if node:
                    for child in node.children:
                        collect_structures(child)

            collect_structures(call_node)

        # 提取数据结构详细信息
        for struct_name in func_data_structures:
            if struct_name in result.file_boundary.file_data_structures:
                struct_info = result.file_boundary.file_data_structures[struct_name]
                structures.append({
                    "name": struct_name,
                    "type": struct_info.get("type", "unknown"),
                    "definition": struct_info.get("definition", ""),
                    "location": f"{result.target_file}:{struct_info.get('line', 0)}"
                })
            elif struct_name in result.data_structures:
                # 从全局数据结构中获取
                ds_info = result.data_structures[struct_name]
                structures.append({
                    "name": struct_name,
                    "type": ds_info.type if hasattr(ds_info, 'type') else "unknown",
                    "definition": ds_info.definition if hasattr(ds_info, 'definition') else "",
                    "location": ds_info.location if hasattr(ds_info, 'location') else ""
                })

    return structures


def _get_call_chain(result, function_name: str) -> str:
    """获取调用链的文本表示"""
    if function_name not in result.call_chains:
        return ""

    call_node = result.call_chains[function_name]
    lines = []

    def format_node(node, indent=0):
        if node:
            prefix = "  " * indent
            marker = "[外部]" if node.is_external else ""
            lines.append(f"{prefix}├─ {node.function_name} {marker}")
            for child in node.children:
                format_node(child, indent + 1)

    format_node(call_node)
    return "\n".join(lines)
