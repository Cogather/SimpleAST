"""
全面测试搜索系统 - 验证能否找到文档中列出的所有定义

根据 PidDiamMsgProc_Analysis.md 中的内容测试
"""
import sys
sys.path.insert(0, '.')

from simple_ast.searchers import StructureSearcher, SignatureSearcher, ConstantSearcher

# 测试项目路径
PROJECT_ROOT = 'projects/ince_diam'

# 测试用例：从文档中提取的关键定义
TEST_CASES = {
    'structures': [
        ('MsgBlock', 'v_base.h'),
        ('tFeAppMsg', 'fe_types.h'),
        ('DiamAppMsg', 'DiamApiUi.h'),
        ('DiamAvp', 'DiamApiUi.h'),
        ('tDiamCb', 'diamadapt.h'),
    ],
    'constants': [
        ('PID_DIAM', 'v_appdef.h'),
        ('DOPRA_PID_TIMER', 'v_iddef.h'),
        ('PID_SF', 'v_appdef.h'),
        ('PID_DSP', 'v_appdef.h'),
        ('PID_HAPD', 'v_appdef.h'),
        ('PID_MAINTAIN', 'v_appdef.h'),
        ('PID_OM', 'v_appdef.h'),
        ('SLF_HSF_RSP', 'fe_common.h'),
        ('DIAM_CMDFLAG_REQUEST', 'DiamApiUi.h'),
        ('DIAM_CMDFLAG_ANSWER', 'DiamApiUi.h'),
        ('DIAM_REQUEST_FLAG', 'DiamApiUi.h'),
        ('DIAM_SUCCESS', 'DiamApiBase.h'),
        ('DIAM_FALSE', 'DiamApiStack.h'),
        ('VOS_OK', 'v_base.h'),
        ('DIAM_MAX_APP_MSG_BODY_LENGTH', 'DiamApiCfg.h'),
        ('DIAM_MAX_APP_AVP_BODY_LENGTH', 'DiamApiCfg.h'),
    ],
    'macros': [
        ('VOS_MSG_HEADER', 'v_base.h'),
        ('FE_MSG_HEADER', 'fe_types.h'),
        ('DIAM_SSI_MSG_HEADER', 'DiamApiSsi.h'),
        ('DIAM_AVP_HEADER', 'DiamApiUi.h'),
        ('GET_DOPRA_MSG_LEN', 'commonDef.h'),
        ('MSGLEN_CHECK_RETURN', 'commonDef.h'),
        ('OFFSET_OF', 'commonDef.h'),
        ('OFFSET_AFTER', 'commonDef.h'),
    ]
}

def test_structures():
    """测试数据结构搜索"""
    print("=" * 80)
    print("测试 1: 数据结构搜索")
    print("=" * 80)

    searcher = StructureSearcher(PROJECT_ROOT)
    results = []

    for struct_name, expected_file in TEST_CASES['structures']:
        print(f"\n搜索: {struct_name} (预期文件: {expected_file})")
        result = searcher.search(struct_name)

        if result:
            # 检查是否在预期文件中
            if expected_file in result:
                print(f"  [OK] Found in {expected_file}")
                results.append((struct_name, True, expected_file))
                # 显示定义的前3行
                lines = result.split('\n')
                for line in lines[:4]:
                    print(f"    {line}")
            else:
                print(f"  [WARN] Found but file mismatch")
                print(f"    Actual: {result.split(':')[0]}")
                results.append((struct_name, True, 'file_mismatch'))
        else:
            print(f"  [FAIL] Not found")
            results.append((struct_name, False, None))

    return results

def test_constants():
    """测试常量搜索"""
    print("\n" + "=" * 80)
    print("测试 2: 常量定义搜索")
    print("=" * 80)

    searcher = ConstantSearcher(PROJECT_ROOT)
    results = []

    for const_name, expected_file in TEST_CASES['constants']:
        print(f"\n搜索: {const_name} (预期文件: {expected_file})")
        result = searcher.search(const_name)

        if result:
            if expected_file in result:
                print(f"  [OK] Found in {expected_file}")
                results.append((const_name, True, expected_file))
                # 显示定义
                lines = result.split('\n')
                for line in lines[1:]:  # 跳过注释行
                    if line.strip():
                        print(f"    {line}")
                        break
            else:
                print(f"  [WARN] Found but file mismatch")
                results.append((const_name, True, 'file_mismatch'))
        else:
            print(f"  [FAIL] Not found")
            results.append((const_name, False, None))

    return results

def test_macros():
    """测试宏定义搜索"""
    print("\n" + "=" * 80)
    print("测试 3: 宏定义搜索")
    print("=" * 80)

    searcher = ConstantSearcher(PROJECT_ROOT)
    results = []

    for macro_name, expected_file in TEST_CASES['macros']:
        print(f"\n搜索: {macro_name} (预期文件: {expected_file})")
        result = searcher.search(macro_name)

        if result:
            if expected_file in result:
                print(f"  [OK] Found in {expected_file}")
                results.append((macro_name, True, expected_file))
                # 显示定义的第一行
                lines = result.split('\n')
                for line in lines[1:]:
                    if line.strip():
                        print(f"    {line[:80]}...")
                        break
            else:
                print(f"  [WARN] Found but file mismatch")
                results.append((macro_name, True, 'file_mismatch'))
        else:
            print(f"  [FAIL] Not found")
            results.append((macro_name, False, None))

    return results

def print_summary(struct_results, const_results, macro_results):
    """打印测试总结"""
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    all_results = [
        ("数据结构", struct_results),
        ("常量定义", const_results),
        ("宏定义", macro_results)
    ]

    total_tests = 0
    total_found = 0
    total_correct = 0

    for category, results in all_results:
        found = sum(1 for _, success, _ in results if success)
        correct = sum(1 for _, success, file in results if success and file != 'file_mismatch')
        total = len(results)

        total_tests += total
        total_found += found
        total_correct += correct

        print(f"\n{category}:")
        print(f"  Total: {total}")
        print(f"  Found: {found} ({found*100//total}%)")
        print(f"  Correct: {correct} ({correct*100//total}%)")

        # 列出未找到的项
        not_found = [(name, exp) for name, success, exp in results if not success]
        if not_found:
            print(f"  Not found: {', '.join(name for name, _ in not_found)}")

    print(f"\nOverall:")
    print(f"  Total tests: {total_tests}")
    print(f"  Successfully found: {total_found} ({total_found*100//total_tests}%)")
    print(f"  Completely correct: {total_correct} ({total_correct*100//total_tests}%)")

    if total_correct == total_tests:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[INCOMPLETE] {total_tests - total_correct} items need fixing")
        return 1

def main():
    print("开始全面测试搜索系统...")
    print(f"项目路径: {PROJECT_ROOT}")
    print(f"测试项目总数: {len(TEST_CASES['structures']) + len(TEST_CASES['constants']) + len(TEST_CASES['macros'])}")

    try:
        # 运行测试
        struct_results = test_structures()
        const_results = test_constants()
        macro_results = test_macros()

        # 打印总结
        exit_code = print_summary(struct_results, const_results, macro_results)
        sys.exit(exit_code)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
