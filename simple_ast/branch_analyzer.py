"""
分支结构分析器 - 用于单元测试覆盖率指导
分析函数的分支复杂度和关键条件
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from .cpp_parser import CppParser
from .logger import get_logger

logger = get_logger()


@dataclass
class BranchCondition:
    """分支条件信息"""
    line: int
    condition: str
    branch_type: str  # if, switch, for, while
    suggestions: List[str]  # 测试建议


@dataclass
class BranchAnalysis:
    """分支分析结果"""
    cyclomatic_complexity: int  # 圈复杂度
    if_count: int
    switch_count: int
    switch_cases: int  # switch中总case数
    loop_count: int
    early_return_count: int
    conditions: List[BranchCondition]  # 关键分支条件


class BranchAnalyzer:
    """分支结构分析器"""

    def __init__(self):
        self.parser = CppParser()

    def analyze_function(self, func_node, source_code: bytes) -> BranchAnalysis:
        """
        分析函数的分支结构

        Args:
            func_node: 函数AST节点
            source_code: 源代码bytes

        Returns:
            BranchAnalysis: 分支分析结果
        """
        import sys

        # 获取函数名用于日志
        func_name = "unknown"
        declarator = func_node.child_by_field_name('declarator')
        if declarator:
            if declarator.type == 'function_declarator':
                name_node = declarator.child_by_field_name('declarator')
                if name_node:
                    func_name = CppParser.get_node_text(name_node, source_code)
            else:
                func_name = CppParser.get_node_text(declarator, source_code)

        logger.info(f"\n[分支分析] 开始分析函数: {func_name}")

        # 获取函数体
        body_node = self._get_function_body(func_node)
        if not body_node:
            logger.info("[分支分析] 未找到函数体")
            return BranchAnalysis(1, 0, 0, 0, 0, 0, [])

        # 统计各类分支
        if_count = self._count_nodes(body_node, ['if_statement'])
        switch_count = self._count_nodes(body_node, ['switch_statement'])
        switch_cases = self._count_switch_cases(body_node)
        loop_count = self._count_nodes(body_node, ['for_statement', 'while_statement', 'do_statement'])
        early_return_count = self._count_early_returns(body_node)

        logger.info(f"[分支分析] 统计: if={if_count}, switch={switch_count}, case={switch_cases}, loop={loop_count}, early_return={early_return_count}")

        # 计算圈复杂度：1 + 决策点数量
        # 决策点包括：if, while, for, case, &&, ||, ?:
        decision_points = if_count + loop_count + switch_cases
        logical_ops = self._count_logical_operators(body_node, source_code)
        ternary_ops = self._count_ternary_operators(body_node)
        decision_points += logical_ops + ternary_ops

        cyclomatic = 1 + decision_points
        logger.info(f"[分支分析] 圈复杂度: {cyclomatic} (基础1 + 决策点{decision_points}, 逻辑运算符{logical_ops}, 三元运算{ternary_ops})")

        # 提取关键分支条件
        conditions = self._extract_key_conditions(body_node, source_code)
        logger.info(f"[分支分析] 提取了 {len(conditions)} 个关键条件")

        return BranchAnalysis(
            cyclomatic_complexity=cyclomatic,
            if_count=if_count,
            switch_count=switch_count,
            switch_cases=switch_cases,
            loop_count=loop_count,
            early_return_count=early_return_count,
            conditions=conditions
        )

    def _get_function_body(self, func_node):
        """获取函数体节点"""
        for child in func_node.children:
            if child.type == 'compound_statement':
                return child
        return None

    def _count_nodes(self, node, node_types: List[str]) -> int:
        """递归统计指定类型的节点数量"""
        count = 0
        if node.type in node_types:
            count = 1

        for child in node.children:
            count += self._count_nodes(child, node_types)

        return count

    def _count_switch_cases(self, node) -> int:
        """统计switch语句中的case数量"""
        total_cases = 0

        # 找到所有switch语句
        switch_nodes = self._find_all_nodes(node, 'switch_statement')
        for switch_node in switch_nodes:
            # 统计每个switch中的case
            case_count = self._count_nodes(switch_node, ['case_statement'])
            total_cases += case_count

        return total_cases

    def _find_all_nodes(self, node, node_type: str) -> List:
        """查找所有指定类型的节点"""
        result = []
        if node.type == node_type:
            result.append(node)

        for child in node.children:
            result.extend(self._find_all_nodes(child, node_type))

        return result

    def _count_early_returns(self, node) -> int:
        """统计提前返回的数量（不包括函数末尾的return）"""
        # 获取所有return语句
        return_nodes = self._find_all_nodes(node, 'return_statement')

        # 函数体中如果有多个return，除了最后一个，其他都算early return
        # 简化处理：如果有多个return，认为除了1个正常return，其他都是early
        if len(return_nodes) > 1:
            return len(return_nodes) - 1
        return 0

    def _count_logical_operators(self, node, source_code: bytes) -> int:
        """统计逻辑运算符数量 (&&, ||)"""
        count = 0
        logical_ops = self._find_all_nodes(node, 'binary_expression')

        for op_node in logical_ops:
            # 获取运算符
            for child in op_node.children:
                if child.type in ['&&', '||']:
                    count += 1
                    break

        return count

    def _count_ternary_operators(self, node) -> int:
        """统计三元运算符数量 (?:)"""
        return self._count_nodes(node, ['conditional_expression'])

    def _extract_key_conditions(self, node, source_code: bytes) -> List[BranchCondition]:
        """提取关键分支条件"""
        conditions = []

        # 提取if条件
        if_nodes = self._find_all_nodes(node, 'if_statement')
        for if_node in if_nodes[:10]:  # 最多提取10个，避免太长
            condition_info = self._analyze_if_condition(if_node, source_code)
            if condition_info:
                conditions.append(condition_info)

        # 提取switch条件
        switch_nodes = self._find_all_nodes(node, 'switch_statement')
        for switch_node in switch_nodes[:5]:  # 最多5个switch
            condition_info = self._analyze_switch_condition(switch_node, source_code)
            if condition_info:
                conditions.append(condition_info)

        # 提取循环条件（仅for和while的关键循环）
        loop_nodes = self._find_all_nodes(node, 'for_statement')
        loop_nodes.extend(self._find_all_nodes(node, 'while_statement'))
        for loop_node in loop_nodes[:3]:  # 最多3个循环
            condition_info = self._analyze_loop_condition(loop_node, source_code)
            if condition_info:
                conditions.append(condition_info)

        return conditions

    def _analyze_if_condition(self, if_node, source_code: bytes) -> Optional[BranchCondition]:
        """分析if语句的条件"""
        # 找到条件表达式节点
        condition_node = None
        for child in if_node.children:
            if child.type == 'condition_clause' or child.type == 'parenthesized_expression':
                condition_node = child
                break

        if not condition_node:
            return None

        condition_text = CppParser.get_node_text(condition_node, source_code)
        line = if_node.start_point[0] + 1

        # 生成测试建议
        suggestions = self._generate_if_suggestions(condition_text)

        return BranchCondition(
            line=line,
            condition=condition_text,
            branch_type='if',
            suggestions=suggestions
        )

    def _analyze_switch_condition(self, switch_node, source_code: bytes) -> Optional[BranchCondition]:
        """分析switch语句的条件"""
        import sys

        # 找到switch的条件和所有case
        condition_node = None
        for child in switch_node.children:
            if child.type == 'condition_clause' or child.type == 'parenthesized_expression':
                condition_node = child
                break

        if not condition_node:
            return None

        condition_text = CppParser.get_node_text(condition_node, source_code)
        line = switch_node.start_point[0] + 1

        logger.info(f"[分支分析]   分析switch: 行{line}, 条件={condition_text}")

        # 提取所有case标签值
        case_nodes = self._find_all_nodes(switch_node, 'case_statement')
        case_values = []
        logger.info(f"[分支分析]     找到 {len(case_nodes)} 个case节点")

        for idx, case_node in enumerate(case_nodes):  # 显示所有case值
            # case语句的第一个子节点通常是值表达式
            for child in case_node.children:
                if child.type not in ['case', ':']:
                    case_value = CppParser.get_node_text(child, source_code).strip()
                    if case_value:
                        case_values.append(case_value)
                        if idx < 5:  # 只打印前5个，避免日志过长
                            logger.info(f"[分支分析]       case {idx+1}: {case_value}")
                    break

        if len(case_values) > 5:
            logger.info(f"[分支分析]       ... 还有 {len(case_values)-5} 个case")

        has_default = self._count_nodes(switch_node, ['default_statement']) > 0
        logger.info(f"[分支分析]     有default分支: {has_default}")

        suggestions = []
        if case_values:
            # 显示所有case值（不截断）
            display_values = case_values.copy()
            if has_default:
                display_values.append('default')

            case_display = ', '.join(display_values)
            suggestions.append(f"case值: {case_display}")
            logger.info(f"[分支分析]     生成建议: {len(display_values)} 个case值")
        else:
            suggestions.append(f"测试 {len(case_nodes)} 个case分支")
            if has_default:
                suggestions.append("包含default分支")

        return BranchCondition(
            line=line,
            condition=condition_text,
            branch_type='switch',
            suggestions=suggestions
        )

    def _analyze_loop_condition(self, loop_node, source_code: bytes) -> Optional[BranchCondition]:
        """分析循环条件"""
        # 找到循环条件
        condition_node = None
        loop_type = loop_node.type.replace('_statement', '')

        for child in loop_node.children:
            if child.type in ['condition_clause', 'parenthesized_expression']:
                condition_node = child
                break

        if not condition_node:
            return None

        condition_text = CppParser.get_node_text(condition_node, source_code)
        line = loop_node.start_point[0] + 1

        suggestions = self._generate_loop_suggestions(condition_text, loop_type)

        return BranchCondition(
            line=line,
            condition=condition_text,
            branch_type=loop_type,
            suggestions=suggestions
        )

    def _generate_if_suggestions(self, condition: str) -> List[str]:
        """根据if条件生成测试建议"""
        suggestions = ["测试true和false两种情况"]

        # 检测比较运算符
        if '>' in condition or '<' in condition:
            suggestions.append("边界测试: 等于、大于、小于边界值")
        if '==' in condition or '!=' in condition:
            suggestions.append("等值测试: 相等和不等情况")
        if 'nullptr' in condition or 'NULL' in condition or '!= 0' in condition:
            suggestions.append("空指针测试: null和非null")
        if '&&' in condition or '||' in condition:
            suggestions.append("组合条件: 各子条件的不同组合")

        return suggestions

    def _generate_loop_suggestions(self, condition: str, loop_type: str) -> List[str]:
        """根据循环条件生成测试建议"""
        suggestions = [
            "边界测试: 0次迭代",
            "边界测试: 1次迭代",
            "正常情况: 多次迭代"
        ]

        if 'size' in condition.lower() or 'count' in condition.lower() or 'length' in condition.lower():
            suggestions.append("大值测试: 集合/数组为空或很大")

        return suggestions


def format_branch_analysis(analysis: BranchAnalysis) -> str:
    """
    格式化分支分析结果为可读文本

    Args:
        analysis: 分支分析结果

    Returns:
        str: 格式化后的文本
    """
    lines = []

    # 基础统计
    lines.append("[分支复杂度]")
    complexity_level = "简单" if analysis.cyclomatic_complexity <= 5 else \
                       "中等" if analysis.cyclomatic_complexity <= 10 else "较复杂"
    lines.append(f"圈复杂度: {analysis.cyclomatic_complexity}（{complexity_level}）")

    # 分支详情
    branch_details = []
    if analysis.if_count > 0:
        branch_details.append(f"if/else: {analysis.if_count}个")
    if analysis.switch_count > 0:
        branch_details.append(f"switch: {analysis.switch_count}个({analysis.switch_cases}个case)")
    if analysis.loop_count > 0:
        branch_details.append(f"循环: {analysis.loop_count}个")
    if analysis.early_return_count > 0:
        branch_details.append(f"提前返回: {analysis.early_return_count}处")

    if branch_details:
        lines.append(f"分支结构: {', '.join(branch_details)}")

    lines.append(f"建议测试用例: ≥ {analysis.cyclomatic_complexity} 组")
    lines.append("")

    # 关键条件
    if analysis.conditions:
        lines.append("[关键分支条件]")
        lines.append("")

        for i, cond in enumerate(analysis.conditions, 1):
            branch_label = {
                'if': 'if条件',
                'switch': 'switch分支',
                'for': 'for循环',
                'while': 'while循环'
            }.get(cond.branch_type, cond.branch_type)

            lines.append(f"{i}. {branch_label} (行{cond.line})")
            lines.append(f"   {cond.condition}")
            for suggestion in cond.suggestions:
                lines.append(f"   → {suggestion}")
            lines.append("")

    return "\n".join(lines)
