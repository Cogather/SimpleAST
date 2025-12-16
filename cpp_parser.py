"""
Tree-sitter based C++ parser wrapper.
"""
import os
from pathlib import Path
from typing import Optional
from tree_sitter import Language, Parser, Node, Tree


class CppParser:
    """Wrapper for tree-sitter C++ parser."""

    def __init__(self):
        self.parser = None
        self._init_parser()

    def _init_parser(self):
        """Initialize tree-sitter parser with C++ language."""
        try:
            import tree_sitter_cpp

            # Get C++ language pointer and create Language object
            lang_ptr = tree_sitter_cpp.language()
            CPP_LANGUAGE = Language(lang_ptr, "cpp")

            # Create parser and set language
            self.parser = Parser()
            self.parser.set_language(CPP_LANGUAGE)

        except Exception as e:
            raise RuntimeError(f"Failed to initialize C++ parser: {e}")

    def parse_file(self, file_path: str) -> Optional[Tree]:
        """
        Parse a C++ source file.

        Args:
            file_path: Path to the C++ file

        Returns:
            Tree-sitter Tree object or None if parsing fails
        """
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()
            return self.parser.parse(source_code)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def parse_string(self, source_code: str) -> Optional[Tree]:
        """
        Parse C++ source code from string.

        Args:
            source_code: C++ source code as string

        Returns:
            Tree-sitter Tree object or None if parsing fails
        """
        try:
            return self.parser.parse(bytes(source_code, 'utf8'))
        except Exception as e:
            print(f"Error parsing source code: {e}")
            return None

    @staticmethod
    def get_node_text(node: Node, source_code: bytes) -> str:
        """Extract text content from a node."""
        return source_code[node.start_byte:node.end_byte].decode('utf8')

    @staticmethod
    def find_nodes_by_type(node: Node, node_type: str) -> list:
        """
        Recursively find all nodes of a specific type.

        Args:
            node: Root node to search from
            node_type: Type of node to find (e.g., 'function_definition')

        Returns:
            List of matching nodes
        """
        results = []

        if node.type == node_type:
            results.append(node)

        for child in node.children:
            results.extend(CppParser.find_nodes_by_type(child, node_type))

        return results

    @staticmethod
    def find_child_by_type(node: Node, child_type: str) -> Optional[Node]:
        """Find first direct child of a specific type."""
        for child in node.children:
            if child.type == child_type:
                return child
        return None

    @staticmethod
    def get_function_name(func_node: Node, source_code: bytes) -> str:
        """Extract function name from function_definition or function_declarator node."""
        if func_node.type == 'function_definition':
            declarator = CppParser.find_child_by_type(func_node, 'function_declarator')
            if declarator:
                func_node = declarator

        # Look for function_declarator if not already
        if func_node.type != 'function_declarator':
            declarator = CppParser.find_child_by_type(func_node, 'function_declarator')
            if declarator:
                func_node = declarator

        # Find identifier or qualified_identifier
        for child in func_node.children:
            if child.type in ['identifier', 'field_identifier', 'destructor_name']:
                return CppParser.get_node_text(child, source_code)
            elif child.type == 'qualified_identifier':
                # Get the last part of qualified name
                parts = CppParser.get_node_text(child, source_code).split('::')
                return parts[-1] if parts else ""
            elif child.type == 'scoped_identifier':
                # Get the name part
                name_node = CppParser.find_child_by_type(child, 'identifier')
                if name_node:
                    return CppParser.get_node_text(name_node, source_code)

        return ""

    @staticmethod
    def get_function_signature(func_node: Node, source_code: bytes) -> str:
        """
        Extract complete function signature.

        For function_definition nodes, extracts the declaration part (without body).
        """
        if func_node.type == 'function_definition':
            # Get everything before the compound_statement (body)
            body = CppParser.find_child_by_type(func_node, 'compound_statement')
            if body:
                signature_end = body.start_byte
                signature_start = func_node.start_byte
                signature = source_code[signature_start:signature_end].decode('utf8').strip()
                return signature

        # For declarations, return full text
        return CppParser.get_node_text(func_node, source_code).strip()


if __name__ == "__main__":
    # Simple test
    parser = CppParser()
    code = """
    int add(int a, int b) {
        return a + b;
    }
    """
    tree = parser.parse_string(code)
    if tree:
        print("Parser initialized successfully!")
        print(f"Root node type: {tree.root_node.type}")
