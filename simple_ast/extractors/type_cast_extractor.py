"""
类型转换提取器 - 分析函数中的类型转换关系

对于单元测试，类型转换信息非常重要：
- 同一指针的多次转换说明多态使用
- 需要准备不同类型的测试数据
- 理解数据结构之间的关系
"""
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from ..cpp_parser import CppParser
from ..logger import get_logger

logger = get_logger()


class TypeCastExtractor:
    """类型转换提取器"""

    def __init__(self):
        """初始化提取器"""
        self.parser = CppParser()

    def extract_from_function(
        self,
        file_path: str,
        function_name: str,
        source_code: bytes = None
    ) -> Dict[str, any]:
        """
        从函数中提取类型转换关系

        Args:
            file_path: 文件路径
            function_name: 函数名
            source_code: 源代码（可选）

        Returns:
            Dict: {
                'casts': [
                    {
                        'source_var': 'pMsg',
                        'target_var': 'pFeMsg',
                        'source_type': 'MsgBlock',
                        'target_type': 'tFeAppMsg',
                        'line': 4,
                        'code': 'tFeAppMsg *pFeMsg = (tFeAppMsg *)pMsg'
                    }
                ],
                'usage': {
                    'pFeMsg': {
                        'type': 'tFeAppMsg',
                        'fields': ['MsgType'],
                        'locations': [30],
                        'branches': ['PID_SF']
                    }
                }
            }
        """
        # 读取源代码
        if source_code is None:
            try:
                with open(file_path, 'rb') as f:
                    source_code = f.read()
            except Exception as e:
                logger.error(f"[类型转换提取] 无法读取文件: {file_path}, {e}")
                return {'casts': [], 'usage': {}}

        # 解析AST
        tree = self.parser.parser.parse(source_code)
        if not tree:
            logger.error(f"[类型转换提取] 解析失败: {file_path}")
            return {'casts': [], 'usage': {}}

        # 查找目标函数
        func_defs = CppParser.find_nodes_by_type(tree.root_node, 'function_definition')
        target_func_node = None

        for func_def in func_defs:
            name = CppParser.get_function_name(func_def, source_code)
            if name == function_name:
                target_func_node = func_def
                break

        if not target_func_node:
            logger.info(f"[类型转换提取] 未找到函数: {function_name}")
            return {'casts': [], 'usage': {}}

        logger.info(f"[类型转换提取] 分析函数: {function_name}")

        # 提取类型转换
        casts = []
        self._extract_type_casts(target_func_node, source_code, casts)

        # 提取使用信息
        usage = {}
        for cast in casts:
            if cast['target_var']:
                self._extract_variable_usage(
                    target_func_node,
                    cast['target_var'],
                    cast['target_type'],
                    source_code,
                    usage
                )

        logger.info(f"[类型转换提取] 找到 {len(casts)} 个类型转换")
        return {'casts': casts, 'usage': usage}

    def _extract_type_casts(self, func_node, source_code: bytes, casts: List[Dict]):
        """
        提取类型转换表达式

        识别模式：
        1. Type *var = (Type *)source
        2. var = (Type *)source
        3. func((Type *)var)
        """
        # 查找所有声明语句（包含初始化）
        declarations = CppParser.find_nodes_by_type(func_node, 'declaration')

        for decl in declarations:
            # 查找init_declarator
            init_declarators = CppParser.find_nodes_by_type(decl, 'init_declarator')

            for init_decl in init_declarators:
                # 获取变量名
                declarator = init_decl.child_by_field_name('declarator')
                if not declarator:
                    continue

                target_var = self._extract_variable_name(declarator, source_code)
                if not target_var:
                    continue

                # 获取类型
                type_node = decl.child_by_field_name('type')
                target_type = None
                if type_node:
                    target_type = self._extract_type_name(type_node, source_code)

                # 获取初始化值（可能包含强制转换）
                value = init_decl.child_by_field_name('value')
                if value and value.type == 'cast_expression':
                    # 获取转换后的类型
                    cast_type = value.child_by_field_name('type')
                    if cast_type:
                        cast_type_name = self._extract_type_name(cast_type, source_code)
                        if cast_type_name:
                            target_type = cast_type_name

                    # 获取源变量
                    cast_value = value.child_by_field_name('value')
                    source_var = None
                    source_type = None
                    if cast_value:
                        source_var = CppParser.get_node_text(cast_value, source_code)

                    # 获取完整代码
                    line = init_decl.start_point[0] + 1
                    code = CppParser.get_node_text(init_decl, source_code)

                    casts.append({
                        'source_var': source_var,
                        'target_var': target_var,
                        'source_type': None,  # 需要从函数参数推断
                        'target_type': target_type,
                        'line': line,
                        'code': code
                    })

    def _extract_variable_name(self, declarator, source_code: bytes) -> Optional[str]:
        """从声明器中提取变量名"""
        if declarator.type == 'identifier':
            return CppParser.get_node_text(declarator, source_code)
        elif declarator.type == 'pointer_declarator':
            child = declarator.child_by_field_name('declarator')
            if child:
                return self._extract_variable_name(child, source_code)

        # 尝试查找identifier
        identifiers = CppParser.find_nodes_by_type(declarator, 'identifier')
        if identifiers:
            return CppParser.get_node_text(identifiers[0], source_code)

        return None

    def _extract_type_name(self, type_node, source_code: bytes) -> Optional[str]:
        """从类型节点提取类型名"""
        # 查找type_identifier
        type_ids = CppParser.find_nodes_by_type(type_node, 'type_identifier')
        if type_ids:
            return CppParser.get_node_text(type_ids[0], source_code)

        # 查找identifier
        identifiers = CppParser.find_nodes_by_type(type_node, 'identifier')
        if identifiers:
            return CppParser.get_node_text(identifiers[0], source_code)

        return None

    def _extract_variable_usage(
        self,
        func_node,
        var_name: str,
        var_type: str,
        source_code: bytes,
        usage: Dict
    ):
        """
        提取变量的使用信息

        包括：
        - 访问了哪些字段
        - 在哪些位置使用
        - 在哪些分支中使用
        """
        if var_name in usage:
            return

        usage[var_name] = {
            'type': var_type,
            'fields': [],
            'locations': [],
            'branches': []
        }

        # 查找所有字段访问: var->field 或 var.field
        field_exprs = CppParser.find_nodes_by_type(func_node, 'field_expression')

        for field_expr in field_exprs:
            # 检查是否是目标变量
            argument = field_expr.child_by_field_name('argument')
            if argument:
                arg_text = CppParser.get_node_text(argument, source_code)
                if arg_text == var_name:
                    # 获取字段名
                    field = field_expr.child_by_field_name('field')
                    if field:
                        field_name = CppParser.get_node_text(field, source_code)
                        if field_name not in usage[var_name]['fields']:
                            usage[var_name]['fields'].append(field_name)

                        line = field_expr.start_point[0] + 1
                        if line not in usage[var_name]['locations']:
                            usage[var_name]['locations'].append(line)

    def format_type_casts(self, cast_info: Dict) -> str:
        """
        格式化类型转换信息为可读文本

        Args:
            cast_info: extract_from_function返回的结果

        Returns:
            格式化的文本
        """
        if not cast_info['casts']:
            return ""

        lines = []
        lines.append("[类型转换关系]")

        # 按源变量分组
        source_groups = {}
        for cast in cast_info['casts']:
            source = cast['source_var'] or '未知'
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(cast)

        for source_var, casts in sorted(source_groups.items()):
            lines.append(f"  {source_var} 的转换:")
            for cast in casts:
                target = cast['target_var']
                target_type = cast['target_type']
                line = cast['line']

                lines.append(f"    → {target} ({target_type} *) [行{line}]")

                # 添加使用信息
                if target in cast_info['usage']:
                    usage = cast_info['usage'][target]
                    if usage['fields']:
                        fields_str = ', '.join(usage['fields'])
                        lines.append(f"       访问字段: {fields_str}")
                    if usage['locations']:
                        locs = usage['locations'][:3]  # 最多显示3个位置
                        locs_str = ', '.join([f"行{loc}" for loc in locs])
                        if len(usage['locations']) > 3:
                            locs_str += f" ... (共{len(usage['locations'])}处)"
                        lines.append(f"       使用位置: {locs_str}")

        return "\n".join(lines)
