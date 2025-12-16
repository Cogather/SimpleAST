# SimpleAST 使用指南

## 项目简介

SimpleAST 是一个基于 Python 和 tree-sitter 的 C++ 静态代码分析工具，**无需编译环境即可分析 C++ 项目**。

## 核心功能

### 1. 入口函数分类
自动识别三类函数：
- **API 函数**：在 .h 文件中声明的公共接口
- **INTERNAL 函数**：仅在 .cpp 文件内部使用的静态函数
- **EXPORTED 函数**：在 .cpp 中定义但可能被外部使用的函数

### 2. 函数调用链追踪
从入口函数递归追踪所有函数调用，生成调用树，包括：
- 完整的调用层次结构
- 每个函数的定义位置
- 递归调用检测
- 外部函数标记

### 3. 函数签名提取
提取所有相关函数的完整签名和定义位置

### 4. 数据结构分析
- 识别 struct/class/enum/typedef 定义
- 追踪数据结构在哪些函数中被使用
- 显示数据结构的定义预览

## 安装

### 1. 创建虚拟环境
```bash
python -m venv venv
```

### 2. 激活虚拟环境
Windows:
```bash
venv\Scripts\activate
```

Linux/Mac:
```bash
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

### 命令行方式

```bash
python cpp_analyzer.py <项目根目录> <目标CPP文件>
```

**示例：**
```bash
python cpp_analyzer.py ./example_project ./example_project/src/main.cpp
```

### Python API 方式

```python
from cpp_analyzer import CppProjectAnalyzer

# 初始化分析器
analyzer = CppProjectAnalyzer(project_root="./your_project")

# 分析指定文件
result = analyzer.analyze_file("src/main.cpp")

# 打印报告
print(result.format_report())

# 或导出为 JSON
with open("output.json", "w") as f:
    f.write(result.to_json())
```

### 运行示例测试

```bash
python test_analyzer.py
```

## 输出示例

### 1. 入口函数分类
```
API Functions (declared in headers):
  • registerUser
    Location: src\main.cpp:19
    Declared in: include\api.h:10
    Signature: bool registerUser(const User& user)

Internal Functions (file-local):
  • validateUser
    Location: src\main.cpp:11
```

### 2. 调用链
```
Call chain from: registerUser
----------------------------------------
registerUser [src\main.cpp:19]
  ├─ logAction [src\utils.cpp:23]
  ├─ validateUser [src\main.cpp:11]
    ├─ empty [EXTERNAL]
    ├─ validateEmail [src\utils.cpp:6]
      ├─ find [EXTERNAL]
  ├─ saveToDatabase [src\utils.cpp:17]
```

### 3. 数据结构
```
STRUCT: User
  Defined in: include\data_types.h:8
  Used by functions:
    - registerUser
    - validateUser
  Used in files: src\main.cpp
  Definition preview:
    struct User {
        int id;
        std::string name;
```

## 适用场景

✅ **适用于：**
- 无法编译的遗留代码分析
- 快速理解代码结构和调用关系
- 代码审查和文档生成
- 依赖分析
- 重构前的影响分析

❌ **不适用于：**
- 需要精确类型推导的场景
- 复杂模板元编程分析
- 运行时多态追踪
- 宏展开后的代码分析

## 技术限制

1. **宏处理**：不展开宏，保留原始文本
2. **模板**：记录模板定义，不进行实例化
3. **虚函数**：无法追踪运行时多态调用
4. **函数指针**：无法追踪通过函数指针的间接调用
5. **编译条件**：不处理 `#ifdef` 等条件编译指令

## 配置选项

### 调整追踪深度

```python
analyzer = CppProjectAnalyzer(project_root="./project")
result = analyzer.analyze_file("main.cpp", trace_depth=15)  # 默认 10
```

### 过滤入口函数类型

```python
from entry_point_classifier import EntryPointClassifier

classifier = EntryPointClassifier(indexer)

# 只获取 API 函数
api_functions = classifier.get_api_functions("src/main.cpp")

# 只获取内部函数
internal_functions = classifier.get_internal_functions("src/main.cpp")
```

## 项目结构

```
SimpleAST/
├── cpp_parser.py              # Tree-sitter 解析器封装
├── project_indexer.py         # 项目索引器（符号表）
├── entry_point_classifier.py  # 入口函数分类器
├── call_chain_tracer.py       # 调用链追踪器
├── data_structure_analyzer.py # 数据结构分析器
├── cpp_analyzer.py            # 主分析器
├── test_analyzer.py           # 测试脚本
├── requirements.txt           # Python 依赖
└── example_project/           # 示例项目
    ├── include/               # 头文件
    │   ├── api.h
    │   └── data_types.h
    └── src/                   # 源文件
        ├── main.cpp
        └── utils.cpp
```

## 扩展开发

### 添加新的分析功能

1. 创建新的分析器类继承基础组件
2. 使用 `ProjectIndexer` 获取符号信息
3. 使用 `CppParser` 进行 AST 遍历
4. 在 `CppProjectAnalyzer` 中集成新功能

### 自定义输出格式

```python
from cpp_analyzer import AnalysisResult

# 自定义格式化函数
def custom_format(result: AnalysisResult) -> str:
    output = []
    for ep in result.entry_points:
        output.append(f"{ep.category}: {ep.name}")
    return "\n".join(output)
```

## 性能建议

1. **大型项目**：首次索引可能需要几分钟，建议缓存索引结果
2. **增量分析**：如果只分析部分文件，可以重用同一个 `analyzer` 实例
3. **深度限制**：对于深度递归的调用链，适当降低 `trace_depth` 可提升性能

## 常见问题

**Q: 为什么有些函数调用没有被追踪到？**
A: 可能是以下原因：
- 通过宏定义的函数调用
- 模板函数调用
- 函数指针或虚函数调用
- 超出了追踪深度限制

**Q: 能否分析单个头文件？**
A: 可以，但结果可能不完整。建议提供整个项目目录以获得完整的符号表。

**Q: 支持哪些 C++ 标准？**
A: Tree-sitter-cpp 支持 C++11/14/17/20，但某些新特性可能需要更新解析器版本。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
