"""调试 StructureSearcher 的优先级匹配"""
from simple_ast.searchers import StructureSearcher

project_root = "projects/ince_diam"
searcher = StructureSearcher(project_root)

# 测试所有三个结构体
test_structures = ["MsgBlock", "DiamAppMsg", "tFeAppMsg"]

for struct_name in test_structures:
    print(f"\n{'='*60}")
    print(f"测试结构体: {struct_name}")
    print('='*60)

    # 获取优先级模式
    pattern_groups = searcher._build_prioritized_patterns(struct_name)

    for priority, patterns in pattern_groups:
        print(f"\n优先级 {priority}:")
        for i, pattern in enumerate(patterns, 1):
            print(f"  模式{i}: {pattern}")

            matches = searcher.grep.search_content(
                pattern=pattern,
                file_glob='*.h',
                max_results=5
            )

            if matches:
                print(f"    找到 {len(matches)} 个匹配:")
                for file_path, line_num, content in matches:
                    print(f"      {file_path.name}:{line_num}: {content.strip()[:80]}")
            else:
                print(f"    [未找到匹配]")
    print()
