"""
函数实现内容提取器 - 提取函数的完整实现代码

功能：从C++源文件中提取指定函数的完整实现内容，包括函数签名和函数体
"""
from pathlib import Path
from typing import Optional, Dict
from ..cpp_parser import CppParser
from ..logger import get_logger

logger = get_logger()


class FunctionImplExtractor:
    """函数实现提取器"""

    def __init__(self, project_root: str = "."):
        """
        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root)
        self.parser = CppParser()

    def extract(self, func_name: str, source_file: str, file_boundary=None) -> Optional[str]:
        """
        提取函数的完整实现

        Args:
            func_name: 函数名
            source_file: 源文件路径（相对于项目根目录）
            file_boundary: FileBoundary对象，如果提供则直接使用已解析的AST

        Returns:
            函数实现代码字符串，如果未找到则返回None
        """
        logger.info(f"[函数实现提取] 开始提取函数: {func_name}")
        logger.info(f"[函数实现提取] 源文件: {source_file}")

        # 1. 如果提供了file_boundary，优先使用
        if file_boundary and hasattr(file_boundary, 'file_functions'):
            logger.info(f"[函数实现提取] 使用已缓存的AST")
            if func_name in file_boundary.file_functions:
                func_info = file_boundary.file_functions[func_name]
                func_node = func_info.get('node')
                source_code = file_boundary.source_code

                if func_node and source_code:
                    impl = self._extract_from_node(func_node, source_code)
                    if impl:
                        logger.info(f"[函数实现提取] ✓ 从缓存AST成功提取 {func_name} ({len(impl)} 字符)")
                        return impl
                    else:
                        logger.warning(f"[函数实现提取] ✗ 从缓存AST提取失败")
            else:
                logger.warning(f"[函数实现提取] 函数 {func_name} 不在 file_boundary.file_functions 中")

        # 2. 如果没有file_boundary或提取失败，则解析文件
        file_path = self.project_root / source_file
        if not file_path.exists():
            logger.error(f"[函数实现提取] 文件不存在: {file_path}")
            return None

        logger.info(f"[函数实现提取] 解析文件: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"[函数实现提取] 读取文件失败: {e}")
            return None

        # 解析文件
        tree = self.parser.parse(source_code)
        if not tree or not tree.root_node:
            logger.error(f"[函数实现提取] 解析AST失败")
            return None

        # 3. 查找函数节点
        func_node = self._find_function_node(tree.root_node, func_name, source_code)
        if not func_node:
            logger.warning(f"[函数实现提取] 未找到函数: {func_name}")
            return None

        # 4. 提取函数实现
        impl = self._extract_from_node(func_node, source_code)
        if impl:
            logger.info(f"[函数实现提取] ✓ 成功提取 {func_name} ({len(impl)} 字符)")
        else:
            logger.warning(f"[函数实现提取] ✗ 提取失败")

        return impl

    def extract_all(self, source_file: str, function_list: list = None, file_boundary=None) -> Dict[str, str]:
        """
        批量提取多个函数的实现

        Args:
            source_file: 源文件路径
            function_list: 要提取的函数名列表，如果为None则提取所有函数
            file_boundary: FileBoundary对象

        Returns:
            字典 {函数名: 实现代码}
        """
        result = {}

        # 如果提供了file_boundary，直接从中提取所有函数
        if file_boundary and hasattr(file_boundary, 'file_functions'):
            functions_to_extract = function_list or list(file_boundary.file_functions.keys())
            logger.info(f"[批量提取] 从缓存AST提取 {len(functions_to_extract)} 个函数")

            for func_name in functions_to_extract:
                impl = self.extract(func_name, source_file, file_boundary)
                if impl:
                    result[func_name] = impl

            return result

        # 否则解析文件
        file_path = self.project_root / source_file
        if not file_path.exists():
            logger.error(f"[批量提取] 文件不存在: {file_path}")
            return result

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"[批量提取] 读取文件失败: {e}")
            return result

        tree = self.parser.parse(source_code)
        if not tree or not tree.root_node:
            logger.error(f"[批量提取] 解析AST失败")
            return result

        # 查找所有函数定义
        all_func_nodes = self._find_all_function_nodes(tree.root_node, source_code)

        # 筛选要提取的函数
        if function_list:
            func_nodes = {name: node for name, node in all_func_nodes.items() if name in function_list}
        else:
            func_nodes = all_func_nodes

        logger.info(f"[批量提取] 找到 {len(func_nodes)} 个函数")

        # 提取每个函数的实现
        for func_name, func_node in func_nodes.items():
            impl = self._extract_from_node(func_node, source_code)
            if impl:
                result[func_name] = impl

        return result

    def _find_function_node(self, root_node, func_name: str, source_code: str):
        """查找指定函数的节点"""
        # 查找所有函数定义节点
        function_defs = CppParser.find_nodes_by_type(root_node, 'function_definition')

        for func_def in function_defs:
            # 获取声明器节点
            declarator = func_def.child_by_field_name('declarator')
            if not declarator:
                continue

            # 提取函数名
            name = self._extract_function_name(declarator, source_code)
            if name == func_name:
                return func_def

        return None

    def _find_all_function_nodes(self, root_node, source_code: str) -> Dict[str, any]:
        """查找所有函数节点，返回 {函数名: 节点} 字典"""
        result = {}
        function_defs = CppParser.find_nodes_by_type(root_node, 'function_definition')

        for func_def in function_defs:
            declarator = func_def.child_by_field_name('declarator')
            if not declarator:
                continue

            name = self._extract_function_name(declarator, source_code)
            if name:
                result[name] = func_def

        return result

    def _extract_function_name(self, declarator, source_code: str) -> Optional[str]:
        """从声明器节点中提取函数名"""
        # 处理不同类型的声明器
        # function_declarator -> identifier
        # pointer_declarator -> function_declarator -> identifier
        # reference_declarator -> function_declarator -> identifier

        current = declarator
        max_depth = 10  # 防止无限循环
        depth = 0

        while current and depth < max_depth:
            depth += 1

            # 检查是否是 function_declarator
            if current.type == 'function_declarator':
                # 查找 declarator 字段（函数名）
                name_node = current.child_by_field_name('declarator')
                if name_node:
                    # 如果是 identifier，直接返回
                    if name_node.type == 'identifier':
                        return CppParser.get_node_text(name_node, source_code)
                    # 如果是其他类型（如 field_identifier, qualified_identifier），继续处理
                    elif name_node.type == 'field_identifier':
                        return CppParser.get_node_text(name_node, source_code)
                    elif name_node.type == 'qualified_identifier':
                        # 对于 A::B 这样的限定名，提取最后的标识符
                        name_parts = CppParser.get_node_text(name_node, source_code).split('::')
                        return name_parts[-1] if name_parts else None
                    else:
                        # 继续向下查找
                        current = name_node
                        continue
                else:
                    break

            # 检查是否是 pointer_declarator 或 reference_declarator
            elif current.type in ['pointer_declarator', 'reference_declarator']:
                # 查找 declarator 字段
                current = current.child_by_field_name('declarator')
                continue

            # 如果是 identifier，直接返回
            elif current.type == 'identifier':
                return CppParser.get_node_text(current, source_code)

            else:
                break

        return None

    def _extract_from_node(self, func_node, source_code: str) -> Optional[str]:
        """从函数节点提取完整实现代码"""
        if not func_node:
            return None

        try:
            # 获取函数节点的完整文本
            func_text = CppParser.get_node_text(func_node, source_code)
            return func_text
        except Exception as e:
            logger.error(f"[函数实现提取] 提取节点文本失败: {e}")
            return None
