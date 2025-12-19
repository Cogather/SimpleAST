"""测试 StructureExtractor 提取三个结构体"""
from simple_ast.extractors import StructureExtractor

project_root = "projects/ince_diam"
target_file = "projects/ince_diam/common/source/diam/diamadapt.cpp"

extractor = StructureExtractor(project_root=project_root)

test_structures = ["MsgBlock", "DiamAppMsg", "tFeAppMsg"]

for struct_name in test_structures:
    print(f"\n{'='*60}")
    print(f"提取: {struct_name}")
    print('='*60)

    definition = extractor.extract(struct_name, target_file)
    if definition:
        print("[SUCCESS]")
        print(definition)
    else:
        print("[FAILED] 未找到定义")
