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
                        # 对于switch，显示case值
                        if cond.branch_type == 'switch' and cond.suggestions:
                            for sug in cond.suggestions:
                                lines.append(f"     {sug}")

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

        # 3. 如果有边界分析结果，添加边界中检测到的外部数据结构
        boundary_types_count = 0
        if self.result.file_boundary and hasattr(self.result.file_boundary, 'external_data_structures'):
            boundary_types = self.result.file_boundary.external_data_structures
            all_types.update(boundary_types)
            boundary_types_count = len(boundary_types)
            logger.info(f"[数据结构提取] 边界分析: 找到 {boundary_types_count} 个外部类型")

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

        external_count = 0
        external_filtered = 0
        for type_name in all_types:
            # 跳过关键字和基础typedef
            if type_name.upper() in keywords or type_name.upper() in basic_typedefs:
                logger.info(f"[数据结构提取] ✗ 过滤关键字/基础typedef: {type_name}")
                external_filtered += 1
                continue

            # 跳过已添加的
            if type_name in used_ds:
                continue

            # 跳过基础类型模式
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
