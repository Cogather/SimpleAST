# 搜索策略设计文档

## 1. 设计目标

### 核心原则
- **准确性优先**：宁可多搜索，不能漏掉关键信息
- **简单可扩展**：易于添加新的搜索场景，避免过度设计
- **性能可控**：合理限制搜索范围，避免超时
- **用户友好**：搜索失败时提供明确的反馈

### 适用场景
1. 数据结构定义查找
2. 函数签名查找
3. 常量/宏定义查找
4. （未来可扩展）枚举定义、类型别名等

## 2. 搜索工具选择

### 可用工具对比

| 工具 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **Grep (ripgrep)** | 速度快，支持正则，自动忽略 .git | 需要精确的正则表达式 | 内容搜索（推荐） |
| **Glob** | 简单，文件名匹配 | 只能找文件，不能搜内容 | 文件查找 |
| **Python 遍历** | 灵活，可自定义逻辑 | 慢，需要手动处理编码等 | 复杂逻辑 |

**推荐策略**：主要使用 **Grep tool**，辅以 Python 文件读取

## 3. 搜索场景分类

### 场景 1: 数据结构定义

#### 输入
```python
struct_name = "MsgBlock"
```

#### 可能的定义形式
```cpp
// 形式1: 直接定义
struct MsgBlock {
    int field1;
};

// 形式2: typedef 单别名
typedef struct {
    int field1;
} MsgBlock;

// 形式3: typedef 多别名
typedef struct MsgCB {
    int field1;
} MSG_CB, MsgBlock;

// 形式4: class (C++)
class MsgBlock {
    int field1;
};

// 形式5: using (C++11)
using MsgBlock = std::shared_ptr<MsgCB>;
```

#### 搜索策略

**第一步：Grep 搜索定义行**

```python
# 正则表达式设计
patterns = [
    r'^\s*(struct|class)\s+{name}\s*[{{;]',      # struct MsgBlock { 或 ;
    r'^\s*typedef\s+.*\s+{name}\s*;',             # typedef ... MsgBlock;
    r'}}\s*\w*,?\s*{name}\s*;',                   # } MSG_CB, MsgBlock;
    r'^\s*using\s+{name}\s*=',                    # using MsgBlock = ...
]

# 组合成一个正则（用 | 连接）
combined_pattern = '|'.join(patterns)

# Grep 参数
grep_params = {
    'pattern': combined_pattern.replace('{name}', re.escape(struct_name)),
    'path': project_root,
    'glob': '*.h',           # 只搜索头文件
    'output_mode': 'files_with_matches',  # 先找到文件
    'head_limit': 10,        # 最多返回 10 个文件（避免太多重复）
}
```

**第二步：提取完整定义**

```python
def extract_full_structure(file_path: str, struct_name: str) -> Optional[str]:
    """
    从文件中提取完整的结构体定义

    处理：
    1. 找到定义开始的行
    2. 如果是多行（有花括号），提取到匹配的 } 为止
    3. 限制最大行数（如 60 行），避免提取整个文件
    """
    # 读取文件
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # 搜索开始行
    for i, line in enumerate(lines):
        if match_pattern(line, struct_name):
            # 提取多行定义
            definition = extract_multiline_definition(lines, i, max_lines=60)
            return f"// 来自: {file_path.name}\n{definition}"

    return None
```

**匹配精度问题**

❌ **错误**：
```python
pattern = r'MsgBlock'  # 会匹配 MsgBlockEx, pMsgBlock
```

✅ **正确**：
```python
pattern = r'\bMsgBlock\b'  # 词边界，只匹配完整单词
```

**词边界 `\b` 说明**：
- `\b` 匹配单词字符（a-z, A-Z, 0-9, _）与非单词字符的边界
- `\bMsgBlock\b` 会匹配：`struct MsgBlock {`、`MsgBlock *p;`
- 不会匹配：`MsgBlockEx`、`pMsgBlock`

---

### 场景 2: 函数签名

#### 输入
```python
func_name = "CheckPidDiamMsg"
```

