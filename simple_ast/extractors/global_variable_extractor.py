"""
全局变量提取器 - 提取函数中使用的全局变量

对于单元测试，全局变量的信息非常重要：
- 需要在测试前初始化
- 可能需要Mock
- 影响函数行为
"""
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
                    'operations': ['read', 'write'],  # 操作类型
                    'locations': [10, 15, 20],  # 使用位置（行号）
                    'is_likely_global': True  # 是否可能是全局变量
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
        global_vars = {}
        self._extract_global_variables(target_func_node, source_code, global_vars)

        logger.info(f"[全局变量提取] 找到 {len(global_vars)} 个可能的全局变量")
        return global_vars

    def _extract_global_variables(
        self,
        func_node,
        source_code: bytes,
        global_vars: Dict[str, Dict]
    ):
        """
        从函数节点中提取全局变量

        全局变量识别规则：
        1. 以 g_ 或 G_ 开头（常见命名约定）
        2. 全大写且包含下划线（如 MAX_SIZE）
        3. 不是局部变量声明
        """
        # 查找所有标识符
        identifiers = CppParser.find_nodes_by_type(func_node, 'identifier')

        # 收集局部变量名（排除）
        local_vars = self._get_local_variables(func_node, source_code)
        logger.debug(f"[全局变量提取] 局部变量: {local_vars}")

        for identifier in identifiers:
            var_name = CppParser.get_node_text(identifier, source_code)
            line_num = identifier.start_point[0] + 1

            # 跳过局部变量
            if var_name in local_vars:
                continue

            # 检查是否符合全局变量命名规则
            if not self._is_likely_global_variable(var_name):
                continue

            # 初始化变量信息
            if var_name not in global_vars:
                global_vars[var_name] = {
                    'operations': set(),
                    'locations': [],
                    'is_likely_global': True
                }

            # 判断操作类型（读还是写）
            operation = self._determine_operation(identifier, source_code)
            global_vars[var_name]['operations'].add(operation)
            global_vars[var_name]['locations'].append(line_num)

        # 转换set为list（用于JSON序列化）
        for var_name in global_vars:
            global_vars[var_name]['operations'] = sorted(list(global_vars[var_name]['operations']))
            global_vars[var_name]['locations'] = sorted(list(set(global_vars[var_name]['locations'])))

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
        1. 以 g_ 或 G_ 或 s_ (static) 开头 → 全局变量
        2. 全大写且包含下划线 → 可能是全局常量，但需要排除宏
        3. 排除常见的宏模式
        """
        # 规则1: 命名约定 - g_, G_, s_, S_ 前缀（最可靠）
        if var_name.startswith(('g_', 'G_', 's_', 'S_')):
            return True

        # 排除明显的宏模式（这些应该在[常量定义]中处理）
        macro_patterns = [
            'GET_', 'SET_', 'RESET_', 'CLEAR_',
            'OFFSET_', 'MSGLEN_', '_CHECK', '_RETURN',
            '_LOG', 'LOG_', 'PRINT_', 'TRACE_',
            'DIAM_FALSE', 'DIAM_TRUE', 'VOS_NULL', 'NULL_'
        ]

        for pattern in macro_patterns:
            if pattern in var_name:
                return False

        # 规则2: 全大写+下划线（可能是全局常量）
        # 但只接受特定长度，排除太长的（通常是宏）
        if '_' in var_name and len(var_name) <= 30:
            # 检查是否全大写
            name_without_underscore = var_name.replace('_', '')
            if name_without_underscore.replace('0', '').replace('1', '').replace('2', '').replace('3', '').replace('4', '').replace('5', '').replace('6', '').replace('7', '').replace('8', '').replace('9', '').isupper():
                # 进一步检查：全局常量通常是 XXX_YYY 形式
                # 但不是 PID_XXX, DIAM_XXX 这种枚举值
                if not var_name.startswith(('PID_', 'DIAM_', 'VOS_', 'ERR_', 'MSG_')):
                    return True

        return False

    def _determine_operation(self, identifier_node, source_code: bytes) -> str:
        """
        判断对变量的操作类型

        Returns:
            'read' | 'write' | 'read_write'
        """
        # 检查父节点类型
        parent = identifier_node.parent

        if not parent:
            return 'read'

        # 赋值表达式左侧 = 写操作
        if parent.type == 'assignment_expression':
            left = parent.child_by_field_name('left')
            if left and self._contains_node(left, identifier_node):
                return 'write'

        # 自增/自减 = 读写
        if parent.type in ('update_expression', 'compound_literal_expression'):
            return 'read_write'

        # 默认为读操作
        return 'read'

    def _contains_node(self, parent, target_node) -> bool:
        """检查parent是否包含target_node"""
        if parent == target_node:
            return True

        for child in parent.children:
            if self._contains_node(child, target_node):
                return True

        return False

    def format_global_variables(self, global_vars: Dict[str, Dict]) -> str:
        """
        格式化全局变量信息为可读文本

        Args:
            global_vars: extract_from_function返回的结果

        Returns:
            格式化的文本
        """
        if not global_vars:
            return ""

        lines = []
        lines.append("[全局变量]")

        for var_name in sorted(global_vars.keys()):
            info = global_vars[var_name]
            operations = ', '.join(info['operations'])
            locations = ', '.join([f"行{loc}" for loc in info['locations'][:5]])  # 最多显示5个位置

            if len(info['locations']) > 5:
                locations += f" ... (共{len(info['locations'])}处)"

            lines.append(f"  {var_name}:")
            lines.append(f"    操作: {operations}")
            lines.append(f"    位置: {locations}")

        return "\n".join(lines)
