"""
Main C++ Project Analyzer - integrates all components.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict

from .project_indexer import ProjectIndexer
from .entry_point_classifier import EntryPointClassifier, EntryPointInfo
from .call_chain_tracer import CallChainTracer, CallNode
from .data_structure_analyzer import DataStructureAnalyzer, DataStructureInfo
from .analysis_modes import AnalysisMode, get_mode_config, AnalysisModeConfig
from .single_file_analyzer import SingleFileAnalyzer, FileBoundary
from .branch_analyzer import BranchAnalyzer, format_branch_analysis
from .external_classifier import ExternalFunctionClassifier, format_classified_externals


@dataclass
class AnalysisResult:
    """Complete analysis result for a C++ file."""
    target_file: str
    entry_points: List[EntryPointInfo]
    call_chains: Dict[str, CallNode]
    function_signatures: Dict[str, str]  # function_name -> signature
    data_structures: Dict[str, DataStructureInfo]
    mode: str = "full_project"  # 分析模式
    file_boundary: Optional[FileBoundary] = None  # 单文件边界信息（仅在 single_file_boundary 模式）
    branch_analyses: Dict[str, 'BranchAnalysis'] = None  # 函数分支分析结果（func_name -> BranchAnalysis）
    external_classifier: Optional['ExternalFunctionClassifier'] = None  # 外部函数分类器

    def format_report(self) -> str:
        """Format the complete analysis as a readable report."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"C++ Static Analysis Report")
        lines.append(f"Target File: {self.target_file}")
        lines.append(f"Analysis Mode: {self.mode}")
        lines.append("=" * 80)

        # 如果是单文件边界模式，添加边界信息
        if self.mode == "single_file_boundary" and self.file_boundary:
            lines.append("\n" + "=" * 80)
            lines.append("FILE BOUNDARY ANALYSIS")
            lines.append("=" * 80)
            lines.append(f"\nInternal Functions ({len(self.file_boundary.internal_functions)}):")
            for func in sorted(self.file_boundary.internal_functions):
                lines.append(f"  • {func}")

            lines.append(f"\nExternal Functions Called ({len(self.file_boundary.external_functions)}):")
            for func in sorted(self.file_boundary.external_functions):
                lines.append(f"  • {func} [EXTERNAL]")

            lines.append(f"\nInternal Data Structures ({len(self.file_boundary.internal_data_structures)}):")
            for ds in sorted(self.file_boundary.internal_data_structures):
                lines.append(f"  • {ds}")

            lines.append(f"\nExternal Data Structures Used ({len(self.file_boundary.external_data_structures)}):")
            for ds in sorted(self.file_boundary.external_data_structures):
                lines.append(f"  • {ds} [EXTERNAL]")
            lines.append("")

        # Section 1: Entry Points
        lines.append("\n" + "=" * 80)
        lines.append("1. ENTRY POINT FUNCTIONS")
        lines.append("=" * 80)

        api_functions = [ep for ep in self.entry_points if ep.category == 'API']
        internal_functions = [ep for ep in self.entry_points if ep.category == 'INTERNAL']
        exported_functions = [ep for ep in self.entry_points if ep.category == 'EXPORTED']

        if api_functions:
            lines.append("\nAPI Functions (declared in headers):")
            for ep in api_functions:
                lines.append(f"  • {ep.name}")
                lines.append(f"    Location: {ep.file_path}:{ep.line_number}")
                if ep.declaration_location:
                    lines.append(f"    Declared in: {ep.declaration_location}")
                lines.append(f"    Signature: {ep.signature[:100]}...")

        if internal_functions:
            lines.append("\nInternal Functions (file-local):")
            for ep in internal_functions:
                lines.append(f"  • {ep.name}")
                lines.append(f"    Location: {ep.file_path}:{ep.line_number}")

        if exported_functions:
            lines.append("\nExported Functions (defined in .cpp, may be used externally):")
            for ep in exported_functions:
                lines.append(f"  • {ep.name}")
                lines.append(f"    Location: {ep.file_path}:{ep.line_number}")

        # Section 2: Call Chains
        lines.append("\n" + "=" * 80)
        lines.append("2. FUNCTION CALL CHAINS")
        lines.append("=" * 80)

        if self.call_chains:
            for func_name, call_tree in self.call_chains.items():
                lines.append(f"\nCall chain from: {func_name}")
                lines.append("-" * 40)
                if call_tree:
                    tracer = CallChainTracer(None)  # Just for formatting
                    lines.append(tracer.format_call_tree(call_tree))
                else:
                    lines.append("  (No calls or could not trace)")
        else:
            lines.append("\nNo call chains traced.")

        # Section 3: Function Signatures
        lines.append("\n" + "=" * 80)
        lines.append("3. FUNCTION SIGNATURES")
        lines.append("=" * 80)

        if self.function_signatures:
            for func_name in sorted(self.function_signatures.keys()):
                sig = self.function_signatures[func_name]
                lines.append(f"\n{func_name}:")
                lines.append(f"  {sig}")
        else:
            lines.append("\nNo function signatures collected.")

        # Section 4: Data Structures
        lines.append("\n" + "=" * 80)
        lines.append("4. DATA STRUCTURES")
        lines.append("=" * 80)

        if self.data_structures:
            analyzer = DataStructureAnalyzer(None)  # Just for formatting
            lines.append("\n" + analyzer.format_data_structures(self.data_structures))
        else:
            lines.append("\nNo data structures found or analyzed.")

        lines.append("\n" + "=" * 80)
        lines.append("End of Report")
        lines.append("=" * 80)

        return "\n".join(lines)

    def to_json(self) -> str:
        """Export analysis result as JSON."""
        # Convert to serializable format
        data = {
            'target_file': self.target_file,
            'entry_points': [
                {
                    'name': ep.name,
                    'category': ep.category,
                    'file_path': ep.file_path,
                    'line_number': ep.line_number,
                    'signature': ep.signature,
                    'declaration_location': ep.declaration_location
                }
                for ep in self.entry_points
            ],
            'call_chains': {
                name: self._call_node_to_dict(tree)
                for name, tree in self.call_chains.items()
            },
            'function_signatures': self.function_signatures,
            'data_structures': {
                name: {
                    'name': ds.name,
                    'type': ds.type,
                    'file_path': ds.file_path,
                    'line_number': ds.line_number,
                    'definition': ds.definition,
                    'used_by_functions': list(ds.used_by_functions),
                    'used_in_files': list(ds.used_in_files)
                }
                for name, ds in self.data_structures.items()
            }
        }
        return json.dumps(data, indent=2)

    def _call_node_to_dict(self, node: Optional[CallNode]) -> Optional[dict]:
        """Convert CallNode tree to dictionary."""
        if not node:
            return None

        return {
            'function_name': node.function_name,
            'file_path': node.file_path,
            'line_number': node.line_number,
            'signature': node.signature,
            'called_from_line': node.called_from_line,
            'is_external': node.is_external,
            'is_recursive': node.is_recursive,
            'children': [self._call_node_to_dict(child) for child in node.children]
        }

    def classify_functions_by_module(self) -> Dict[str, List[str]]:
        """根据函数名前缀自动分类到模块"""
        from .call_chain_tracer import CallChainTracer

        modules = {
            'drawing': [],      # 绘图相关
            'font': [],         # 字体相关
            'style': [],        # 样式相关
            'texture': [],      # 纹理相关
            'path': [],         # 路径相关
            'primitive': [],    # 基础图元
            'internal': [],     # 内部工具函数
            'other': []         # 其他
        }

        # 关键词映射
        keywords = {
            'drawing': ['Draw', 'Render', 'Add'],
            'font': ['Font', 'Glyph', 'Text', 'Char'],
            'style': ['Style', 'Color'],
            'texture': ['Texture', 'Image', 'Pixel'],
            'path': ['Path', 'Arc', 'Bezier'],
            'primitive': ['Rect', 'Circle', 'Line', 'Triangle', 'Quad', 'Polygon', 'Polyline', 'Ngon', 'Ellipse'],
            'internal': ['_', 'Decode', 'stb_', 'stb__', 'Decompress', 'Unpack']
        }

        all_functions = set(self.file_boundary.internal_functions) if self.file_boundary else set(self.function_signatures.keys())

        for func_name in all_functions:
            classified = False
            for module, kws in keywords.items():
                if any(kw in func_name for kw in kws):
                    modules[module].append(func_name)
                    classified = True
                    break

            if not classified:
                modules['other'].append(func_name)

        # 移除空模块
        return {k: sorted(v) for k, v in modules.items() if v}

    def generate_summary_report(self) -> str:
        """生成摘要报告"""
        lines = []
        lines.append("=" * 80)
        lines.append("📊 分析摘要报告")
        lines.append("=" * 80)
        lines.append(f"目标文件: {self.target_file}")
        lines.append(f"分析模式: {self.mode}")
        lines.append("")

        # 边界统计
        if self.file_boundary:
            lines.append("=" * 80)
            lines.append("文件边界统计")
            lines.append("=" * 80)
            lines.append(f"内部函数: {len(self.file_boundary.internal_functions)} 个")
            lines.append(f"外部函数调用: {len(self.file_boundary.external_functions)} 个")
            lines.append(f"内部数据结构: {len(self.file_boundary.internal_data_structures)} 个")
            lines.append(f"外部数据结构: {len(self.file_boundary.external_data_structures)} 个")
            lines.append("")

        # 功能模块分类
        modules = self.classify_functions_by_module()
        if modules:
            lines.append("=" * 80)
            lines.append("功能模块分类")
            lines.append("=" * 80)
            for module, functions in modules.items():
                module_names = {
                    'drawing': '绘图模块',
                    'font': '字体管理',
                    'style': '样式配置',
                    'texture': '纹理处理',
                    'path': '路径生成',
                    'primitive': '几何图元',
                    'internal': '内部工具',
                    'other': '其他功能'
                }
                lines.append(f"\n[{module_names.get(module, module)}] ({len(functions)} 个函数)")
                # 只显示前 10 个，其他用省略号
                for func in functions[:10]:
                    lines.append(f"  • {func}")
                if len(functions) > 10:
                    lines.append(f"  ... 还有 {len(functions) - 10} 个函数")
                lines.append(f"  → 详见: functions/{module}.txt")

        # 调用链复杂度分析
        if self.call_chains:
            lines.append("\n" + "=" * 80)
            lines.append("复杂度分析")
            lines.append("=" * 80)

            depths = []
            for func_name, call_tree in self.call_chains.items():
                depth = self._get_call_depth(call_tree)
                depths.append((func_name, depth))

            if depths:
                depths.sort(key=lambda x: x[1], reverse=True)
                avg_depth = sum(d for _, d in depths) / len(depths)
                max_func, max_depth = depths[0]

                lines.append(f"平均调用深度: {avg_depth:.1f} 层")
                lines.append(f"最深调用链: {max_func} ({max_depth} 层)")
                lines.append("")
                lines.append("调用深度 Top 5:")
                for func, depth in depths[:5]:
                    lines.append(f"  • {func}: {depth} 层")

        # 外部依赖摘要
        if self.file_boundary and self.file_boundary.external_functions:
            lines.append("\n" + "=" * 80)
            lines.append("外部依赖摘要 (Top 10)")
            lines.append("=" * 80)
            ext_funcs = sorted(self.file_boundary.external_functions)[:10]
            for func in ext_funcs:
                lines.append(f"  • {func}")
            if len(self.file_boundary.external_functions) > 10:
                lines.append(f"  ... 还有 {len(self.file_boundary.external_functions) - 10} 个外部函数")
            lines.append("\n  → 完整列表见: boundary.txt")

        lines.append("\n" + "=" * 80)
        lines.append("详细信息")
        lines.append("=" * 80)
        lines.append("  📋 boundary.txt          - 完整的文件边界分析")
        lines.append("  📁 functions/            - 按模块分类的函数列表")
        lines.append("  🔗 call_chains.txt       - 所有函数的调用链")
        lines.append("  📦 data_structures.txt   - 数据结构详情")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _get_call_depth(self, node: Optional[CallNode], current_depth: int = 0) -> int:
        """计算调用链的深度"""
        if not node or not node.children:
            return current_depth

        max_child_depth = current_depth
        for child in node.children:
            child_depth = self._get_call_depth(child, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth

    def generate_boundary_report(self) -> str:
        """生成边界分析详细报告"""
        if not self.file_boundary:
            return "No boundary information available."

        lines = []
        lines.append("=" * 80)
        lines.append("文件边界详细分析")
        lines.append("=" * 80)
        lines.append(f"文件: {self.target_file}")
        lines.append("")

        lines.append("=" * 80)
        lines.append(f"内部函数 ({len(self.file_boundary.internal_functions)} 个)")
        lines.append("=" * 80)
        for func in sorted(self.file_boundary.internal_functions):
            lines.append(f"  • {func}")

        lines.append("\n" + "=" * 80)
        lines.append(f"外部函数调用 ({len(self.file_boundary.external_functions)} 个)")
        lines.append("=" * 80)
        for func in sorted(self.file_boundary.external_functions):
            lines.append(f"  • {func}")

        lines.append("\n" + "=" * 80)
        lines.append(f"内部数据结构 ({len(self.file_boundary.internal_data_structures)} 个)")
        lines.append("=" * 80)
        for ds in sorted(self.file_boundary.internal_data_structures):
            lines.append(f"  • {ds}")

        lines.append("\n" + "=" * 80)
        lines.append(f"外部数据结构 ({len(self.file_boundary.external_data_structures)} 个)")
        lines.append("=" * 80)
        for ds in sorted(self.file_boundary.external_data_structures):
            lines.append(f"  • {ds}")

        return "\n".join(lines)

    def generate_call_chains_report(self) -> str:
        """生成所有调用链报告"""
        lines = []
        lines.append("=" * 80)
        lines.append("函数调用链详细报告")
        lines.append("=" * 80)
        lines.append(f"文件: {self.target_file}")
        lines.append(f"共 {len(self.call_chains)} 个函数的调用链")
        lines.append("")

        if self.call_chains:
            from .call_chain_tracer import CallChainTracer
            tracer = CallChainTracer(None)

            for func_name in sorted(self.call_chains.keys()):
                call_tree = self.call_chains[func_name]
                lines.append("=" * 80)
                lines.append(f"调用链: {func_name}")
                lines.append("=" * 80)
                if call_tree:
                    lines.append(tracer.format_call_tree(call_tree))
                else:
                    lines.append("  (无调用)")
                lines.append("")

        return "\n".join(lines)

    def generate_data_structures_report(self) -> str:
        """生成数据结构详细报告"""
        lines = []
        lines.append("=" * 80)
        lines.append("数据结构详细报告")
        lines.append("=" * 80)
        lines.append(f"文件: {self.target_file}")
        lines.append("")

        if self.data_structures:
            from .data_structure_analyzer import DataStructureAnalyzer
            analyzer = DataStructureAnalyzer(None)
            lines.append(analyzer.format_data_structures(self.data_structures))
        else:
            lines.append("未发现数据结构定义")

        return "\n".join(lines)

    def generate_functions_by_module_report(self, module: str, functions: List[str]) -> str:
        """生成单个模块的函数详细报告"""
        lines = []
        module_names = {
            'drawing': '绘图模块',
            'font': '字体管理',
            'style': '样式配置',
            'texture': '纹理处理',
            'path': '路径生成',
            'primitive': '几何图元',
            'internal': '内部工具',
            'other': '其他功能'
        }

        lines.append("=" * 80)
        lines.append(f"{module_names.get(module, module)} - 函数列表")
        lines.append("=" * 80)
        lines.append(f"共 {len(functions)} 个函数")
        lines.append("")

        for func_name in functions:
            lines.append("=" * 80)
            lines.append(f"函数: {func_name}")
            lines.append("=" * 80)

            # 函数签名
            if func_name in self.function_signatures:
                lines.append(f"签名: {self.function_signatures[func_name]}")

            # 调用链（简化版）
            if func_name in self.call_chains:
                call_tree = self.call_chains[func_name]
                depth = self._get_call_depth(call_tree)
                lines.append(f"调用深度: {depth} 层")

                # 列出直接调用的函数
                if call_tree and call_tree.children:
                    lines.append(f"直接调用 ({len(call_tree.children)} 个):")
                    for child in call_tree.children[:10]:  # 只显示前 10 个
                        status = "[EXTERNAL]" if child.is_external else "[内部]"
                        lines.append(f"  • {child.function_name} {status}")
                    if len(call_tree.children) > 10:
                        lines.append(f"  ... 还有 {len(call_tree.children) - 10} 个调用")

            lines.append("")

        return "\n".join(lines)

    def generate_simple_summary_report(self) -> str:
        """生成简化版摘要报告（无分类信息）"""
        lines = []
        lines.append("=" * 80)
        lines.append("📊 分析摘要报告")
        lines.append("=" * 80)
        lines.append(f"目标文件: {self.target_file}")
        lines.append(f"分析模式: {self.mode}")
        lines.append("")

        # 边界统计
        if self.file_boundary:
            lines.append("=" * 80)
            lines.append("文件边界统计")
            lines.append("=" * 80)
            lines.append(f"内部函数: {len(self.file_boundary.internal_functions)} 个")
            lines.append(f"外部函数调用: {len(self.file_boundary.external_functions)} 个")
            lines.append(f"内部数据结构: {len(self.file_boundary.internal_data_structures)} 个")
            lines.append(f"外部数据结构: {len(self.file_boundary.external_data_structures)} 个")
            lines.append("")

        # 调用链复杂度分析
        if self.call_chains:
            lines.append("=" * 80)
            lines.append("复杂度分析")
            lines.append("=" * 80)

            depths = []
            for func_name, call_tree in self.call_chains.items():
                depth = self._get_call_depth(call_tree)
                depths.append((func_name, depth))

            if depths:
                depths.sort(key=lambda x: x[1], reverse=True)
                avg_depth = sum(d for _, d in depths) / len(depths)
                max_func, max_depth = depths[0]

                lines.append(f"平均调用深度: {avg_depth:.1f} 层")
                lines.append(f"最深调用链: {max_func} ({max_depth} 层)")
                lines.append("")
                lines.append("调用深度 Top 5:")
                for func, depth in depths[:5]:
                    lines.append(f"  • {func}: {depth} 层")

        # 外部依赖摘要
        if self.file_boundary and self.file_boundary.external_functions:
            lines.append("\n" + "=" * 80)
            lines.append("外部依赖摘要 (Top 10)")
            lines.append("=" * 80)
            ext_funcs = sorted(self.file_boundary.external_functions)[:10]
            for func in ext_funcs:
                lines.append(f"  • {func}")
            if len(self.file_boundary.external_functions) > 10:
                lines.append(f"  ... 还有 {len(self.file_boundary.external_functions) - 10} 个外部函数")
            lines.append("\n  → 完整列表见: boundary.txt")

        lines.append("\n" + "=" * 80)
        lines.append("详细信息")
        lines.append("=" * 80)
        lines.append("  📋 boundary.txt          - 完整的文件边界分析")
        lines.append("  📁 functions/            - 每个函数的独立详情文件")
        lines.append("  🔗 call_chains.txt       - 所有函数的调用链")
        lines.append("  📦 data_structures.txt   - 数据结构详情")
        lines.append("=" * 80)

        return "\n".join(lines)

    def generate_all_functions_report(self) -> str:
        """生成所有函数的详情报告（单文件，无分类）"""
        lines = []
        lines.append("=" * 80)
        lines.append("所有函数详情")
        lines.append("=" * 80)
        lines.append(f"文件: {self.target_file}")

        all_functions = sorted(self.file_boundary.internal_functions) if self.file_boundary else sorted(self.function_signatures.keys())
        lines.append(f"共 {len(all_functions)} 个函数")
        lines.append("")

        for func_name in all_functions:
            lines.append("=" * 80)
            lines.append(f"函数: {func_name}")
            lines.append("=" * 80)

            # 函数签名
            if func_name in self.function_signatures:
                lines.append(f"签名: {self.function_signatures[func_name]}")

            # 调用链（简化版）
            if func_name in self.call_chains:
                call_tree = self.call_chains[func_name]
                depth = self._get_call_depth(call_tree)
                lines.append(f"调用深度: {depth} 层")

                # 列出直接调用的函数
                if call_tree and call_tree.children:
                    lines.append(f"直接调用 ({len(call_tree.children)} 个):")
                    for child in call_tree.children[:20]:  # 显示前 20 个
                        status = "[EXTERNAL]" if child.is_external else "[内部]"
                        lines.append(f"  • {child.function_name} {status}")
                    if len(call_tree.children) > 20:
                        lines.append(f"  ... 还有 {len(call_tree.children) - 20} 个调用")

            lines.append("")

        return "\n".join(lines)

    def generate_single_function_report(self, func_name: str) -> str:
        """生成单个函数的完整测试上下文报告（递归展开所有内部依赖）"""
        lines = []
        visited = set()
        all_data_structures = set()  # 收集所有使用的数据结构
        all_external_funcs = set()   # 收集所有外部函数（用于常量提取）

        # 递归生成主函数及其所有内部依赖
        self._generate_recursive_function_info(func_name, lines, "", visited, all_data_structures, all_external_funcs)

        # 提取并展示常量/宏定义
        constants = self._extract_constants_from_function(func_name)
        if constants:
            lines.append("\n[常量定义]")
            for const_name, const_def in sorted(constants.items()):
                if const_def:
                    lines.append(f"{const_name}: {const_def}")

        # 统一展示数据结构定义章节
        if all_data_structures:
            lines.append("\n[数据结构]")

            # 分类：内部定义 vs 外部引用
            internal_ds = [ds for ds in all_data_structures if ds in self.data_structures]
            external_ds = [ds for ds in all_data_structures if ds not in self.data_structures]

            # 显示内部定义的数据结构（有完整代码）
            if internal_ds:
                for ds in sorted(internal_ds):
                    if self.file_boundary and hasattr(self.file_boundary, 'file_data_structures') and ds in self.file_boundary.file_data_structures:
                        ds_info = self.file_boundary.file_data_structures[ds]
                        lines.append(f"\n{ds} ({ds_info['type']}, 内部 {self.target_file}:{ds_info['line']}):")
                        lines.append(ds_info['definition'])
                    else:
                        lines.append(f"\n{ds} (内部)")

            # 尝试从头文件读取外部数据结构
            if external_ds:
                for ds in sorted(external_ds):
                    definition = self._try_read_external_data_structure(ds)
                    if definition:
                        lines.append(f"\n{ds} (外部):")
                        lines.append(definition)

        return "\n".join(lines)

    def _generate_recursive_function_info(self, func_name: str, lines: List[str], number_prefix: str, visited: Set[str], all_data_structures: Set[str], all_external_funcs: Set[str]):
        """递归生成函数信息（带序号层级）"""
        # 防止循环依赖
        if func_name in visited:
            return
        visited.add(func_name)

        # === 1. 函数签名 ===
        if number_prefix:
            lines.append(f"\n{number_prefix} {func_name}")
        else:
            lines.append(f"函数: {func_name}")

        if func_name in self.function_signatures:
            sig = self.function_signatures[func_name]
            sig_part = sig.split('//')[0].strip()
            if '//' in sig:
                location = sig.split('//')[-1].strip()
                lines.append(f"{sig_part} // {location}")
            else:
                lines.append(sig_part)

        # === 2. 分支复杂度分析（仅当圈复杂度>5时） ===
        if hasattr(self, 'branch_analyses') and self.branch_analyses and func_name in self.branch_analyses:
            branch_analysis = self.branch_analyses[func_name]
            if branch_analysis.cyclomatic_complexity > 5:
                # 简化版分支信息
                lines.append(f"圈复杂度: {branch_analysis.cyclomatic_complexity}")
                if branch_analysis.conditions:
                    lines.append("关键分支:")

                    # 优先显示switch（包含case信息），然后显示if
                    switch_conditions = [c for c in branch_analysis.conditions if c.branch_type == 'switch']
                    other_conditions = [c for c in branch_analysis.conditions if c.branch_type != 'switch']

                    # 显示所有条件（不截断）
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

        if func_name in self.call_chains:
            call_tree = self.call_chains[func_name]
            if call_tree and call_tree.children:
                for child in call_tree.children:
                    if child.is_external:
                        direct_external_deps.add(child.function_name)
                        all_external_funcs.add(child.function_name)  # 收集到全局
                    else:
                        direct_internal_deps.append(child.function_name)

        # === 4. Mock清单（仅显示业务外部依赖，并搜索签名） ===
        if direct_external_deps:
            # 使用分类器分类外部函数
            classified = self.external_classifier.classify(direct_external_deps)

            # 仅显示业务外部依赖（隐藏标准库和日志函数）
            if classified['business']:
                lines.append("Mock:")
                for func in sorted(classified['business']):
                    # 尝试搜索函数签名
                    signature = self._search_function_signature(func)
                    if signature:
                        lines.append(f"  {func}: {signature}")
                    else:
                        lines.append(f"  {func}")

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
                self._generate_recursive_function_info(dep_func, lines, new_prefix, visited, all_data_structures, all_external_funcs)

    def _extract_data_structures_from_single_function(self, func_name: str):
        """从单个函数签名中提取使用的数据结构"""
        import re
        used_ds = {}

        if func_name not in self.function_signatures:
            return used_ds

        sig = self.function_signatures[func_name]

        # 检查已知的数据结构（文件内部定义的）
        for ds_name in self.data_structures.keys():
            if ds_name in sig:
                used_ds[ds_name] = self.data_structures[ds_name]

        # 通用类型提取：从签名中提取所有可能的类型名
        # 1. 匹配参数类型：类型名 + 指针/引用/空格
        # 例如：MsgBlock *pMsg, const ImVec2& pos, ImU32 col
        type_pattern = r'\b([A-Z][a-zA-Z0-9_]*)\s*[\*&\s]'
        type_matches = re.findall(type_pattern, sig)

        # 2. 匹配类名（成员函数的类）
        # 例如：void ImDrawList::AddConvexPolyFilled
        class_pattern = r'\b([A-Z][a-zA-Z0-9_]*)::'
        class_matches = re.findall(class_pattern, sig)

        # 合并所有匹配
        all_types = set(type_matches + class_matches)

        # 去重并过滤掉明显不是类型的关键字和基础类型
        # 1. C++关键字
        keywords = {'VOID', 'INT', 'CHAR', 'BOOL', 'FLOAT', 'DOUBLE', 'LONG', 'SHORT',
                   'CONST', 'STATIC', 'INLINE', 'VIRTUAL', 'EXPLICIT', 'TYPEDEF',
                   'UNSIGNED', 'SIGNED'}

        # 2. 常见的typedef基础类型（通常不需要显示定义）
        basic_typedefs = {'UINT8', 'UINT16', 'UINT32', 'UINT64',
                         'INT8', 'INT16', 'INT32', 'INT64',
                         'DWORD', 'WORD', 'BYTE', 'SIZE_T'}

        # 3. 项目特定的基础类型模式（VOS_VOID, VOS_UINT32等）
        # 匹配：VOS_XXX, DIAM_UINT32 等基础类型
        basic_type_patterns = [
            r'^VOS_(VOID|INT|UINT|CHAR|BOOL|LONG|SHORT|DWORD|WORD|BYTE)\d*$',
            r'^DIAM_(VOID|INT|UINT|CHAR|BOOL|UINT32|INT32)\d*$',
            r'^(Above|Below|Mod|Add|Del)$',  # 注释标记词
            r'^[A-Z]{1,3}\d{10,}$',  # DTS编号（如DTS2014111810080）
        ]

        for type_name in all_types:
            # 跳过C++关键字
            if type_name.upper() in keywords or type_name.upper() in basic_typedefs:
                continue

            # 跳过已添加的
            if type_name in used_ds:
                continue

            # 跳过基础类型模式
            is_basic_type = False
            for pattern in basic_type_patterns:
                if re.match(pattern, type_name):
                    is_basic_type = True
                    break

            if is_basic_type:
                continue

            # 添加为外部类型（后续会尝试查找定义）
            used_ds[type_name] = None

        return used_ds

    def _try_read_external_data_structure(self, struct_name: str) -> Optional[str]:
        """尝试从头文件中读取外部数据结构的定义（文本搜索）"""
        from pathlib import Path
        import re

        # 常见的头文件位置
        target_file_path = Path(self.target_file)
        possible_headers = []

        # 1. 同目录下的同名.h文件
        header_same_name = target_file_path.with_suffix('.h')
        if header_same_name.exists():
            possible_headers.append(header_same_name)

        # 2. 同目录下的其他.h文件（例如 imgui.h）
        header_dir = target_file_path.parent
        if header_dir.exists():
            for h_file in header_dir.glob('*.h'):
                if h_file not in possible_headers:
                    possible_headers.append(h_file)

        # 3. 上层include目录
        include_dirs = [
            header_dir / 'include',
            header_dir.parent / 'include',
        ]
        for inc_dir in include_dirs:
            if inc_dir.exists():
                for h_file in inc_dir.glob('*.h'):
                    possible_headers.append(h_file)

        # 在头文件中搜索定义（文本搜索）
        for header_file in possible_headers[:10]:  # 限制搜索范围
            try:
                with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 搜索结构体定义
                definition = self._search_struct_by_text(content, struct_name, header_file.name)
                if definition:
                    return definition

            except Exception as e:
                # 读取失败，继续尝试下一个
                continue

        return None

    def _search_struct_by_text(self, content: str, struct_name: str, filename: str) -> Optional[str]:
        """用文本搜索查找数据结构定义"""
        import re

        lines = content.split('\n')

        # 搜索模式（按优先级）
        patterns = [
            # 1. struct/class 定义: struct Name { 或 struct Name\n{
            (rf'^\s*(struct|class)\s+{re.escape(struct_name)}\s*$', 'struct'),
            (rf'^\s*(struct|class)\s+{re.escape(struct_name)}\s*\{{', 'struct'),

            # 2. typedef: typedef ... Name;
            (rf'^\s*typedef\s+.*\s+{re.escape(struct_name)}\s*;', 'typedef'),

            # 3. using (C++11): using Name = ...;
            (rf'^\s*using\s+{re.escape(struct_name)}\s*=', 'using'),
        ]

        for line_num, line in enumerate(lines):
            for pattern, def_type in patterns:
                match = re.search(pattern, line)
                if match:
                    # 找到了，提取完整定义
                    if def_type == 'typedef' or def_type == 'using':
                        # typedef/using 通常是单行
                        return f"// 来自: {filename}\n{line.strip()}"

                    elif def_type == 'struct':
                        # struct/class 需要找到完整的 body
                        definition_lines = [line]
                        brace_count = line.count('{') - line.count('}')

                        # 如果第一行没有 {，继续找
                        if '{' not in line:
                            for next_line in lines[line_num + 1:line_num + 5]:
                                definition_lines.append(next_line)
                                if '{' in next_line:
                                    brace_count = next_line.count('{') - next_line.count('}')
                                    break

                        # 继续读取直到找到匹配的 }
                        start_idx = line_num + len(definition_lines)
                        for i, next_line in enumerate(lines[start_idx:], start=start_idx):
                            definition_lines.append(next_line)
                            brace_count += next_line.count('{') - next_line.count('}')

                            if brace_count == 0 and '}' in next_line:
                                # 找到结束
                                break

                            # 限制最大行数
                            if len(definition_lines) >= 60:
                                definition_lines.append(f"    // ... (省略剩余部分)")
                                definition_lines.append("};")
                                break

                        definition = '\n'.join(definition_lines)
                        return f"// 来自: {filename}\n{definition}"

        return None

    def _search_function_signature(self, func_name: str) -> Optional[str]:
        """搜索外部函数的签名（在头文件中）"""
        from pathlib import Path
        import re

        # 常见的头文件位置
        target_file_path = Path(self.target_file)
        possible_headers = []

        # 1. 同目录下的同名.h文件
        header_same_name = target_file_path.with_suffix('.h')
        if header_same_name.exists():
            possible_headers.append(header_same_name)

        # 2. 同目录下的其他.h文件
        header_dir = target_file_path.parent
        if header_dir.exists():
            for h_file in header_dir.glob('*.h'):
                if h_file not in possible_headers:
                    possible_headers.append(h_file)

        # 在头文件中搜索函数声明
        for header_file in possible_headers[:10]:
            try:
                with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 搜索函数声明（支持多行）
                # 模式：返回类型 函数名(参数)
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    # 简单匹配：包含函数名的行
                    if func_name in line and '(' in line:
                        # 可能是函数声明
                        # 提取完整声明（可能跨行）
                        declaration = line.strip()

                        # 如果没有分号且没有花括号，可能跨行
                        if ';' not in declaration and '{' not in declaration and i + 1 < len(lines):
                            for next_line in lines[i+1:i+5]:
                                declaration += ' ' + next_line.strip()
                                if ';' in next_line or '{' in next_line:
                                    break

                        # 清理
                        declaration = declaration.split(';')[0].strip()
                        declaration = declaration.split('{')[0].strip()

                        # 验证是否真的是目标函数
                        if re.search(rf'\b{re.escape(func_name)}\s*\(', declaration):
                            return declaration

            except Exception:
                continue

        return None

    def _extract_constants_from_function(self, func_name: str) -> Dict[str, str]:
        """从函数中提取使用的常量和宏定义"""
        from pathlib import Path
        import re

        if func_name not in self.function_signatures:
            return {}

        # 从函数签名和分支条件中提取标识符
        identifiers = set()

        # 1. 从函数签名提取
        sig = self.function_signatures[func_name]
        # 提取大写标识符（通常是常量/宏）
        upper_identifiers = re.findall(r'\b[A-Z][A-Z0-9_]+\b', sig)
        identifiers.update(upper_identifiers)

        # 2. 从分支条件提取
        if hasattr(self, 'branch_analyses') and self.branch_analyses and func_name in self.branch_analyses:
            branch_analysis = self.branch_analyses[func_name]
            for condition in branch_analysis.conditions:
                # 从条件本身提取
                upper_ids = re.findall(r'\b[A-Z][A-Z0-9_]+\b', condition.condition)
                identifiers.update(upper_ids)

                # 从switch的suggestions中提取case值
                if condition.branch_type == 'switch' and condition.suggestions:
                    for sug in condition.suggestions:
                        # suggestions格式：'case值: MSG_LOGIN, MSG_LOGOUT, ...'
                        if sug.startswith('case值:'):
                            case_values_str = sug.replace('case值:', '').strip()
                            # 提取每个case值
                            case_values = [v.strip() for v in case_values_str.split(',')]
                            for case_val in case_values:
                                # 移除" ... 共X个case"后缀
                                if '...' in case_val:
                                    break
                                # 移除"default"
                                if case_val != 'default':
                                    identifiers.add(case_val)

        if not identifiers:
            return {}

        # 在头文件中搜索这些标识符的定义
        constants = {}
        target_file_path = Path(self.target_file)
        possible_headers = []

        # 1. 先搜索当前.cpp文件本身（枚举可能在文件内部）
        possible_headers.append(target_file_path)

        # 2. 收集头文件
        header_same_name = target_file_path.with_suffix('.h')
        if header_same_name.exists():
            possible_headers.append(header_same_name)

        header_dir = target_file_path.parent
        if header_dir.exists():
            for h_file in header_dir.glob('*.h'):
                if h_file not in possible_headers:
                    possible_headers.append(h_file)

        # 搜索定义
        for identifier in identifiers:
            for header_file in possible_headers[:10]:
                try:
                    with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            # 搜索 #define 或 enum
                            if re.search(rf'^\s*#define\s+{re.escape(identifier)}\b', line):
                                constants[identifier] = line.strip()
                                break
                            elif re.search(rf'^\s*{re.escape(identifier)}\s*=', line):
                                # enum 成员
                                constants[identifier] = line.strip()
                                break

                    if identifier in constants:
                        break

                except Exception:
                    continue

        return constants

    def _collect_all_dependencies(self, node, internal_set, external_set, exclude_func=None, visited=None):
        """递归收集所有依赖函数（防止循环依赖）"""
        if visited is None:
            visited = set()

        if not node or not node.children:
            return

        for child in node.children:
            # 跳过主函数自己（避免递归引用）
            if child.function_name == exclude_func:
                continue

            # 防止循环依赖：已经访问过的函数不再递归
            if child.function_name in visited:
                continue

            if child.is_external:
                external_set.add(child.function_name)
            else:
                internal_set.add(child.function_name)
                visited.add(child.function_name)  # 标记为已访问

                # 递归收集内部函数的依赖
                if child.function_name in self.call_chains:
                    self._collect_all_dependencies(
                        self.call_chains[child.function_name],
                        internal_set,
                        external_set,
                        exclude_func,
                        visited
                    )

    def _extract_data_structures_from_function(self, func_name, internal_deps):
        """从函数签名中提取使用的数据结构"""
        used_ds = {}

        # 检查主函数
        if func_name in self.function_signatures:
            sig = self.function_signatures[func_name]
            for ds_name in self.data_structures.keys():
                if ds_name in sig:
                    used_ds[ds_name] = self.data_structures[ds_name]

        # 检查依赖的内部函数
        for dep_func in internal_deps:
            if dep_func in self.function_signatures:
                sig = self.function_signatures[dep_func]
                for ds_name in self.data_structures.keys():
                    if ds_name in sig:
                        used_ds[ds_name] = self.data_structures[ds_name]

        # 简单提取常见类型（ImVec2, ImU32等）
        all_sigs = [self.function_signatures.get(func_name, "")]
        all_sigs.extend([self.function_signatures.get(f, "") for f in internal_deps if f in self.function_signatures])

        combined_sig = " ".join(all_sigs)
        common_types = ['ImVec2', 'ImVec4', 'ImU32', 'ImU8', 'ImWchar', 'ImDrawIdx',
                       'ImDrawCmd', 'ImDrawVert', 'ImDrawList', 'ImFont', 'ImFontAtlas']

        for type_name in common_types:
            if type_name in combined_sig and type_name not in used_ds:
                used_ds[type_name] = None  # 外部类型

        return used_ds


class CppProjectAnalyzer:
    """Main analyzer class that orchestrates all analysis components."""

    def __init__(self, project_root: str, mode: AnalysisMode = AnalysisMode.FULL_PROJECT):
        """
        Initialize the analyzer.

        Args:
            project_root: Path to the root directory of the C++ project
            mode: Analysis mode
        """
        self.project_root = Path(project_root).resolve()
        self.mode = mode
        self.mode_config = get_mode_config(mode)

        print(f"Initializing analyzer for project: {self.project_root}")
        print(f"Analysis mode: {self.mode.value} - {self.mode_config.description}")

        # 根据模式初始化组件
        if self.mode_config.requires_full_index:
            # 全局索引模式
            print("Mode requires full project indexing...")
            self.indexer = ProjectIndexer(str(self.project_root))
            self.classifier = EntryPointClassifier(self.indexer)
            self.tracer = CallChainTracer(self.indexer)
            self.data_analyzer = DataStructureAnalyzer(self.indexer)

            # Index the project
            print("Indexing project files...")
            self.indexer.index_project()
            print("Indexing complete!")

            self.single_file_analyzer = None
        else:
            # 单文件模式或其他不需要全局索引的模式
            print("Mode does not require full project indexing.")
            self.indexer = None
            self.classifier = None
            self.tracer = None
            self.data_analyzer = None

            # 初始化单文件分析器
            self.single_file_analyzer = SingleFileAnalyzer(str(self.project_root))

        # 分支分析器（所有模式都可用）
        self.branch_analyzer = BranchAnalyzer()

        # 外部函数分类器（所有模式都可用）
        self.external_classifier = ExternalFunctionClassifier()

    def analyze_file(self, target_file: str, trace_depth: int = 10, target_function: Optional[str] = None) -> AnalysisResult:
        """
        Analyze a specific C++ file.

        Args:
            target_file: Path to the target .cpp file (relative to project root or absolute)
            trace_depth: Maximum depth for call chain tracing
            target_function: Optional. If specified, only analyze this function

        Returns:
            AnalysisResult containing all analysis data
        """
        # 根据模式选择分析方法
        if self.mode == AnalysisMode.SINGLE_FILE_BOUNDARY:
            return self._analyze_file_boundary_mode(target_file, trace_depth, target_function)
        else:
            return self._analyze_file_full_mode(target_file, trace_depth, target_function)

    def _analyze_file_boundary_mode(self, target_file: str, trace_depth: int, target_function: Optional[str]) -> AnalysisResult:
        """单文件边界模式分析"""
        # Normalize file path
        target_path = Path(target_file)
        if not target_path.is_absolute():
            target_path = self.project_root / target_file

        print(f"\nAnalyzing file in boundary mode: {target_path}")
        if target_function:
            print(f"Target function: {target_function}")

        # 读取文件
        source_code = self.single_file_analyzer._read_file(target_path)
        if not source_code:
            raise ValueError(f"Could not read file: {target_path}")

        # 解析并存储文件路径
        self.single_file_analyzer._file_path = str(target_path)
        from .cpp_parser import CppParser
        parser = CppParser()
        tree = parser.parser.parse(source_code)  # 使用内部 parser 的 parse 方法
        if not tree:
            raise ValueError(f"Failed to parse file: {target_path}")

        root_node = tree.root_node

        # 分析文件边界
        boundary = self.single_file_analyzer.analyze_file(str(target_path))

        # 获取入口点
        entry_points = self.single_file_analyzer.get_entry_points(source_code, str(target_path))

        # 过滤目标函数
        if target_function:
            entry_points = [ep for ep in entry_points if ep.name == target_function]
            if not entry_points:
                print(f"  Warning: Function '{target_function}' not found in file!")
                available_funcs = list(self.single_file_analyzer.file_functions.keys())
                print(f"  Available functions: {', '.join(available_funcs[:10])}")
                if len(available_funcs) > 10:
                    print(f"  ... and {len(available_funcs) - 10} more")

        print(f"  Found {len(entry_points)} functions to analyze")

        # 追踪调用链（仅文件内）
        print("Tracing function call chains (file internal only)...")
        call_chains = {}
        function_signatures = {}

        for ep in entry_points:
            print(f"  Tracing: {ep.name}...")
            call_tree = self.single_file_analyzer.trace_call_chain(
                ep.name,
                source_code,
                max_depth=trace_depth
            )
            if call_tree:
                call_chains[ep.name] = call_tree

                # 收集函数签名
                self._collect_signatures_from_tree(call_tree, function_signatures)

        print(f"  Traced {len(call_chains)} call chains")

        # 获取数据结构信息
        print("Analyzing data structures...")
        data_structures = self.single_file_analyzer.get_data_structures_info()
        print(f"  Found {len(data_structures)} data structures")

        # 分析函数分支结构
        print("Analyzing branch structures...")
        branch_analyses = {}
        for func_name in self.single_file_analyzer.file_functions.keys():
            func_info = self.single_file_analyzer.file_functions[func_name]
            func_node = func_info['node']
            branch_analysis = self.branch_analyzer.analyze_function(func_node, source_code)
            branch_analyses[func_name] = branch_analysis
        print(f"  Analyzed {len(branch_analyses)} functions")

        # 创建结果
        result = AnalysisResult(
            target_file=str(target_path),
            entry_points=entry_points,
            call_chains=call_chains,
            function_signatures=function_signatures,
            data_structures=data_structures,
            mode=self.mode.value,
            file_boundary=boundary,
            branch_analyses=branch_analyses,
            external_classifier=self.external_classifier
        )

        print("\nBoundary analysis complete!")
        return result

    def _collect_signatures_from_tree(self, node: CallNode, signatures: Dict[str, str]):
        """从调用树收集函数签名"""
        if not node:
            return

        if node.function_name not in signatures:
            location = f"{node.file_path}:{node.line_number}" if not node.is_external else "<external>"
            signatures[node.function_name] = f"{node.signature} // {location}"

        for child in node.children:
            self._collect_signatures_from_tree(child, signatures)

    def _analyze_file_full_mode(self, target_file: str, trace_depth: int, target_function: Optional[str]) -> AnalysisResult:
        """全局索引模式分析（原始模式）"""
        # Normalize file path
        target_path = Path(target_file)
        if target_path.is_absolute():
            rel_path = str(target_path.relative_to(self.project_root))
        else:
            rel_path = str(target_path)

        print(f"\nAnalyzing file in full project mode: {rel_path}")
        if target_function:
            print(f"Target function: {target_function}")

        # Set trace depth
        self.tracer.max_depth = trace_depth

        # Step 1: Classify entry points
        print("Step 1: Identifying entry point functions...")
        all_entry_points = self.classifier.classify_file_functions(rel_path)

        # Filter to target function if specified
        if target_function:
            entry_points = [ep for ep in all_entry_points if ep.name == target_function]
            if not entry_points:
                print(f"  Warning: Function '{target_function}' not found in file!")
                print(f"  Available functions: {', '.join([ep.name for ep in all_entry_points[:10]])}")
                if len(all_entry_points) > 10:
                    print(f"  ... and {len(all_entry_points) - 10} more")
        else:
            entry_points = all_entry_points

        print(f"  Found {len(entry_points)} entry point functions")

        # Step 2: Trace call chains
        print("Step 2: Tracing function call chains...")
        call_chains = {}
        all_called_functions = set()

        for ep in entry_points:
            print(f"  Tracing: {ep.name}...")
            call_tree = self.tracer.trace_from_entry_point(ep.name, rel_path)
            if call_tree:
                call_chains[ep.name] = call_tree
                all_called_functions.update(self.tracer.get_all_called_functions(call_tree))

        print(f"  Traced {len(call_chains)} call chains")

        # Step 3: Collect function signatures
        print("Step 3: Collecting function signatures...")
        function_signatures = {}
        for func_name in all_called_functions:
            func_def = self.indexer.find_definition(func_name)
            if func_def:
                function_signatures[func_name] = f"{func_def.signature} // {func_def.file_path}:{func_def.line_number}"

        print(f"  Collected {len(function_signatures)} function signatures")

        # Step 4: Analyze data structures
        print("Step 4: Analyzing data structures...")
        data_structures = self.data_analyzer.analyze_data_structures(all_called_functions)
        print(f"  Found {len(data_structures)} data structures")

        # Create result
        result = AnalysisResult(
            target_file=rel_path,
            entry_points=entry_points,
            call_chains=call_chains,
            function_signatures=function_signatures,
            data_structures=data_structures,
            mode=self.mode.value,
            external_classifier=self.external_classifier
        )

        print("\nAnalysis complete!")
        return result

    def quick_analyze(self, target_file: str) -> str:
        """
        Quick analysis with formatted report output.

        Args:
            target_file: Path to target file

        Returns:
            Formatted text report
        """
        result = self.analyze_file(target_file)
        return result.format_report()


def main():
    """Example usage."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python cpp_analyzer.py <project_root> <target_cpp_file>")
        print("\nExample:")
        print("  python cpp_analyzer.py ./my_project ./my_project/src/main.cpp")
        sys.exit(1)

    project_root = sys.argv[1]
    target_file = sys.argv[2]

    # Create analyzer
    analyzer = CppProjectAnalyzer(project_root)

    # Analyze file
    result = analyzer.analyze_file(target_file)

    # Print report
    print("\n" + result.format_report())

    # Optionally save JSON
    output_json = "analysis_result.json"
    with open(output_json, 'w') as f:
        f.write(result.to_json())
    print(f"\nJSON output saved to: {output_json}")


if __name__ == "__main__":
    main()
