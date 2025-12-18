# 项目结构

```
SimpleAST/
├── simple_ast/              # 核心源代码包
│   ├── __init__.py         # 包初始化，导出主要 API
│   ├── cpp_parser.py       # C++ AST 解析器（基于 tree-sitter）
│   ├── project_indexer.py  # 全局符号表索引器
│   ├── entry_point_classifier.py  # 入口函数分类器
│   ├── call_chain_tracer.py       # 函数调用链追踪器
│   ├── data_structure_analyzer.py # 数据结构分析器
│   ├── single_file_analyzer.py    # 单文件边界分析器
│   ├── analysis_modes.py          # 分析模式定义
│   └── cpp_analyzer.py            # 主分析器（整合所有组件）
│
├── tests/                   # 测试文件和测试数据
│   ├── __init__.py
│   ├── test_analyzer.py    # 分析器测试
│   ├── test_treesitter.py  # tree-sitter 测试
│   ├── test_gbk_chinese.cpp      # GBK 编码测试文件
│   ├── test_chinese.cpp          # 中文测试文件
│   ├── test_gbk.cpp              # 基础 GBK 测试
│   └── create_gbk_test.py        # GBK 测试文件生成器
│
├── doc/                     # 项目文档
│   ├── PRD.md              # 产品需求文档
│   ├── USAGE.md            # 详细使用指南
│   └── QUICKSTART.md       # 快速开始指南
│
├── examples/                # 示例项目（可选）
│
├── projects/                # 用于测试的第三方项目
│   └── imgui-master/
│
├── output/                  # 分析结果输出目录
│   ├── *.txt               # 文本报告
│   └── *.json              # JSON 数据
│
├── logs/                    # 执行日志
│   └── analyze_*.log
│
├── venv/                    # Python 虚拟环境
│
├── analyze.py               # 命令行入口脚本
├── requirements.txt         # Python 依赖
├── README.md               # 项目说明（简洁版）
└── .gitignore              # Git 忽略配置
```

## 模块说明

### 核心包 (simple_ast/)

所有核心代码都在 `simple_ast` 包中，作为标准 Python 包组织：

- **cpp_parser.py**: 封装 tree-sitter C++ 解析器
- **project_indexer.py**: 构建项目级别的符号表
- **entry_point_classifier.py**: 区分 API/内部/导出函数
- **call_chain_tracer.py**: 追踪函数调用关系
- **data_structure_analyzer.py**: 分析数据结构依赖
- **single_file_analyzer.py**: 单文件快速分析
- **analysis_modes.py**: 多模式配置
- **cpp_analyzer.py**: 主入口，整合所有分析器

### 测试 (tests/)

所有测试相关的文件：
- 单元测试
- 集成测试
- 测试数据（C++ 测试文件）

### 文档 (doc/)

完整的项目文档：
- PRD: 产品需求和技术原理
- USAGE: 详细使用教程
- QUICKSTART: 快速参考

## 使用方式

### 作为包导入

```python
from simple_ast import CppProjectAnalyzer, AnalysisMode

analyzer = CppProjectAnalyzer("./project", mode=AnalysisMode.SINGLE_FILE_BOUNDARY)
result = analyzer.analyze_file("src/main.cpp")
print(result.format_report())
```

### 命令行工具

```bash
python analyze.py <项目根目录> <目标文件> [模式]
```

## 开发指南

### 添加新功能

1. 在 `simple_ast/` 中创建新模块
2. 在 `simple_ast/__init__.py` 中导出公共 API
3. 在 `tests/` 中添加测试
4. 更新文档

### 运行测试

```bash
# 激活虚拟环境
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac

# 运行测试
python -m pytest tests/

# 或运行单个测试
python tests/test_analyzer.py
```

### 安装依赖

```bash
pip install -r requirements.txt
```
