"""
单函数报告生成器 - 生成完整的测试上下文报告

原位置：AnalysisResult.generate_single_function_report() 及相关方法

职责：
- 递归展开函数依赖
- 生成Mock清单
- 提取数据结构
- 提取常量定义
- 格式化输出
"""
import sys
from typing import Dict, List, Set, Optional
from ..extractors import ConstantExtractor, SignatureExtractor, StructureExtractor
from ..searchers import HeaderSearcher
from ..logger import get_logger
logger = get_logger()



class FunctionReporter:
    """单函数报告生成器 - 简单实用，不过度设计"""

    def __init__(self, result, config=None):
        """
        Args:
            result: AnalysisResult 对象
            config: 配置对象（可选）
        """
        self.result = result
        self.config = config or {}

        # 使用 AnalysisResult 中的项目根目录
        project_root = result.project_root if hasattr(result, 'project_root') else "."

        # 创建提取器
        header_searcher = HeaderSearcher()
        self.constant_extractor = ConstantExtractor(header_searcher, project_root=project_root)
        self.signature_extractor = SignatureExtractor(header_searcher)

        # StructureExtractor 使用全局搜索
        self.structure_extractor = StructureExtractor(project_root=project_root)

    def generate(self, func_name: str) -> str:
        """
        生成单个函数的完整测试上下文报告

        Args:
            func_name: 函数名

        Returns:
            格式化的报告文本
        """
        lines = []
        visited = set()
        all_data_structures = set()
        all_external_funcs = set()

        # 递归生成主函数及其所有内部依赖
        self._generate_recursive_function_info(
            func_name, lines, "", visited, all_data_structures, all_external_funcs
        )

        # 提取并展示常量/宏定义
        constants = self.constant_extractor.extract(
            func_name,
            self.result.function_signatures,
            self.result.branch_analyses,
            self.result.target_file
        )

        if constants:
            lines.append("\n[常量定义]")
            for const_name, const_def in sorted(constants.items()):
                if const_def:
                    lines.append(f"{const_name}: {const_def}")

        # 统一展示数据结构定义章节
        if all_data_structures:
            lines.append("\n[数据结构]")

            # 分类：内部定义 vs 外部引用
            internal_ds = [ds for ds in all_data_structures if ds in self.result.data_structures]
            external_ds = [ds for ds in all_data_structures if ds not in self.result.data_structures]

            # 显示内部定义的数据结构（有完整代码）
            if internal_ds:
                for ds in sorted(internal_ds):
                    if (self.result.file_boundary and
                        hasattr(self.result.file_boundary, 'file_data_structures') and
                        ds in self.result.file_boundary.file_data_structures):
                        ds_info = self.result.file_boundary.file_data_structures[ds]
                        lines.append(f"\n{ds} ({ds_info['type']}, 内部 {self.result.target_file}:{ds_info['line']}):")
                        lines.append(ds_info['definition'])
                    else:
                        lines.append(f"\n{ds} (内部)")

            # 尝试从头文件读取外部数据结构
            if external_ds:
                for ds in sorted(external_ds):
                    definition = self.structure_extractor.extract(ds, self.result.target_file)
                    if definition:
                        lines.append(f"\n{ds} (外部):")
                        lines.append(definition)

        return "\n".join(lines)

    def _generate_recursive_function_info(self, func_name: str, lines: List[str],
                                         number_prefix: str, visited: Set[str],
                                         all_data_structures: Set[str],
                                         all_external_funcs: Set[str]):
        """递归生成函数信息（带序号层级）"""
        # 防止循环依赖
        if func_name in visited:
            logger.info(f"[递归展开] 跳过已访问函数: {func_name}")
            return
        visited.add(func_name)

        depth = len(number_prefix.split('.')) if number_prefix else 0
        indent = "  " * depth
        logger.info(f"{indent}[递归展开] 处理函数: {func_name} (层级: {number_prefix or '主函数'})")

        # === 1. 函数签名 ===
        if number_prefix:
            lines.append(f"\n{number_prefix} {func_name}")
        else:
            lines.append(f"函数: {func_name}")

        if func_name in self.result.function_signatures:
            sig = self.result.function_signatures[func_name]
            sig_part = sig.split('//')[0].strip()
            if '//' in sig:
                location = sig.split('//')[-1].strip()
                lines.append(f"{sig_part} // {location}")
            else:
                lines.append(sig_part)

        # === 2. 分支复杂度分析（仅当圈复杂度>5时） ===
        if (hasattr(self.result, 'branch_analyses') and self.result.branch_analyses and
            func_name in self.result.branch_analyses):
            branch_analysis = self.result.branch_analyses[func_name]
            if branch_analysis.cyclomatic_complexity > 5:
                lines.append(f"圈复杂度: {branch_analysis.cyclomatic_complexity}")
                if branch_analysis.conditions:
                    lines.append("关键分支:")

                    # 优先显示switch（包含case信息），然后显示if
                    switch_conditions = [c for c in branch_analysis.conditions if c.branch_type == 'switch']
                    other_conditions = [c for c in branch_analysis.conditions if c.branch_type != 'switch']

                    display_conditions = switch_conditions + other_conditions

                    for idx, cond in enumerate(display_conditions, 1):
                        lines.append(f"  {idx}. {cond.condition}")
                        # 对于switch，显示case值和详细信息
                        if cond.branch_type == 'switch' and cond.suggestions:
                            for sug in cond.suggestions:
                                lines.append(f"     {sug}")

                            # 显示每个 case 的详细信息
                            if hasattr(cond, 'switch_cases') and cond.switch_cases:
                                lines.append("     详细分支:")
                                for case_info in cond.switch_cases:
                                    lines.append(f"       case {case_info.case_value}:")
                                    if case_info.called_functions:
                                        func_list = ', '.join(case_info.called_functions)
                                        lines.append(f"         调用: {func_list}")
                                    lines.append(f"         位置: 行{case_info.line_start}-{case_info.line_end}")

        # === 3. 收集直接依赖 ===
        direct_internal_deps = []
        direct_external_deps = set()

        if func_name in self.result.call_chains:
            call_tree = self.result.call_chains[func_name]
            if call_tree and call_tree.children:
                logger.info(f"{indent}[递归展开]   找到 {len(call_tree.children)} 个直接调用")
                for child in call_tree.children:
                    if child.is_external:
                        direct_external_deps.add(child.function_name)
                        all_external_funcs.add(child.function_name)
                    else:
                        direct_internal_deps.append(child.function_name)

                internal_count = len(direct_internal_deps)
                external_count = len(direct_external_deps)
                logger.info(f"{indent}[递归展开]   分类: 内部{internal_count}个, 外部{external_count}个")
            else:
                logger.info(f"{indent}[递归展开]   无直接调用")
        else:
            logger.info(f"{indent}[递归展开]   警告: 未找到调用链信息")

        # === 4. Mock清单（仅显示业务外部依赖，并搜索签名） ===
        if direct_external_deps:
            # 使用分类器分类外部函数
            classified = self.result.external_classifier.classify(direct_external_deps)

            print(f"{indent}[Mock生成] 外部函数分类: 业务{len(classified.get('business', []))}个, "
                  f"标准库{len(classified.get('standard_lib', []))}个, "
                  f"日志{len(classified.get('logging', []))}个", file=sys.stderr)

            # 仅显示业务外部依赖（隐藏标准库和日志函数）
            if classified['business']:
                lines.append("Mock:")
                for func in sorted(classified['business']):
                    # 尝试搜索函数签名
                    signature = self.signature_extractor.extract(func, self.result.target_file)
                    if signature:
                        lines.append(f"  {func}: {signature}")
                        logger.info(f"{indent}[Mock生成]   ✓ {func}: 找到签名")
                    else:
                        lines.append(f"  {func}")
                        logger.info(f"{indent}[Mock生成]   ✗ {func}: 未找到签名")
            else:
                logger.info(f"{indent}[Mock生成] 无业务外部依赖（已过滤标准库和日志）")
        else:
            logger.info(f"{indent}[Mock生成] 无外部依赖")

        # === 5. 数据结构 - 只列出名称，收集到 all_data_structures ===
        used_data_structures = self._extract_data_structures_from_single_function(func_name)

        if used_data_structures:
            # 添加到全局收集set
            all_data_structures.update(used_data_structures.keys())
            # 只列出名称
            lines.append(f"数据结构: {', '.join(sorted(used_data_structures.keys()))}")

        # === 6. 递归显示内部依赖函数 ===
        if direct_internal_deps:
            for idx, dep_func in enumerate(direct_internal_deps, start=1):
                # 生成序号前缀
                if number_prefix:
                    new_prefix = f"{number_prefix}.{idx}"
                else:
                    new_prefix = f"{idx}"

                # 递归生成依赖函数的完整信息
                self._generate_recursive_function_info(
                    dep_func, lines, new_prefix, visited, all_data_structures, all_external_funcs
                )

    def _extract_data_structures_from_single_function(self, func_name: str):
        """从单个函数签名和边界分析中提取使用的数据结构"""
        import re
        used_ds = {}

        if func_name not in self.result.function_signatures:
            return used_ds

        sig = self.result.function_signatures[func_name]
        logger.info(f"\n[数据结构提取] 分析函数: {func_name}")
        logger.info(f"[数据结构提取] 签名: {sig[:100]}...")

        # 过滤基础类型的模式
        basic_type_patterns = [
            r'^VOS_(VOID|INT|UINT|CHAR|BOOL|LONG|SHORT|DWORD|WORD|BYTE)\d*$',
            r'^DIAM_(VOID|INT|UINT|CHAR|BOOL|UINT32|INT32)\d*$',
        ]

        # 检查已知的数据结构（文件内部定义的），但过滤掉基础类型
        internal_count = 0
        filtered_count = 0
        for ds_name in self.result.data_structures.keys():
            if ds_name in sig:
                # 检查是否是基础类型
                is_basic_type = False
                for pattern in basic_type_patterns:
                    if re.match(pattern, ds_name):
                        is_basic_type = True
                        logger.info(f"[数据结构提取] ✗ 过滤基础类型: {ds_name} (匹配模式: {pattern})")
                        filtered_count += 1
                        break

                if not is_basic_type:
                    used_ds[ds_name] = self.result.data_structures[ds_name]
                    logger.info(f"[数据结构提取] ✓ 内部结构: {ds_name}")
                    internal_count += 1

        logger.info(f"[数据结构提取] 内部结构: 找到 {internal_count} 个, 过滤 {filtered_count} 个")

        # 通用类型提取：从签名中提取所有可能的类型名
        # 1. 匹配参数类型：类型名 + 指针/引用/空格
        type_pattern = r'\b([A-Z][a-zA-Z0-9_]*)\s*[\*&\s]'
        type_matches = re.findall(type_pattern, sig)

        # 2. 匹配类名（成员函数的类）
        class_pattern = r'\b([A-Z][a-zA-Z0-9_]*)::'
        class_matches = re.findall(class_pattern, sig)

        # 合并所有匹配
        all_types = set(type_matches + class_matches)

        # 3. 从函数体中提取实际使用的类型
        boundary_types_count = 0
        function_body_types = self._extract_types_from_function_body(func_name)
        if function_body_types:
            all_types.update(function_body_types)
            boundary_types_count = len(function_body_types)
            logger.info(f"[数据结构提取] 函数体分析: 找到 {boundary_types_count} 个类型")

        logger.info(f"[数据结构提取] 正则提取: {len(type_matches)} 个参数类型, {len(class_matches)} 个类名, 边界分析 {boundary_types_count} 个")
        if all_types:
            logger.info(f"[数据结构提取] 待过滤类型: {sorted(all_types)}")

        # 过滤关键字和基础类型
        keywords = {'VOID', 'INT', 'CHAR', 'BOOL', 'FLOAT', 'DOUBLE', 'LONG', 'SHORT',
                   'CONST', 'STATIC', 'INLINE', 'VIRTUAL', 'EXPLICIT', 'TYPEDEF',
                   'UNSIGNED', 'SIGNED'}
        basic_typedefs = {'UINT8', 'UINT16', 'UINT32', 'UINT64',
                         'INT8', 'INT16', 'INT32', 'INT64',
                         'DWORD', 'WORD', 'BYTE', 'SIZE_T'}

        # 常见的参数名模式（这些不应该被识别为类型）
        param_name_patterns = [
            r'^p[A-Z]',         # pMsg, pBuf, pValue - 指针参数命名习惯
            r'^ps[A-Z]',        # psLocalAddr, psRemoteAddr - 指针到结构体
            r'^puc[A-Z]',       # pucData, pucStr - 指针到unsigned char
            r'^pul[A-Z]',       # pulDataLength, pulHandleTm - 指针到unsigned long
            r'^ph[A-Z]',        # phTimerGrp - 句柄指针
            r'^(IN|OUT|INOUT|IO)$',  # 参数方向修饰符
            r'^PT[A-Z]',        # PTDiamOsAllocMsg - 函数指针类型前缀
        ]

        # 常见的宏/修饰符
        common_macros = {'IN', 'OUT', 'INOUT', 'IO', 'OPTIONAL', 'CONST'}

        external_count = 0
        external_filtered = 0
        for type_name in all_types:
            # 1. 跳过关键字和基础typedef
            if type_name.upper() in keywords or type_name.upper() in basic_typedefs:
                logger.info(f"[数据结构提取] ✗ 过滤关键字/基础typedef: {type_name}")
                external_filtered += 1
                continue

            # 2. 跳过常见宏
            if type_name in common_macros:
                logger.info(f"[数据结构提取] ✗ 过滤宏定义: {type_name}")
                external_filtered += 1
                continue

            # 3. 跳过参数名模式
            is_param_name = False
            for pattern in param_name_patterns:
                if re.match(pattern, type_name):
                    logger.info(f"[数据结构提取] ✗ 过滤参数名: {type_name} (匹配 {pattern})")
                    external_filtered += 1
                    is_param_name = True
                    break

            if is_param_name:
                continue

            # 4. 跳过已添加的
            if type_name in used_ds:
                continue

            # 5. 跳过基础类型模式
            is_basic_type = False
            for pattern in basic_type_patterns:
                if re.match(pattern, type_name):
                    is_basic_type = True
                    logger.info(f"[数据结构提取] ✗ 过滤项目基础类型: {type_name}")
                    external_filtered += 1
                    break

            if not is_basic_type:
                # 添加为外部类型
                used_ds[type_name] = None
                logger.info(f"[数据结构提取] ✓ 外部类型: {type_name}")
                external_count += 1

        logger.info(f"[数据结构提取] 外部类型: 找到 {external_count} 个, 过滤 {external_filtered} 个")
        logger.info(f"[数据结构提取] 总计: {len(used_ds)} 个数据结构 (内部 {internal_count} + 外部 {external_count})")

        return used_ds

    def _extract_types_from_function_body(self, func_name: str) -> set:
        """
        从函数体的 AST 节点中提取实际使用的类型

        提取策略：
        1. 从函数体中查找所有 type_identifier 节点（变量声明、类型转换等）
        2. 从直接调用的函数签名中提取类型

        Args:
            func_name: 函数名

        Returns:
            set: 函数体中使用的类型名称集合
        """
        types = set()

        # 检查是否有 file_boundary 和函数节点信息
        if not self.result.file_boundary:
            logger.debug(f"[函数体类型提取] 无 file_boundary 信息")
            return types

        file_boundary = self.result.file_boundary

        # 检查是否有函数信息
        if not hasattr(file_boundary, 'file_functions') or not file_boundary.file_functions:
            logger.debug(f"[函数体类型提取] file_boundary 无 file_functions")
            return types

        # 检查函数是否在文件中
        if func_name not in file_boundary.file_functions:
            logger.debug(f"[函数体类型提取] 函数 {func_name} 不在 file_functions 中")
            return types

        # 获取函数节点和源代码
        func_info = file_boundary.file_functions[func_name]
        func_node = func_info.get('node')
        source_code = file_boundary.source_code

        if not func_node or not source_code:
            logger.debug(f"[函数体类型提取] 缺少函数节点或源代码")
            return types

        # 从函数体中提取类型
        from ..cpp_parser import CppParser

        # 1. 查找函数体节点
        body_node = func_node.child_by_field_name('body')
        if not body_node:
            logger.debug(f"[函数体类型提取] 函数 {func_name} 无函数体")
            return types

        # 2. 从函数体中查找所有 type_identifier
        type_nodes = CppParser.find_nodes_by_type(body_node, 'type_identifier')
        for type_node in type_nodes:
            type_name = CppParser.get_node_text(type_node, source_code)
            if type_name:
                types.add(type_name)

        # 3. 查找结构体/类类型的限定名（如 struct Foo）
        struct_specifiers = CppParser.find_nodes_by_type(body_node, 'struct_specifier')
        for spec_node in struct_specifiers:
            # 获取结构体名称
            name_node = spec_node.child_by_field_name('name')
            if name_node:
                struct_name = CppParser.get_node_text(name_node, source_code)
                if struct_name:
                    types.add(struct_name)

        logger.debug(f"[函数体类型提取] 从函数体提取到 {len(types)} 个类型: {sorted(types)}")

        return types

