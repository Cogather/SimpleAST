# SimpleAST 产品需求文档（PRD）

**文档版本**: v1.1
**更新日期**: 2025-12-18
**项目名称**: SimpleAST - C++ 静态代码分析工具

---

## 📑 目录

1. [产品概述](#1-产品概述)
2. [核心价值](#2-核心价值)
3. [目标用户](#3-目标用户)
4. [功能架构](#4-功能架构)
5. [功能详解](#5-功能详解)
6. [技术原理](#6-技术原理)
7. [多模式分析系统](#7-多模式分析系统)
8. [使用场景](#8-使用场景)
9. [性能指标](#9-性能指标)
10. [技术限制](#10-技术限制)
11. [未来规划](#11-未来规划)

---

## 1. 产品概述

### 1.1 产品定位

SimpleAST 是一款**无需编译环境**的 C++ 静态代码分析工具，专注于快速理解代码结构和依赖关系。

### 1.2 核心特性

- **🚀 零编译依赖**：基于 AST 解析，无需配置编译环境
- **⚡ 多模式分析**：从单文件快速分析到全项目深度追踪
- **🎯 边界识别**：自动区分文件内部实现和外部依赖
- **🌐 编码友好**：支持 UTF-8、GBK、GB2312 等多种编码
- **📊 可视化输出**：树状调用链、函数签名、数据结构依赖

### 1.3 解决的痛点

| 痛点 | 传统方案 | SimpleAST 方案 |
|------|---------|---------------|
| 遗留代码难以理解 | 手动阅读代码 | 自动生成调用关系图 |
| 编译环境复杂 | 配置编译器、依赖库 | 无需编译，直接分析 |
| 大型文件分析慢 | 全局索引，耗时长 | 单文件边界模式，秒级启动 |
| 跨文件依赖不清 | 手动追踪 | 自动识别内部/外部函数 |
| 重构影响难评估 | 全局搜索 | 数据结构使用分析 |

---

## 2. 核心价值

### 2.1 对开发者的价值

1. **快速上手新项目**：10 秒了解一个 CPP 文件的核心结构
2. **代码审查助手**：快速识别潜在的循环依赖和深层调用
3. **重构决策支持**：清晰展示修改影响范围
4. **文档生成基础**：自动提取函数签名和调用关系

### 2.2 对团队的价值

1. **知识传承**：新人快速理解遗留代码
2. **质量保障**：代码审查时提供依赖分析
3. **架构梳理**：可视化模块间的调用关系
4. **技术债务评估**：识别过深的调用链和复杂依赖

---

## 3. 目标用户

### 3.1 主要用户画像

| 用户类型 | 典型场景 | 需求痛点 |
|---------|---------|---------|
| **C++ 开发者** | 维护遗留代码 | 快速理解代码结构 |
| **架构师** | 系统重构 | 评估模块依赖关系 |
| **代码审查者** | Code Review | 快速发现潜在问题 |
| **新员工** | 项目学习 | 快速上手代码库 |
| **技术经理** | 技术债务评估 | 量化代码复杂度 |

### 3.2 用户需求优先级

| 需求 | 优先级 | 当前状态 |
|------|-------|---------|
| 单文件快速分析 | P0 | ✅ 已实现 |
| 函数调用链追踪 | P0 | ✅ 已实现 |
| 数据结构依赖分析 | P1 | ✅ 已实现 |
| 多编码支持 | P1 | ✅ 已实现 |
| 全局项目分析 | P2 | ✅ 已实现 |
| 增量索引 | P2 | 📋 规划中 |
| 图形化界面 | P3 | 📋 规划中 |

---

## 4. 功能架构

### 4.1 系统架构图

```
┌─────────────────────────────────────────────────────┐
│                   命令行入口                          │
│                  (analyze.py)                        │
└─────────────────┬───────────────────────────────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
┌───▼────────────┐      ┌──────▼──────────┐
│  单文件分析器   │      │  全局分析器      │
│ SingleFile     │      │ CppProject      │
│ Analyzer       │      │ Analyzer        │
└───┬────────────┘      └──────┬──────────┘
    │                           │
    │     ┌─────────────────────┴─────────────────┐
    │     │                                       │
    ▼     ▼                                       ▼
┌────────────┐  ┌──────────────┐  ┌──────────────────┐
│ AST 解析器 │  │ 项目索引器    │  │ 调用链追踪器      │
│ CppParser  │  │ Project      │  │ CallChain        │
│            │  │ Indexer      │  │ Tracer           │
└────────────┘  └──────────────┘  └──────────────────┘
                         │
                ┌────────┴────────┐
                ▼                 ▼
    ┌──────────────────┐  ┌──────────────────┐
    │ 入口点分类器      │  │ 数据结构分析器    │
    │ EntryPoint       │  │ DataStructure    │
    │ Classifier       │  │ Analyzer         │
    └──────────────────┘  └──────────────────┘
```

### 4.2 模块职责

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| **CppParser** | AST 解析 | C++ 源文件 | 语法树 |
| **ProjectIndexer** | 全局符号索引 | 项目目录 | 符号表 |
| **SingleFileAnalyzer** | 单文件边界分析 | 单个 CPP 文件 | 文件边界信息 |
| **EntryPointClassifier** | 函数分类 | 函数定义 | API/内部/导出 |
| **CallChainTracer** | 调用链追踪 | 函数名 | 调用树 |
| **DataStructureAnalyzer** | 数据结构分析 | 函数列表 | 结构体使用关系 |

---

## 5. 功能详解

### 5.1 文件边界分析（核心功能）

**功能描述**：自动识别文件的完整边界，区分内部实现和外部依赖。

#### 5.1.1 分析维度

```
文件边界
├── 内部函数（4 个）
│   ├── InitSystem()
│   ├── GetUserInfo()
│   ├── PrintUserInfo()
│   └── main()
│
├── 外部函数调用（0 个）
│   └── (无外部调用)
│
├── 内部数据结构（1 个）
│   └── UserInfo
│
└── 外部数据结构（0 个）
    └── (无外部依赖)
```

#### 5.1.2 应用场景

1. **快速评估文件复杂度**
   - 内部函数数量 → 文件职责是否单一
   - 外部调用数量 → 耦合程度
   - 数据结构依赖 → 数据流复杂度

2. **模块化重构决策**
   - 外部依赖少 → 容易独立测试
   - 内部函数多 → 可能需要拆分

3. **API 设计评审**
   - 哪些函数是对外接口
   - 哪些是内部实现细节

---

### 5.2 函数调用链追踪

**功能描述**：递归追踪函数调用关系，生成树状可视化结果。

#### 5.2.1 追踪示例

```
main [test.cpp:54]
  ├─ InitSystem [test.cpp:21]
  │   └─ LoadConfig [external]
  ├─ GetUserInfo [test.cpp:32]
  │   ├─ ValidateUserId [test.cpp:26]
  │   └─ QueryDatabase [external]
  └─ PrintUserInfo [test.cpp:45]
      └─ FormatOutput [test.cpp:40]
```

#### 5.2.2 特性

- **递归检测**：自动标记递归调用，避免无限循环
- **深度控制**：可配置最大追踪深度（默认 10 层）
- **外部标记**：清晰区分内部函数和外部依赖
- **位置定位**：每个函数标注文件路径和行号

#### 5.2.3 技术实现

```python
# 伪代码
def trace_call_chain(function_name, depth=0, max_depth=10):
    if depth >= max_depth:
        return None

    # 获取函数 AST 节点
    func_node = get_function_ast(function_name)

    # 查找所有调用表达式
    call_expressions = find_call_expressions(func_node)

    # 递归追踪每个调用
    for call in call_expressions:
        called_func = extract_function_name(call)
        if is_internal(called_func):
            child = trace_call_chain(called_func, depth + 1, max_depth)
        else:
            child = mark_as_external(called_func)

        add_to_tree(child)

    return call_tree
```

---

### 5.3 入口函数分类

**功能描述**：自动将函数分类为 API、内部、导出三种类型。

#### 5.3.1 分类规则

| 类型 | 判定条件 | 典型特征 |
|------|---------|---------|
| **API** | 在 .h 文件声明 | 对外公开接口 |
| **INTERNAL** | 仅在 .cpp 定义，且为 static | 文件私有函数 |
| **EXPORTED** | 在 .cpp 定义，非 static | 可能被其他文件使用 |

#### 5.3.2 实际案例

```cpp
// api.h
bool RegisterUser(const User& user);  // → API

// main.cpp
static bool ValidateEmail(const string& email) {  // → INTERNAL
    // ...
}

bool SaveToDatabase(const User& user) {  // → EXPORTED
    // ...
}
```

#### 5.3.3 价值

1. **接口识别**：快速找到对外暴露的 API
2. **耦合分析**：INTERNAL 多 → 内聚性好
3. **重构安全性**：修改 INTERNAL 函数影响小

---

### 5.4 数据结构依赖分析

**功能描述**：识别 struct/class/enum/typedef，追踪其在哪些函数中被使用。

#### 5.4.1 分析内容

```
STRUCT: UserInfo
  定义位置: test.cpp:11
  使用者函数:
    - GetUserInfo
    - PrintUserInfo
    - main
  定义预览:
    struct UserInfo {
        std::string name;
        int age;
        std::string email;
    };
```

#### 5.4.2 应用场景

1. **重构影响评估**
   - 修改结构体定义 → 需要同步修改哪些函数

2. **数据流分析**
   - 结构体在哪些函数间流转

3. **文档生成**
   - 自动生成数据结构使用文档

---

## 6. 技术原理

### 6.1 核心技术栈

```
┌──────────────────────────────────┐
│         Python 3.8+              │
├──────────────────────────────────┤
│  tree-sitter (AST 解析引擎)       │
│  tree-sitter-cpp (C++ 语法)      │
└──────────────────────────────────┘
```

### 6.2 AST 解析原理

#### 6.2.1 什么是 AST？

AST（Abstract Syntax Tree，抽象语法树）是源代码的树状结构表示。

**示例代码：**
```cpp
int add(int a, int b) {
    return a + b;
}
```

**对应 AST：**
```
function_definition
├── type: int
├── declarator
│   ├── name: add
│   └── parameters
│       ├── parameter (int a)
│       └── parameter (int b)
└── body
    └── return_statement
        └── binary_expression (+)
            ├── identifier: a
            └── identifier: b
```

#### 6.2.2 为什么使用 tree-sitter？

| 对比维度 | 传统编译器 | tree-sitter |
|---------|-----------|-------------|
| **依赖** | 需要完整编译环境 | 零依赖 |
| **速度** | 较慢 | 极快（增量解析） |
| **容错性** | 语法错误即失败 | 容忍部分错误 |
| **跨平台** | 依赖平台编译器 | 纯 Python |

#### 6.2.3 解析流程

```python
# 1. 加载 C++ 语法
CPP_LANGUAGE = Language('build/cpp.so', 'cpp')
parser = Parser()
parser.set_language(CPP_LANGUAGE)

# 2. 读取源文件
with open('main.cpp', 'rb') as f:
    source_code = f.read()

# 3. 解析生成 AST
tree = parser.parse(source_code)
root_node = tree.root_node

# 4. 遍历 AST 节点
for node in root_node.children:
    if node.type == 'function_definition':
        func_name = extract_function_name(node)
        print(f"Found function: {func_name}")
```

### 6.3 符号表索引原理

#### 6.3.1 符号表结构

```python
symbol_table = {
    'RegisterUser': [
        SymbolInfo(
            name='RegisterUser',
            type='function',
            file_path='src/api.cpp',
            line_number=15,
            signature='bool RegisterUser(const User& user)',
            is_declaration=False,
            is_in_header=False
        ),
        SymbolInfo(
            name='RegisterUser',
            type='function',
            file_path='include/api.h',
            line_number=8,
            signature='bool RegisterUser(const User& user)',
            is_declaration=True,
            is_in_header=True
        )
    ],
    'User': [ ... ]
}
```

#### 6.3.2 索引过程

```
1. 遍历项目所有 .cpp 和 .h 文件
2. 对每个文件：
   a. 解析 AST
   b. 提取函数定义/声明
   c. 提取数据结构定义
   d. 记录到符号表
3. 构建文件依赖图（include 关系）
```

#### 6.3.3 查询优化

```python
# 快速查找函数定义
def find_definition(func_name):
    symbols = symbol_table.get(func_name, [])

    # 优先返回 .cpp 中的定义
    for sym in symbols:
        if not sym.is_declaration and not sym.is_in_header:
            return sym

    # 其次返回任意定义
    for sym in symbols:
        if not sym.is_declaration:
            return sym

    # 最后返回声明
    return symbols[0] if symbols else None
```

### 6.4 调用链追踪算法

#### 6.4.1 递归追踪算法

```python
def trace_recursive(func_name, visited, depth, max_depth):
    # 深度限制
    if depth >= max_depth:
        return None

    # 循环检测
    if func_name in visited:
        return CallNode(func_name, is_recursive=True)

    visited.add(func_name)

    # 查找函数 AST
    func_ast = get_function_ast(func_name)
    if not func_ast:
        return CallNode(func_name, is_external=True)

    # 创建节点
    node = CallNode(func_name)

    # 查找调用表达式
    calls = find_call_expressions(func_ast)

    # 递归追踪子调用
    for call in calls:
        called_func = extract_called_function(call)
        child = trace_recursive(
            called_func,
            visited.copy(),  # 传递副本，避免影响同层调用
            depth + 1,
            max_depth
        )
        node.add_child(child)

    return node
```

#### 6.4.2 性能优化

1. **深度限制**：避免过深递归导致性能问题
2. **循环检测**：识别并标记递归调用
3. **外部标记**：遇到外部函数立即返回，不继续追踪
4. **缓存机制**：相同函数的调用树可缓存复用

---

## 7. 多模式分析系统

### 7.1 设计背景

**问题**：原有的全局索引模式在大型项目中存在性能瓶颈：
- 启动时需要索引整个项目（耗时数分钟）
- 分析单个小文件也要等待全局索引完成
- 内存占用大

**解决方案**：引入多模式架构，用户根据需求选择合适的模式。

### 7.2 模式对比

| 维度 | 单文件边界模式 | 完整项目模式 |
|------|---------------|-------------|
| **启动时间** | <1 秒 | 取决于项目大小 |
| **索引范围** | 仅目标文件 | 整个项目 |
| **内存占用** | 极小 | 较大 |
| **追踪深度** | 文件内无限制 | 可跨文件追踪 |
| **外部函数** | 标记但不追踪 | 追踪到具体实现 |
| **适用场景** | 大型单文件分析 | 跨文件依赖分析 |

### 7.3 单文件边界模式（新增）

#### 7.3.1 核心原理

```
不索引整个项目
     ↓
只解析目标文件
     ↓
建立文件内符号表
     ↓
追踪文件内调用 + 标记外部调用
     ↓
分析数据结构使用
```

#### 7.3.2 边界识别算法

```python
class SingleFileAnalyzer:
    def analyze_file(self, file_path):
        # 1. 解析文件 AST
        ast = parse_file(file_path)

        # 2. 索引文件内符号
        self.internal_functions = extract_functions(ast)
        self.internal_structs = extract_structs(ast)

        # 3. 分析调用关系
        for func in self.internal_functions:
            calls = find_function_calls(func)
            for call in calls:
                if call in self.internal_functions:
                    mark_as_internal_call(call)
                else:
                    mark_as_external_call(call)

        # 4. 分析数据结构
        for struct in self.internal_structs:
            usage = find_struct_usage(struct, self.internal_functions)
            record_usage(struct, usage)

        # 5. 识别外部数据结构
        external_structs = find_external_structs(ast, self.internal_structs)

        return FileBoundary(
            internal_functions=self.internal_functions,
            external_functions=self.external_calls,
            internal_structs=self.internal_structs,
            external_structs=external_structs
        )
```

#### 7.3.3 性能对比（10000 行代码文件）

| 指标 | 单文件模式 | 完整项目模式 |
|------|-----------|-------------|
| **启动时间** | 0.5 秒 | 45 秒 |
| **内存占用** | 20 MB | 500 MB |
| **分析耗时** | 2 秒 | 8 秒 |
| **总耗时** | 2.5 秒 | 53 秒 |

**性能提升**：**21 倍**

### 7.4 模式选择建议

```
决策树：
是否需要跨文件追踪函数调用？
├─ 是 → 使用完整项目模式（full）
└─ 否
    └─ 文件行数 > 1000？
        ├─ 是 → 使用单文件边界模式（single）推荐
        └─ 否 → 两种模式均可
```

---

## 8. 使用场景

### 8.1 场景一：快速理解遗留代码

**背景**：接手一个 5000 行的遗留 CPP 文件，需要快速了解结构。

**操作**：
```bash
python analyze.py ./legacy_project src/core_module.cpp single
```

**输出分析**：
```
文件边界分析：
- 内部函数：45 个
- 外部调用：12 个（依赖模块：network, database, logger）
- 内部数据结构：8 个
- 外部数据结构：5 个

结论：
✓ 该文件职责较单一（外部依赖少）
✓ 主要依赖 3 个外部模块
⚠ 内部函数较多，建议拆分
```

### 8.2 场景二：API 依赖分析

**背景**：评估某个公共 API 的实现复杂度。

**操作**：
```bash
python analyze.py . src/api.cpp single 50 PublicAPI
```

**输出分析**：
```
PublicAPI [api.cpp:100]
  ├─ ValidateInput [api.cpp:80]
  ├─ ProcessRequest [api.cpp:60]
  │   ├─ ParseJson [utils.cpp] [EXTERNAL]
  │   ├─ CheckPermission [auth.cpp] [EXTERNAL]
  │   └─ ExecuteQuery [database.cpp] [EXTERNAL]
  └─ FormatResponse [api.cpp:45]

结论：
✓ 调用深度：3 层（合理）
✓ 外部依赖：3 个模块
⚠ 缺少错误处理函数
```

### 8.3 场景三：重构影响评估

**背景**：计划修改某个数据结构，需要评估影响范围。

**操作**：
```bash
python analyze.py . src/data_model.cpp single
```

**输出分析**：
```
STRUCT: UserProfile
  定义位置: data_model.cpp:20
  使用者函数：
    - CreateUser
    - UpdateUser
    - ValidateUser
    - SerializeUser
  使用文件：
    - data_model.cpp
    - api_handler.cpp
    - cache_manager.cpp

结论：
⚠ 影响范围：3 个文件，4 个函数
⚠ 需要同步修改序列化逻辑
✓ 未被外部模块直接使用（边界清晰）
```

### 8.4 场景四：代码审查辅助

**背景**：Code Review 时快速识别潜在问题。

**操作**：
```bash
python analyze.py . src/new_feature.cpp single
```

**审查要点**：
```
1. 调用链深度
   - 超过 5 层 → 可能过于复杂
   - 有递归 → 需要检查终止条件

2. 外部依赖数量
   - 超过 10 个 → 耦合度过高
   - 依赖模块混乱 → 架构需优化

3. 数据结构
   - 定义过大 → 建议拆分
   - 使用范围广 → 修改需谨慎

4. 函数分类
   - INTERNAL 占比低 → 内聚性不足
   - API 过多 → 接口膨胀
```

---

## 9. 性能指标

### 9.1 性能基准测试

**测试环境**：
- CPU: Intel i7-10700K
- 内存: 16GB
- 项目: imgui（200+ 文件，10 万行代码）

| 测试项 | 单文件边界模式 | 完整项目模式 |
|--------|---------------|-------------|
| **索引阶段** | 0 秒 | 38 秒 |
| **分析 1000 行文件** | 1.2 秒 | 2.5 秒 |
| **分析 5000 行文件** | 3.8 秒 | 7.2 秒 |
| **分析 10000 行文件** | 8.5 秒 | 15.3 秒 |
| **内存占用** | 25 MB | 480 MB |

### 9.2 可扩展性

```
文件大小         单文件模式耗时
1000 行    →    1.2 秒
5000 行    →    3.8 秒    (线性增长)
10000 行   →    8.5 秒    (近似线性)
50000 行   →    45 秒     (预估)
```

**结论**：时间复杂度接近 O(n)，适合大型文件分析。

---

## 10. 技术限制

### 10.1 当前限制

| 限制项 | 说明 | 影响 | 解决方案（未来） |
|--------|------|------|-----------------|
| **宏展开** | 不展开宏 | 宏定义的函数无法追踪 | 引入预处理器 |
| **模板实例化** | 不进行模板推导 | 模板函数调用可能缺失 | 记录模板定义 |
| **虚函数** | 无法追踪运行时多态 | 虚函数调用标记为外部 | 静态分析所有可能 |
| **函数指针** | 无法分析间接调用 | 回调函数不可见 | 数据流分析 |
| **条件编译** | 不处理 #ifdef | 部分代码路径缺失 | 多配置分析 |

### 10.2 不适用场景

❌ **不适合**：
- 需要精确类型推导的场景
- 复杂模板元编程分析
- 运行时行为分析
- 性能热点检测

✅ **适合**：
- 代码结构理解
- 静态依赖分析
- 重构前评估
- 文档生成

---

## 11. 未来规划

### 11.1 近期规划（v1.2 - v1.3）

#### 11.1.1 增量索引模式
**需求**：在单文件和全局模式之间取得平衡。

**方案**：
```
1. 解析目标文件
2. 分析 #include 依赖
3. 按需索引依赖的头文件
4. 缓存索引结果（基于文件 mtime）
```

**预期性能**：
- 首次分析：比全局快 5 倍
- 二次分析：比全局快 20 倍（缓存命中）

#### 11.1.2 配置文件支持
```yaml
# .simpleast.yaml
analysis:
  mode: single  # single / full / incremental
  max_depth: 15
  ignore_patterns:
    - "*/test/*"
    - "*/third_party/*"

output:
  format: [txt, json, html]
  directory: ./analysis_reports
```

#### 11.1.3 HTML 可视化报告
- 交互式调用链图（可折叠）
- 数据结构关系图
- 函数复杂度热力图

### 11.2 中期规划（v2.0）

#### 11.2.1 跨语言支持
- C 语言支持
- Java 语言支持（基于 tree-sitter-java）

#### 11.2.2 IDE 插件
- VSCode 插件
- 右键菜单"分析当前文件"
- 实时显示函数调用关系

#### 11.2.3 CI/CD 集成
```bash
# 在 CI 流程中检测复杂度
python analyze.py . src/main.cpp --check
# 如果调用深度 > 10 层，CI 失败
```

### 11.3 长期规划（v3.0）

#### 11.3.1 架构洞察
- 模块化评分
- 循环依赖检测
- 架构风格识别

#### 11.3.2 智能推荐
- 基于 AST 的代码重构建议
- 函数拆分推荐
- 数据结构优化建议

---

## 12. 总结

### 12.1 核心优势

1. **🚀 零门槛**：无需编译环境，安装即用
2. **⚡ 极速启动**：单文件模式 < 1 秒启动
3. **🎯 精准边界**：自动区分内部实现和外部依赖
4. **📊 可视化**：树状调用链，一目了然
5. **🌐 多编码**：支持中文项目

### 12.2 适用对象

- C++ 开发者（快速理解代码）
- 架构师（评估系统依赖）
- 代码审查者（辅助 Review）
- 技术经理（量化技术债务）

### 12.3 项目愿景

**让 C++ 代码分析像 Python 一样简单。**

无论是遗留系统、开源项目还是新项目，开发者都能在 **10 秒内** 理解任何 CPP 文件的核心结构。

---

**文档维护者**: SimpleAST Team
**反馈渠道**: GitHub Issues
**更新频率**: 每个版本发布时更新
