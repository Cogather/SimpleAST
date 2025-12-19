"""
常量提取器 - 从函数中提取常量和宏定义

原位置：AnalysisResult._extract_constants_from_function()
"""
import re
import sys
from pathlib import Path
from typing import Dict, Set, Optional
from ..searchers import HeaderSearcher


class ConstantExtractor:
    """常量提取器 - 简单实用"""

    def __init__(self, header_searcher: Optional[HeaderSearcher] = None):
        self.header_searcher = header_searcher or HeaderSearcher()

    def extract(self, func_name: str, function_signatures: Dict[str, str],
                branch_analyses: Dict, target_file: str) -> Dict[str, str]:
        """
        从函数中提取使用的常量和宏定义

        Args:
            func_name: 函数名
            function_signatures: 函数签名字典
            branch_analyses: 分支分析结果
            target_file: 目标文件路径

        Returns:
            常量定义字典 {name: definition}
        """
        if func_name not in function_signatures:
            print(f"[常量提取] 警告: 函数 {func_name} 不在签名列表中", file=sys.stderr)
            return {}

        print(f"\n[常量提取] 开始分析函数: {func_name}", file=sys.stderr)

        # 收集标识符
        identifiers = self._collect_identifiers(func_name, function_signatures, branch_analyses)

        if not identifiers:
            print(f"[常量提取] 没有提取到任何标识符", file=sys.stderr)
            return {}

        print(f"[常量提取] 总共提取到 {len(identifiers)} 个唯一标识符", file=sys.stderr)

        # 搜索定义
        constants = self._search_definitions(identifiers, target_file)

        # 统计结果
        found_count = len(constants)
        not_found = identifiers - set(constants.keys())
        print(f"[常量提取] 完成: 找到 {found_count}/{len(identifiers)} 个定义", file=sys.stderr)
        if not_found and len(not_found) <= 10:
            print(f"[常量提取] 未找到: {sorted(not_found)}", file=sys.stderr)

        return constants

    def _collect_identifiers(self, func_name: str, function_signatures: Dict[str, str],
                            branch_analyses: Dict) -> Set[str]:
        """收集标识符（从签名、分支条件、case值）"""
        identifiers = set()

        # 1. 从函数签名提取
        sig = function_signatures[func_name]
        upper_identifiers = re.findall(r'\b[A-Z][A-Z0-9_]+\b', sig)
        identifiers.update(upper_identifiers)
        print(f"[常量提取] 从签名提取到 {len(upper_identifiers)} 个大写标识符: {upper_identifiers[:10]}", file=sys.stderr)

        # 2. 从分支条件提取
        if branch_analyses and func_name in branch_analyses:
            branch_analysis = branch_analyses[func_name]
            print(f"[常量提取] 找到分支分析，共 {len(branch_analysis.conditions)} 个条件", file=sys.stderr)

            for idx, condition in enumerate(branch_analysis.conditions):
                # 从条件本身提取
                upper_ids = re.findall(r'\b[A-Z][A-Z0-9_]+\b', condition.condition)
                identifiers.update(upper_ids)
                print(f"[常量提取]   条件{idx+1} [{condition.branch_type}]: 提取 {len(upper_ids)} 个标识符", file=sys.stderr)

                # 从 switch 的 suggestions 中提取 case 值
                if condition.branch_type == 'switch' and condition.suggestions:
                    for sug in condition.suggestions:
                        if sug.startswith('case值:'):
                            case_values_str = sug.replace('case值:', '').strip()
                            case_values = [v.strip() for v in case_values_str.split(',')]
                            print(f"[常量提取]   switch找到 {len(case_values)} 个case值: {case_values}", file=sys.stderr)
                            for case_val in case_values:
                                if '...' in case_val:
                                    break
                                if case_val != 'default':
                                    identifiers.add(case_val)

        return identifiers

    def _search_definitions(self, identifiers: Set[str], target_file: str) -> Dict[str, str]:
        """在头文件中搜索定义"""
        constants = {}
        possible_headers = self.header_searcher.find_headers(target_file)

        print(f"[常量提取] 准备搜索 {len(possible_headers)} 个文件", file=sys.stderr)
        for h in possible_headers[:10]:
            print(f"[常量提取]   - {h.name}", file=sys.stderr)
        if len(possible_headers) > 10:
            print(f"[常量提取]   ... 还有 {len(possible_headers) - 10} 个文件", file=sys.stderr)

        # 搜索定义
        for identifier in identifiers:
            for header_file in possible_headers:
                try:
                    with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            # 搜索 #define 或 enum
                            if re.search(rf'^\s*#define\s+{re.escape(identifier)}\b', line):
                                constants[identifier] = line.strip()
                                print(f"[常量提取] ✓ 在 {header_file.name} 找到 #define {identifier}", file=sys.stderr)
                                break
                            elif re.search(rf'^\s*{re.escape(identifier)}\s*=', line):
                                # enum 成员
                                constants[identifier] = line.strip()
                                print(f"[常量提取] ✓ 在 {header_file.name} 找到 enum {identifier}", file=sys.stderr)
                                break

                    if identifier in constants:
                        break

                except Exception as e:
                    print(f"[常量提取] ✗ 读取 {header_file.name} 失败: {e}", file=sys.stderr)
                    continue

        return constants
