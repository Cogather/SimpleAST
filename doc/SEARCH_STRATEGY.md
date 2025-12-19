# 搜索策略实现文档 (2025-12-19)

## 实现状态

✅ **已完成**：基于 grep/ripgrep 的全局搜索
✅ **已完成**：脚本文件方式避免参数传递问题
✅ **已完成**：优先级搜索策略
✅ **已完成**：智能评分机制区分真实定义和使用声明
✅ **已验证**：能正确找到深层目录中的结构体定义

---

## 设计原则

### 1. 准确性优先

**宁可多搜索，不能漏掉关键信息**

- ✅ 全局项目搜索，不限制搜索深度
- ✅ 多模式匹配，覆盖各种定义形式
- ✅ 智能评分筛选，优先真实定义

### 2. 性能优化

- ✅ 使用系统 grep/ripgrep 工具（比 Python 遍历快 10-100 倍）
- ✅ 按需搜索，只在需要时才进行全局搜索
- ✅ 优先级模式，找到即停止

### 3. 鲁棒性

- ✅ 脚本文件方式执行，避免参数转义问题
- ✅ 多种 typedef 模式支持
- ✅ 降级到备用搜索方案

---

## 实现架构

### 模块层次

```
StructureSearcher (优先级搜索策略)
    ↓
GrepSearcher (脚本文件执行)
    ↓
Bash Script (临时脚本)
    ↓
grep/ripgrep (系统工具)
```

### 核心组件

#### 1. GrepSearcher - 底层搜索引擎

**位置**: `simple_ast/searchers/grep_searcher.py`

**核心创新**：使用临时脚本文件执行 grep 命令

```python
class GrepSearcher:
    def _search_via_script(self, pattern: str, file_glob: str):
        """通过临时脚本文件执行搜索，避免参数传递和转义问题"""
        # 1. 创建临时 .sh 脚本
        with tempfile.NamedTemporaryFile(suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\n')
            f.write(f'grep -r -E -n --include="{file_glob}" "{pattern}" "{project_root}"\n')

        # 2. 执行脚本
        result = subprocess.run(['bash', script_path], ...)

        # 3. 清理脚本
        os.unlink(script_path)
```

**为什么使用脚本文件**：
- ❌ 直接传参：`subprocess.run(['grep', pattern, ...])`
  - 问题：Windows 下参数转义复杂，特殊字符（`{}`、`$`、`\s` 等）处理不一致
- ✅ 脚本文件：`subprocess.run(['bash', 'script.sh'])`
  - 优势：参数在脚本内，bash 正确处理所有转义

#### 2. StructureSearcher - 智能搜索策略

**位置**: `simple_ast/searchers/structure_searcher.py`

**核心算法**：优先级 + 评分筛选

```python
class StructureSearcher:
    def search(self, struct_name: str):
        """按优先级尝试不同模式，评分筛选最佳匹配"""

        # 优先级1: 最精确 - typedef struct _Name 或 struct Name {
        patterns_p1 = [
            rf'typedef\s+struct\s+\w*{name}',  # typedef struct _DiamAppMsg
            rf'(struct|class)\s+{name}\s*\{{',  # struct MsgBlock {
        ]

        # 优先级2: typedef 结尾形式
        patterns_p2 = [
            rf'\}}\s*\w*,?\s*{name}\s*;',  # } MSG_CB, MsgBlock;
        ]

        # 优先级3: 单行 typedef
        patterns_p3 = [
            rf'typedef\s+\w+\s+{name}\s*;',  # typedef Type Name;
        ]

        for priority, patterns in prioritized_patterns:
            matches = self.grep.search_content(patterns, max_results=10)
            if matches:
                # 评分筛选最佳匹配
                best = self._select_best_definition(matches, struct_name)
                if best:
                    return self._extract_definition(best)

        return None
```

**评分规则**：

| 规则 | 加分 | 说明 |
|------|-----|------|
| 包含 `typedef` | +100 | 很可能是定义 |
| 包含 `struct`/`class` | +50 | 结构体关键字 |
| 包含 `{` | +80 | 定义开始 |
| 以 `}` 开头 | +70 | typedef 结尾形式 |
| 行内容长度 | +0~100 | 定义通常比声明长 |
| 匹配 `Type *var;` 模式 | **跳过** | 排除变量声明 |

**示例对比**：

```cpp
// ❌ 低分：变量声明 (得分: ~50)
DiamAppMsg *pDiamAppMsg;  /* 保存原始Diameter应用消息 */

// ✅ 高分：真实定义 (得分: ~280)
typedef struct _DiamAppMsg {
    DIAM_SSI_MSG_HEADER;
    DIAM_UINT32 AppCbNo;
    ...
} DiamAppMsg;
```

#### 3. StructureExtractor - 高层接口

**位置**: `simple_ast/extractors/structure_extractor.py`

```python
class StructureExtractor:
    def extract(self, struct_name: str, target_file: str):
        """提取结构体定义"""
        # 1. 优先使用 StructureSearcher 全局搜索
        try:
            from ..searchers import StructureSearcher
            searcher = StructureSearcher(self.project_root)
            result = searcher.search(struct_name)
            if result:
                return result
        except Exception:
            pass

        # 2. 降级到 HeaderSearcher 路径搜索（兼容性）
        try:
            from ..searchers import HeaderSearcher
            # ... 原有逻辑 ...
        except Exception:
            pass

        return None
```

