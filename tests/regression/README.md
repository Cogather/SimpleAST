# 回归测试使用文档

## 概述

回归测试框架用于验证代码变更不会破坏现有功能。通过对比分析输出的 `functions/` 目录中的 txt 文件，确保功能的稳定性。

## TXT 文件格式说明

每个函数的 txt 文件包含以下结构化信息：

### 文件结构示例

```
函数: PidDiamMsgProc
VOS_VOID PidDiamMsgProc(MsgBlock *pMsg) // diamadapt.cpp:1
圈复杂度: 15
关键分支:
  1. (pMsg->ulSenderPid)
     case值: PID_DIAM, DOPRA_PID_TIMER, PID_SF, PID_DSP, PID_HAPD, PID_MAINTAIN, PID_OM, default
     详细分支:
       case PID_DIAM:
         调用: procMsgFromDiam
         位置: 行17-19
       case DOPRA_PID_TIMER:
         调用: AdaptDiamProcessMsgFromTimer
         位置: 行21-24
       ...
  2. (!CheckPidDiamMsg(pMsg))
  3. (SLF_HSF_RSP == pFeMsg->MsgType)
  ...
Mock:
  AdaptDiamProcessMsgFromTimer: AdaptDiamProcessMsgFromTimer(pMsg)
  DiamMsgProcForPidOM: if (DiamMsgProcForPidOM(pMsg, pFeMsg) != VOS_OK)
  DiamProcAppMsg: ulRet = DiamProcAppMsg((DiamAppMsg *)pAppMsg)
  ...
数据结构: DiamAppMsg, MsgBlock, tFeAppMsg

[常量定义]
DIAM_CMDFLAG_ANSWER: #define DIAM_CMDFLAG_ANSWER     0x00
DIAM_CMDFLAG_REQUEST: #define DIAM_CMDFLAG_REQUEST    0x01
PID_DIAM: #define PID_DIAM            306
...

[数据结构]

DiamAppMsg (外部):
// 来自: DiamApiUi.h:19
typedef struct _DiamAppMsg {
    DIAM_SSI_MSG_HEADER;
    DIAM_UINT32 AppCbNo;
    DIAM_UINT32 AppSubCbNo;
    ...
} DiamAppMsg;

MsgBlock (外部):
// 来自: v_base.h:49
typedef struct MsgCB {
    VOS_UINT32 ulSenderCpuId;
    VOS_UINT32 ulSenderPid;
    ...
} MSG_CB, MsgBlock;
```

### 格式说明

1. **函数签名**
   - 函数名
   - 完整签名（返回类型、参数）
   - 源文件位置（文件名:行号）

2. **圈复杂度**
   - McCabe 复杂度值
   - 用于评估测试工作量

3. **关键分支**
   - if/else 条件
   - switch/case 分支（含所有 case 值）
   - 循环条件
   - 每个分支的调用函数和位置

4. **Mock 清单**
   - 需要 Mock 的外部函数
   - 函数调用上下文
   - 用于单元测试准备

5. **数据结构列表**
   - 函数使用的数据结构名称

6. **常量定义**
   - 从分支条件中提取的常量
   - 完整的 #define 定义
   - 自动搜索项目中的定义

7. **数据结构详情**
   - 完整的结构体定义
   - 标注内部/外部
   - 源文件位置

## 目录结构

```
tests/regression/
├── __init__.py
├── test_regression.py      # 主测试脚本
├── utils.py                # 工具函数（对比、报告生成）
├── fixtures/               # 测试用例（C++ 代码）
│   ├── simple_call_chain.cpp
│   ├── test_chinese.cpp
│   ├── test_complex_branches.cpp
│   ├── test_data_struct.cpp
│   └── test_switch.cpp
├── baselines/              # 黄金标准输出（首次运行生成）
│   ├── simple_call_chain/
│   │   ├── summary.txt
│   │   ├── boundary.txt
│   │   └── functions/
│   │       ├── add.txt
│   │       ├── multiply.txt
│   │       └── ...
│   └── ...
└── reports/                # 测试报告（每次运行生成）
    ├── simple_call_chain_report.txt
    └── ...
```

## 使用方法

### 1. 首次运行 - 生成基准数据

```bash
# Windows (使用 venv)
venv\Scripts\python.exe tests/regression/test_regression.py --update-baseline

# Linux/Mac
python3 tests/regression/test_regression.py --update-baseline
```

这会：
- 对 `fixtures/` 中的每个 .cpp 文件运行分析
- 生成输出到 `baselines/` 目录
- 这些输出作为"黄金标准"，用于后续对比

### 2. 运行回归测试

```bash
# 运行所有测试
venv\Scripts\python.exe tests/regression/test_regression.py

# 运行特定测试
venv\Scripts\python.exe tests/regression/test_regression.py --test simple_call_chain
```

