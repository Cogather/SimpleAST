"""测试 ripgrep 在 GrepSearcher 中的使用"""
from simple_ast.searchers.search_config import SearchConfig, SearchTool, set_search_tool
from simple_ast.searchers import GrepSearcher

# 强制使用 ripgrep
set_search_tool(SearchTool.RIPGREP)

project_root = "projects/ince_diam"
searcher = GrepSearcher(project_root)

print(f"使用工具: {searcher.config.command}")
print(f"项目根目录: {searcher.project_root}")
print()

# 测试模式
patterns = {
    "typedef\\s+struct\\s+\\w*DiamAppMsg": "DiamAppMsg - 优先级1模式1",
    "\\}\\s*\\w*,?\\s*MsgBlock\\s*;": "MsgBlock - 优先级2",
    "typedef\\s+struct\\s*\\{": "tFeAppMsg - 优先级1模式2 (匿名struct)",
}

for pattern, desc in patterns.items():
    print(f"{'='*60}")
    print(f"测试: {desc}")
    print(f"模式: {pattern}")
    print()

    matches = searcher.search_content(
        pattern=pattern,
        file_glob='*.h',
        max_results=5
    )

    if matches:
        print(f"找到 {len(matches)} 个匹配:")
        for file_path, line_num, content in matches:
            print(f"  {file_path.name}:{line_num}: {content.strip()[:80]}")
    else:
        print("未找到匹配")
    print()
