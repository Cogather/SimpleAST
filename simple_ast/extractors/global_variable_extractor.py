"""
全局变量提取器 - 提取函数中使用的全局变量

对于单元测试，全局变量的信息非常重要：
- 需要在测试前初始化
- 可能需要Mock
- 影响函数行为
"""
import re
from typing import Set, Dict, List, Optional
from pathlib import Path
from ..cpp_parser import CppParser
from ..logger import get_logger

logger = get_logger()


class GlobalVariableExtractor:
    """全局变量提取器"""

    def __init__(self):
        """初始化提取器"""
        self.parser = CppParser()

    def extract_from_function(
        self,
        file_path: str,
        function_name: str,
        source_code: bytes = None
    ) -> Dict[str, Dict[str, any]]:
        """
        从函数中提取全局变量使用情况

        Args:
            file_path: 文件路径
            function_name: 函数名
            source_code: 源代码（可选，如果不提供则读取文件）

        Returns:
            Dict: {
                'variable_name': {
                    'definition': 'DIAM_BOOL g_StringFailedAvp = DIAM_FALSE;',  # 变量定义
                    'type': 'DIAM_BOOL',  # 类型
                    'file': 'diamadapt.cpp',  # 定义文件
                    'line': 123  # 定义行号
                }
            }
        """
        # 读取源代码
        if source_code is None:
            try:
                with open(file_path, 'rb') as f:
                    source_code = f.read()
            except Exception as e:
                logger.error(f"[全局变量提取] 无法读取文件: {file_path}, {e}")
                return {}

        # 解析AST
        tree = self.parser.parser.parse(source_code)
        if not tree:
            logger.error(f"[全局变量提取] 解析失败: {file_path}")
            return {}

        # 查找目标函数
        func_defs = CppParser.find_nodes_by_type(tree.root_node, 'function_definition')
        target_func_node = None

        for func_def in func_defs:
            name = CppParser.get_function_name(func_def, source_code)
            if name == function_name:
                target_func_node = func_def
                break

        if not target_func_node:
            logger.info(f"[全局变量提取] 未找到函数: {function_name}")
            return {}

        logger.info(f"[全局变量提取] 分析函数: {function_name}")

        # 提取全局变量访问
        global_var_names = set()
        self._extract_global_variable_names(target_func_node, source_code, global_var_names)

        if not global_var_names:
            logger.info(f"[全局变量提取] 未找到全局变量")
            return {}

        # 搜索全局变量定义
        global_vars = {}
        from pathlib import Path
        project_root = Path(file_path).parent
        for var_name in global_var_names:
            definition_info = self._search_variable_definition(var_name, project_root)
            if definition_info:
                global_vars[var_name] = definition_info

        logger.info(f"[全局变量提取] 找到 {len(global_vars)} 个全局变量定义")
        return global_vars

    def _extract_global_variable_names(
        self,
        func_node,
        source_code: bytes,
        global_var_names: Set[str]
    ):
        """
        从函数节点中提取全局变量名

        只提取符合全局变量命名规范的标识符
        """
        # 查找所有标识符
        identifiers = CppParser.find_nodes_by_type(func_node, 'identifier')

        # 收集局部变量名（排除）
        local_vars = self._get_local_variables(func_node, source_code)
        logger.debug(f"[全局变量提取] 局部变量: {local_vars}")

        for identifier in identifiers:
            var_name = CppParser.get_node_text(identifier, source_code)

            # 跳过局部变量
            if var_name in local_vars:
                continue

            # 检查是否符合全局变量命名规则
            if self._is_likely_global_variable(var_name):
                global_var_names.add(var_name)

    def _search_variable_definition(self, var_name: str, project_root: Path) -> Optional[Dict]:
        """
        搜索全局变量定义

        Args:
            var_name: 变量名
            project_root: 项目根目录

        Returns:
            Dict包含：definition, type, file, line
        """
        from ..searchers import GrepSearcher

        grep = GrepSearcher(str(project_root))

        # 搜索变量定义模式：Type var_name = ...;
        # 或者 Type var_name;
        pattern = rf'\b\w+\s+{re.escape(var_name)}\s*(=|;)'

        results = grep.search_content(
            pattern=pattern,
            file_glob='*.cpp',
            max_results=5
        )

        if not results:
            # 尝试在头文件中搜索
            results = grep.search_content(
                pattern=pattern,
                file_glob='*.h',
                max_results=5
            )

        if not results:
            logger.info(f"[全局变量提取] 未找到 {var_name} 的定义")
            return None

        # 取第一个结果
        file_path, line_num, line_content = results[0]

        # 提取类型
        var_type = self._extract_type_from_declaration(line_content, var_name)

        return {
            'definition': line_content.strip(),
            'type': var_type or '未知',
            'file': file_path.name,
            'line': line_num
        }

    def _extract_type_from_declaration(self, declaration: str, var_name: str) -> Optional[str]:
        """从声明中提取类型"""
        # 简单的类型提取：找到 var_name 之前的部分
        # Type var_name = ...
        pattern = rf'(\w+(?:\s*\*)?)\s+{re.escape(var_name)}\b'
        match = re.search(pattern, declaration)

        if match:
            return match.group(1).strip()

        return None

    def _get_local_variables(self, func_node, source_code: bytes) -> Set[str]:
        """
        获取函数中的局部变量名

        Returns:
            Set[str]: 局部变量名集合
        """
        local_vars = set()

        # 1. 函数参数
        param_list = func_node.child_by_field_name('parameters')
        if param_list:
            param_decls = CppParser.find_nodes_by_type(param_list, 'parameter_declaration')
            for param in param_decls:
                declarator = param.child_by_field_name('declarator')
                if declarator:
                    # 处理各种声明器类型
                    param_name = self._extract_declarator_name(declarator, source_code)
                    if param_name:
                        local_vars.add(param_name)

        # 2. 局部变量声明
        declarations = CppParser.find_nodes_by_type(func_node, 'declaration')
        for decl in declarations:
            declarator = decl.child_by_field_name('declarator')
            if declarator:
                var_name = self._extract_declarator_name(declarator, source_code)
                if var_name:
                    local_vars.add(var_name)

        return local_vars

    def _extract_declarator_name(self, declarator, source_code: bytes) -> Optional[str]:
        """从声明器中提取变量名"""
        if declarator.type == 'identifier':
            return CppParser.get_node_text(declarator, source_code)
        elif declarator.type == 'pointer_declarator':
            # int *pVar
            child = declarator.child_by_field_name('declarator')
            if child:
                return self._extract_declarator_name(child, source_code)
        elif declarator.type == 'init_declarator':
            # int var = 0
            child = declarator.child_by_field_name('declarator')
            if child:
                return self._extract_declarator_name(child, source_code)
        elif declarator.type == 'array_declarator':
            # int arr[10]
            child = declarator.child_by_field_name('declarator')
            if child:
                return self._extract_declarator_name(child, source_code)

        # 尝试查找任何identifier子节点
        identifiers = CppParser.find_nodes_by_type(declarator, 'identifier')
        if identifiers:
            return CppParser.get_node_text(identifiers[0], source_code)

        return None

    def _is_likely_global_variable(self, var_name: str) -> bool:
        """
        判断是否可能是全局变量

        规则：
        1. 以 g_ 或 G_ 开头 → 全局变量（最可靠）
        2. 排除所有大写的标识符（常量/宏）
        3. 排除预编译宏标识符（以_开头结尾）
        """
        # 规则1: 命名约定 - g_, G_ 前缀（最可靠）
        if var_name.startswith(('g_', 'G_')):
            return True

        # 规则2: 排除全大写（常量/枚举/宏）
        if var_name.isupper():
            return False

        # 规则3: 排除预编译宏模式 _XXX_
        if var_name.startswith('_') and var_name.endswith('_'):
            return False

        # 规则4: 排除常见的宏模式
        macro_patterns = [
            'GET_', 'SET_', 'RESET_', 'CLEAR_',
            'OFFSET_', 'MSGLEN_', '_CHECK', '_RETURN',
            '_LOG', 'LOG_', 'PRINT_', 'TRACE_',
        ]

        for pattern in macro_patterns:
            if pattern in var_name:
                return False

        # 其他情况不认为是全局变量
        # 因为C++的全局变量应该有明确的命名规范
        return False
