"""
单函数报告生成器 - 生成完整的测试上下文报告

原位置：AnalysisResult.generate_single_function_report() 及相关方法

职责：
- 递归展开函数依赖
- 生成Mock清单
- 提取数据结构
- 提取常量定义
- 提取全局变量
- 提取类型转换关系
- 格式化输出
"""
import sys
from typing import Dict, List, Set, Optional
from ..extractors import ConstantExtractor, SignatureExtractor, StructureExtractor, MacroExtractor, GlobalVariableExtractor, TypeCastExtractor, FunctionImplExtractor
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
        self.constant_extractor = ConstantExtractor(
            header_searcher,
            project_root=project_root,
            file_boundary=result.file_boundary  # 传递file_boundary以复用AST
        )
        self.signature_extractor = SignatureExtractor(header_searcher)

        # StructureExtractor 使用全局搜索
        self.structure_extractor = StructureExtractor(project_root=project_root)

        # MacroExtractor 用于宏展开
        self.macro_extractor = MacroExtractor(project_root=project_root)

        # GlobalVariableExtractor 用于全局变量提取
        self.global_var_extractor = GlobalVariableExtractor()

        # TypeCastExtractor 用于类型转换提取
        self.type_cast_extractor = TypeCastExtractor()

        # FunctionImplExtractor 用于函数实现提取
        self.impl_extractor = FunctionImplExtractor(project_root=project_root)

        # 构建函数暴露状态映射 {函数名: (category, declaration_location)}
        # 使用 file_boundary 中的所有函数信息，而不只是 entry_points（可能被过滤）
        self.function_exposure_map = {}
        self._build_complete_exposure_map()

    def _build_complete_exposure_map(self):
        """
        构建完整的函数暴露状态映射，包含文件中的所有函数

        这个方法复刻了 SingleFileAnalyzer.get_entry_points() 的分类逻辑
        """
        # 优先使用 entry_points（如果有完整的）
        if hasattr(self.result, 'entry_points') and self.result.entry_points:
            for ep in self.result.entry_points:
                self.function_exposure_map[ep.name] = (ep.category, ep.declaration_location)

        # 如果 file_boundary 中有更多函数信息，补充到映射中
        if (hasattr(self.result, 'file_boundary') and self.result.file_boundary and
            hasattr(self.result.file_boundary, 'file_functions') and self.result.file_boundary.file_functions):

            from pathlib import Path

            # 查找对应的头文件中的函数声明
            target_file_path = Path(self.result.project_root) / self.result.target_file
            header_functions = self._find_header_declarations(str(target_file_path))

            # 为每个函数分类
            for func_name, func_info in self.result.file_boundary.file_functions.items():
                # 如果已经在映射中，跳过
                if func_name in self.function_exposure_map:
                    continue

                is_static = func_info.get('is_static', False)

                # 分类逻辑（与 SingleFileAnalyzer.get_entry_points() 一致）
                if is_static:
                    category = 'INTERNAL'
                    decl_location = ""
                elif func_name in header_functions:
                    category = 'API'
                    decl_location = header_functions[func_name]
                else:
                    category = 'EXPORTED'
                    decl_location = ""

                self.function_exposure_map[func_name] = (category, decl_location)
                logger.info(f"[暴露状态映射] {func_name}: {category}")

    def _find_header_declarations(self, cpp_file_path: str) -> dict:
        """
        查找cpp文件对应的头文件中的函数声明
        使用简单的文本搜索
        """
        from pathlib import Path

        header_funcs = {}
        cpp_path = Path(cpp_file_path)

        if not cpp_path.is_absolute():
            cpp_path = cpp_path.resolve()

        possible_headers = [
            cpp_path.with_suffix('.h'),
            cpp_path.with_suffix('.hpp'),
        ]

        # 获取要搜索的函数列表
        search_functions = set()
        if (hasattr(self.result, 'file_boundary') and self.result.file_boundary and
            hasattr(self.result.file_boundary, 'file_functions')):
            search_functions = set(self.result.file_boundary.file_functions.keys())

        for header_path in possible_headers:
            if header_path.exists():
                try:
                    with open(header_path, 'r', encoding='utf-8', errors='ignore') as f:
                        header_content = f.read()

                    # 简单的文本搜索
                    for func_name in search_functions:
                        if func_name in header_content:
                            for line in header_content.split('\n'):
                                # 跳过注释行
                                if line.strip().startswith('//') or line.strip().startswith('/*'):
                                    continue

                                # 检查行是否包含函数名且看起来像声明
                                if func_name in line and '(' in line:
                                    header_funcs[func_name] = str(header_path)
                                    logger.info(f"[头文件检测] 发现 {func_name} 在 {header_path.name}")
                                    break

                    if header_funcs:
                        logger.info(f"[头文件检测] 在 {header_path.name} 中找到 {len(header_funcs)} 个函数声明")
                    break
                except Exception as e:
                    logger.debug(f"[头文件检测] 读取 {header_path} 失败: {e}")
                    continue

        return header_funcs

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

        # === 提取并展示函数实现（放在最前面） ===
        func_impl = self.impl_extractor.extract(
            func_name,
            self.result.target_file,
            self.result.file_boundary
        )

        if func_impl:
            lines.append("=" * 80)
            lines.append(f"[函数实现] {func_name}")
            lines.append("=" * 80)
            lines.append(func_impl)
            lines.append("")
            lines.append("=" * 80)
            lines.append("[分析信息]")
            lines.append("=" * 80)
        else:
            logger.warning(f"[函数实现] 未能提取 {func_name} 的实现代码")

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

        # 提取全局变量
        from pathlib import Path
        target_file_path = Path(self.result.project_root) / self.result.target_file
        global_vars = self.global_var_extractor.extract_from_function(
            str(target_file_path),
            func_name
        )

        # 提取类型转换关系
        type_casts = self.type_cast_extractor.extract_from_function(
            str(target_file_path),
            func_name
        )

        # 过滤掉已经在常量定义中的项（避免重复）
        if constants and global_vars:
            for const_name in constants.keys():
                if const_name in global_vars:
                    del global_vars[const_name]
                    logger.info(f"[全局变量] 过滤常量: {const_name}")

        if constants:
            lines.append("\n[常量定义]")
            for const_name, const_def in sorted(constants.items()):
                if const_def:
                    lines.append(f"{const_name}: {const_def}")

                    # 如果是函数宏（包含括号），尝试展开完整定义
                    if '(' in const_name or self.macro_extractor.is_likely_macro(const_name):
                        macro_expansion = self.macro_extractor.extract_macro_definition(
                            const_name,
                            self.result.target_file
                        )
                        if macro_expansion and len(macro_expansion) > len(const_def) + 20:
                            # 只有当展开内容显著更长时才显示（避免重复）
                            # 多行宏需要格式化
                            if '\n' in macro_expansion:
                                lines.append(f"  /* 宏展开: */")
                                for line in macro_expansion.split('\n'):
                                    lines.append(f"  {line}")
                            else:
                                lines.append(f"  /* 宏展开: {macro_expansion} */")
                            logger.info(f"[宏展开输出] {const_name}: 已展开")

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

                        # 展开定义中的宏
                        definition = self._expand_macros_in_definition(ds_info['definition'])
                        lines.append(definition)
                    else:
                        lines.append(f"\n{ds} (内部)")

            # 尝试从头文件读取外部数据结构
            if external_ds:
                for ds in sorted(external_ds):
                    definition = self.structure_extractor.extract(ds, self.result.target_file)
                    if definition:
                        lines.append(f"\n{ds} (外部):")

                        # 展开定义中的宏
                        definition = self._expand_macros_in_definition(definition)
                        lines.append(definition)

        # 显示类型转换关系（如果有）
        if type_casts and type_casts.get('casts'):
            lines.append("\n[类型转换关系]")

            # 按源变量分组
            source_groups = {}
            for cast in type_casts['casts']:
                source = cast['source_var'] or '未知'
                if source not in source_groups:
                    source_groups[source] = []
                source_groups[source].append(cast)

            for source_var, casts in sorted(source_groups.items()):
                lines.append(f"  {source_var} 的转换:")
                for cast in casts:
                    target = cast['target_var']
                    target_type = cast['target_type']
                    line_num = cast['line']

                    # 添加使用信息（访问的字段）
                    usage_info = ""
                    if target in type_casts.get('usage', {}):
                        usage = type_casts['usage'][target]
                        if usage.get('fields'):
                            fields_str = ', '.join(usage['fields'])
                            usage_info = f" → 访问字段: {fields_str}"

                    lines.append(f"    → {target} ({target_type}*) [行{line_num}]{usage_info}")

        # 显示全局变量（如果有）
        if global_vars:
            lines.append("\n[全局变量]")
            for var_name in sorted(global_vars.keys()):
                info = global_vars[var_name]
                lines.append(f"  {var_name}:")
                lines.append(f"    类型: {info['type']}")
                lines.append(f"    定义: {info['definition']}")
                lines.append(f"    位置: {info['file']}:{info['line']}")

        return "\n".join(lines)

    def _get_exposure_info(self, func_name: str) -> str:
        """
        获取函数暴露状态信息

        Returns:
            暴露状态说明字符串
        """
        if func_name not in self.function_exposure_map:
            return ""

        category, decl_location = self.function_exposure_map[func_name]

        if category == 'API':
            # 在头文件中声明，是公开API
            if decl_location:
                # decl_location 是完整路径，提取文件名
                from pathlib import Path
                header_file = Path(decl_location).name
                return f"[已暴露: {header_file}]"
            else:
                return "[已暴露: 头文件]"
        elif category == 'INTERNAL':
            # 内部函数（static或匿名命名空间）
            return "[内部函数: static，不可extern]"
        elif category == 'EXPORTED':
            # 在cpp中定义但没有在头文件中声明
            return "[未暴露: 其他文件使用需要extern声明]"

        return ""

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

        # === 1. 提取函数实现（对于内部依赖函数） ===
        is_internal_dep = bool(number_prefix)
        if is_internal_dep:
            func_impl = self.impl_extractor.extract(
                func_name,
                self.result.target_file,
                self.result.file_boundary
            )
            if func_impl:
                lines.append("")
                lines.append("=" * 80)
                lines.append(f"[函数实现] {func_name}")
                lines.append("=" * 80)
                lines.append(func_impl)
                lines.append("")
                lines.append("=" * 80)
                lines.append("[分析信息]")
                lines.append("=" * 80)

        # === 2. 函数签名 ===
        if number_prefix:
            # 内部依赖函数：添加 [内部] 标记
            lines.append(f"\n{number_prefix} {func_name} [内部]")
        else:
            # 主函数
            lines.append(f"函数: {func_name}")

        if func_name in self.result.function_signatures:
            sig = self.result.function_signatures[func_name]
            sig_part = sig.split('//')[0].strip()
            if '//' in sig:
                location = sig.split('//')[-1].strip()
                lines.append(f"{sig_part} // {location}")
            else:
                lines.append(sig_part)

        # === 3. 显示函数暴露状态 ===
        exposure_info = self._get_exposure_info(func_name)
        if exposure_info:
            lines.append(exposure_info)

        # === 4. 分支复杂度分析（仅当圈复杂度>5时） ===
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

        # === 5. 收集直接依赖 ===
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

        # === 6. Mock清单（仅显示业务外部依赖，并搜索签名） ===
        if direct_external_deps:
            # 使用分类器分类外部函数
            classified = self.result.external_classifier.classify(direct_external_deps)

            print(f"{indent}[Mock生成] 外部函数分类: 业务{len(classified.get('business', []))}个, "
                  f"宏{len(classified.get('macros', []))}个, "
                  f"标准库{len(classified.get('standard_library', []))}个, "
                  f"日志{len(classified.get('logging_utility', []))}个", file=sys.stderr)

            # 仅显示业务外部依赖（隐藏标准库、日志函数和宏定义）
            if classified['business']:
                lines.append("Mock: (外部函数,需要Mock)")
                for func in sorted(classified['business']):
                    # 尝试搜索函数签名
                    signature = self.signature_extractor.extract(func, self.result.target_file)
                    if signature:
                        lines.append(f"  {func} [外部]: {signature}")
                        logger.info(f"{indent}[Mock生成]   ✓ {func}: 找到签名")
                    else:
                        lines.append(f"  {func} [外部]")
                        logger.info(f"{indent}[Mock生成]   ✗ {func}: 未找到签名")
            else:
                logger.info(f"{indent}[Mock生成] 无业务外部依赖（已过滤宏、标准库和日志）")
        else:
            logger.info(f"{indent}[Mock生成] 无外部依赖")

        # === 7. 数据结构 - 只列出名称，收集到 all_data_structures ===
        used_data_structures = self._extract_data_structures_from_single_function(func_name)

        if used_data_structures:
            # 添加到全局收集set
            all_data_structures.update(used_data_structures.keys())
            # 只列出名称
            lines.append(f"数据结构: {', '.join(sorted(used_data_structures.keys()))}")

        # === 8. 递归显示内部依赖函数 ===
        if direct_internal_deps:
            # 仅在主函数时添加章节标题
            if not number_prefix:
                lines.append("\n[内部依赖函数] (同文件定义,不需要Mock)")

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

    def _expand_macros_in_definition(self, definition: str) -> str:
        """
        展开数据结构定义中的宏

        Args:
            definition: 原始数据结构定义

        Returns:
            展开宏后的定义
        """
        import re

        lines = definition.split('\n')
        result_lines = []

        for line in lines:
            # 检查是否有独立的宏标识符（全大写+下划线）
            # 匹配类似 "    VOS_MSG_HEADER" 或 "    VOS_MSG_HEADER  /* comment */"
            match = re.match(r'^(\s*)([A-Z][A-Z0-9_]+)\s*(\/\*.*\*\/)?$', line.strip())
            if match:
                indent = re.match(r'^(\s*)', line).group(1)  # 保留原缩进
                macro_name = match.group(2)
                comment = match.group(3) or ''  # 保留注释

                logger.debug(f"[宏展开] 检测到结构体宏: {macro_name}")

                # 尝试展开这个宏
                expansion = self.macro_extractor.extract_struct_macro(macro_name)
                if expansion:
                    # 添加注释标记
                    result_lines.append(f"{indent}/* {macro_name} 展开: */")
                    # 添加展开内容（保持原缩进）
                    for exp_line in expansion.split('\n'):
                        result_lines.append(f"{indent}{exp_line}")
                    # 如果原行有注释，也保留
                    if comment:
                        result_lines.append(f"{indent}{comment}")
                    logger.info(f"[宏展开] ✓ {macro_name}: 已展开到结构体定义中")
                else:
                    # 未找到展开，保留原行
                    result_lines.append(line)
                    logger.debug(f"[宏展开] ✗ {macro_name}: 未找到定义")
            else:
                # 普通行，直接保留
                result_lines.append(line)

        return '\n'.join(result_lines)

