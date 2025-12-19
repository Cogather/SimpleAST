# SimpleAST - C++ Static Code Analyzer

快速分析 C++ 代码结构和依赖关系的静态分析工具，**无需编译即可使用**。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行分析

```bash
# 单文件边界分析（推荐，快速）
python analyze.py <项目根目录> <目标CPP文件>

# 示例
python analyze.py . test_gbk_chinese.cpp
python analyze.py D:\my_project src\main.cpp
```

### 3. 查看结果

结果自动保存到 `output/` 目录（可通过 `--output` 自定义）：

**小型文件（≤50 个函数）**：
- `*.txt` - 可读的分析报告
- `*.json` - 结构化数据

**大型文件（>50 个函数）**：自动生成分层目录
```
output/<项目>_<文件>_<时间>/
├── summary.txt              # 📊 摘要报告（统计数据、复杂度分析）
├── boundary.txt             # 📋 边界分析（内部/外部函数和数据结构）
├── functions/               # 📁 每个函数的独立详情文件
│   ├── AddCircle.txt        #     [主函数] 信息 + Mock清单 + 内部依赖
│   ├── PrimRect.txt         #     完整测试上下文，递归展开所有依赖
│   └── ...                  #     每个文件可独立用于单元测试生成
├── call_chains.txt          # 🔗 完整调用链
├── data_structures.txt      # 📦 数据结构详情
└── analysis.json            # 📊 JSON格式数据
```

## 📋 分析模式

### 单文件边界模式（默认）
```bash
python analyze.py . main.cpp single
```
- ⚡ **极速启动**：无需索引整个项目
- 🎯 **文件边界分析**：内部函数依赖 + 外部调用 + 数据结构
- 📦 **适合大型文件**：轻松分析 10000+ 行代码
- 🚀 **智能优化**：指定函数时只分析相关依赖，不分析无关函数

### 完整项目模式
```bash
python analyze.py . main.cpp full
```
- 🔍 **全局索引**：跨文件追踪函数调用
- 📊 **完整依赖图**：项目级别的分析
- ⏱️ **首次较慢**：需要索引整个项目

## 📖 详细文档

- **PRD 文档**：[doc/PRD.md](doc/PRD.md) - 功能说明和技术原理
- **项目结构**：[doc/PROJECT_STRUCTURE.md](doc/PROJECT_STRUCTURE.md) - 项目组织和开发指南

## ✨ 核心功能

- ✅ 函数调用链追踪（树状可视化）
- ✅ 入口函数分类（API/内部/导出）
- ✅ 数据结构依赖分析（内部定义+外部引用）
- ✅ 函数签名提取
- ✅ 文件边界分析（内部/外部区分）
- ✅ 递归依赖展开（完整测试上下文生成）
- ✅ **分支复杂度分析**（圈复杂度+关键分支条件，覆盖率指导）
- ✅ **Switch/Case完整识别**（显示所有case值，不截断）
- ✅ **常量定义自动提取**（从条件、case值中提取并搜索定义，支持递归搜索include目录）
- ✅ **智能类型过滤**（自动过滤VOS_VOID等基础typedef）
- ✅ **外部函数分类**（业务依赖/标准库/日志工具，智能Mock清单）
- ✅ 智能分层输出（大型文件自动拆分为独立函数文件）
- ✅ 可配置输出目录（支持自定义输出路径）
- ✅ 支持中文注释和多种编码（UTF-8/GBK/GB2312）

## 🔧 配置

### 外部函数分类配置

创建 `.simple_ast_config.json` 文件自定义Mock清单分类：

```json
{
  "external_function_classification": {
    "custom_exclusions": {
      "patterns": [
        "FE_LOG",        // 项目日志函数
        "MY_PROJECT_*"   // 项目特定工具
      ]
    }
  }
}
```

详细配置说明：[doc/EXTERNAL_CLASSIFICATION.md](doc/EXTERNAL_CLASSIFICATION.md)


## 🎯 使用场景

- 📝 理解遗留代码结构
- 🔍 API 依赖分析
- 🔧 重构影响评估
- 📊 代码审查辅助
- 🗺️ 生成调用关系图
- 🧪 单元测试准备（生成完整测试上下文和Mock清单）

## ⚙️ 参数说明

```bash
python analyze.py <项目根目录> <目标文件> [模式] [深度] [函数名] [--output <输出目录>]
```

- **模式**：`single`（默认）/ `full`
- **深度**：调用链追踪深度（默认：根据模式自动设置）
- **函数名**：只分析指定函数
- **--output**：自定义输出目录（默认：`./output`）

**示例：**
```bash
# 分析指定函数，追踪深度 50
python analyze.py . main.cpp single 50 MyFunction

# 完整项目模式，深度 15
python analyze.py ./project src/api.cpp full 15

# 自定义输出目录
python analyze.py . main.cpp --output ./my_results
python analyze.py . main.cpp single 50 --output /tmp/analysis
```

### 查看详细分析日志

如果分析结果不符合预期（缺少常量、数据结构等），可以查看详细日志定位问题：

```bash
# Windows
python analyze.py . test.cpp single 15 MyFunc 2>&1 | more

# Linux/Mac
python analyze.py . test.cpp single 15 MyFunc 2>&1 | less

# 保存日志到文件
python analyze.py . test.cpp single 15 MyFunc 2>debug.log
```

日志会显示：
- 常量提取过程（从哪里提取、找到哪些、哪些未找到）
- 数据结构过滤过程（保留了哪些、过滤了哪些、原因）
- 文件搜索路径

## 🔧 技术栈

- **Python 3.8+**
- **tree-sitter** - AST 解析
- **tree-sitter-cpp** - C++ 语言支持

## 📄 许可证

MIT License