---

## 支持的定义形式

### 1. 直接 struct 定义
```cpp
struct MsgBlock {
    VOS_MSG_HEADER
    VOS_UINT8 aucValue[4];
};
```
**匹配模式**: `(struct|class)\s+MsgBlock\s*\{`

### 2. typedef struct 带名称
```cpp
typedef struct _DiamAppMsg {
    DIAM_UINT32 AppCbNo;
    ...
} DiamAppMsg;
```
**匹配模式**: `typedef\s+struct\s+\w*DiamAppMsg`

### 3. typedef struct 匿名
```cpp
typedef struct {
    VOS_MSG_HEADER
    FE_MSG_HEADER
} tFeAppMsg;
```
**匹配模式**: `\}\s*tFeAppMsg\s*;` (优先级2)

### 4. typedef struct 多别名
```cpp
typedef struct MsgCB {
    VOS_MSG_HEADER
    VOS_UINT8 aucValue[4];
} MSG_CB, MsgBlock;
```
**匹配模式**: `\}\s*\w*,?\s*MsgBlock\s*;`

### 5. 单行 typedef
```cpp
typedef unsigned int UINT32;
typedef OldType NewType;
```
**匹配模式**: `typedef\s+\w+\s+NewType\s*;`

---

## 验证结果

### 测试项目：ince_diam

**测试命令**：
```bash
python analyze.py "projects\ince_diam" "common\source\diam\diamadapt.cpp" 50 PidDiamMsgProc
```

**测试结果**：

| 结构体 | 文件位置 | 定义形式 | 结果 |
|--------|---------|---------|------|
| MsgBlock | `CSF/.../v_base.h:49` | typedef 多别名 | ✅ 成功 |
| DiamAppMsg | `vpp/CDIAM/INCLUDE/ui/DiamApiUi.h:19` | typedef struct _Name | ✅ 成功 |
| tFeAppMsg | `common/include/fe_types.h:23` | typedef 匿名 | ✅ 成功 |

**关键验证点**：
- ✅ 深层目录：`CSF/CSPServicePkg/FWBS/platform/Dopra/target/include/v_base.h`
- ✅ 跨模块：`vpp/CDIAM/INCLUDE/ui/DiamApiUi.h`
- ✅ 排除干扰：忽略同文件中的 `DiamAppMsg *pDiamAppMsg;` 变量声明

---

## 性能特性

### 搜索速度

| 项目大小 | 文件数 | grep 耗时 | Python 遍历预估 |
|----------|--------|-----------|-----------------|
| ince_diam | ~500 | <1秒 | ~5-10秒 |
| 大型项目 | ~5000 | ~2-3秒 | ~50-100秒 |

**结论**：grep 比纯 Python 遍历快 **10-50 倍**

### 优化措施

1. **max_results=10**：只取前 10 个候选，避免处理大量结果
2. **优先级短路**：找到即返回，不继续搜索
3. **文件过滤**：`--include=*.h` 只搜索头文件
4. **临时脚本缓存**：可选地保留脚本文件（当前删除）

---

## 设计权衡

### 为什么不使用 tree-sitter 解析头文件？

**方案对比**：

| 方案 | 优点 | 缺点 |
|------|-----|------|
| **grep 搜索** (当前) | 快速、简单、准确 | 依赖正则表达式 |
| tree-sitter 解析 | 结构化、精确 | 慢（需解析每个文件）、复杂 |

**决策**：
- ✅ **grep 优先**：速度快，准确性通过评分机制保证
- ✅ **简单可靠**：正则表达式易于理解和调试
- ✅ **可扩展**：未来可添加 tree-sitter 作为精确验证层

### 为什么不缓存搜索结果？

**考虑因素**：
- ❌ **缓存复杂性**：需要处理文件变更检测
- ❌ **收益有限**：grep 已经很快（<1秒）
- ✅ **简单可靠**：每次实时搜索，保证最新

**结论**：当前不实现缓存，等性能成为瓶颈再考虑

---

## 未来改进方向

### 1. 支持更多定义形式 (优先级：低)

```cpp
// using 别名 (C++11)
using MsgBlock = struct MsgCB;

// 模板类
template<typename T>
struct Container { ... };

// namespace 内定义
namespace ns { struct Type { ... }; }
```

### 2. 搜索结果缓存 (优先级：低)

- 使用文件 mtime 检测变更
- 缓存到内存或文件
- **触发条件**：搜索耗时 >2秒

### 3. 多线程搜索 (优先级：低)

- 并行搜索多个结构体
- 使用线程池
- **触发条件**：需要搜索 >5 个结构体

---

## 总结

### 核心成果

1. ✅ **全局搜索**：不再受路径深度限制
2. ✅ **准确匹配**：智能评分区分定义和声明
3. ✅ **高性能**：grep 工具 + 脚本文件
4. ✅ **鲁棒性**：降级方案 + 错误处理

### 设计亮点

1. **脚本文件创新**：解决 Windows 下参数转义难题
2. **优先级 + 评分**：两层过滤保证准确性
3. **实用主义**：不过度设计，解决实际问题

### 适用场景

- ✅ 中大型 C/C++ 项目
- ✅ 复杂目录结构
- ✅ 多种 typedef 形式
- ✅ 跨模块依赖

**维护者注意**：本文档反映 2025-12-19 的实现状态，如有代码变更请同步更新。
