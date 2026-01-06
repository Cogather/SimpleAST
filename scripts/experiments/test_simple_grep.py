"""测试 GrepSearcher.search_content 方法"""
from simple_ast.searchers import GrepSearcher

project_root = "projects/ince_diam"
searcher = GrepSearcher(project_root)

# 测试一个简单的模式
pattern = r'typedef.*DiamAppMsg'

print(f"搜索模式: {pattern}")
print(f"项目根目录: {searcher.project_root}")
print()

matches = searcher.search_content(
    pattern=pattern,
    file_glob='*.h',
    max_results=10
)

print(f"找到 {len(matches)} 个匹配:")
for file_path, line_num, content in matches:
    print(f"  {file_path}:{line_num}")
    print(f"    {content.strip()}")