#### 可能的形式
```cpp
// 声明（想要）
bool CheckPidDiamMsg(const MsgBlock *pMsg);
VOS_UINT32 CheckPidDiamMsg(MsgBlock *pMsg);
static inline void CheckPidDiamMsg(int x);

// 调用（不想要）
if (CheckPidDiamMsg(pMsg)) { ... }
result = CheckPidDiamMsg(pMsg);
```

#### 区分声明和调用

**特征对比**：

| 特征 | 函数声明 | 函数调用 |
|------|----------|----------|
| 位置 | 通常在行首（可能有修饰符） | 在表达式中 |
| 前面 | 返回类型、修饰符 | 可能是 `if`、`=`、`,` 等 |
| 后面 | 参数列表，`;` 或 `{` 结尾 | 参数，可能在更大表达式中 |

#### 搜索策略

**方案 1：宽松模式**（可能有误报）
```python
pattern = rf'\b{re.escape(func_name)}\s*\('
# 匹配：函数名后紧跟 (
```

**方案 2：精确模式**（推荐）
```python
# 要求行首有返回类型
pattern = rf'^\s*\w+\s+[\w\*&\s]+{re.escape(func_name)}\s*\('
#          ^^^^  ^^^^  ^^^^^^^^^^^^
#          行首  返回类型  可能的修饰符/指针

# 示例匹配：
# VOS_UINT32 CheckPidDiamMsg(
# static inline bool CheckPidDiamMsg(
# void* CheckPidDiamMsg(
```

**方案 3：排除调用**（辅助）
```python
# 如果前面是这些关键字，很可能是调用而非声明
exclude_keywords = ['if', 'while', 'for', 'return', '=', ',']

def is_function_declaration(line: str, func_name: str) -> bool:
    """判断是声明还是调用"""
    # 查找函数名位置
    idx = line.find(func_name)
    if idx == -1:
        return False

    # 检查前面是否有排除关键字
    prefix = line[:idx].strip()
    for keyword in exclude_keywords:
        if prefix.endswith(keyword):
            return False  # 可能是调用

    return True  # 可能是声明
```

#### 多行签名处理

```cpp
// 多行签名
VOS_UINT32
CheckPidDiamMsg(
    const MsgBlock *pMsg,
    int flag
);
```

**策略**：
1. 找到包含函数名的行
2. 如果没有 `;` 或 `{`，继续读取后续行（最多 5 行）
3. 拼接成完整签名

---

### 场景 3: 常量/宏定义

#### 输入
```python
const_name = "PID_DIAM"
```

#### 可能的形式
```cpp
// 形式1: #define
#define PID_DIAM 306

// 形式2: enum
enum {
    PID_DIAM = 306,
    PID_SF = 206,
};

// 形式3: const
const int PID_DIAM = 306;

// 形式4: constexpr (C++11)
constexpr int PID_DIAM = 306;
```

#### 搜索策略

```python
patterns = [
    rf'^\s*#define\s+{re.escape(const_name)}\b',     # #define PID_DIAM
    rf'^\s*{re.escape(const_name)}\s*=',             # PID_DIAM = 306
    rf'^\s*(const|constexpr)\s+\w+\s+{re.escape(const_name)}\s*=',  # const int PID_DIAM =
]

# 搜索参数
grep_params = {
    'pattern': '|'.join(patterns),
    'path': project_root,
    'glob': '*.h',
    'output_mode': 'content',
    'head_limit': 1,  # 常量定义通常只有一个
    '-n': True,       # 显示行号
}
```

**特殊情况：enum**

```cpp
enum ProcessId {
    PID_DIAM = 306,
    PID_SF = 206,
};
```

如果找到的是 enum 成员，可能需要：
1. 只返回该行：`PID_DIAM = 306,`
2. 或者返回整个 enum 定义

**推荐**：只返回该行（简单，够用）

---

## 4. 代码设计

### 4.1 架构设计

```
simple_ast/
└── searchers/
    ├── __init__.py
    ├── base_searcher.py          # 基类（可选，如果需要共享逻辑）
    ├── grep_searcher.py          # 核心：基于 Grep 的搜索器
    ├── structure_searcher.py     # 数据结构搜索
    ├── signature_searcher.py     # 函数签名搜索
    └── constant_searcher.py      # 常量搜索
```

