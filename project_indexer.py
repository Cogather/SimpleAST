"""
Project-wide symbol table indexer for C++ files.
"""
import os
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from cpp_parser import CppParser


@dataclass
class SymbolInfo:
    """Information about a symbol (function, class, struct, etc.)."""
    name: str
    type: str  # 'function', 'class', 'struct', 'enum', 'typedef'
    file_path: str
    line_number: int
    signature: str
    is_declaration: bool  # True if declaration, False if definition
    is_in_header: bool


class ProjectIndexer:
    """Builds and maintains a symbol table for the entire project."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.parser = CppParser()
        self.symbol_table: Dict[str, List[SymbolInfo]] = {}
        self.file_symbols: Dict[str, Set[str]] = {}  # file -> symbols defined
        self.include_graph: Dict[str, List[str]] = {}  # file -> included files

    def index_project(self):
        """Index all C++ files in the project."""
        cpp_files = self._find_cpp_files()
        print(f"Found {len(cpp_files)} C++ files to index...")

        for file_path in cpp_files:
            self._index_file(file_path)

        print(f"Indexed {len(self.symbol_table)} unique symbols")

    def _find_cpp_files(self) -> List[Path]:
        """Find all C++ source and header files in project."""
        extensions = {'.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.hxx'}
        cpp_files = []

        for root, dirs, files in os.walk(self.project_root):
            # Skip common build/dependency directories
            dirs[:] = [d for d in dirs if d not in {'build', 'cmake-build-debug',
                                                      'node_modules', '.git', 'venv'}]

            for file in files:
                if Path(file).suffix in extensions:
                    cpp_files.append(Path(root) / file)

        return cpp_files

    def _index_file(self, file_path: Path):
        """Index symbols in a single file."""
        # Try multiple encodings
        source_code = None
        encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252']

        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read()  # Test if encoding works
                # If successful, read as bytes for tree-sitter
                with open(file_path, 'rb') as f:
                    source_code = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if source_code is None:
            print(f"Warning: Could not decode {file_path} with any supported encoding")
            return

        try:
            tree = self.parser.parse_file(str(file_path))
            if not tree:
                return

            is_header = file_path.suffix in {'.h', '.hpp', '.hxx'}
            rel_path = str(file_path.relative_to(self.project_root))

            # Index includes
            self._index_includes(tree.root_node, source_code, rel_path)

            # Index functions
            self._index_functions(tree.root_node, source_code, rel_path, is_header)

            # Index data structures
            self._index_data_structures(tree.root_node, source_code, rel_path, is_header)

        except Exception as e:
            print(f"Error indexing {file_path}: {e}")

    def _index_includes(self, root_node, source_code: bytes, file_path: str):
        """Index #include directives."""
        includes = []
        preproc_includes = CppParser.find_nodes_by_type(root_node, 'preproc_include')

        for inc_node in preproc_includes:
            # Find the path node
            path_node = CppParser.find_child_by_type(inc_node, 'string_literal')
            if not path_node:
                path_node = CppParser.find_child_by_type(inc_node, 'system_lib_string')

            if path_node:
                inc_path = CppParser.get_node_text(path_node, source_code).strip('"<>')
                includes.append(inc_path)

        self.include_graph[file_path] = includes

    def _index_functions(self, root_node, source_code: bytes, file_path: str, is_header: bool):
        """Index function declarations and definitions."""
        # Find function definitions
        func_defs = CppParser.find_nodes_by_type(root_node, 'function_definition')
        for func_node in func_defs:
            self._add_function_symbol(func_node, source_code, file_path, is_header, is_declaration=False)

        # Find function declarations
        func_decls = CppParser.find_nodes_by_type(root_node, 'declaration')
        for decl_node in func_decls:
            # Check if it's a function declaration
            declarator = CppParser.find_child_by_type(decl_node, 'function_declarator')
            if declarator:
                self._add_function_symbol(decl_node, source_code, file_path, is_header, is_declaration=True)

    def _add_function_symbol(self, func_node, source_code: bytes, file_path: str,
                            is_header: bool, is_declaration: bool):
        """Add a function symbol to the symbol table."""
        func_name = CppParser.get_function_name(func_node, source_code)
        if not func_name:
            return

        signature = CppParser.get_function_signature(func_node, source_code)
        line_number = func_node.start_point[0] + 1

        symbol_info = SymbolInfo(
            name=func_name,
            type='function',
            file_path=file_path,
            line_number=line_number,
            signature=signature,
            is_declaration=is_declaration,
            is_in_header=is_header
        )

        if func_name not in self.symbol_table:
            self.symbol_table[func_name] = []
        self.symbol_table[func_name].append(symbol_info)

        if file_path not in self.file_symbols:
            self.file_symbols[file_path] = set()
        self.file_symbols[file_path].add(func_name)

    def _index_data_structures(self, root_node, source_code: bytes, file_path: str, is_header: bool):
        """Index struct, class, enum, typedef definitions."""
        structure_types = ['struct_specifier', 'class_specifier', 'enum_specifier', 'type_definition']

        for struct_type in structure_types:
            nodes = CppParser.find_nodes_by_type(root_node, struct_type)
            for node in nodes:
                self._add_structure_symbol(node, source_code, file_path, is_header, struct_type)

    def _add_structure_symbol(self, node, source_code: bytes, file_path: str,
                             is_header: bool, node_type: str):
        """Add a data structure symbol to the symbol table."""
        # Find the name
        name_node = CppParser.find_child_by_type(node, 'type_identifier')
        if not name_node:
            # For typedef, look for identifier
            name_node = CppParser.find_child_by_type(node, 'identifier')

        if not name_node:
            return

        struct_name = CppParser.get_node_text(name_node, source_code)
        line_number = node.start_point[0] + 1

        # Get full signature (limited to first 200 chars for brevity)
        signature = CppParser.get_node_text(node, source_code)
        if len(signature) > 200:
            signature = signature[:200] + "..."

        # Determine type
        symbol_type = {
            'struct_specifier': 'struct',
            'class_specifier': 'class',
            'enum_specifier': 'enum',
            'type_definition': 'typedef'
        }.get(node_type, 'unknown')

        symbol_info = SymbolInfo(
            name=struct_name,
            type=symbol_type,
            file_path=file_path,
            line_number=line_number,
            signature=signature,
            is_declaration=False,
            is_in_header=is_header
        )

        if struct_name not in self.symbol_table:
            self.symbol_table[struct_name] = []
        self.symbol_table[struct_name].append(symbol_info)

        if file_path not in self.file_symbols:
            self.file_symbols[file_path] = set()
        self.file_symbols[file_path].add(struct_name)

    def find_symbol(self, symbol_name: str) -> List[SymbolInfo]:
        """Find all occurrences of a symbol."""
        return self.symbol_table.get(symbol_name, [])

    def find_definition(self, symbol_name: str) -> Optional[SymbolInfo]:
        """Find the definition (not declaration) of a symbol."""
        symbols = self.find_symbol(symbol_name)
        # Prefer definitions in .cpp files
        for sym in symbols:
            if not sym.is_declaration and not sym.is_in_header:
                return sym
        # Fall back to any definition
        for sym in symbols:
            if not sym.is_declaration:
                return sym
        # If only declarations exist, return the first one
        return symbols[0] if symbols else None

    def get_file_symbols(self, file_path: str) -> Set[str]:
        """Get all symbols defined in a file."""
        return self.file_symbols.get(file_path, set())
