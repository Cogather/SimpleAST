"""
SimpleAST - C++ Static Code Analyzer

A Python-based static analysis tool for C++ projects that works without compilation.
"""

__version__ = "1.1.0"
__author__ = "SimpleAST Team"

from .cpp_analyzer import CppProjectAnalyzer, AnalysisResult
from .analysis_modes import AnalysisMode, get_mode_from_string

__all__ = [
    "CppProjectAnalyzer",
    "AnalysisResult",
    "AnalysisMode",
    "get_mode_from_string",
]
