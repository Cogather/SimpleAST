"""
Main C++ Project Analyzer - integrates all components.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from project_indexer import ProjectIndexer
from entry_point_classifier import EntryPointClassifier, EntryPointInfo
from call_chain_tracer import CallChainTracer, CallNode
from data_structure_analyzer import DataStructureAnalyzer, DataStructureInfo


@dataclass
class AnalysisResult:
    """Complete analysis result for a C++ file."""
    target_file: str
    entry_points: List[EntryPointInfo]
    call_chains: Dict[str, CallNode]
    function_signatures: Dict[str, str]  # function_name -> signature
    data_structures: Dict[str, DataStructureInfo]

    def format_report(self) -> str:
        """Format the complete analysis as a readable report."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"C++ Static Analysis Report")
        lines.append(f"Target File: {self.target_file}")
        lines.append("=" * 80)

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


class CppProjectAnalyzer:
    """Main analyzer class that orchestrates all analysis components."""

    def __init__(self, project_root: str):
        """
        Initialize the analyzer.

        Args:
            project_root: Path to the root directory of the C++ project
        """
        self.project_root = Path(project_root).resolve()
        print(f"Initializing analyzer for project: {self.project_root}")

        # Initialize components
        self.indexer = ProjectIndexer(str(self.project_root))
        self.classifier = EntryPointClassifier(self.indexer)
        self.tracer = CallChainTracer(self.indexer)
        self.data_analyzer = DataStructureAnalyzer(self.indexer)

        # Index the project
        print("Indexing project files...")
        self.indexer.index_project()
        print("Indexing complete!")

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
        # Normalize file path
        target_path = Path(target_file)
        if target_path.is_absolute():
            rel_path = str(target_path.relative_to(self.project_root))
        else:
            rel_path = str(target_path)

        print(f"\nAnalyzing file: {rel_path}")
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
            data_structures=data_structures
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
