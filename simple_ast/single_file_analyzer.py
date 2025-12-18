"""
单文件边界分析器 - 深度分析单个文件的完整边界
不需要全局索引，快速分析大型文件
"""
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

from .cpp_parser import CppParser
from .entry_point_classifier import EntryPointInfo
from .call_chain_tracer import CallNode
from .data_structure_analyzer import DataStructureInfo


@dataclass
class FileBoundary:
    """文件边界信息"""
    # 文件内定义的函数
    internal_functions: Set[str]

    # 调用的外部函数
    external_functions: Set[str]

    # 文件内定义的数据结构
    internal_data_structures: Set[str]

    # 使用的外部数据结构
    external_data_structures: Set[str]

    # 文件路径
    file_path: str


class SingleFileAnalyzer:
    """单文件边界分析器 - 不需要全局索引"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.parser = CppParser()

        # 当前文件的符号表
        self.file_functions: Dict[str, dict] = {}  # function_name -> {node, signature, line}
        self.file_data_structures: Dict[str, dict] = {}  # struct_name -> {node, type, line, definition}

        # 边界追踪
        self.internal_functions: Set[str] = set()
        self.external_functions: Set[str] = set()
        self.internal_data_structures: Set[str] = set()
        self.external_data_structures: Set[str] = set()

    def analyze_file(self, file_path: str) -> FileBoundary:
        """
        分析单个文件的边界

        Args:
            file_path: 文件路径（相对于项目根目录或绝对路径）

        Returns:
            FileBoundary: 文件边界信息
        """
        # 规范化路径
        target_path = Path(file_path)
        if not target_path.is_absolute():
            target_path = self.project_root / file_path

        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {target_path}")

        print(f"Analyzing file boundary: {target_path}")

        # 读取文件
        source_code = self._read_file(target_path)
        if not source_code:
            raise ValueError(f"Could not read file: {target_path}")

        # 解析 AST
        tree = self.parser.parser.parse(source_code)
        if not tree:
            raise ValueError(f"Failed to parse file: {target_path}")

        root_node = tree.root_node

        # 步骤1: 索引文件内的所有函数定义
        print("  Step 1: Indexing functions in file...")
        self._index_file_functions(root_node, source_code)
        print(f"    Found {len(self.file_functions)} functions")

        # 步骤2: 索引文件内的所有数据结构定义
        print("  Step 2: Indexing data structures in file...")
        self._index_file_data_structures(root_node, source_code)
        print(f"    Found {len(self.file_data_structures)} data structures")

        # 步骤3: 分析函数调用，区分内部/外部
        print("  Step 3: Analyzing function calls...")
        self._analyze_function_calls(root_node, source_code)
        print(f"    Internal: {len(self.internal_functions)}, External: {len(self.external_functions)}")

        # 步骤4: 分析数据结构使用，区分内部/外部
        print("  Step 4: Analyzing data structure usage...")
        self._analyze_data_structure_usage(root_node, source_code)
        print(f"    Internal: {len(self.internal_data_structures)}, External: {len(self.external_data_structures)}")

        # 构建边界信息
        boundary = FileBoundary(
            internal_functions=self.internal_functions.copy(),
            external_functions=self.external_functions.copy(),
            internal_data_structures=self.internal_data_structures.copy(),
            external_data_structures=self.external_data_structures.copy(),
            file_path=str(target_path)
        )

        print("  Boundary analysis complete!")
        return boundary

    def _read_file(self, file_path: Path) -> Optional[bytes]:
        """读取文件内容，尝试多种编码"""
        encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252']

        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read()  # 测试编码
                # 成功后读取为 bytes
                with open(file_path, 'rb') as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue

        return None

    def _index_file_functions(self, root_node, source_code: bytes):
        """索引文件中定义的所有函数"""
        func_defs = CppParser.find_nodes_by_type(root_node, 'function_definition')

        for func_node in func_defs:
            func_name = CppParser.get_function_name(func_node, source_code)
            if not func_name:
                continue

            signature = CppParser.get_function_signature(func_node, source_code)
            line_number = func_node.start_point[0] + 1

            self.file_functions[func_name] = {
                'node': func_node,
                'signature': signature,
                'line': line_number
            }

            # 标记为内部函数
            self.internal_functions.add(func_name)

    def _index_file_data_structures(self, root_node, source_code: bytes):
        """索引文件中定义的所有数据结构"""
        structure_types = {
            'struct_specifier': 'struct',
            'class_specifier': 'class',
            'enum_specifier': 'enum',
            'type_definition': 'typedef'
        }

        for node_type, struct_type in structure_types.items():
            nodes = CppParser.find_nodes_by_type(root_node, node_type)

            for node in nodes:
                # 查找名称
                name_node = CppParser.find_child_by_type(node, 'type_identifier')
                if not name_node:
                    name_node = CppParser.find_child_by_type(node, 'identifier')

                if not name_node:
                    continue

                struct_name = CppParser.get_node_text(name_node, source_code)
                line_number = node.start_point[0] + 1

                # 获取定义（限制长度）
                definition = CppParser.get_node_text(node, source_code)
                if len(definition) > 500:
                    definition = definition[:500] + "..."

                self.file_data_structures[struct_name] = {
                    'node': node,
                    'type': struct_type,
                    'line': line_number,
                    'definition': definition
                }

                # 标记为内部数据结构
                self.internal_data_structures.add(struct_name)

    def _analyze_function_calls(self, root_node, source_code: bytes):
        """分析函数调用，区分内部和外部"""
        call_expressions = CppParser.find_nodes_by_type(root_node, 'call_expression')

        for call_node in call_expressions:
            # 获取被调用的函数名
            func_node = call_node.child_by_field_name('function')
            if not func_node:
                continue

            called_func = CppParser.get_node_text(func_node, source_code)

            # 处理成员函数调用（obj.method() 或 obj->method()）
            if '.' in called_func or '->' in called_func:
                # 提取方法名
                parts = called_func.replace('->', '.').split('.')
                if len(parts) >= 2:
                    called_func = parts[-1]

            # 过滤掉明显的标准库函数
            if self._is_standard_library_function(called_func):
                continue

            # 判断是内部还是外部
            if called_func in self.file_functions:
                # 已经在 internal_functions 中了
                pass
            else:
                # 外部函数
                self.external_functions.add(called_func)

    def _analyze_data_structure_usage(self, root_node, source_code: bytes):
        """分析数据结构使用，区分内部和外部"""
        # 查找所有类型标识符
        type_identifiers = CppParser.find_nodes_by_type(root_node, 'type_identifier')

        for type_node in type_identifiers:
            type_name = CppParser.get_node_text(type_node, source_code)

            # 过滤标准库类型
            if self._is_standard_library_type(type_name):
                continue

            # 判断是内部还是外部
            if type_name in self.file_data_structures:
                # 已经在 internal_data_structures 中了
                pass
            else:
                # 外部数据结构
                self.external_data_structures.add(type_name)

    def _is_standard_library_function(self, func_name: str) -> bool:
        """判断是否是标准库函数"""
        std_functions = {
            'printf', 'scanf', 'sprintf', 'fprintf', 'snprintf',
            'malloc', 'free', 'calloc', 'realloc',
            'memcpy', 'memset', 'memmove', 'memcmp',
            'strlen', 'strcpy', 'strcat', 'strcmp', 'strncpy', 'strncmp',
            'fopen', 'fclose', 'fread', 'fwrite', 'fseek', 'ftell',
            'exit', 'abort', 'assert',
            'sqrt', 'pow', 'sin', 'cos', 'exp', 'log',
        }
        return func_name in std_functions

    def _is_standard_library_type(self, type_name: str) -> bool:
        """判断是否是标准库类型"""
        std_types = {
            'string', 'vector', 'list', 'map', 'set', 'unordered_map', 'unordered_set',
            'queue', 'stack', 'deque', 'priority_queue',
            'shared_ptr', 'unique_ptr', 'weak_ptr',
            'mutex', 'thread', 'atomic',
            'ifstream', 'ofstream', 'fstream', 'stringstream',
            'int8_t', 'int16_t', 'int32_t', 'int64_t',
            'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
            'size_t', 'ptrdiff_t',
        }
        return type_name in std_types

    def get_entry_points(self, source_code: bytes, file_path: str) -> List[EntryPointInfo]:
        """获取入口点函数列表（用于兼容原有接口）"""
        entry_points = []

        for func_name, func_info in self.file_functions.items():
            entry_points.append(EntryPointInfo(
                name=func_name,
                category='INTERNAL',  # 单文件模式下都是内部函数
                file_path=file_path,
                line_number=func_info['line'],
                signature=func_info['signature'],
                declaration_location=None
            ))

        return entry_points

    def trace_call_chain(self, func_name: str, source_code: bytes, max_depth: int = 100) -> Optional[CallNode]:
        """追踪函数调用链（仅在文件内部追踪）"""
        if func_name not in self.file_functions:
            return None

        return self._trace_function_calls_recursive(
            func_name,
            source_code,
            visited=set(),
            depth=0,
            max_depth=max_depth
        )

    def _trace_function_calls_recursive(
        self,
        func_name: str,
        source_code: bytes,
        visited: Set[str],
        depth: int,
        max_depth: int
    ) -> Optional[CallNode]:
        """递归追踪函数调用"""
        if depth >= max_depth:
            return None

        if func_name not in self.file_functions:
            # 外部函数，创建外部节点
            return CallNode(
                function_name=func_name,
                file_path="<external>",
                line_number=0,
                signature="<external function>",
                called_from_line=0,
                is_external=True,
                is_recursive=False,
                children=[]
            )

        func_info = self.file_functions[func_name]
        func_node = func_info['node']

        # 创建当前节点
        current_node = CallNode(
            function_name=func_name,
            file_path=self._current_file_path,
            line_number=func_info['line'],
            signature=func_info['signature'],
            called_from_line=0,
            is_external=False,
            is_recursive=(func_name in visited),
            children=[]
        )

        if func_name in visited:
            return current_node

        visited.add(func_name)

        # 查找函数体中的所有调用
        call_expressions = CppParser.find_nodes_by_type(func_node, 'call_expression')

        for call_expr in call_expressions:
            func_expr = call_expr.child_by_field_name('function')
            if not func_expr:
                continue

            called_name = CppParser.get_node_text(func_expr, source_code)

            # 处理成员函数调用
            if '.' in called_name or '->' in called_name:
                parts = called_name.replace('->', '.').split('.')
                if len(parts) >= 2:
                    called_name = parts[-1]

            # 过滤标准库函数
            if self._is_standard_library_function(called_name):
                continue

            # 递归追踪
            child_node = self._trace_function_calls_recursive(
                called_name,
                source_code,
                visited.copy(),
                depth + 1,
                max_depth
            )

            if child_node:
                child_node.called_from_line = call_expr.start_point[0] + 1
                current_node.children.append(child_node)

        return current_node

    def get_data_structures_info(self) -> Dict[str, DataStructureInfo]:
        """获取数据结构信息（用于兼容原有接口）"""
        data_structures = {}

        for struct_name, struct_info in self.file_data_structures.items():
            data_structures[struct_name] = DataStructureInfo(
                name=struct_name,
                type=struct_info['type'],
                file_path=self._current_file_path,
                line_number=struct_info['line'],
                definition=struct_info['definition'],
                used_by_functions=set(),  # 可以进一步分析
                used_in_files={self._current_file_path}
            )

        return data_structures

    @property
    def _current_file_path(self) -> str:
        """当前分析的文件路径"""
        return getattr(self, '_file_path', '<unknown>')
