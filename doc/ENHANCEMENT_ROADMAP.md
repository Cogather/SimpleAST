# 功能增强实现路线图

## 目标
在当前AST+检索工具基础上，实现：
1. 函数签名的完整解析（参数、返回值）
2. 代码位置标注系统
3. 宏定义递归展开

---

## 1. 函数签名详细解析 ⭐

### 实现位置
`simple_ast/extractors/signature_extractor.py`

### 当前状态
```python
# 当前只提取签名字符串
function_signatures = {
    "PidDiamMsgProc": "VOS_VOID PidDiamMsgProc(MsgBlock *pMsg)"
}
```

### 目标状态
```python
function_signatures = {
    "PidDiamMsgProc": {
        "signature": "VOS_VOID PidDiamMsgProc(MsgBlock *pMsg)",
        "return_type": "VOS_VOID",
        "parameters": [
            {
                "type": "MsgBlock *",
                "name": "pMsg",
                "description": "消息块指针"
            }
        ],
        "location": "diamadapt.cpp:589"
    }
}
```

### 实现方案
```python
def extract_function_details(function_node, source_code):
    """从 tree-sitter 节点提取函数详细信息"""

    # 1. 提取返回值类型
    return_type_node = function_node.child_by_field_name('type')
    return_type = get_node_text(return_type_node, source_code)

    # 2. 提取函数名和参数
    declarator = function_node.child_by_field_name('declarator')

    # 找到函数名（function_declarator 的子节点）
    func_name = None
    params_node = None

    for child in declarator.children:
        if child.type == 'identifier':
            func_name = get_node_text(child, source_code)
        elif child.type == 'parameter_list':
            params_node = child

    # 3. 提取参数列表
    parameters = []
    if params_node:
        for param in params_node.named_children:
            if param.type == 'parameter_declaration':
                param_type_node = param.child_by_field_name('type')
                param_declarator = param.child_by_field_name('declarator')

                param_type = get_node_text(param_type_node, source_code) if param_type_node else ""
                param_name = get_node_text(param_declarator, source_code) if param_declarator else ""

                # 处理指针、引用
                if param_declarator:
                    for child in param.children:
                        if child.type in ['*', '&']:
                            param_type += child.type

                parameters.append({
                    "type": param_type.strip(),
                    "name": param_name.strip()
                })

    # 4. 位置信息
    location = f"{function_node.start_point[0] + 1}"

    return {
        "return_type": return_type,
        "name": func_name,
        "parameters": parameters,
        "location": location
    }
```

### 工作量
- 代码修改：SignatureExtractor 类
- 测试：验证各种参数形式（指针、引用、const等）
- **预计时间：4-6小时**

---

## 2. 代码位置标注系统 ⭐⭐

### 实现位置
- `simple_ast/analyzers/branch_analyzer.py` - 分支位置
- `simple_ast/extractors/structure_extractor.py` - 结构体位置
- `simple_ast/extractors/constant_extractor.py` - 常量位置

### 目标输出格式

**分支位置**：
```
#### 1.2.1 输入验证

```cpp
// 位置: common/source/diam/diamadapt.cpp:595-599
if (!CheckPidDiamMsg(pMsg)) {
    return;
}
```
```

**函数位置**：
```
#### CheckPidDiamMsg

- **函数签名**: `bool CheckPidDiamMsg(const MsgBlock *pMsg)`
- **定义位置**: `common/include/diam/diam_pub.h:539`
- **实现位置**: `common/source/diam/diamadapt.cpp:531`
```

### 实现方案

#### 2.1 分支位置标注
```python
# 在 BranchAnalyzer 中添加位置信息
class BranchCondition:
    def __init__(self, ...):
        self.start_line = None
        self.end_line = None
        self.code_snippet = None

def _analyze_if_statement(self, node, ...):
    condition = BranchCondition(
        condition=condition_text,
        branch_type='if',
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        code_snippet=self._extract_code_snippet(node)
    )
```

