"""
Data structure analyzer - analyzes data structures and their usage.
"""
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from cpp_parser import CppParser
from project_indexer import ProjectIndexer, SymbolInfo
from call_chain_tracer import CallNode


@dataclass
class DataStructureInfo:
    """Information about a data structure."""
    name: str
    type: str  # 'struct', 'class', 'enum', 'typedef'
    file_path: str
    line_number: int
    definition: str  # Full or partial definition
    used_by_functions: Set[str] = field(default_factory=set)
    used_in_files: Set[str] = field(default_factory=set)


class DataStructureAnalyzer:
    """Analyzes data structures and tracks their usage."""

    def __init__(self, indexer: ProjectIndexer):
        self.indexer = indexer
        self.parser = CppParser()

    def analyze_data_structures(self, relevant_functions: Set[str]) -> Dict[str, DataStructureInfo]:
        """
        Analyze all data structures used by the given set of functions.

        Args:
            relevant_functions: Set of function names to analyze

        Returns:
            Dictionary mapping structure name to DataStructureInfo
        """
        structures = {}

        # First, collect all data structures defined in the project
        for symbol_name, symbol_list in self.indexer.symbol_table.items():
            for symbol in symbol_list:
                if symbol.type in ['struct', 'class', 'enum', 'typedef']:
                    if symbol_name not in structures:
                        structures[symbol_name] = DataStructureInfo(
                            name=symbol_name,
                            type=symbol.type,
                            file_path=symbol.file_path,
                            line_number=symbol.line_number,
                            definition=symbol.signature
                        )

        # Now analyze usage in relevant functions
        for func_name in relevant_functions:
            func_def = self.indexer.find_definition(func_name)
            if not func_def:
                continue

            # Find data structures used in this function
            used_types = self._find_used_types(func_def)

            for type_name in used_types:
                if type_name in structures:
                    structures[type_name].used_by_functions.add(func_name)
                    structures[type_name].used_in_files.add(func_def.file_path)

        return structures

    def _find_used_types(self, func_symbol: SymbolInfo) -> Set[str]:
        """
        Find all data types used in a function (parameters, return type, local variables).

        Args:
            func_symbol: SymbolInfo for the function

        Returns:
            Set of type names used
        """
        used_types = set()

        try:
            full_path = self.indexer.project_root / func_symbol.file_path
            with open(full_path, 'rb') as f:
                source_code = f.read()

            tree = self.parser.parse_file(str(full_path))
            if not tree:
                return used_types

            # Find the function definition
            func_defs = CppParser.find_nodes_by_type(tree.root_node, 'function_definition')

            target_func_node = None
            for func_def in func_defs:
                name = CppParser.get_function_name(func_def, source_code)
                if name == func_symbol.name:
                    target_func_node = func_def
                    break

            if not target_func_node:
                return used_types

            # Extract types from:
            # 1. Return type
            # 2. Parameters
            # 3. Local variable declarations

            # Get return type
            return_types = self._extract_types_from_node(target_func_node, source_code, 'type_identifier')
            used_types.update(return_types)

            # Get parameter types
            param_list = CppParser.find_child_by_type(target_func_node, 'parameter_list')
            if param_list:
                param_types = self._extract_types_from_node(param_list, source_code, 'type_identifier')
                used_types.update(param_types)

            # Get local variable types (from declaration statements)
            declarations = CppParser.find_nodes_by_type(target_func_node, 'declaration')
            for decl in declarations:
                decl_types = self._extract_types_from_node(decl, source_code, 'type_identifier')
                used_types.update(decl_types)

            # Also look for primitive types wrapped in structs/classes
            # Look for qualified identifiers (namespace::Type)
            qualified_ids = CppParser.find_nodes_by_type(target_func_node, 'qualified_identifier')
            for qid in qualified_ids:
                text = CppParser.get_node_text(qid, source_code)
                # Extract the last part (type name)
                parts = text.split('::')
                if parts:
                    used_types.add(parts[-1])

        except Exception as e:
            print(f"Error finding used types in {func_symbol.name}: {e}")

        return used_types

    def _extract_types_from_node(self, node, source_code: bytes, target_type: str) -> Set[str]:
        """
        Extract all type identifiers from a node.

        Args:
            node: Tree-sitter node to search
            source_code: Source code bytes
            target_type: Node type to search for (e.g., 'type_identifier')

        Returns:
            Set of type names
        """
        types = set()
        type_nodes = CppParser.find_nodes_by_type(node, target_type)

        for type_node in type_nodes:
            type_name = CppParser.get_node_text(type_node, source_code)
            # Filter out primitive types
            if type_name not in {'int', 'char', 'float', 'double', 'void', 'bool',
                                'short', 'long', 'unsigned', 'signed', 'size_t'}:
                types.add(type_name)

        return types

    def analyze_from_call_tree(self, call_tree_root: CallNode) -> Dict[str, DataStructureInfo]:
        """
        Analyze data structures used in a call tree.

        Args:
            call_tree_root: Root of the call tree

        Returns:
            Dictionary of data structures used
        """
        # Get all functions in the call tree
        all_functions = self._get_functions_from_tree(call_tree_root)

        # Analyze data structures used by these functions
        return self.analyze_data_structures(all_functions)

    def _get_functions_from_tree(self, node: CallNode) -> Set[str]:
        """Recursively get all function names from a call tree."""
        functions = {node.function_name}

        for child in node.children:
            functions.update(self._get_functions_from_tree(child))

        return functions

    def format_data_structures(self, structures: Dict[str, DataStructureInfo]) -> str:
        """
        Format data structures as a readable report.

        Args:
            structures: Dictionary of DataStructureInfo

        Returns:
            Formatted string
        """
        if not structures:
            return "No data structures found."

        lines = ["Data Structures:", "=" * 80]

        # Sort by type, then name
        sorted_structs = sorted(structures.values(),
                               key=lambda s: (s.type, s.name))

        for struct in sorted_structs:
            lines.append(f"\n{struct.type.upper()}: {struct.name}")
            lines.append(f"  Defined in: {struct.file_path}:{struct.line_number}")

            if struct.used_by_functions:
                lines.append(f"  Used by functions:")
                for func in sorted(struct.used_by_functions):
                    lines.append(f"    - {func}")
            else:
                lines.append(f"  Used by: (none in analyzed call chains)")

            if struct.used_in_files:
                lines.append(f"  Used in files: {', '.join(sorted(struct.used_in_files))}")

            # Show definition preview (first 3 lines)
            def_lines = struct.definition.split('\n')[:3]
            if def_lines:
                lines.append(f"  Definition preview:")
                for def_line in def_lines:
                    lines.append(f"    {def_line}")

        return "\n".join(lines)

    def get_structure_dependencies(self, structures: Dict[str, DataStructureInfo]) -> Dict[str, Set[str]]:
        """
        Analyze dependencies between data structures.

        Args:
            structures: Dictionary of DataStructureInfo

        Returns:
            Dictionary mapping structure name to set of structures it depends on
        """
        dependencies = {}

        for struct_name, struct_info in structures.items():
            deps = set()

            # Parse the definition to find member types
            for other_name in structures.keys():
                if other_name != struct_name and other_name in struct_info.definition:
                    deps.add(other_name)

            dependencies[struct_name] = deps

        return dependencies
