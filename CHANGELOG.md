# 更新日志

## [2025-12-19] 新增搜索系统 - Grep-based 全局搜索

### 🎯 解决的问题
用户反馈：真实项目分析时无法找到外部定义的数据结构（如 `MsgBlock` 在 `v_base.h`）。原因是 `HeaderSearcher` 只搜索3层父目录的 `../include`，无法处理复杂的企业项目目录结构。

### 🆕 新增模块

#### 1. `simple_ast/searchers/grep_searcher.py` - Grep搜索器基础设施
- 使用系统 grep 命令（Git Bash自带）或 ripgrep 进行全局项目搜索
- 支持从项目根目录递归搜索所有头文件
- **Windows路径支持**：正确处理 `D:\path` 格式的盘符冒号
- 支持多行定义提取（如完整的struct定义）
- 向上查找结构体开始（处理 `} MSG_CB, MsgBlock;` 形式的typedef）

#### 2. `simple_ast/searchers/structure_searcher.py` - 数据结构搜索器
- 搜索 struct、class、typedef、using 定义
- 支持多种定义形式：
  - `struct MsgBlock { ... };`
  - `typedef struct { ... } MsgBlock;`
  - `typedef struct MsgCB { ... } MSG_CB, MsgBlock;` (多别名)
  - `using MsgBlock = ...;` (C++11)

#### 3. `simple_ast/searchers/signature_searcher.py` - 函数签名搜索器
- 在头文件中搜索函数声明
- 区分函数声明和函数调用
- 支持多行函数签名提取

#### 4. `simple_ast/searchers/constant_searcher.py` - 常量定义搜索器
- 搜索 #define、enum、const、constexpr 定义
- 支持 enum 成员搜索

#### 5. `simple_ast/searchers/search_config.py` - 搜索工具配置系统
- **可配置搜索工具**：支持 grep 或 ripgrep (rg)
- 自动检测可用工具（优先使用 ripgrep）
- 统一的命令构建接口
- 用户可通过 `set_search_tool(SearchTool.GREP)` 指定工具

### 🔧 技术细节

#### Windows路径问题修复
**问题**：Windows绝对路径包含盘符冒号（如 `D:\path\file.h:123:content`），导致 `split(':')` 错误分割。

**解决方案**：
```python
# 检测Windows路径（盘符后有冒号）
if len(line) > 2 and line[1] == ':' and line[2] in ('\\', '/'):
    # 查找所有冒号位置
    colon_positions = [i for i, c in enumerate(line) if c == ':']
    # 第一个是盘符，第二个是行号前
    file_path_end = colon_positions[1]
    file_path = Path(line[:file_path_end])
    remaining = line[file_path_end + 1:]
    parts = remaining.split(':', 1)  # line_num和content
```

#### 正则表达式兼容性
Git Bash的grep需要使用扩展正则（`-E`）并使用POSIX字符类：
- `\s` → `[[:space:]]` (空白字符)
- `\w` → 使用 `.*` 的宽松匹配

#### 多行定义提取
对于 `} MSG_CB, MsgBlock;` 形式，需要：
1. 匹配结束行
2. 向上查找对应的 `{` 和 `typedef struct`
3. 反向计算括号平衡

### ✅ 验证结果

**测试用例**：搜索 `projects/ince_diam` 项目中的 `MsgBlock`

**结果**：
```
[SUCCESS] Found MsgBlock definition:
============================================================
// 来自: v_base.h:49
typedef struct MsgCB {
    VOS_MSG_HEADER
    VOS_UINT8  aucValue[4];
} MSG_CB, MsgBlock;
```

**文件位置**：`CSF/CSPServicePkg/FWBS/platform/Dopra/target/include/v_base.h`

### 📊 与原有 HeaderSearcher 对比

| 特性 | HeaderSearcher | GrepSearcher |
|------|----------------|--------------|
| 搜索范围 | 3层父目录 | 全项目 |
| 搜索路径 | `../include` 映射 | 递归所有目录 |
| 复杂项目 | ❌ 无法处理 | ✅ 支持 |
| Windows路径 | ❌ 未处理 | ✅ 正确处理 |
| 搜索工具 | Python遍历 | grep/ripgrep |
| 性能 | 慢 | 快 |

### 🔮 未来工作

**Phase 1（已完成）**：
- ✅ 基础 GrepSearcher
- ✅ StructureSearcher、SignatureSearcher、ConstantSearcher
- ✅ 搜索工具配置系统
- ✅ Windows路径支持

**Phase 2（下一步）**：
- 集成到 extractors（替换现有的头文件搜索）
- 测试真实项目分析
- 性能优化（结果缓存）