#### 2.2 函数定义位置
```python
# 在搜索函数签名时记录位置
def find_function_definition(func_name, project_root):
    # 使用 GrepSearcher 搜索函数定义
    pattern = rf'^\s*\w+\s+{func_name}\s*\('
    results = grep_searcher.search_content(pattern, show_line_numbers=True)

    if results:
        file_path, line_num, content = results[0]
        return {
            "location": f"{file_path.name}:{line_num}",
            "signature": content
        }
```

#### 2.3 代码片段提取
```python
def extract_code_snippet(node, source_code):
    """从AST节点提取代码片段"""
    start_line = node.start_point[0]
    end_line = node.end_point[0]

    lines = source_code.split('\n')
    snippet_lines = lines[start_line:end_line + 1]

    return '\n'.join(snippet_lines)
```

### 工作量
- 修改 BranchAnalyzer：添加位置字段
- 修改 SignatureExtractor：搜索时记录位置
- 修改 Reporter：输出位置信息
- **预计时间：6-8小时**

---

## 3. 宏定义递归展开 ⭐⭐⭐

### 实现位置
新建 `simple_ast/extractors/macro_expander.py`

### 目标效果

**当前输出**：
```cpp
typedef struct {
    VOS_MSG_HEADER
    FE_MSG_HEADER
    VOS_UINT8 MsgBody[4];
} tFeAppMsg;
```

**目标输出**：
```cpp
typedef struct {
    VOS_MSG_HEADER                /* dopra消息头 */
    FE_MSG_HEADER                 /* FE的消息头 */
    VOS_UINT8 MsgBody[4];
} tFeAppMsg;

其中，VOS_MSG_HEADER 展开为：
    VOS_UINT32 ulSenderCpuId;
    VOS_UINT32 ulSenderPid;
    VOS_UINT32 ulReceiverCpuId;
    VOS_UINT32 ulReceiverPid;
    VOS_UINT32 ulLength;

FE_MSG_HEADER 展开为：
    VOS_UINT32 SenderCb;
    VOS_UINT32 ReceiverCb;
    VOS_UINT32 MsgType;
    ...
```

### 实现方案

```python
class MacroExpander:
    """宏定义展开器"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.grep_searcher = GrepSearcher(project_root)
        self.macro_cache = {}  # 缓存已展开的宏

    def find_macro_definition(self, macro_name: str) -> Optional[str]:
        """搜索宏定义"""
        pattern = rf'^\s*#define\s+{re.escape(macro_name)}\b'
        results = self.grep_searcher.search_content(
            pattern=pattern,
            file_glob='*.h',
            max_results=1,
            context_lines=10  # 获取后续行（处理多行宏）
        )

        if not results:
            return None

        file_path, line_num, content = results[0]

        # 提取完整的宏内容（处理续行符 \）
        return self._extract_macro_content(file_path, line_num)

    def _extract_macro_content(self, file_path: Path, start_line: int) -> str:
        """提取完整宏内容（处理续行符）"""
        macro_lines = []

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

            for i in range(start_line - 1, len(lines)):
                line = lines[i].rstrip()

                # 去掉 #define 和宏名
                if i == start_line - 1:
                    line = re.sub(r'^\s*#define\s+\w+\s*', '', line)

                # 检查是否有续行符
                if line.endswith('\\'):
                    macro_lines.append(line[:-1].strip())
                else:
                    macro_lines.append(line.strip())
                    break

        return '\n'.join(macro_lines)

    def expand_macro(self, macro_name: str, max_depth: int = 5) -> Optional[str]:
        """递归展开宏"""
        # 检查缓存
        if macro_name in self.macro_cache:
            return self.macro_cache[macro_name]

        # 搜索宏定义
        macro_content = self.find_macro_definition(macro_name)
        if not macro_content:
            return None

        # 递归展开嵌套的宏
        expanded = self._expand_nested_macros(macro_content, depth=0, max_depth=max_depth)

        # 缓存结果
        self.macro_cache[macro_name] = expanded
        return expanded

    def _expand_nested_macros(self, content: str, depth: int, max_depth: int) -> str:
        """递归展开嵌套的宏"""
        if depth >= max_depth:
            return content

        # 查找所有可能的宏引用（大写标识符）
        macro_refs = re.findall(r'\b[A-Z][A-Z0-9_]{2,}\b', content)

        for ref in set(macro_refs):
            # 避免循环引用
            if ref in self.macro_cache:
                nested_content = self.macro_cache[ref]
            else:
                nested_content = self.find_macro_definition(ref)

            if nested_content:
                # 递归展开
                nested_content = self._expand_nested_macros(
                    nested_content,
                    depth + 1,
                    max_depth
                )
                content = content.replace(ref, nested_content)

        return content

    def expand_struct_macros(self, struct_text: str) -> str:
        """展开结构体定义中的宏"""
        lines = struct_text.split('\n')
        expanded_lines = []

        for line in lines:
            # 查找行中的宏引用
            macro_refs = re.findall(r'\b[A-Z][A-Z0-9_]{2,}\b', line)

            if macro_refs:
                # 尝试展开每个宏
                for macro in macro_refs:
                    expanded = self.expand_macro(macro)
                    if expanded:
                        # 添加注释和展开内容
                        expanded_lines.append(f"{line}  /* 展开: */")
                        for exp_line in expanded.split('\n'):
                            expanded_lines.append(f"    {exp_line}")
                        break
                else:
                    expanded_lines.append(line)
            else:
                expanded_lines.append(line)

        return '\n'.join(expanded_lines)
```

