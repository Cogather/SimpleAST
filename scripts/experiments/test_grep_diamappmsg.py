"""测试 GrepSearcher 搜索 DiamAppMsg 时找到的第一个匹配"""
from simple_ast.searchers import GrepSearcher
import re

project_root = "projects/ince_diam"
searcher = GrepSearcher(project_root)

struct_name = "DiamAppMsg"
name = re.escape(struct_name)

# 测试每个模式单独匹配到什么
patterns = [
    (rf'(struct|class)[[:space:]]+{name}[[:space:]]*[{{;]', "struct/class"),
    (rf'typedef.*[[:space:]]+{name}[[:space:]]*;', "typedef"),
    (rf'}}.*{name}[[:space:]]*;', "} typedef结尾"),
    (rf'using[[:space:]]+{name}[[:space:]]*=', "using"),
]

print(f"搜索结构体: {struct_name}\n")

for pattern, desc in patterns:
    print(f"模式: {desc}")
    print(f"正则: {pattern}")

    # 搜索第一个匹配
    matches = searcher.search_content(pattern, '*.h', max_results=5)
    if matches:
        print(f"  匹配到 {len(matches)} 项:")
        for file_path, line_num, content in matches:
            print(f"    {file_path}:{line_num}: {content.strip()}")
    else:
        print("  [未匹配]")
    print()

# 测试合并模式（StructureSearcher实际使用的）
combined = '|'.join([p[0] for p in patterns])
print("="*60)
print("合并模式搜索:")
first_match = searcher.search_first_match(combined, '*.h')
if first_match:
    file_path, line_num = first_match
    print(f"第一个匹配: {file_path}:{line_num}")
else:
    print("未找到匹配")
