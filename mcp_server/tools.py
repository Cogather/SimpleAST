"""
MCP 工具实现

定义 SimpleAST 提供的 MCP 工具
"""
import asyncio
from pathlib import Path
from typing import Dict, Any

from simple_ast import CppProjectAnalyzer, AnalysisMode
from .utils import extract_function_test_context


async def get_function_test_context(
    project_root: str,
    target_file: str,
    function_name: str,
    trace_depth: int = 50
) -> Dict[str, Any]:
    """
    获取 C++ 函数的完整测试上下文

    分析指定 C++ 函数，返回生成单元测试所需的所有信息，包括：
    - 函数源代码
    - Mock 清单（需要 Mock 的外部函数）
    - 内部依赖函数的实现
    - 相关数据结构定义
    - 调用链和复杂度分析

    Args:
        project_root: C++ 项目根目录的绝对路径
        target_file: 目标文件相对于项目根目录的路径（如 "src/main.cpp"）
        function_name: 要分析的函数名
        trace_depth: 调用链追踪深度（默认 50）

    Returns:
        包含完整测试上下文的字典，包括函数签名、源代码、Mock清单、
        内部依赖、数据结构、调用链等信息
    """
    try:
        # 验证路径
        project_path = Path(project_root)
        if not project_path.exists():
            return {
                "error": f"项目目录不存在: {project_root}",
                "error_type": "PathNotFound"
            }

        target_path = project_path / target_file
        if not target_path.exists():
            return {
                "error": f"目标文件不存在: {target_file}",
                "error_type": "FileNotFound"
            }

        # 路径遍历防护
        if ".." in target_file or target_file.startswith("/"):
            return {
                "error": f"非法的文件路径: {target_file}",
                "error_type": "InvalidPath"
            }

        # 在线程池中执行同步分析
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _sync_analyze,
            project_root,
            target_file,
            function_name,
            trace_depth
        )

        return result

    except Exception as e:
        return {
            "error": f"分析失败: {str(e)}",
            "error_type": type(e).__name__
        }


def _sync_analyze(
    project_root: str,
    target_file: str,
    function_name: str,
    trace_depth: int
) -> Dict[str, Any]:
    """
    同步执行分析（在线程池中运行）

    Args:
        project_root: 项目根目录
        target_file: 目标文件
        function_name: 函数名
        trace_depth: 追踪深度

    Returns:
        分析结果字典
    """
    # 创建分析器（使用单文件边界模式）
    analyzer = CppProjectAnalyzer(
        project_root,
        mode=AnalysisMode.SINGLE_FILE_BOUNDARY
    )

    # 分析文件
    result = analyzer.analyze_file(
        target_file,
        trace_depth=trace_depth,
        target_function=function_name
    )

    # 转换为 MCP 友好的格式
    context = extract_function_test_context(result, function_name)

    return context
