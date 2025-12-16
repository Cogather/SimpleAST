"""
Entry point classifier - distinguishes API functions from internal functions.
"""
from typing import List, Set
from dataclasses import dataclass
from cpp_parser import CppParser
from project_indexer import ProjectIndexer, SymbolInfo


@dataclass
class EntryPointInfo:
    """Information about an entry point function."""
    name: str
    category: str  # 'API', 'INTERNAL', 'EXPORTED'
    file_path: str
    line_number: int
    signature: str
    declaration_location: str = ""  # Where it's declared (for API functions)


class EntryPointClassifier:
    """Classifies functions as API or internal entry points."""

    def __init__(self, indexer: ProjectIndexer):
        self.indexer = indexer
        self.parser = CppParser()

    def classify_file_functions(self, target_file: str) -> List[EntryPointInfo]:
        """
        Classify all functions defined in the target file.

        Categories:
        - API: Declared in .h file, implemented in .cpp (public API)
        - INTERNAL: Defined only in .cpp (static or anonymous namespace)
        - EXPORTED: Defined in .cpp but no explicit declaration in .h
        """
        entry_points = []

        # Get all function symbols in this file
        file_symbols = self.indexer.get_file_symbols(target_file)

        for symbol_name in file_symbols:
            symbol_infos = self.indexer.find_symbol(symbol_name)

            # Filter to functions only
            func_infos = [s for s in symbol_infos if s.type == 'function']
            if not func_infos:
                continue

            # Check if this function is defined in our target file
            target_def = None
            for info in func_infos:
                if info.file_path == target_file and not info.is_declaration:
                    target_def = info
                    break

            if not target_def:
                continue

            # Classify based on declarations
            category = self._classify_function(symbol_name, target_def, func_infos)

            # Find declaration location if API
            decl_location = ""
            if category == 'API':
                for info in func_infos:
                    if info.is_in_header and (info.is_declaration or not info.is_declaration):
                        decl_location = f"{info.file_path}:{info.line_number}"
                        break

            entry_point = EntryPointInfo(
                name=symbol_name,
                category=category,
                file_path=target_def.file_path,
                line_number=target_def.line_number,
                signature=target_def.signature,
                declaration_location=decl_location
            )
            entry_points.append(entry_point)

        return entry_points

    def _classify_function(self, func_name: str, definition: SymbolInfo,
                          all_occurrences: List[SymbolInfo]) -> str:
        """
        Classify a function based on its declarations and definitions.

        Logic:
        1. If declared in a .h file -> API
        2. If 'static' keyword or in anonymous namespace -> INTERNAL
        3. Otherwise -> EXPORTED (might be used by other .cpp files)
        """
        # Check if declared in any header file
        has_header_declaration = any(
            info.is_in_header for info in all_occurrences
        )

        if has_header_declaration:
            return 'API'

        # Check if static or in anonymous namespace
        if self._is_internal_linkage(definition):
            return 'INTERNAL'

        return 'EXPORTED'

    def _is_internal_linkage(self, func_info: SymbolInfo) -> bool:
        """
        Check if function has internal linkage (static or anonymous namespace).
        """
        signature = func_info.signature.lower()

        # Check for 'static' keyword
        if 'static ' in signature or signature.startswith('static'):
            return True

        # Check for anonymous namespace (simplified check)
        # In practice, would need to parse the file to check namespace scope
        # For now, we'll mark non-header, non-declared functions as potentially internal

        return False

    def find_entry_points(self, target_file: str,
                         include_internal: bool = True,
                         include_exported: bool = True) -> List[EntryPointInfo]:
        """
        Find entry point functions in target file with filtering.

        Args:
            target_file: Path to the target .cpp file (relative to project root)
            include_internal: Include INTERNAL functions
            include_exported: Include EXPORTED functions

        Returns:
            List of entry points matching the criteria
        """
        all_entry_points = self.classify_file_functions(target_file)

        filtered = []
        for ep in all_entry_points:
            if ep.category == 'API':
                filtered.append(ep)
            elif ep.category == 'INTERNAL' and include_internal:
                filtered.append(ep)
            elif ep.category == 'EXPORTED' and include_exported:
                filtered.append(ep)

        return filtered

    def get_api_functions(self, target_file: str) -> List[EntryPointInfo]:
        """Get only API functions (declared in headers) from target file."""
        return [ep for ep in self.classify_file_functions(target_file)
                if ep.category == 'API']

    def get_internal_functions(self, target_file: str) -> List[EntryPointInfo]:
        """Get only internal functions from target file."""
        return [ep for ep in self.classify_file_functions(target_file)
                if ep.category == 'INTERNAL']
