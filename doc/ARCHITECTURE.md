# SimpleAST 代码架构详解

## 📋 目录

1. [架构概览](#架构概览)
2. [分层架构](#分层架构)
3. [核心模块详解](#核心模块详解)
4. [数据流转](#数据流转)
5. [设计模式](#设计模式)
6. [扩展点](#扩展点)

---

## 架构概览

### 整体设计理念

SimpleAST 采用**分层插件化架构**，核心思想：

```
无需编译 → AST解析 → 模块化分析 → 灵活输出
```

**关键特性**：
- ✅ **无编译依赖**：基于 tree-sitter AST，不需要编译器
- ✅ **模式化分析**：支持多种分析模式，灵活切换
- ✅ **模块化设计**：每个分析器职责单一，易于扩展
- ✅ **性能优化**：按需分析，避免不必要的计算

### 项目结构

```
SimpleAST/
├── simple_ast/              # 核心包
│   ├── __init__.py          # 包入口，导出主要API
│   ├── analysis_modes.py    # 分析模式定义
│   ├── cpp_parser.py        # Tree-sitter包装器（基础层）
│   ├── cpp_analyzer.py      # 主分析器（协调层）
│   │
│   ├── # 索引层（全局模式）
│   ├── project_indexer.py   # 全局项目索引
│   │
│   ├── # 分析层（功能模块）
│   ├── single_file_analyzer.py    # 单文件边界分析
│   ├── entry_point_classifier.py  # 入口函数分类
│   ├── call_chain_tracer.py       # 调用链追踪
│   ├── data_structure_analyzer.py # 数据结构分析
│   ├── branch_analyzer.py         # 分支复杂度分析
│   ├── external_classifier.py     # 外部函数分类
│   └── auto_classifier.py         # 自动分类（AI辅助）
│
├── analyze.py               # 命令行入口
├── tests/                   # 测试代码和数据
├── output/                  # 输出目录
├── logs/                    # 日志目录
└── doc/                     # 文档
```

---

## 分层架构

### 架构分层图

```
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application Layer)                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  analyze.py - 命令行接口，参数解析，输出管理        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 协调层 (Orchestration Layer)                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  CppProjectAnalyzer - 主分析器                       │    │
│  │  • 模式选择                                           │    │
│  │  • 组件协调                                           │    │
│  │  • 结果聚合                                           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AnalysisResult - 结果数据模型                       │    │
│  │  • 统一数据格式                                       │    │
│  │  • 报告生成                                           │    │
│  │  • JSON序列化                                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    索引层 (Indexing Layer)                    │
│  ┌──────────────────────┐     ┌─────────────────────────┐   │
│  │ ProjectIndexer       │     │ SingleFileAnalyzer      │   │
│  │ 全局项目索引         │     │ 单文件边界分析          │   │
│  │ • 文件扫描           │     │ • 函数索引              │   │
│  │ • 函数索引           │     │ • 数据结构索引          │   │
│  │ • 跨文件依赖         │     │ • 内外部区分            │   │
│  └──────────────────────┘     └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   分析层 (Analysis Layer)                     │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │ CallChainTracer │  │ BranchAnalyzer   │  │ External   │ │
│  │ 调用链追踪      │  │ 分支分析         │  │ Classifier │ │
│  └─────────────────┘  └──────────────────┘  └────────────┘ │
│                                                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │ EntryPoint      │  │ DataStructure    │  │ Auto       │ │
│  │ Classifier      │  │ Analyzer         │  │ Classifier │ │
│  └─────────────────┘  └──────────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    基础层 (Foundation Layer)                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  CppParser - Tree-sitter 包装器                      │    │
│  │  • AST 解析                                           │    │
│  │  • 节点遍历                                           │    │
│  │  • 文本提取                                           │    │
│  │  • 多编码支持                                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AnalysisMode - 模式配置                             │    │
│  │  • 模式定义（枚举）                                   │    │
│  │  • 配置管理（dataclass）                              │    │
│  │  • 策略选择                                           │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     第三方库 (External Libraries)             │
│  • tree-sitter        - AST 解析引擎                         │
│  • tree-sitter-cpp    - C++ 语言支持                         │
│  • pathlib           - 路径处理                              │
│  • dataclasses       - 数据模型                              │
└─────────────────────────────────────────────────────────────┘
```

### 分层职责

| 层级 | 职责 | 关键组件 |
|------|------|----------|
| **应用层** | 用户接口、参数处理、输出格式化 | `analyze.py` |
| **协调层** | 模式选择、组件协调、结果聚合 | `CppProjectAnalyzer`, `AnalysisResult` |
| **索引层** | 代码索引、符号表构建 | `ProjectIndexer`, `SingleFileAnalyzer` |
| **分析层** | 具体分析功能实现 | 各种 Analyzer 和 Classifier |
| **基础层** | AST 解析、通用工具 | `CppParser`, `AnalysisMode` |

---

## 核心模块详解

### 1. 基础层 (Foundation)

#### `cpp_parser.py` - AST 解析器

**职责**：封装 tree-sitter，提供 C++ 代码解析能力

**核心方法**：
```python
class CppParser:
    def __init__(self)
        # 初始化 tree-sitter C++ 解析器

    def parse_file(file_path) -> Tree
        # 解析文件，返回 AST

    def parse_string(source_code) -> Tree
        # 解析字符串代码

    @staticmethod
    def get_node_text(node, source_code) -> str
        # 提取节点文本，支持多编码（UTF-8, GBK, GB2312）

    @staticmethod
    def find_nodes_by_type(node, node_type) -> List[Node]
        # 递归查找特定类型的节点

    @staticmethod
    def get_function_name(func_node, source_code) -> str
        # 提取函数名（包括成员函数、模板等）

    @staticmethod
    def get_function_signature(func_node, source_code) -> str
        # 提取完整函数签名
```

**设计要点**：
- 🎯 使用静态方法提供工具函数（无需实例化）
- 🌍 多编码支持：UTF-8 → GBK → GB2312 → Latin-1 回退链
- 🔧 封装 tree-sitter 复杂性，提供简洁 API

---

#### `analysis_modes.py` - 分析模式

**职责**：定义分析模式和配置策略

**核心设计**：

```python
class AnalysisMode(Enum):
    FULL_PROJECT        # 全局索引模式
    SINGLE_FILE_BOUNDARY # 单文件边界模式 ⭐ 默认
    INCREMENTAL         # 增量模式（未来）
    LIGHTWEIGHT         # 轻量模式（未来）

@dataclass
class AnalysisModeConfig:
    mode: AnalysisMode
    requires_full_index: bool      # 是否需要全局索引
    max_trace_depth: int           # 最大追踪深度
    trace_external_functions: bool # 是否追踪外部函数
    analyze_data_structures: bool  # 是否分析数据结构
    description: str
```

**模式对比**：

| 模式 | 全局索引 | 追踪深度 | 追踪外部 | 场景 |
|------|---------|---------|---------|------|
| **FULL_PROJECT** | ✅ 需要 | 10 | ✅ 是 | 项目级全局分析 |
| **SINGLE_FILE_BOUNDARY** ⭐ | ❌ 不需要 | 100 | ❌ 否 | 快速单文件分析（推荐） |
| INCREMENTAL | ❌ 不需要 | 10 | ✅ 是 | 按需索引（未来） |
| LIGHTWEIGHT | ❌ 不需要 | 0 | ❌ 否 | 只提取结构（未来） |

**策略模式**：不同模式对应不同的配置和执行路径

---

### 2. 索引层 (Indexing)

#### `project_indexer.py` - 全局项目索引器

**职责**：扫描整个项目，建立全局符号表

**使用场景**：`FULL_PROJECT` 模式

**核心功能**：
```python
class ProjectIndexer:
    def index_project(self)
        # 递归扫描项目所有 .cpp/.h 文件
        # 建立全局函数定义索引

    def find_definition(func_name) -> FunctionDefinition
        # 查找函数定义（跨文件）

    def find_declarations(func_name) -> List[str]
        # 查找所有声明位置
```

**优缺点**：
- ✅ 优点：支持跨文件调用链追踪，完整依赖图
- ❌ 缺点：首次扫描慢，内存占用大

---

#### `single_file_analyzer.py` - 单文件边界分析器 ⭐

**职责**：深度分析单个文件的完整边界（不需要全局索引）

**使用场景**：`SINGLE_FILE_BOUNDARY` 模式（默认）

**核心数据结构**：
```python
@dataclass
class FileBoundary:
    internal_functions: Set[str]          # 文件内定义的函数
    external_functions: Set[str]          # 调用的外部函数
    internal_data_structures: Set[str]    # 文件内定义的数据结构
    external_data_structures: Set[str]    # 使用的外部数据结构
    file_data_structures: Dict[str, dict] # 数据结构详细信息
```

**分析流程**：

```
1. 索引函数 → self.file_functions
   └─ 遍历 function_definition 节点
      └─ 提取函数名、签名、位置

2. 索引数据结构 → self.file_data_structures
   └─ 遍历 struct/class/enum 节点
      └─ 提取名称、类型、定义

3. 分析函数调用 → internal_functions / external_functions
   └─ 遍历 call_expression 节点
      └─ 区分：在 file_functions 中？→ 内部 : 外部

4. 分析数据结构使用 → internal_data_structures / external_data_structures
   └─ 扫描函数签名、参数、局部变量
      └─ 区分：在 file_data_structures 中？→ 内部 : 外部
```

**核心方法**：
```python
class SingleFileAnalyzer:
    def analyze_file(file_path) -> FileBoundary
        # 分析文件边界

    def trace_call_chain(func_name, source_code, max_depth) -> CallNode
        # 追踪调用链（仅文件内）

    def get_entry_points(source_code, file_path) -> List[EntryPointInfo]
        # 识别入口函数

    def get_data_structures_info() -> Dict[str, DataStructureInfo]
        # 获取数据结构信息
```

**设计要点**：
- 🚀 无需全局索引，快速启动
- 🎯 清晰区分内部/外部边界
- 💡 外部函数标记但不深入（避免无限追踪）

---

### 3. 分析层 (Analysis)

#### `call_chain_tracer.py` - 调用链追踪器

**职责**：追踪函数调用链，构建调用树

**核心数据结构**：
```python
@dataclass
class CallNode:
    function_name: str
    file_path: str
    line_number: int
    signature: str
    called_from_line: int
    is_external: bool      # 是否外部函数
    is_recursive: bool     # 是否递归调用
    children: List[CallNode]  # 子调用节点（树结构）
```

**追踪逻辑**：
```
追踪入口函数 X:
├─ 找到 X 的所有 call_expression
│  ├─ 函数 A (内部) → 递归追踪 A
│  │  ├─ 函数 B (内部) → 递归追踪 B
│  │  └─ 函数 C (外部) → 标记 is_external=True, 不再深入
│  └─ 函数 D (内部) → 递归追踪 D
│     └─ 函数 A (循环) → 标记 is_recursive=True, 停止
└─ 递归深度限制（max_depth）
```

**防护机制**：
- 🔄 检测递归调用（`is_recursive`）
- 🛑 深度限制（默认100层）
- 🎯 访问标记（防止重复追踪）

---

#### `branch_analyzer.py` - 分支复杂度分析器

**职责**：分析函数分支结构，计算圈复杂度，提取关键条件

**核心数据结构**：
```python
@dataclass
class BranchCondition:
    line: int
    branch_type: str          # 'if', 'switch', 'loop'
    condition: str            # 条件表达式
    suggestions: List[str]    # 建议（如 case 值列表）

@dataclass
class BranchAnalysis:
    function_name: str
    cyclomatic_complexity: int     # 圈复杂度
    if_count: int
    switch_count: int
    switch_cases: int
    loop_count: int
    conditions: List[BranchCondition]  # 关键条件
```

**圈复杂度计算**：
```python
圈复杂度 = 1 (基础)
         + if_count
         + switch_count
         + case_count
         + loop_count
         + logical_operators_count (&&, ||)
         + ternary_count (? :)
```

**switch 分析增强**：
- 提取所有 case 值（不截断）
- 显示 default 分支存在性
- 格式化显示：`case值: PID_DIAM, DOPRA_PID_TIMER, ... 共8个case`

**使用场景**：
- 单元测试覆盖率指导（知道有哪些分支需要测试）
- 复杂度评估（CC > 10 警告）
- 重构建议

---

#### `external_classifier.py` - 外部函数分类器

**职责**：将外部函数分类为 业务依赖 / 标准库 / 日志工具

**分类策略**：

```python
分类逻辑:
├─ 标准库函数 (standard_lib)
│  ├─ C 标准库: printf, malloc, strcpy, memset, ...
│  ├─ C++ 标准库: std::*, string::*, vector::*, ...
│  └─ POSIX: open, read, write, pthread_*, ...
│
├─ 日志/调试函数 (logging)
│  ├─ 通用模式: *LOG*, *log*, *Log*, *Print*, *Debug*
│  ├─ 项目特定: FE_LOG, VOS_LOG, DIAM_LOG, ...
│  └─ 用户配置: .simple_ast_config.json 自定义排除
│
└─ 业务依赖函数 (business) ⭐ Mock 清单
   └─ 其他所有外部函数
```

**输出优化**：
- ✅ **只显示业务依赖**在 Mock 清单中
- ❌ **隐藏标准库和日志函数**（减少噪音）
- 🔍 **尝试搜索函数签名**（在头文件中）

**配置支持**：
```json
{
  "external_function_classification": {
    "custom_exclusions": {
      "patterns": ["FE_LOG", "MY_PROJECT_*"]
    }
  }
}
```

---

#### `entry_point_classifier.py` - 入口函数分类器

**职责**：识别和分类入口点函数

**分类规则**：
```python
API 函数:
  ├─ 在头文件中声明
  └─ 在 .cpp 中实现

INTERNAL 函数:
  ├─ static 函数
  ├─ 匿名命名空间函数
  └─ 文件局部函数

EXPORTED 函数:
  └─ 其他公开函数（可能被外部使用）
```

---

#### `data_structure_analyzer.py` - 数据结构分析器

**职责**：分析数据结构定义和使用

**支持的类型**：
- `struct`
- `class`
- `enum`
- `typedef`
- `using` (C++11)

**提取信息**：
- 定义位置（文件:行号）
- 完整定义代码
- 使用该结构的函数列表
- 内部定义 vs 外部引用

---

### 4. 协调层 (Orchestration)

#### `cpp_analyzer.py` - 主分析器 (核心)

**职责**：
1. 根据分析模式选择执行路径
2. 协调各个分析模块
3. 聚合分析结果
4. 生成多种格式报告

**核心类**：

```python
class CppProjectAnalyzer:
    def __init__(self, project_root, mode=AnalysisMode.SINGLE_FILE_BOUNDARY)
        # 根据模式初始化不同组件
        if mode.requires_full_index:
            self.indexer = ProjectIndexer(...)
            self.classifier = EntryPointClassifier(...)
            self.tracer = CallChainTracer(...)
        else:
            self.single_file_analyzer = SingleFileAnalyzer(...)

        # 通用组件
        self.branch_analyzer = BranchAnalyzer()
        self.external_classifier = ExternalFunctionClassifier()

    def analyze_file(self, target_file, trace_depth, target_function) -> AnalysisResult
        # 路由到不同的分析方法
        if mode == SINGLE_FILE_BOUNDARY:
            return self._analyze_file_boundary_mode(...)
        else:
            return self._analyze_file_full_mode(...)
```

**执行流程（单文件模式）**：

```
1. 分析文件边界 (SingleFileAnalyzer)
   └─ 区分内部/外部函数和数据结构

2. 追踪调用链 (SingleFileAnalyzer)
   └─ 为每个入口函数构建调用树

3. 收集函数签名
   └─ 从调用树递归收集

4. 获取数据结构信息
   └─ 内部定义 + 尝试读取外部定义

5. 分析分支结构 (BranchAnalyzer) ⭐ 优化点
   ├─ 如果指定 target_function:
   │  └─ 只分析目标函数 + 依赖函数
   └─ 否则: 分析所有函数

6. 分类外部函数 (ExternalClassifier)
   └─ 业务依赖 / 标准库 / 日志

7. 构建 AnalysisResult
   └─ 统一数据模型
```

**性能优化**：
- 🎯 目标函数模式：只分析相关函数（97.6% 性能提升）
- 🔍 递归依赖收集：`_collect_internal_functions_from_chain()`
- 📊 清晰日志：`Target function mode: analyzing X functions`

---

#### `AnalysisResult` - 结果数据模型

**职责**：统一的分析结果数据结构

**数据模型**：
```python
@dataclass
class AnalysisResult:
    target_file: str
    entry_points: List[EntryPointInfo]
    call_chains: Dict[str, CallNode]
    function_signatures: Dict[str, str]
    data_structures: Dict[str, DataStructureInfo]
    mode: str
    file_boundary: Optional[FileBoundary]
    branch_analyses: Dict[str, BranchAnalysis]
    external_classifier: ExternalFunctionClassifier
```

**报告生成方法**：
```python
def format_report(self) -> str
    # 完整的文本报告

def to_json(self) -> str
    # JSON 格式输出

def generate_summary_report(self) -> str
    # 摘要报告

def generate_boundary_report(self) -> str
    # 边界分析报告

def generate_call_chains_report(self) -> str
    # 调用链报告

def generate_single_function_report(self, func_name) -> str
    # 单个函数的完整测试上下文
    # 递归展开所有依赖，包括：
    #   - 函数签名
    #   - 分支复杂度（CC > 5）
    #   - Mock 清单（业务外部依赖）
    #   - 数据结构（内部定义 + 外部引用）
    #   - 常量定义（从条件/case 提取）
```

---

### 5. 应用层 (Application)

#### `analyze.py` - 命令行工具

**职责**：
1. 参数解析
2. 日志管理
3. 输出格式化
4. 错误处理

**输出策略**：

```python
if 函数数量 > 50:
    # 大型文件：分层输出
    output/
    ├── summary.txt              # 摘要报告
    ├── boundary.txt             # 边界分析
    ├── functions/               # 每个函数独立文件 ⭐ 优化
    │   ├── FuncA.txt            #   只生成目标函数及依赖
    │   └── FuncB.txt
    ├── call_chains.txt
    ├── data_structures.txt
    └── analysis.json
else:
    # 小型文件：单文件输出
    output/
    ├── analysis.txt
    └── analysis.json
```

**优化点（target_function 指定时）**：
- 只生成目标函数及其依赖的文件
- 递归收集调用链中的所有内部函数
- 避免生成大量空文件

---

## 数据流转

### 完整数据流程图

```
[用户输入]
    │ analyze.py . main.cpp single 15 MyFunc
    ↓
[参数解析]
    │ mode=SINGLE_FILE_BOUNDARY
    │ target_file=main.cpp
    │ target_function=MyFunc
    │ trace_depth=15
    ↓
[CppProjectAnalyzer.__init__]
    │ 根据 mode 初始化组件
    │ • SingleFileAnalyzer (单文件模式)
    │ • BranchAnalyzer
    │ • ExternalClassifier
    ↓
[analyze_file()] → _analyze_file_boundary_mode()
    │
    ├─ [1] SingleFileAnalyzer.analyze_file()
    │      │
    │      ├─ CppParser.parse_file()
    │      │  └─ tree-sitter → AST
    │      │
    │      ├─ _index_file_functions()
    │      │  └─ file_functions: {func_name: {node, signature, line}}
    │      │
    │      ├─ _index_file_data_structures()
    │      │  └─ file_data_structures: {struct_name: {node, type, definition}}
    │      │
    │      ├─ _analyze_function_calls()
    │      │  ├─ internal_functions: Set[str]
    │      │  └─ external_functions: Set[str]
    │      │
    │      └─ _analyze_data_structure_usage()
    │         ├─ internal_data_structures: Set[str]
    │         └─ external_data_structures: Set[str]
    │
    │      └→ FileBoundary
    │
    ├─ [2] 过滤入口点（target_function）
    │      entry_points = [ep for ep in all_eps if ep.name == target_function]
    │
    ├─ [3] 追踪调用链
    │      for ep in entry_points:
    │          call_tree = SingleFileAnalyzer.trace_call_chain(ep.name, max_depth=15)
    │          └→ CallNode (树结构)
    │
    ├─ [4] 收集函数签名
    │      递归遍历 call_tree
    │      └→ function_signatures: Dict[str, str]
    │
    ├─ [5] 获取数据结构信息
    │      SingleFileAnalyzer.get_data_structures_info()
    │      └→ data_structures: Dict[str, DataStructureInfo]
    │
    ├─ [6] 分析分支结构 ⭐ 优化
    │      if target_function:
    │          # 收集目标函数及依赖
    │          functions_to_analyze = {target_function}
    │          _collect_internal_functions_from_chain(call_tree, functions_to_analyze)
    │          # 只分析这些函数（5个 vs 208个）
    │
    │      for func_name in functions_to_analyze:
    │          BranchAnalyzer.analyze_function(func_node)
    │
    │      └→ branch_analyses: Dict[str, BranchAnalysis]
    │
    └─ [7] 构建 AnalysisResult
           └→ AnalysisResult(
                  target_file, entry_points, call_chains,
                  function_signatures, data_structures,
                  file_boundary, branch_analyses,
                  external_classifier
              )
    ↓
[生成报告]
    │
    ├─ 判断输出模式
    │  if len(functions) > 50 or target_function:
    │      # 分层输出
    │  else:
    │      # 单文件输出
    │
    ├─ 生成函数文件 ⭐ 优化
    │  if target_function:
    │      # 收集目标函数及依赖
    │      all_functions = {target_function}
    │      collect_internal_funcs(call_tree) → all_functions
    │      # 只生成这些文件（5个 vs 208个）
    │
    │  for func_name in all_functions:
    │      report = AnalysisResult.generate_single_function_report(func_name)
    │      # 递归展开依赖，包括：
    │      #   - 函数签名和位置
    │      #   - 分支复杂度（CC > 5 才显示）
    │      #   - Mock 清单（业务外部依赖 + 签名搜索）
    │      #   - 数据结构列表
    │      #   - 内部依赖函数（递归展开）
    │      #   - 常量定义（从条件/case提取）
    │
    │      # 常量提取流程：
    │      constants = _extract_constants_from_function(func_name)
    │          ├─ 从函数签名提取大写标识符
    │          ├─ 从分支条件提取
    │          ├─ 从 switch case 值提取
    │          └─ 在头文件中搜索定义 ⭐ 增强
    │             ├─ 当前 .cpp 文件
    │             ├─ 同目录 .h 文件
    │             └─ 递归搜索 include/ 目录（3层向上）
    │                ├─ common/source/diam → common/include/diam
    │                └─ 最多搜索 50 个文件
    │
    │      write(functions/func_name.txt, report)
    │
    ├─ 生成其他报告
    │  ├─ summary.txt
    │  ├─ boundary.txt
    │  ├─ call_chains.txt
    │  └─ data_structures.txt
    │
    └─ 生成 JSON
       └─ analysis.json
    ↓
[输出完成]
    📁 output/_main_20250119_123456/
    📊 summary.txt
    📋 boundary.txt
    📁 functions/ (5 个文件，不是 208 个)
    📝 logs/analyze_20250119_123456.log
```

---

## 设计模式

### 1. 策略模式 (Strategy Pattern)

**应用场景**：`AnalysisMode` - 不同分析模式对应不同的执行策略

```python
class CppProjectAnalyzer:
    def analyze_file(self, ...):
        if self.mode == AnalysisMode.SINGLE_FILE_BOUNDARY:
            return self._analyze_file_boundary_mode(...)
        else:
            return self._analyze_file_full_mode(...)
```

**优点**：
- 灵活切换分析策略
- 易于添加新模式
- 配置驱动

---

### 2. 门面模式 (Facade Pattern)

**应用场景**：`CppProjectAnalyzer` 封装多个子系统

```python
CppProjectAnalyzer (门面)
    ├─ ProjectIndexer
    ├─ SingleFileAnalyzer
    ├─ CallChainTracer
    ├─ BranchAnalyzer
    └─ ExternalClassifier
```

**优点**：
- 简化用户接口
- 降低子系统耦合
- 统一入口

---

### 3. 工厂模式 (Factory Pattern)

**应用场景**：根据配置创建不同的分析器组件

```python
if mode_config.requires_full_index:
    self.indexer = ProjectIndexer(...)
    self.tracer = CallChainTracer(...)
else:
    self.single_file_analyzer = SingleFileAnalyzer(...)
```

---

### 4. 访问者模式 (Visitor Pattern)

**应用场景**：遍历 AST 树节点

```python
def find_nodes_by_type(node, node_type):
    results = []
    if node.type == node_type:
        results.append(node)
    for child in node.children:
        results.extend(find_nodes_by_type(child, node_type))
    return results
```

---

### 5. 组合模式 (Composite Pattern)

**应用场景**：`CallNode` 调用树

```python
@dataclass
class CallNode:
    function_name: str
    children: List[CallNode]  # 递归结构，树形调用链
```

---

### 6. 适配器模式 (Adapter Pattern)

**应用场景**：`CppParser` 封装 tree-sitter

```python
class CppParser:
    # 适配 tree-sitter 的复杂 API
    def parse_file(self, file_path) -> Tree:
        # 封装多编码处理

    @staticmethod
    def get_node_text(node, source_code) -> str:
        # 封装多编码解码
```

---

## 扩展点

### 1. 新增分析模式

**步骤**：
1. 在 `AnalysisMode` 枚举中添加新模式
2. 在 `MODE_CONFIGS` 中定义配置
3. 在 `CppProjectAnalyzer.analyze_file()` 中添加路由逻辑
4. 实现对应的 `_analyze_file_xxx_mode()` 方法

**示例**（增量模式）：
```python
# 1. 定义模式
class AnalysisMode(Enum):
    INCREMENTAL = "incremental"

# 2. 配置
MODE_CONFIGS[AnalysisMode.INCREMENTAL] = AnalysisModeConfig(...)

# 3. 路由
def analyze_file(self, ...):
    if self.mode == AnalysisMode.INCREMENTAL:
        return self._analyze_file_incremental_mode(...)

# 4. 实现
def _analyze_file_incremental_mode(self, ...):
    # 按需索引相关文件
    ...
```

---

### 2. 新增分析器

**步骤**：
1. 创建新的分析器模块（如 `metrics_analyzer.py`）
2. 实现分析逻辑
3. 在 `CppProjectAnalyzer` 中集成
4. 在 `AnalysisResult` 中添加结果字段

**示例**（代码指标分析）：
```python
# 1. 创建 metrics_analyzer.py
class MetricsAnalyzer:
    def analyze_metrics(self, func_node, source_code):
        return {
            'lines_of_code': ...,
            'comment_ratio': ...,
            'nesting_depth': ...
        }

# 2. 集成到 CppProjectAnalyzer
self.metrics_analyzer = MetricsAnalyzer()

# 3. 在 analyze_file 中调用
metrics = self.metrics_analyzer.analyze_metrics(...)

# 4. 添加到 AnalysisResult
@dataclass
class AnalysisResult:
    metrics: Dict[str, Any] = None
```

---

### 3. 自定义输出格式

**步骤**：
1. 在 `AnalysisResult` 中添加新的生成方法
2. 在 `analyze.py` 中调用

**示例**（生成 Markdown）：
```python
# 1. 添加方法
def generate_markdown_report(self) -> str:
    lines = []
    lines.append("# Analysis Report")
    lines.append(f"## File: {self.target_file}")
    # ...
    return "\n".join(lines)

# 2. 在 analyze.py 中使用
md_file = result_dir / "report.md"
with open(md_file, 'w', encoding='utf-8') as f:
    f.write(result.generate_markdown_report())
```

---

### 4. 支持新语言

**步骤**：
1. 安装对应的 tree-sitter 语言包（如 `tree-sitter-python`）
2. 扩展 `CppParser` 或创建新的 Parser
3. 适配语言特定的节点类型

**示例**（支持 Python）：
```python
class PythonParser:
    def _init_parser(self):
        import tree_sitter_python
        lang_ptr = tree_sitter_python.language()
        PYTHON_LANGUAGE = Language(lang_ptr, "python")
        self.parser = Parser()
        self.parser.set_language(PYTHON_LANGUAGE)

    def get_function_name(self, func_node, source_code):
        # Python 节点类型: 'function_definition'
        # 适配 Python 语法
        ...
```

---

## 总结

### 架构优势

1. **分层清晰**：基础层 → 索引层 → 分析层 → 协调层 → 应用层
2. **模块化**：每个分析器职责单一，低耦合
3. **可扩展**：多种扩展点，易于添加新功能
4. **高性能**：按需分析，避免不必要计算
5. **灵活配置**：策略模式支持多种分析模式

### 核心设计思想

- 🎯 **单一职责**：每个模块专注一件事
- 🔌 **插件化**：分析器可独立添加/移除
- 📊 **数据驱动**：统一的数据模型（`AnalysisResult`）
- ⚡ **性能优先**：目标函数优化、缓存、按需索引
- 🌍 **国际化友好**：多编码支持（UTF-8, GBK, GB2312）

---

## 未来优化方向

1. **增量索引**：只重新分析修改的文件
2. **缓存机制**：缓存解析结果、头文件搜索结果
3. **并行分析**：多线程/多进程并行分析
4. **AI 辅助**：LLM 辅助分类和建议
5. **可视化**：生成调用图、依赖图
6. **IDE 集成**：VS Code / CLion 插件

---

**文档版本**：v1.0
**更新日期**：2025-01-19
**维护者**：SimpleAST Team