这会：
- 重新运行分析
- 与 `baselines/` 中的基准对比
- 生成差异报告到 `reports/` 目录
- 显示测试结果（通过/失败）

### 3. 更新基准（功能改进后）

当你有意改进功能，导致输出变化时：

```bash
# 更新所有基准
venv\Scripts\python.exe tests/regression/test_regression.py --update-baseline

# 只更新特定测试的基准
venv\Scripts\python.exe tests/regression/test_regression.py --update-baseline --test simple_call_chain
```

## 对比内容

回归测试会对比以下内容：

### 1. 文件数量
- `functions/` 目录中的 txt 文件数量
- 缺失的文件
- 新增的文件

### 2. 文件内容
对每个函数的 txt 文件进行逐行对比，包括：
- 函数签名和圈复杂度
- 关键分支信息
- Mock 清单
- 数据结构定义
- 常量定义

### 3. 摘要文件
- `summary.txt` - 统计信息
- `boundary.txt` - 边界分析

## 测试报告

每次测试运行后，会在 `reports/` 目录生成详细报告：

```
================================================================================
回归测试报告: simple_call_chain
时间: 2026-01-08 16:30:00
================================================================================

✅ 测试通过 - 无差异

## 关键指标对比

✅ function_file_count:
   预期: 4
   实际: 4

================================================================================
```

如果有差异，报告会显示：

```
❌ 测试失败 - 发现差异

## 关键指标对比

❌ function_file_count:
   预期: 4
   实际: 5

## 结构差异

1. 路径: extra_files
   预期: None
   实际: ['new_function.txt']

## 文件内容差异

发现 1 个文件有差异:

### calculate.txt

--- baseline/calculate.txt
+++ actual/calculate.txt
@@ -5,7 +5,7 @@
-圈复杂度: 3
+圈复杂度: 4
...
```

## 添加新测试用例

1. 在 `tests/regression/fixtures/` 中添加新的 .cpp 文件
2. 运行 `--update-baseline` 生成基准
3. 后续运行会自动包含新测试

示例：

```bash
# 1. 创建新测试文件
echo "int foo() { return 42; }" > tests/regression/fixtures/my_test.cpp

# 2. 生成基准
venv\Scripts\python.exe tests/regression/test_regression.py --update-baseline --test my_test

# 3. 运行测试
venv\Scripts\python.exe tests/regression/test_regression.py --test my_test
```

## 工作流程建议

### 日常开发
1. 修改代码前，运行回归测试确保当前状态正常
2. 修改代码后，再次运行回归测试
3. 如果测试失败，检查是预期改进还是意外退化

### 功能改进
1. 实现新功能或改进
2. 运行回归测试，查看差异
3. 确认差异是预期的改进
4. 使用 `--update-baseline` 更新基准

### CI/CD 集成
在 CI 流程中添加：

```yaml
# .github/workflows/test.yml
- name: Run regression tests
  run: |
    python tests/regression/test_regression.py
```

## 故障排查

### 问题：找不到 Python
```bash
# 确保虚拟环境已激活
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 问题：找不到测试文件
```bash
# 检查 fixtures 目录
ls tests/regression/fixtures/

# 确保有 .cpp 文件
```

### 问题：基准不存在
```bash
# 首次运行需要生成基准
python tests/regression/test_regression.py --update-baseline
```

## 高级用法

### 自定义对比逻辑

编辑 `tests/regression/utils.py` 中的 `normalize_txt_content()` 函数，添加自定义的标准化规则。

### 调整差异容忍度

修改 `compare_txt_files()` 函数，添加对特定差异的忽略逻辑。

## 注意事项

1. **基准数据的管理**
   - 基准数据应该提交到版本控制
   - 团队成员共享相同的基准
   - 定期审查和更新基准

2. **路径标准化**
   - 工具会自动移除绝对路径
   - 只保留文件名和行号
   - 确保跨平台一致性

3. **测试隔离**
   - 每个测试用例应该独立
   - 不依赖其他测试的状态
   - 使用临时目录避免污染

## 示例输出

```
找到 5 个测试用例
================================================================================

================================================================================
测试: simple_call_chain
文件: /app/tests/regression/fixtures/simple_call_chain.cpp
================================================================================
运行分析...
✓ 分析完成: /app/tests/regression/temp_output/simple_call_chain
对比差异...

报告已保存: /app/tests/regression/reports/simple_call_chain_report.txt

================================================================================
回归测试报告: simple_call_chain
时间: 2026-01-08 16:30:00
================================================================================

✅ 测试通过 - 无差异

## 关键指标对比

✅ function_file_count:
   预期: 4
   实际: 4

================================================================================
✅ 测试通过

================================================================================
测试总结
================================================================================
总计: 5
✅ 通过: 5
❌ 失败: 0
================================================================================
```
