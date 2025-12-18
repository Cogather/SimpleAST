"""Test tree-sitter import"""
try:
    from tree_sitter import Language, Parser
    import tree_sitter_cpp

    print("Imports successful!")

    # Get language pointer
    lang_ptr = tree_sitter_cpp.language()
    print(f"Language pointer: {lang_ptr}")
    print(f"Language pointer type: {type(lang_ptr)}")

    # Create Language object with name
    CPP_LANGUAGE = Language(lang_ptr, "cpp")
    print(f"Language object: {CPP_LANGUAGE}")
    print(f"Language type: {type(CPP_LANGUAGE)}")

    # Create parser
    parser = Parser()
    parser.set_language(CPP_LANGUAGE)
    print(f"Parser created: {parser}")

    # Test parse
    code = b"int main() { return 0; }"
    tree = parser.parse(code)
    print(f"Tree: {tree}")
    print(f"Root node: {tree.root_node}")
    print(f"Root node type: {tree.root_node.type}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
