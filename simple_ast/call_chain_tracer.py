"""
Call chain tracer - traces function call chains from entry points.
"""
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from pathlib import Path
from .cpp_parser import CppParser
from .project_indexer import ProjectIndexer, SymbolInfo


@dataclass
class CallNode:
    """Represents a node in the call chain tree."""
    function_name: str
    file_path: str = ""
    line_number: int = 0
    signature: str = ""
    called_from_line: int = 0  # Line where this function is called
    children: List['CallNode'] = field(default_factory=list)
    is_external: bool = False  # True if definition not found in project
    is_recursive: bool = False  # True if this creates a cycle


class CallChainTracer:
    """Traces function call chains from entry points."""

    def __init__(self, indexer: ProjectIndexer):
        self.indexer = indexer
        self.parser = CppParser()
        self.max_depth = 999  # Effectively unlimited for internal-only tracing
        self.trace_internal_only = True  # Only trace functions in same file

    def trace_from_entry_point(self, entry_point_name: str,
                               entry_file: str) -> Optional[CallNode]:
        """
        Trace the call chain starting from an entry point function.

        Args:
            entry_point_name: Name of the entry point function
            entry_file: File where the entry point is defined

        Returns:
            Root CallNode representing the call tree
        """
        # Find the entry point definition
        entry_def = None
        for symbol in self.indexer.find_symbol(entry_point_name):
            if symbol.file_path == entry_file and not symbol.is_declaration:
                entry_def = symbol
                break

        if not entry_def:
            print(f"Warning: Could not find definition for {entry_point_name} in {entry_file}")
            return None

        # Create root node
        root = CallNode(
            function_name=entry_point_name,
            file_path=entry_def.file_path,
            line_number=entry_def.line_number,
            signature=entry_def.signature
        )

        # Trace calls recursively
        visited = set()  # Track visited functions to detect cycles
        self._trace_calls_recursive(root, visited, depth=0, entry_file=entry_file)

        return root

    def _trace_calls_recursive(self, node: CallNode, visited: Set[str], depth: int, entry_file: str):
        """
        Recursively trace function calls.

        Args:
            node: Current CallNode
            visited: Set of function names already visited (cycle detection)
            depth: Current recursion depth
            entry_file: Original entry point file (for internal-only tracing)
        """
        if depth >= self.max_depth:
            return

        # Mark as visited
        func_key = f"{node.file_path}:{node.function_name}"
        if func_key in visited:
            node.is_recursive = True
            return

        visited.add(func_key)

        # Parse the function body to find calls
        called_functions = self._extract_function_calls(node.file_path, node.function_name)

        for call_name, call_line in called_functions:
            # Find the definition of the called function
            call_def = self.indexer.find_definition(call_name)

            if call_def:
                # Check if function is external (in different file)
                is_external_file = (call_def.file_path != entry_file)

                # Create child node
                child_node = CallNode(
                    function_name=call_name,
                    file_path=call_def.file_path,
                    line_number=call_def.line_number,
                    signature=call_def.signature,
                    called_from_line=call_line,
                    is_external=is_external_file  # Mark as external if in different file
                )
                node.children.append(child_node)

                # Only recursively trace if it's in the same file (when trace_internal_only is True)
                if self.trace_internal_only:
                    if not is_external_file:
                        # Internal function - continue tracing
                        self._trace_calls_recursive(child_node, visited.copy(), depth + 1, entry_file)
                    # else: External function - stop tracing here, just mark it
                else:
                    # Trace all functions regardless of file
                    self._trace_calls_recursive(child_node, visited.copy(), depth + 1, entry_file)
            else:
                # External or unresolved function (not in project)
                child_node = CallNode(
                    function_name=call_name,
                    called_from_line=call_line,
                    is_external=True
                )
                node.children.append(child_node)

        visited.remove(func_key)

    def _extract_function_calls(self, file_path: str, function_name: str) -> List[tuple]:
        """
        Extract all function calls within a specific function.

        Returns:
            List of (called_function_name, line_number) tuples
        """
        try:
            full_path = self.indexer.project_root / file_path
            with open(full_path, 'rb') as f:
                source_code = f.read()

            tree = self.parser.parse_file(str(full_path))
            if not tree:
                return []

            # Find the function definition
            func_defs = CppParser.find_nodes_by_type(tree.root_node, 'function_definition')

            target_func_node = None
            for func_def in func_defs:
                name = CppParser.get_function_name(func_def, source_code)
                if name == function_name:
                    target_func_node = func_def
                    break

            if not target_func_node:
                return []

            # Find all call_expression nodes within this function
            call_nodes = CppParser.find_nodes_by_type(target_func_node, 'call_expression')

            calls = []
            for call_node in call_nodes:
                call_name = self._extract_call_name(call_node, source_code)
                if call_name:
                    line_num = call_node.start_point[0] + 1
                    calls.append((call_name, line_num))

            return calls

        except Exception as e:
            print(f"Error extracting calls from {file_path}::{function_name}: {e}")
            return []

    def _extract_call_name(self, call_node, source_code: bytes) -> Optional[str]:
        """
        Extract the function name from a call_expression node.

        Handles:
        - Simple calls: foo()
        - Method calls: obj.foo()
        - Scoped calls: namespace::foo()
        """
        # The first child is typically the function identifier
        function_node = call_node.children[0] if call_node.children else None

        if not function_node:
            return None

        if function_node.type == 'identifier':
            return CppParser.get_node_text(function_node, source_code)

        elif function_node.type == 'qualified_identifier':
            # namespace::function
            text = CppParser.get_node_text(function_node, source_code)
            parts = text.split('::')
            return parts[-1] if parts else None

        elif function_node.type == 'field_expression':
            # obj.method() or ptr->method()
            # Get the field name (method name)
            field_node = CppParser.find_child_by_type(function_node, 'field_identifier')
            if field_node:
                return CppParser.get_node_text(field_node, source_code)

        elif function_node.type == 'scoped_identifier':
            # Class::method
            name_node = call_node.children[0].children[-1] if call_node.children[0].children else None
            if name_node:
                return CppParser.get_node_text(name_node, source_code)

        return None

    def format_call_tree(self, root: CallNode, indent: int = 0) -> str:
        """
        Format the call tree as a readable string.

        Args:
            root: Root CallNode
            indent: Current indentation level

        Returns:
            Formatted string representation
        """
        if not root:
            return ""

        lines = []
        prefix = "  " * indent

        # Format current node
        if indent == 0:
            # Root node (entry point)
            location = f"[{root.file_path}:{root.line_number}]"
            lines.append(f"{root.function_name} {location}")
        else:
            # Child node
            symbol = "├─" if indent > 0 else ""
            status = ""
            if root.is_recursive:
                status = " [RECURSIVE]"
            elif root.is_external:
                # Show external file info if available, otherwise mark as EXTERNAL
                if root.file_path:
                    status = f" [EXTERNAL: {root.file_path}:{root.line_number}]"
                else:
                    status = " [EXTERNAL]"
            else:
                status = f" [{root.file_path}:{root.line_number}]"

            lines.append(f"{prefix}{symbol} {root.function_name}{status}")

        # Format children
        for child in root.children:
            lines.append(self.format_call_tree(child, indent + 1))

        return "\n".join(lines)

    def get_all_called_functions(self, root: CallNode) -> Set[str]:
        """
        Get a flat set of all functions called in the tree.

        Args:
            root: Root CallNode

        Returns:
            Set of function names
        """
        result = {root.function_name}

        for child in root.children:
            result.update(self.get_all_called_functions(child))

        return result