**Phase 3（可选）**：
- 支持更多搜索场景（枚举、宏展开）
- 跨语言支持

### 📚 相关文档

- `doc/SEARCH_STRATEGY.md` - 搜索策略详细设计
- `doc/ARCHITECTURE.md` - 架构文档

---

## [2025-12-19] 重构版本 - 实用性优先

### 🎯 重构目标
根据用户指示"完整重构吧，注意不要过度设计和过度实现"，进行实用性优先的代码重构。

### 🆕 新增模块

#### 1. `simple_ast/searchers/` - 搜索器模块
- **`header_searcher.py`**：统一的头文件搜索逻辑
  - 消除 3 处重复代码（~150 行）
  - 支持 `source/` → `include/` 目录映射
  - 递归搜索最多 3 层父目录
  - 性能优化：最多搜索 50 个文件

#### 2. `simple_ast/extractors/` - 信息提取器模块
- **`constant_extractor.py`**：常量/宏定义提取器
  - 从函数签名提取大写标识符
  - 从分支条件提取常量
  - 从 switch case 值提取
  - 在头文件中搜索定义

- **`signature_extractor.py`**：函数签名提取器
  - 从头文件搜索函数声明
  - 支持多行函数声明
  - 自动清理注释和修饰符

- **`structure_extractor.py`**：数据结构定义提取器
  - 支持 struct、class、typedef、using
  - 完整提取结构体定义（最多 60 行）
  - 自动处理花括号匹配

#### 3. `simple_ast/reporters/` - 报告生成器模块
- **`function_reporter.py`**：单函数报告生成器（~300 行）
  - 递归展开函数依赖
  - 生成 Mock 清单（业务函数）
  - 提取数据结构
  - 提取常量定义
  - 格式化输出

### 🔧 核心改进

#### `cpp_analyzer.py`
- **简化 `generate_single_function_report()`**
  - 从 ~600 行复杂实现简化为委托调用
  - 委托给 `FunctionReporter` 处理
  - 保留原有方法以确保向后兼容

**重构前**：
```python
def generate_single_function_report(self, func_name: str) -> str:
    # ~600 行复杂逻辑
    lines = []
    visited = set()
    # ... 大量复杂代码 ...
```

**重构后**：
```python
def generate_single_function_report(self, func_name: str) -> str:
    """委托给 FunctionReporter 实现，降低复杂度"""
    from .reporters import FunctionReporter
    reporter = FunctionReporter(self)
    return reporter.generate(func_name)
```

### 📊 代码度量改善

| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| `cpp_analyzer.py` 职责数 | 多个 | 核心分析 | 职责更清晰 |
| 最大方法行数 | ~600 | ~100 | -83% |
| 代码重复 | 3处×50行 | 0 | -150行 |
| 模块总数 | 8 | 11 | +3 |
| 可测试性 | 低 | 高 | 模块独立 |

### ✅ 验证结果

**功能完全正常**：
- ✅ 分析功能：正常
- ✅ 报告生成：正常
- ✅ 分支分析：正常（圈复杂度识别）
- ✅ Mock 生成：正常（自动分类，过滤标准库）
- ✅ 常量提取：正常（从头文件搜索）
- ✅ 数据结构：正常（内部/外部分类）

**测试用例**：
```bash
python analyze.py . tests/test_real_scenario.cpp single 15 PidDiamMsgProc
```

结果：所有功能正常，报告正确生成。

### 📚 文档更新

- 新增 `doc/ARCHITECTURE.md` - 完整的架构文档
- 新增 `doc/REFACTORING_PROPOSAL.md` - 重构分析报告
- 新增 `doc/REFACTORING_SUMMARY.md` - 重构总结

### 🎨 设计原则

**✅ 遵循的原则**：
1. **DRY**：消除重复代码
2. **SRP**：单一职责原则
3. **实用性优先**：只重构有问题的部分
4. **向后兼容**：保留原有接口

**❌ 避免的过度设计**：
1. 不引入工厂模式
2. 不创建不必要的基类/接口
3. 不过度分层
4. 不重写稳定的核心逻辑

### 🔮 未来改进方向

可选的进一步重构（ROI 中等）：
1. 分离 `AnalysisResult` 的完整报告方法
2. 提取配置管理类

不建议的改动：
- ❌ 重写 `CppProjectAnalyzer`（核心逻辑稳定）
- ❌ 引入依赖注入框架（过度设计）
- ❌ 完全模块化（当前已足够）

---

## [2025-12-18] 功能增强版本

### 新增功能
- 分支复杂度分析
- Mock 函数生成
- 常量定义提取
- 数据结构提取
- 外部函数分类

（更多历史版本...）