**设计原则**：
- ✅ 每个搜索器独立（单一职责）
- ✅ 共享 `GrepSearcher` 基础设施
- ❌ 不引入复杂的继承层次
- ❌ 不过度抽象

### 4.2 核心组件：GrepSearcher

```python
# simple_ast/searchers/grep_searcher.py

from typing import List, Optional
import re

class GrepSearcher:
    """基于 Grep tool 的通用搜索器"""

    def __init__(self, project_root: str):
        self.project_root = project_root

    def search_pattern(
        self,
        pattern: str,
        file_glob: str = '*.h',
        max_results: int = 10,
        return_content: bool = False
    ) -> List[str]:
        """
        通用的 Grep 搜索

        Args:
            pattern: 正则表达式
            file_glob: 文件匹配模式（如 '*.h', '*.cpp'）
            max_results: 最多返回结果数
            return_content: True=返回内容，False=返回文件路径

        Returns:
            匹配的文件路径或内容列表
        """
        from ..tools import grep  # 假设有这样的工具接口

        output_mode = 'content' if return_content else 'files_with_matches'

        result = grep(
            pattern=pattern,
            path=self.project_root,
            glob=file_glob,
            output_mode=output_mode,
            head_limit=max_results,
            n=True  # 显示行号
        )

        return result

    def search_multiline_definition(
        self,
        start_pattern: str,
        end_pattern: str = r'\}',
        file_glob: str = '*.h',
        max_lines: int = 60
    ) -> Optional[str]:
        """
        搜索多行定义（如结构体）

        策略：
        1. 用 start_pattern 找到开始行
        2. 读取文件，提取到 end_pattern 为止
        3. 限制最大行数
        """
        files = self.search_pattern(start_pattern, file_glob, max_results=1, return_content=False)

        if not files:
            return None

        file_path = files[0]
        # 读取并提取多行定义...
        return self._extract_definition(file_path, start_pattern, end_pattern, max_lines)

    def _extract_definition(self, file_path, start_pattern, end_pattern, max_lines):
        """从文件中提取定义（私有方法）"""
        # 实现细节...
        pass
```

### 4.3 特化搜索器（简单继承或组合）

#### 方案 A: 组合（推荐）

```python
# simple_ast/searchers/structure_searcher.py

from .grep_searcher import GrepSearcher
import re

class StructureSearcher:
    """数据结构搜索器"""

    def __init__(self, project_root: str):
        self.grep = GrepSearcher(project_root)

    def search(self, struct_name: str) -> Optional[str]:
        """
        搜索数据结构定义

        Returns:
            完整的结构体定义文本，未找到返回 None
        """
        # 1. 构造搜索模式
        patterns = self._build_patterns(struct_name)
        combined = '|'.join(patterns)

        # 2. 搜索
        result = self.grep.search_multiline_definition(
            start_pattern=combined,
            end_pattern=r'\}',
            file_glob='*.h',
            max_lines=60
        )

        return result

    def _build_patterns(self, struct_name: str) -> List[str]:
        """构造搜索模式"""
        name = re.escape(struct_name)
        return [
            rf'^\s*(struct|class)\s+{name}\s*[{{;]',
            rf'^\s*typedef\s+.*\s+{name}\s*;',
            rf'}}\s*\w*,?\s*{name}\s*;',
            rf'^\s*using\s+{name}\s*=',
        ]
```

#### 方案 B: 继承（可选）

```python
class StructureSearcher(GrepSearcher):
    """数据结构搜索器"""

    def search_structure(self, struct_name: str) -> Optional[str]:
        patterns = self._build_patterns(struct_name)
        combined = '|'.join(patterns)

        return self.search_multiline_definition(
            start_pattern=combined,
            end_pattern=r'\}',
            file_glob='*.h'
        )
```

**推荐组合**：更灵活，依赖关系更清晰

### 4.4 使用接口

```python
# 在 extractors 中使用

from simple_ast.searchers import StructureSearcher, SignatureSearcher, ConstantSearcher

class StructureExtractor:
    def __init__(self, project_root: str):
        self.searcher = StructureSearcher(project_root)

    def extract(self, struct_name: str) -> Optional[str]:
        # 搜索定义
        definition = self.searcher.search(struct_name)

        # 格式化输出
        if definition:
            return f"// 数据结构定义\n{definition}"

        return None
```

