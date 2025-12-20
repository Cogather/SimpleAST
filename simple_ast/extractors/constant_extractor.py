"""
常量提取器 - 从函数中提取常量和宏定义

原位置：AnalysisResult._extract_constants_from_function()
"""
import re
import sys
from pathlib import Path
from typing import Dict, Set, Optional
from ..searchers import HeaderSearcher, GrepSearcher
from ..logger import get_logger
logger = get_logger()



class ConstantExtractor:
    """常量提取器 - 简单实用"""

    def __init__(self, header_searcher: Optional[HeaderSearcher] = None,
                 project_root: Optional[str] = None, file_boundary=None):
        self.header_searcher = header_searcher or HeaderSearcher()
        self.project_root = project_root
        self.grep_searcher = GrepSearcher(project_root) if project_root else None
        self.file_boundary = file_boundary  # 用于复用已解析的AST

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
            logger.info(f"[常量提取] 警告: 函数 {func_name} 不在签名列表中")
            return {}

        logger.info(f"\n[常量提取] 开始分析函数: {func_name}")

        # 收集标识符
        identifiers = self._collect_identifiers(func_name, function_signatures, branch_analyses, target_file)

        if not identifiers:
            logger.info(f"[常量提取] 没有提取到任何标识符")
            return {}

        logger.info(f"[常量提取] 总共提取到 {len(identifiers)} 个唯一标识符")

        # 搜索定义
        constants = self._search_definitions(identifiers, target_file)

        # 统计结果
        found_count = len(constants)
        not_found = identifiers - set(constants.keys())
        logger.info(f"[常量提取] 完成: 找到 {found_count}/{len(identifiers)} 个定义")
        if not_found and len(not_found) <= 10:
            logger.info(f"[常量提取] 未找到: {sorted(not_found)}")

        return constants

    def _collect_identifiers(self, func_name: str, function_signatures: Dict[str, str],
                            branch_analyses: Dict, target_file: str) -> Set[str]:
        """收集标识符（从签名、分支条件、case值、函数体）"""
        identifiers = set()

        # 1. 从函数签名提取
        sig = function_signatures[func_name]
        upper_identifiers = re.findall(r'\b[A-Z][A-Z0-9_]+\b', sig)
        identifiers.update(upper_identifiers)
        logger.info(f"[常量提取] 从签名提取到 {len(upper_identifiers)} 个大写标识符")

        # 2. 从分支条件提取
        if branch_analyses and func_name in branch_analyses:
            branch_analysis = branch_analyses[func_name]
            logger.info(f"[常量提取] 找到分支分析，共 {len(branch_analysis.conditions)} 个条件")

            for idx, condition in enumerate(branch_analysis.conditions):
                # 从条件本身提取
                upper_ids = re.findall(r'\b[A-Z][A-Z0-9_]+\b', condition.condition)
                identifiers.update(upper_ids)

                # 从 switch 的 suggestions 中提取 case 值
                if condition.branch_type == 'switch' and condition.suggestions:
                    for sug in condition.suggestions:
                        if sug.startswith('case值:'):
                            case_values_str = sug.replace('case值:', '').strip()
                            case_values = [v.strip() for v in case_values_str.split(',')]
                            for case_val in case_values:
                                if '...' in case_val:
                                    break
                                if case_val != 'default':
                                    identifiers.add(case_val)

        # 3. 从函数体中提取（新增）
        body_identifiers = self._extract_from_function_body(target_file, func_name)
        if body_identifiers:
            identifiers.update(body_identifiers)
            logger.info(f"[常量提取] 从函数体提取到 {len(body_identifiers)} 个标识符")

        return identifiers

    def _extract_from_function_body(self, target_file: str, func_name: str) -> Set[str]:
        """
        从函数体中提取大写标识符（宏和常量）

        Returns:
            Set[str]: 大写标识符集合
        """
        identifiers = set()

        try:
            # 优先使用 file_boundary 中已解析的函数信息（避免重复解析大文件）
            if self.file_boundary and hasattr(self.file_boundary, 'file_functions'):
                if func_name in self.file_boundary.file_functions:
                    func_info = self.file_boundary.file_functions[func_name]
                    func_node = func_info.get('node')
                    source_code = self.file_boundary.source_code

                    if func_node and source_code:
                        logger.debug(f"[常量提取-函数体] ✓ 使用已解析的函数节点: {func_name}")

                        # 从函数体中提取所有标识符
                        from ..cpp_parser import CppParser
                        func_text = CppParser.get_node_text(func_node, source_code)
                        # 只提取全大写的标识符（可能是宏或常量）
                        upper_ids = re.findall(r'\b[A-Z][A-Z0-9_]+\b', func_text)
                        identifiers.update(upper_ids)

                        logger.debug(f"[常量提取-函数体] ✓ 从函数体提取到 {len(upper_ids)} 个大写标识符")
                        return identifiers
                    else:
                        logger.warning(f"[常量提取-函数体] file_boundary中缺少函数节点或源代码")
                else:
                    logger.warning(f"[常量提取-函数体] file_boundary中未找到函数: {func_name}")

            # 降级方案：重新读取和解析文件（大文件可能失败）
            logger.debug(f"[常量提取-函数体] 降级到重新解析文件模式")

            # 读取源文件
            from pathlib import Path
            if self.project_root:
                file_path = Path(self.project_root) / target_file
            else:
                file_path = Path(target_file)

            logger.debug(f"[常量提取-函数体] 尝试读取文件: {file_path}")

            if not file_path.exists():
                logger.warning(f"[常量提取-函数体] 文件不存在: {file_path}")
                logger.warning(f"[常量提取-函数体] project_root={self.project_root}, target_file={target_file}")
                return identifiers

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            logger.debug(f"[常量提取-函数体] 文件读取成功，大小: {len(content)} 字符")

            # 使用tree-sitter解析
            from ..cpp_parser import CppParser
            parser = CppParser()
            tree = parser.parse_file(str(file_path))

            if not tree:
                logger.warning(f"[常量提取-函数体] tree-sitter解析失败: {file_path}")
                return identifiers

            logger.debug(f"[常量提取-函数体] tree-sitter解析成功")

            # 查找目标函数
            func_defs = CppParser.find_nodes_by_type(tree.root_node, 'function_definition')
            logger.debug(f"[常量提取-函数体] 文件中共有 {len(func_defs)} 个函数")

            target_func = None

            for func_def in func_defs:
                name = CppParser.get_function_name(func_def, content.encode())
                if name == func_name:
                    target_func = func_def
                    logger.debug(f"[常量提取-函数体] ✓ 找到目标函数: {func_name}")
                    break

            if not target_func:
                logger.warning(f"[常量提取-函数体] 未找到目标函数: {func_name}")
                logger.warning(f"[常量提取-函数体] 文件中的函数: {[CppParser.get_function_name(f, content.encode()) for f in func_defs[:5]]}")
                return identifiers

            # 从函数体中提取所有标识符
            func_text = CppParser.get_node_text(target_func, content.encode())
            # 只提取全大写的标识符（可能是宏或常量）
            upper_ids = re.findall(r'\b[A-Z][A-Z0-9_]+\b', func_text)
            identifiers.update(upper_ids)

            logger.debug(f"[常量提取-函数体] ✓ 从函数体提取到 {len(upper_ids)} 个大写标识符")

        except Exception as e:
            logger.error(f"[常量提取-函数体] 提取失败: {e}")
            import traceback
            logger.error(f"[常量提取-函数体] 堆栈: {traceback.format_exc()}")

        return identifiers

    def _search_definitions(self, identifiers: Set[str], target_file: str) -> Dict[str, str]:
        """在头文件中搜索定义 - 使用全局搜索"""
        constants = {}

        # 优先使用 GrepSearcher 进行全局搜索
        if self.grep_searcher:
            logger.info(f"[常量提取] 使用 GrepSearcher 进行全局搜索")
            return self._search_with_grep(identifiers)

        # 降级到原有的 HeaderSearcher 方法
        logger.info(f"[常量提取] 使用 HeaderSearcher 进行局部搜索（降级）")
        return self._search_with_header_searcher(identifiers, target_file)

    def _search_with_grep(self, identifiers: Set[str]) -> Dict[str, str]:
        """使用 GrepSearcher 全局搜索常量定义"""
        constants = {}

        for identifier in identifiers:
            # 搜索 #define
            define_pattern = rf'^\s*#define\s+{re.escape(identifier)}\b'
            results = self.grep_searcher.search_content(
                pattern=define_pattern,
                file_glob='*.h',
                max_results=1
            )

            if results:
                file_path, line_num, line_content = results[0]

                # 检查是否是多行宏（以 \ 结尾）
                if line_content.rstrip().endswith('\\'):
                    # 读取完整的多行宏定义
                    full_definition = self._read_multiline_macro(file_path, line_num)
                    constants[identifier] = full_definition
                    logger.info(f"[常量提取] ✓ 在 {file_path.name}:{line_num} 找到多行宏 #define {identifier}")
                else:
                    constants[identifier] = line_content.strip()
                    logger.info(f"[常量提取] ✓ 在 {file_path.name}:{line_num} 找到 #define {identifier}")
                continue

            # 搜索 enum 成员
            enum_pattern = rf'^\s*{re.escape(identifier)}\s*='
            results = self.grep_searcher.search_content(
                pattern=enum_pattern,
                file_glob='*.h',
                max_results=1
            )

            if results:
                file_path, line_num, line_content = results[0]
                constants[identifier] = line_content.strip()
                logger.info(f"[常量提取] ✓ 在 {file_path.name}:{line_num} 找到 enum {identifier}")

        return constants

    def _read_multiline_macro(self, file_path: Path, start_line: int) -> str:
        """
        读取多行宏定义

        Args:
            file_path: 文件路径
            start_line: 起始行号（从1开始）

        Returns:
            完整的多行宏定义
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            if start_line < 1 or start_line > len(lines):
                return ""

            # 读取从start_line开始的所有行，直到不以 \ 结尾
            macro_lines = []
            current_line = start_line - 1  # 转换为0-based索引

            while current_line < len(lines):
                line = lines[current_line].rstrip()
                macro_lines.append(line)

                # 如果不以 \ 结尾，说明宏定义结束
                if not line.endswith('\\'):
                    break

                current_line += 1

                # 安全限制：最多读取20行
                if len(macro_lines) >= 20:
                    break

            # 合并所有行
            full_macro = '\n'.join(macro_lines)
            return full_macro

        except Exception as e:
            logger.error(f"[常量提取] 读取多行宏失败: {file_path}:{start_line}, {e}")
            return ""

    def _search_with_header_searcher(self, identifiers: Set[str], target_file: str) -> Dict[str, str]:
        """使用 HeaderSearcher 在局部文件中搜索（降级方案）"""
        constants = {}
        possible_headers = self.header_searcher.find_headers(target_file)

        logger.info(f"[常量提取] 准备搜索 {len(possible_headers)} 个文件")
        for h in possible_headers[:10]:
            logger.info(f"[常量提取]   - {h.name}")
        if len(possible_headers) > 10:
            logger.info(f"[常量提取]   ... 还有 {len(possible_headers) - 10} 个文件")

        # 搜索定义
        for identifier in identifiers:
            for header_file in possible_headers:
                try:
                    with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            # 搜索 #define 或 enum
                            if re.search(rf'^\s*#define\s+{re.escape(identifier)}\b', line):
                                constants[identifier] = line.strip()
                                logger.info(f"[常量提取] ✓ 在 {header_file.name} 找到 #define {identifier}")
                                break
                            elif re.search(rf'^\s*{re.escape(identifier)}\s*=', line):
                                # enum 成员
                                constants[identifier] = line.strip()
                                logger.info(f"[常量提取] ✓ 在 {header_file.name} 找到 enum {identifier}")
                                break

                    if identifier in constants:
                        break

                except Exception as e:
                    logger.info(f"[常量提取] ✗ 读取 {header_file.name} 失败: {e}")
                    continue

        return constants
