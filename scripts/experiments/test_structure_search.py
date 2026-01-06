"""测试 StructureSearcher 是否能找到结构体定义"""
from simple_ast.searchers import StructureSearcher

project_root = "projects/ince_diam"
searcher = StructureSearcher(project_root)

# 测试三个结构体
test_structures = ["MsgBlock", "DiamAppMsg", "tFeAppMsg"]

for struct_name in test_structures:
    print(f"\n{'='*60}")
    print(f"搜索: {struct_name}")
    print('='*60)

    result = searcher.search(struct_name)
    if result:
        print(f"[SUCCESS] 找到定义:")
        print(result)
    else:
        print(f"[FAILED] 未找到定义")
