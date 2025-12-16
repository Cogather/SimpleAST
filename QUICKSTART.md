# 🚀 快速开始指南

## 📋 使用方法（超简单）

### 基本用法
```bash
venv\Scripts\python.exe analyze.py <项目根目录> <目标CPP文件> [追踪深度]
```

### 实例演示

#### 示例 1：分析示例项目
```bash
venv\Scripts\python.exe analyze.py ./example_project src/main.cpp
```

#### 示例 2：分析您的项目（相对路径）
```bash
venv\Scripts\python.exe analyze.py D:\my_cpp_project src\module\feature.cpp
```

#### 示例 3：指定追踪深度
```bash
venv\Scripts\python.exe analyze.py D:\my_project src\main.cpp 15
```

---

## 📂 输出说明

所有结果自动保存到 `output` 目录，文件名格式：
```
<项目名>_<文件名>_<时间戳>.txt   # 文本报告
<项目名>_<文件名>_<时间戳>.json  # JSON数据
```

**示例输出文件名：**
- `my_project_main_20251216_143025.txt`
- `my_project_main_20251216_143025.json`

---

## 🔍 输出内容包括

### 1. 入口函数分类
- **API函数**：在.h文件中声明的公共接口
- **内部函数**：仅在.cpp文件内部使用
- **导出函数**：可能被外部使用的函数

### 2. 函数调用链
完整的树状调用关系，标注：
- 每个函数的定义位置
- 外部函数（标记为 [EXTERNAL]）
- 递归调用（标记为 [RECURSIVE]）

### 3. 函数签名列表
所有相关函数的完整签名和定义位置

### 4. 数据结构分析
- struct/class/enum/typedef 定义
- 在哪些函数中被使用
- 定义预览

---

## 💡 实用技巧

### 技巧 1：快速分析多个文件
创建批处理脚本 `analyze_all.bat`：
```batch
@echo off
set PROJECT=D:\my_project

venv\Scripts\python.exe analyze.py %PROJECT% src\main.cpp
venv\Scripts\python.exe analyze.py %PROJECT% src\utils.cpp
venv\Scripts\python.exe analyze.py %PROJECT% src\api.cpp

echo 所有文件分析完成！
pause
```

### 技巧 2：分析特定模块
```bash
# 分析某个模块的所有cpp文件
venv\Scripts\python.exe analyze.py D:\project src\network\client.cpp
venv\Scripts\python.exe analyze.py D:\project src\network\server.cpp
```

### 技巧 3：比较不同时间的分析结果
由于文件名包含时间戳，可以保留历史分析结果进行对比

---

## ⚙️ 参数说明

### 必需参数
1. **项目根目录**：包含所有C++源文件的目录
2. **目标CPP文件**：要分析的具体文件（相对于项目根目录）

### 可选参数
3. **追踪深度**：调用链追踪的最大深度（默认10）

---

## 📝 常见使用场景

### 场景1：理解遗留代码
```bash
# 快速了解一个陌生的CPP文件
venv\Scripts\python.exe analyze.py D:\legacy_code src\old_module.cpp
```
**查看 output 目录中的 txt 文件，快速了解：**
- 有哪些对外API
- 内部调用关系
- 使用了哪些数据结构

### 场景2：API依赖分析
```bash
# 分析公共API的完整调用链
venv\Scripts\python.exe analyze.py D:\library src\public_api.cpp
```
**查看调用链部分，了解：**
- API内部调用了哪些函数
- 调用深度有多深
- 是否有外部依赖

### 场景3：重构影响分析
```bash
# 分析要重构的文件
venv\Scripts\python.exe analyze.py D:\project src\to_refactor.cpp 20
```
**查看数据结构部分，了解：**
- 哪些函数使用了这个数据结构
- 重构的影响范围

---

## 🎯 指定文件的方式

### 方式1：相对路径（推荐）
```bash
# 文件路径相对于项目根目录
venv\Scripts\python.exe analyze.py D:\project src\main.cpp
venv\Scripts\python.exe analyze.py D:\project src\utils\helper.cpp
```

### 方式2：绝对路径
```bash
# 使用完整的绝对路径
venv\Scripts\python.exe analyze.py D:\project D:\project\src\main.cpp
```

---

## ❓ 常见问题

**Q: 输出目录在哪里？**
A: 在项目根目录下的 `output` 文件夹中。

**Q: 文件名太长怎么办？**
A: 可以手动重命名输出文件，不影响内容。

**Q: 可以分析.h文件吗？**
A: 工具主要设计用于分析.cpp文件。.h文件会在索引阶段被自动处理。

**Q: 如何提高分析速度？**
A: 对于大型项目，首次索引会较慢。如果多次分析同一项目的不同文件，可以考虑在Python代码中重用analyzer对象。

**Q: 中文路径支持吗？**
A: 支持，但建议使用英文路径以获得更好的兼容性。

---

## 🔧 进阶用法

### 作为Python模块使用
如果需要批量分析或自定义输出格式：

```python
from cpp_analyzer import CppProjectAnalyzer
from pathlib import Path

# 创建分析器（只需创建一次）
analyzer = CppProjectAnalyzer("D:/my_project")

# 批量分析
files = ["src/main.cpp", "src/utils.cpp", "src/api.cpp"]

for file in files:
    print(f"分析 {file}...")
    result = analyzer.analyze_file(file)

    # 自定义输出处理
    output_dir = Path("custom_output")
    output_dir.mkdir(exist_ok=True)

    # 保存结果
    output_file = output_dir / f"{Path(file).stem}_report.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result.format_report())
```

---

## 📞 需要帮助？

- 详细技术文档：`USAGE.md`
- 示例项目参考：`example_project/`
- 运行测试验证：`venv\Scripts\python.exe test_analyzer.py`
