"""Debug script to understand switch case AST structure"""
import sys
from pathlib import Path
from simple_ast.cpp_parser import CppParser

# Read the file
file_path = Path(r"D:\work\code\github\cogather\SimpleAST\projects\ince_diam\common\source\diam\diamadapt.cpp")
with open(file_path, 'rb') as f:
    source_code = f.read()

# Parse with tree-sitter
parser = CppParser()
tree = parser.parse_file(file_path)

# Find the switch statement
def find_switch(node):
    if node.type == 'switch_statement':
        return node
    for child in node.children:
        result = find_switch(child)
        if result:
            return result
    return None

switch_node = find_switch(tree.root_node)
if not switch_node:
    print("No switch found")
    sys.exit(1)

print(f"Switch node: {switch_node.type} at line {switch_node.start_point[0] + 1}")
print(f"Children count: {len(switch_node.children)}")
print()

# Get the switch body (compound_statement)
body_node = None
for child in switch_node.children:
    if child.type == 'compound_statement':
        body_node = child
        break

if not body_node:
    print("No compound_statement found")
    sys.exit(1)

print(f"Body node: {body_node.type}")
print(f"Body children count: {len(body_node.children)}")
print()

# Print all children
for i, child in enumerate(body_node.children):
    text = CppParser.get_node_text(child, source_code)
    # Truncate long text
    if len(text) > 60:
        text = text[:60] + "..."
    print(f"[{i:2d}] {child.type:25s} line {child.start_point[0]+1:3d}-{child.end_point[0]+1:3d}  {repr(text)}")
