"""
函数签名提取器 - 从头文件中搜索外部函数的签名

原位置：AnalysisResult._search_function_signature()
"""
import re
import sys
from typing import Optional
from ..searchers import HeaderSearcher


class SignatureExtractor:
    """函数签名提取器"""

    def __init__(self, header_searcher: Optional[HeaderSearcher] = None):
        self.header_searcher = header_searcher or HeaderSearcher()

    def extract(self, func_name: str, target_file: str) -> Optional[str]:
        """
        搜索外部函数的签名（在头文件中）

        Args:
            func_name: 函数名
            target_file: 目标文件路径

        Returns:
            函数签名，未找到返回 None
        """
        possible_headers = self.header_searcher.find_headers(target_file)

        for header_file in possible_headers:
            try:
                with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 搜索函数声明（支持多行）
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if func_name in line and '(' in line:
                        # 可能是函数声明
                        declaration = line.strip()

                        # 如果没有分号且没有花括号，可能跨行
                        if ';' not in declaration and '{' not in declaration and i + 1 < len(lines):
                            for next_line in lines[i+1:i+5]:
                                declaration += ' ' + next_line.strip()
                                if ';' in next_line or '{' in next_line:
                                    break

                        # 清理
                        declaration = declaration.split(';')[0].strip()
                        declaration = declaration.split('{')[0].strip()

                        # 验证是否真的是目标函数
                        if re.search(rf'\b{re.escape(func_name)}\s*\(', declaration):
                            return declaration

            except Exception:
                continue

        return None
