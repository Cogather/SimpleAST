# 详细日志说明

## 日志输出到stderr

所有详细日志通过 `2>&1` 或 `2>debug.log` 查看。

## 日志分类

### 1. [分支分析] - 圈复杂度和条件提取

```
[分支分析] 开始分析函数: PidDiamMsgProc
[分支分析] 统计: if=6, switch=1, case=8, loop=0, early_return=2
[分支分析] 圈复杂度: 15 (基础1 + 决策点14, 逻辑运算符0, 三元运算0)
[分支分析]   分析switch: 行68, 条件=(pMsg->ulSenderPid)
[分支分析]     找到 8 个case节点
[分支分析]       case 1: PID_DIAM
[分支分析]       case 2: DOPRA_PID_TIMER
[分支分析]       case 3: PID_SF
[分支分析]       case 4: PID_DSP
[分支分析]       case 5: PID_HAPD
[分支分析]       ... 还有 3 个case
[分支分析]     有default分支: False
[分支分析]     生成建议: 8 个case值
[分支分析] 提取了 7 个关键条件
```

**包含信息**:
- if/switch/loop/early_return 数量统计
- 圈复杂度计算过程
- switch的每个case值
- 是否有default分支

### 2. [递归展开] - 函数调用链遍历

```
[递归展开] 处理函数: PidDiamMsgProc (层级: 主函数)
[递归展开]   找到 14 个直接调用
[递归展开]   分类: 内部0个, 外部13个
```

**包含信息**:
- 当前处理的函数名和层级
- 直接调用的函数数量
- 内部/外部函数分类
- 是否跳过（防止循环依赖）

### 3. [Mock生成] - 外部依赖识别和签名搜索

```
[Mock生成] 外部函数分类: 业务11个, 标准库0个, 日志0个
[Mock生成]   ✗ AdaptDiamProcessMsgFromTimer: 未找到签名
[Mock生成]   ✗ DiamProcAppMsg: 未找到签名
[Mock生成]   ✓ CheckPidDiamMsg: 找到签名
```

**包含信息**:
- 外部函数自动分类（业务/标准库/日志）
- 每个业务函数的签名搜索结果
- ✓ = 找到签名，✗ = 未找到

### 4. [数据结构提取] - 类型识别和过滤

```
[数据结构提取] 分析函数: PidDiamMsgProc
[数据结构提取] 签名: VOS_VOID PidDiamMsgProc(MsgBlock *pMsg) // ...
[数据结构提取] ✓ 内部结构: MsgBlock
[数据结构提取] ✗ 过滤基础类型: VOS_VOID (匹配模式: ^VOS_(VOID|INT|UINT|CHAR|BOOL|LONG|SHORT|DWORD|WORD|BYTE)\d*$)
[数据结构提取] 内部结构: 找到 1 个, 过滤 1 个
[数据结构提取] 正则提取: 2 个参数类型, 0 个类名
[数据结构提取] 待过滤类型: ['MsgBlock', 'VOS_VOID']
[数据结构提取] ✗ 过滤项目基础类型: VOS_VOID (匹配: ^VOS_(VOID|INT|UINT|CHAR|BOOL|LONG|SHORT|DWORD|WORD|BYTE)\d*$)
[数据结构提取] 外部类型: 找到 0 个, 过滤 1 个
[数据结构提取] 总计: 1 个数据结构 (内部 1 + 外部 0)
```

**包含信息**:
- 内部定义的结构（保留/过滤）
- 正则提取的参数类型
- 每个类型的过滤判断和原因
- 最终统计

### 5. [常量提取] - 从签名、条件、case值提取

```
[常量提取] 开始分析函数: PidDiamMsgProc
[常量提取] 从签名提取到 1 个大写标识符: ['VOS_VOID']
[常量提取] 找到分支分析，共 7 个条件
[常量提取]   条件1 [if]: 提取 0 个标识符
[常量提取]   条件2 [if]: 提取 1 个标识符
[常量提取]   条件7 [switch]: 提取 0 个标识符
[常量提取]   switch找到 8 个case值: ['PID_DIAM', 'DOPRA_PID_TIMER', 'PID_SF', 'PID_DSP', 'PID_HAPD', 'PID_MAINTAIN', 'PID_OM', 'default']
[常量提取] 总共提取到 14 个唯一标识符
[常量提取] 准备搜索 1 个文件
[常量提取]   - test_real_scenario.cpp
[常量提取] ✓ 在 test_real_scenario.cpp 找到 #define PID_DIAM
[常量提取] ✓ 在 test_real_scenario.cpp 找到 #define PID_DSP
...
[常量提取] 完成: 找到 13/14 个定义
[常量提取] 未找到: ['VOS_VOID']
```

**包含信息**:
- 从签名/条件/switch case提取的标识符
- 搜索的文件列表
- 每个常量的查找结果
- 未找到的常量列表

### 6. [文件输出] - 报告生成进度（仅大文件>50函数）

```
[文件输出] 生成函数报告 (1/208): AddCircle
[文件输出] ✓ 写入文件: AddCircle.txt (1523 字符)
[文件输出] 生成函数报告 (2/208): AddConvexPolyFilled
[文件输出] ✓ 写入文件: AddConvexPolyFilled.txt (2847 字符)
```

**包含信息**:
- 当前进度（x/total）
- 文件名和大小

## 使用场景

### 诊断：为什么某个常量没找到？

```bash
python analyze.py . test.cpp single 15 MyFunc 2>debug.log
grep "\[常量提取\]" debug.log
```

查看：
1. 是否从switch case中提取到？
2. 搜索了哪些文件？
3. 具体在哪个文件找到/未找到？

### 诊断：为什么某个结构被过滤了？

```bash
grep "\[数据结构提取\]" debug.log | grep "过滤"
```

查看：
1. 匹配的过滤规则
2. 是否误判

### 诊断：为什么Mock清单不完整？

```bash
grep "\[Mock生成\]" debug.log
```

查看：
1. 外部函数分类（哪些被归为标准库/日志）
2. 哪些找到签名，哪些没找到

### 查看完整分析过程

```bash
# 所有日志
python analyze.py . test.cpp single 15 MyFunc 2>&1 | less

# 只看关键部分
python analyze.py . test.cpp single 15 MyFunc 2>&1 | grep -E "\[分支分析\]|\[常量提取\]|\[数据结构提取\]"
```

## 日志级别

当前所有详细日志都输出到 stderr，可以独立控制：

```bash
# 只看结果，不看日志
python analyze.py . test.cpp single 15 MyFunc 2>/dev/null

# 只看日志，不看结果
python analyze.py . test.cpp single 15 MyFunc >/dev/null

# 分别保存
python analyze.py . test.cpp single 15 MyFunc >result.txt 2>debug.log
```
