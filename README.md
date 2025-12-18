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

结果自动保存到 `output/` 目录：

**小型文件（≤50 个函数）**：
- `*.txt` - 可读的分析报告
- `*.json` - 结构化数据

**大型文件（>50 个函数）**：自动生成分层目录
```
output/<项目>_<文件>_<时间>/
├── summary.txt              # 📊 摘要报告（统计数据、模块分类）
├── boundary.txt             # 📋 边界分析（内部/外部函数和数据结构）
├── functions/               # 📁 按模块分类的函数详情
│   ├── drawing.txt
│   ├── font.txt
│   ├── primitive.txt
│   └── ...
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
- ✅ 数据结构依赖分析
- ✅ 函数签名提取
- ✅ 文件边界分析（内部/外部区分）
- ✅ 智能分层输出（大型文件自动按模块分类）
- ✅ 支持中文注释和多种编码（UTF-8/GBK/GB2312）

## 🎯 使用场景

- 📝 理解遗留代码结构
- 🔍 API 依赖分析
- 🔧 重构影响评估
- 📊 代码审查辅助
- 🗺️ 生成调用关系图

## ⚙️ 参数说明

```bash
python analyze.py <项目根目录> <目标文件> [模式] [深度] [函数名]
```

- **模式**：`single`（默认）/ `full`
- **深度**：调用链追踪深度（默认：根据模式自动设置）
- **函数名**：只分析指定函数

**示例：**
```bash
# 分析指定函数，追踪深度 50
python analyze.py . main.cpp single 50 MyFunction

# 完整项目模式，深度 15
python analyze.py ./project src/api.cpp full 15
```

## 🔧 技术栈

- **Python 3.8+**
- **tree-sitter** - AST 解析
- **tree-sitter-cpp** - C++ 语言支持

## 📄 许可证

MIT License