### 使用示例
```python
# 在 StructureExtractor 中使用
expander = MacroExpander(project_root)

# 展开结构体中的宏
expanded_struct = expander.expand_struct_macros(struct_text)
```

### 工作量
- 实现 MacroExpander 类
- 处理多行宏（续行符）
- 处理嵌套宏
- 集成到 StructureExtractor
- 测试各种宏形式
- **预计时间：10-12小时**

---

## 实施计划

### 第一周（快速见效）
- Day 1-2: **函数签名详细解析** (4-6h)
- Day 3-4: **代码位置标注系统** (6-8h)
- Day 5: 集成测试和文档

### 第二周（进阶功能）
- Day 1-3: **宏定义展开** - 基础版 (10-12h)
- Day 4: 测试和优化
- Day 5: 文档和示例

### 预期成果
完成后输出的文档将包含：
- ✅ 完整的函数签名（带参数和返回值）
- ✅ 精确的代码位置（文件:行号范围）
- ✅ 展开的宏定义（结构体中的宏）

---

## 技术栈确认

✅ **已有工具**：
- tree-sitter：AST解析（函数签名、位置）
- GrepSearcher：全局搜索（宏定义）
- 正则表达式：文本解析

✅ **无需新依赖**：
- 所有功能都可以用现有工具实现
- 不需要引入新的库或工具

---

## 风险和注意事项

### 宏展开的限制
1. **函数式宏**（带参数）较难处理
   ```c
   #define OFFSET_OF(type, member) ...
   ```
   - 建议：先不处理，或者只展开定义不替换参数

2. **条件编译**
   ```c
   #ifdef _USC_DIAMRM_
   #define MAX_NUM 6000
   #else
   #define MAX_NUM 2
   #endif
   ```
   - 建议：展开所有可能的定义，标注条件

3. **跨文件宏链**
   - A.h 定义宏1
   - B.h include A.h 并定义宏2（引用宏1）
   - C.h include B.h 并使用宏2
   - 建议：设置最大展开深度（如5层）

### 性能考虑
- 宏展开可能需要多次 grep 搜索
- 建议：使用缓存（已在设计中）
- 预期：每个宏展开 <0.5秒

---

## 总结

**✅ 完全可行**，并且不需要新工具！

| 功能 | 难度 | 时间 | 工具 |
|------|------|------|------|
| 1. 函数签名解析 | ⭐ 简单 | 4-6h | tree-sitter AST |
| 2. 代码位置标注 | ⭐⭐ 容易 | 6-8h | tree-sitter + grep |
| 3. 宏定义展开 | ⭐⭐⭐ 中等 | 10-12h | grep + 递归解析 |

**总计：约 20-26 小时工作量**（2-3个工作日）

实现后，你的工具将达到**期望文档的 80-90% 匹配度**！