---

## 5. 搜索策略表

### 快速参考

| 搜索目标 | 文件类型 | 正则表达式关键点 | 最大结果数 | 是否多行 |
|---------|---------|----------------|-----------|---------|
| 数据结构 | `*.h` | `\b{name}\b` + 上下文（struct/typedef） | 1-10 | ✓ |
| 函数签名 | `*.h` | `\b{name}\s*\(` + 行首返回类型 | 1-5 | ✓ |
| 常量定义 | `*.h` | `#define {name}\b` 或 `{name}\s*=` | 1 | ✗ |
| 宏定义 | `*.h` | `#define {name}\b` | 1 | ✓ |

---

## 6. 性能考虑

### 6.1 搜索范围控制

```python
# 配置项
class SearchConfig:
    max_files_to_search = 1000     # Grep 最多扫描的文件数
    max_results = 10               # 最多返回结果数
    search_timeout = 30            # 搜索超时（秒）
    file_size_limit = 10 * 1024 * 1024  # 单文件最大 10MB
```

### 6.2 缓存策略

```python
# 可选：缓存搜索结果
class CachedGrepSearcher:
    def __init__(self, project_root: str):
        self.grep = GrepSearcher(project_root)
        self._cache = {}  # pattern -> results

    def search_pattern(self, pattern: str, **kwargs):
        cache_key = (pattern, tuple(sorted(kwargs.items())))

        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self.grep.search_pattern(pattern, **kwargs)
        self._cache[cache_key] = result
        return result
```

**注意**：缓存需要考虑文件变化，可能需要基于文件修改时间的失效策略。

### 6.3 渐进式搜索

```python
def progressive_search(struct_name: str):
    """渐进式搜索：从快到慢"""

    # 第1轮：只搜索最常见的位置（快）
    result = quick_search(struct_name, locations=['include/', 'inc/'])
    if result:
        return result

    # 第2轮：全局搜索 *.h（中等）
    result = full_header_search(struct_name)
    if result:
        return result

    # 第3轮：搜索所有文件（慢）
    result = exhaustive_search(struct_name)
    return result
```

---

## 7. 错误处理和降级

### 7.1 搜索失败场景

1. **未找到任何匹配**
   - 返回 `None`
   - 记录日志：`未找到 {name} 的定义`

2. **找到多个定义**
   - 取第一个
   - 可选：记录所有位置供调试

3. **Grep 超时或错误**
   - 捕获异常
   - 降级到 Python 遍历（可选）

### 7.2 降级策略

```python
def search_with_fallback(struct_name: str):
    """带降级的搜索"""

    try:
        # 尝试 Grep
        return grep_search(struct_name)
    except GrepTimeoutError:
        log.warning("Grep 超时，降级到 Python 搜索")
        return python_search(struct_name)
    except Exception as e:
        log.error(f"搜索失败: {e}")
        return None
```

---

## 8. 测试策略

### 8.1 单元测试

```python
def test_structure_search():
    """测试数据结构搜索"""
    searcher = StructureSearcher('projects/test_project')

    # 测试：简单 struct
    result = searcher.search('SimpleStruct')
    assert 'struct SimpleStruct' in result

    # 测试：typedef
    result = searcher.search('TypedefStruct')
    assert 'typedef' in result

    # 测试：未找到
    result = searcher.search('NonExistent')
    assert result is None
```

### 8.2 集成测试

使用真实项目测试：
- `projects/ince_diam/` - 复杂企业项目
- `projects/imgui-master/` - 开源项目

```python
def test_real_project_search():
    """在真实项目中测试"""
    searcher = StructureSearcher('projects/ince_diam')

    # 已知存在的定义
    result = searcher.search('MsgBlock')
    assert result is not None
    assert 'v_base.h' in result  # 验证来源文件
    assert 'VOS_MSG_HEADER' in result  # 验证内容
```

---

## 9. 未来扩展

### 9.1 新增搜索场景

