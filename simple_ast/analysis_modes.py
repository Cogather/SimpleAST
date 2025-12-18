"""
分析模式定义和配置
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class AnalysisMode(Enum):
    """分析模式枚举"""

    # 完整项目模式：索引整个项目，适合全局分析
    FULL_PROJECT = "full_project"

    # 单文件边界模式：深度分析单个文件的完整边界
    # - 文件内所有函数及其依赖关系
    # - 调用的外部函数（标记但不深入实现）
    # - 使用的所有数据结构（内部定义 + 外部引入）
    SINGLE_FILE_BOUNDARY = "single_file_boundary"

    # 增量模式：按需索引相关文件（未来实现）
    INCREMENTAL = "incremental"

    # 轻量模式：仅分析基本结构，不追踪调用链（未来实现）
    LIGHTWEIGHT = "lightweight"


@dataclass
class AnalysisModeConfig:
    """分析模式配置"""
    mode: AnalysisMode

    # 是否需要全局索引
    requires_full_index: bool

    # 最大追踪深度（文件内）
    max_trace_depth: int

    # 是否追踪外部函数实现
    trace_external_functions: bool

    # 是否分析数据结构
    analyze_data_structures: bool

    # 是否分析外部数据结构
    analyze_external_data_structures: bool

    # 描述
    description: str


# 预定义的模式配置
MODE_CONFIGS = {
    AnalysisMode.FULL_PROJECT: AnalysisModeConfig(
        mode=AnalysisMode.FULL_PROJECT,
        requires_full_index=True,
        max_trace_depth=10,
        trace_external_functions=True,
        analyze_data_structures=True,
        analyze_external_data_structures=True,
        description="索引整个项目，全局分析所有依赖关系"
    ),

    AnalysisMode.SINGLE_FILE_BOUNDARY: AnalysisModeConfig(
        mode=AnalysisMode.SINGLE_FILE_BOUNDARY,
        requires_full_index=False,
        max_trace_depth=100,  # 文件内函数调用可以很深
        trace_external_functions=False,  # 不追踪外部函数实现
        analyze_data_structures=True,  # 分析数据结构
        analyze_external_data_structures=True,  # 包括外部数据结构
        description="深度分析单个文件的完整边界：内部函数依赖、外部调用、所有数据结构"
    ),

    AnalysisMode.INCREMENTAL: AnalysisModeConfig(
        mode=AnalysisMode.INCREMENTAL,
        requires_full_index=False,
        max_trace_depth=10,
        trace_external_functions=True,
        analyze_data_structures=True,
        analyze_external_data_structures=True,
        description="按需索引相关文件（未来实现）"
    ),

    AnalysisMode.LIGHTWEIGHT: AnalysisModeConfig(
        mode=AnalysisMode.LIGHTWEIGHT,
        requires_full_index=False,
        max_trace_depth=0,
        trace_external_functions=False,
        analyze_data_structures=False,
        analyze_external_data_structures=False,
        description="轻量级分析，仅提取基本结构（未来实现）"
    ),
}


def get_mode_config(mode: AnalysisMode) -> AnalysisModeConfig:
    """获取模式配置"""
    return MODE_CONFIGS[mode]


def get_mode_from_string(mode_str: str) -> AnalysisMode:
    """从字符串获取模式"""
    mode_map = {
        "full": AnalysisMode.FULL_PROJECT,
        "full_project": AnalysisMode.FULL_PROJECT,
        "single": AnalysisMode.SINGLE_FILE_BOUNDARY,
        "single_file": AnalysisMode.SINGLE_FILE_BOUNDARY,
        "boundary": AnalysisMode.SINGLE_FILE_BOUNDARY,
        "deep": AnalysisMode.SINGLE_FILE_BOUNDARY,
        "incremental": AnalysisMode.INCREMENTAL,
        "light": AnalysisMode.LIGHTWEIGHT,
        "lightweight": AnalysisMode.LIGHTWEIGHT,
    }

    mode_str_lower = mode_str.lower()
    if mode_str_lower not in mode_map:
        raise ValueError(
            f"Unknown mode: {mode_str}. Available modes: {', '.join(mode_map.keys())}"
        )

    return mode_map[mode_str_lower]
