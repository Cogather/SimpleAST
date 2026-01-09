# 回归测试框架

## 快速开始

```bash
# 1. 首次运行 - 生成基准数据
venv\Scripts\python.exe tests/regression/test_regression.py --update-baseline

# 2. 运行回归测试
venv\Scripts\python.exe tests/regression/test_regression.py

# 3. 查看报告
cat tests/regression/reports/*_report.txt
```

## 核心概念

### TXT 文件格式

回归测试对比的是 `functions/` 目录中每个函数的 txt 文件。每个文件包含：

```
函数: FunctionName
返回类型 FunctionName(参数列表) // 文件名.cpp:行号
圈复杂度: N
关键分支:
  1. (条件表达式)
     case值: VALUE1, VALUE2, ...
     详细分支:
       case VALUE1:
         调用: Function1, Function2
         位置: 行X-Y
       ...
  2. (另一个条件)
  ...
Mock:
  ExternalFunc1: 调用上下文
  ExternalFunc2: 调用上下文
  ...
数据结构: Struct1, Struct2, ...

[常量定义]
CONSTANT1: #define CONSTANT1 value
CONSTANT2: #define CONSTANT2 value
...

[数据结构]

Struct1 (内部/外部):
// 来自: 文件名.h:行号
typedef struct {
    字段定义...
} Struct1;
```

**对比内容**：
- 函数签名和位置
- 圈复杂度值
- 关键分支的数量和内容
- Mock 清单的完整性
- 常量定义的准确性
- 数据结构的完整定义

### 为什么对比 TXT 文件？

1. **用户视角** - 对比用户实际看到的输出，而不是内部数据结构
2. **完整性** - 包含所有关键信息：分支、Mock、数据结构、常量
3. **可读性** - 差异报告直观易懂
4. **实用性** - 这些文件直接用于单元测试生成

## 功能特性

✅ **基于实际输出对比** - 对比 `functions/` 目录中的 txt 文件，而不是内部数据结构
✅ **黄金标准管理** - 首次运行生成基准，后续对比差异
✅ **详细差异报告** - 显示文件级别的 diff，清晰展示变更
✅ **路径标准化** - 自动移除绝对路径，确保跨平台一致性
✅ **选择性测试** - 可以只运行特定测试用例
✅ **易于维护** - 功能改进后可以方便地更新基准

## 目录结构

```
tests/regression/
├── README.md              # 详细使用文档
├── test_regression.py     # 主测试脚本
├── utils.py               # 工具函数
├── fixtures/              # 测试用例（.cpp 文件）
├── baselines/             # 黄金标准输出
└── reports/               # 测试报告
```

## 工作原理

1. **生成基准**：对每个测试用例运行分析，保存输出到 `baselines/`
2. **运行测试**：重新运行分析，与基准对比
3. **对比内容**：
   - 函数文件数量
   - 每个函数 txt 文件的内容（逐行对比）
   - summary.txt 和 boundary.txt
4. **生成报告**：显示差异的详细信息

## 使用场景

### 场景 1：日常开发保护
```bash
# 修改代码前
venv\Scripts\python.exe tests/regression/test_regression.py

# 修改代码后
venv\Scripts\python.exe tests/regression/test_regression.py

# 如果失败，检查是否是意外退化
```

### 场景 2：功能改进验证
```bash
# 实现新功能
# ...

# 运行测试查看差异
venv\Scripts\python.exe tests/regression/test_regression.py

# 确认差异是预期的改进
# 更新基准
venv\Scripts\python.exe tests/regression/test_regression.py --update-baseline
```

### 场景 3：添加新测试
```bash
# 1. 添加新的 .cpp 文件到 fixtures/
cp my_test.cpp tests/regression/fixtures/

# 2. 生成基准
venv\Scripts\python.exe tests/regression/test_regression.py --update-baseline --test my_test

# 3. 后续会自动包含在测试中
venv\Scripts\python.exe tests/regression/test_regression.py
```

## 测试报告示例

```
================================================================================
回归测试报告: test_complex_branches
时间: 2026-01-08 16:30:00
================================================================================

✅ 测试通过 - 无差异

## 关键指标对比

✅ function_file_count:
   预期: 3
   实际: 3

================================================================================
```

如果有差异：

```
❌ 测试失败 - 发现差异

## 关键指标对比

❌ function_file_count:
   预期: 3
   实际: 4

## 文件内容差异

发现 1 个文件有差异:

### processData.txt

--- baseline/processData.txt
+++ actual/processData.txt
@@ -2,7 +2,7 @@
 void processData(int* data, int size) // test_complex_branches.cpp:10
-圈复杂度: 5
+圈复杂度: 6
 关键分支:
-  1. (size > 0)
-  2. (data != NULL)
+  1. (data != NULL)
+  2. (size > 0)
+  3. (size < MAX_SIZE)
```

## 详细文档

完整使用说明请参考：[tests/regression/README.md](tests/regression/README.md)

## 演示

运行演示脚本查看完整流程：

```bash
venv\Scripts\python.exe demo_regression_tests.py
```

## CI/CD 集成

在 CI 流程中添加回归测试：

```yaml
# .github/workflows/test.yml
name: Regression Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run regression tests
        run: python tests/regression/test_regression.py
```

## 注意事项

1. **基准数据管理**
   - 基准数据应该提交到版本控制
   - 团队成员共享相同的基准
   - 定期审查和更新基准

2. **测试用例选择**
   - 选择代表性的测试用例
   - 覆盖核心功能和边界情况
   - 保持测试用例简洁

3. **差异判断**
   - 不是所有差异都是问题
   - 功能改进会导致预期的差异
   - 使用 `--update-baseline` 更新基准

## 故障排查

详见 [tests/regression/README.md](tests/regression/README.md) 的故障排查章节。