添加新场景非常简单：

```python
# 1. 创建新的搜索器
class EnumSearcher:
    def __init__(self, project_root: str):
        self.grep = GrepSearcher(project_root)

    def search(self, enum_name: str):
        pattern = rf'^\s*enum\s+(class\s+)?{re.escape(enum_name)}\s*[{{;]'
        return self.grep.search_multiline_definition(pattern, ...)

# 2. 注册到统一接口（可选）
SEARCHERS = {
    'structure': StructureSearcher,
    'signature': SignatureSearcher,
    'constant': ConstantSearcher,
    'enum': EnumSearcher,  # 新增
}
```

### 9.2 支持更多文件类型

```python
# 配置化文件类型
FILE_TYPES = {
    'headers': ['*.h', '*.hpp', '*.hxx', '*.hh'],
    'sources': ['*.c', '*.cpp', '*.cxx', '*.cc'],
    'all': ['*.h', '*.hpp', '*.c', '*.cpp'],
}

# 使用
searcher.search(struct_name, file_types=FILE_TYPES['headers'])
```

### 9.3 跨语言支持

```python
# 策略模式：不同语言不同策略
class CppSearchStrategy:
    file_types = ['*.h', '*.hpp', '*.cpp']
    patterns = {...}

class JavaSearchStrategy:
    file_types = ['*.java']
    patterns = {...}

# 工厂
def get_searcher(language: str, project_root: str):
    strategies = {
        'cpp': CppSearchStrategy,
        'java': JavaSearchStrategy,
    }
    return Searcher(project_root, strategies[language])
```

---

## 10. 总结

### 关键决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 搜索工具 | Grep (ripgrep) | 快速、支持正则 |
| 搜索范围 | 全项目 `*.h` | 准确性优先 |
| 匹配策略 | 词边界 + 上下文 | 避免误匹配 |
| 代码结构 | 组合 > 继承 | 简单、灵活 |
| 性能策略 | 限制结果数 + 超时 | 可控 |
| 扩展性 | 独立的搜索器类 | 易于新增场景 |

### 实现优先级

**Phase 1（当前急需）**：
1. ✅ 数据结构搜索（解决 MsgBlock 问题）
2. ✅ 函数签名搜索
3. ✅ 常量定义搜索

**Phase 2（优化）**：
4. 性能优化（缓存、渐进搜索）
5. 更精确的匹配模式
6. 更好的错误提示

**Phase 3（扩展）**：
7. 枚举、宏展开等
8. 跨语言支持

### 保持简单的原则

- ❌ 不要过早优化（先跑起来）
- ❌ 不要过度抽象（3个场景不需要设计模式）
- ✅ 先实现核心功能
- ✅ 遇到第4个、第5个场景再考虑抽象

---

## 附录：Grep Tool 参数说明

```python
Grep(
    pattern: str,          # 正则表达式
    path: str,             # 搜索路径
    glob: str = None,      # 文件匹配（如 '*.h'）
    type: str = None,      # 文件类型（如 'cpp', 'py'）
    output_mode: str = 'files_with_matches',  # 输出模式
    head_limit: int = None,   # 最多返回条数
    offset: int = 0,          # 跳过前N条
    multiline: bool = False,  # 多行匹配
    i: bool = False,          # 忽略大小写
    n: bool = False,          # 显示行号
    A: int = 0,               # After context
    B: int = 0,               # Before context
    C: int = 0,               # Context
)
```

### 输出模式

- `files_with_matches`: 只返回文件路径（快）
- `content`: 返回匹配的行内容（详细）
- `count`: 返回匹配数量（统计）

### 示例

```python
# 搜索所有包含 "MsgBlock" 的头文件
Grep(
    pattern=r'\bMsgBlock\b',
    path='projects/ince_diam',
    glob='*.h',
    output_mode='files_with_matches',
    head_limit=10
)

# 搜索结构体定义（带上下文）
Grep(
    pattern=r'^\s*struct\s+MsgBlock\s*{',
    path='projects/ince_diam',
    glob='*.h',
    output_mode='content',
    n=True,    # 显示行号
    A=5,       # 显示后5行
    head_limit=1
)
```
