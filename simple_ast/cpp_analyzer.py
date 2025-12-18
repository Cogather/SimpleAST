"""
Main C++ Project Analyzer - integrates all components.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
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

        # === 1. 主函数信息 ===
        lines.append(f"[主函数] {func_name}")
        lines.append("")

        if func_name in self.function_signatures:
            sig = self.function_signatures[func_name]
            lines.append(sig.split('//')[0].strip())
            if '//' in sig:
                location = sig.split('//')[-1].strip()
                lines.append(f"位置: {location}")
            lines.append("")

        # === 2. 收集所有依赖（递归） ===
        all_internal_deps = set()
        all_external_deps = set()

        if func_name in self.call_chains:
            self._collect_all_dependencies(
                self.call_chains[func_name],
                all_internal_deps,
                all_external_deps,
                func_name
            )

        # === 3. 统计概览 ===
        lines.append("[统计]")
        lines.append(f"依赖内部函数: {len(all_internal_deps)} 个")
        lines.append(f"需要Mock外部函数: {len(all_external_deps)} 个")
        lines.append("")

        # === 3.5 分支复杂度分析（仅当圈复杂度>5时） ===
        if hasattr(self, 'branch_analyses') and self.branch_analyses and func_name in self.branch_analyses:
            branch_analysis = self.branch_analyses[func_name]
            if branch_analysis.cyclomatic_complexity > 5:
                lines.append(format_branch_analysis(branch_analysis))

        # === 4. Mock 清单（分类显示） ===
        if all_external_deps:
            lines.append("[Mock清单]")

            # 使用分类器分类外部函数
            classified = self.external_classifier.classify(all_external_deps)

            # 业务外部依赖（最重要）
            if classified['business']:
                lines.append(f"业务外部依赖（需要Mock）: {len(classified['business'])} 个")
                for func in sorted(classified['business']):
                    lines.append(f"- {func}")
                lines.append("")

            # 日志/工具函数
            if classified['logging_utility']:
                lines.append(f"日志/工具函数（可选Mock）: {len(classified['logging_utility'])} 个")
                for func in sorted(classified['logging_utility']):
                    lines.append(f"- {func}")
                lines.append("")

            # 标准库函数
            if classified['standard_library']:
                lines.append(f"标准库函数（通常不需要Mock）: {len(classified['standard_library'])} 个")
                for func in sorted(classified['standard_library']):
                    lines.append(f"- {func}")
                lines.append("")
        else:
            lines.append("")

        # === 5. 内部依赖详情 ===
        if all_internal_deps:
            lines.append("[内部依赖详情]")
            lines.append("")

            for dep_func in sorted(all_internal_deps):
                lines.append(f">> {dep_func}")

                if dep_func in self.function_signatures:
                    sig = self.function_signatures[dep_func]
                    lines.append(sig.split('//')[0].strip())
                    if '//' in sig:
                        location = sig.split('//')[-1].strip()
                        lines.append(location)

                # 直接调用
                if dep_func in self.call_chains:
                    dep_tree = self.call_chains[dep_func]
                    if dep_tree and dep_tree.children:
                        internal = [c.function_name for c in dep_tree.children if not c.is_external]
                        external = [c.function_name for c in dep_tree.children if c.is_external]

                        if internal:
                            lines.append(f"  调用内部: {', '.join(internal)}")
                        if external:
                            lines.append(f"  调用外部: {', '.join(external)}")

                lines.append("")

        # === 6. 数据结构 ===
        used_data_structures = self._extract_data_structures_from_function(func_name, all_internal_deps)

        if used_data_structures:
            internal_ds = [ds for ds in used_data_structures.keys() if ds in self.data_structures]
            external_ds = [ds for ds in used_data_structures.keys() if ds not in self.data_structures]

            if internal_ds or external_ds:
                lines.append("[数据结构]")
                lines.append("")

                # 输出内部数据结构的完整定义
                if internal_ds:
                    lines.append("内部定义:")
                    lines.append("")

                    for ds in sorted(internal_ds):
                        # 从 file_boundary 获取数据结构定义
                        if self.file_boundary and hasattr(self.file_boundary, 'file_data_structures') and ds in self.file_boundary.file_data_structures:
                            ds_info = self.file_boundary.file_data_structures[ds]
                            lines.append(f">> {ds} ({ds_info['type']})")
                            lines.append(f"定义: {self.target_file}:{ds_info['line']}")
                            lines.append(ds_info['definition'])
                            lines.append("")
                        else:
                            # 如果没有定义信息，只显示名称
                            lines.append(f">> {ds}")
                            lines.append("")

                # 输出外部数据结构引用
                if external_ds:
                    lines.append("外部引用:")
                    lines.append(f"{', '.join(sorted(external_ds))}")
                    lines.append("")

        return "\n".join(lines)

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
