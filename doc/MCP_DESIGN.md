# SimpleAST MCP Server 设计文档

**版本**: v1.1
**日期**: 2026-01-09
**目标**: 将 SimpleAST 改造为 MCP Server，为 AI 助手提供 C++ 代码分析能力

---

## 1. 设计目标

为单元测试生成提供完整的函数测试上下文，让 AI 助手能够：
- 获取函数的完整源代码
- 获取 Mock 清单（需要 Mock 的外部函数）
- 获取内部依赖函数的实现
- 获取相关数据结构定义
- 获取调用链和复杂度分析

---

## 2. 核心功能

### 2.1 开放的 Tool

**`get_function_test_context`** - 获取函数的完整测试上下文

**参数**：
```python
project_root: str      # C++ 项目根目录的绝对路径
target_file: str       # 目标文件相对路径（如 "src/main.cpp"）
function_name: str     # 要分析的函数名
trace_depth: int = 50  # 调用链追踪深度（可选）
```

**返回结构**：
```json
{
  "function_name": "ProcessMessage",
  "signature": "int ProcessMessage(int type, const char* data)",
  "location": "handler.cpp:42",
  "source_code": "完整的函数源代码",
  "statistics": {
    "internal_functions": 3,
    "external_functions": 5,
    "data_structures": 2
  },
  "complexity": {
    "cyclomatic": 12,
    "description": "中等复杂度"
  },
  "mock_list": ["ValidateInput", "LogError", "SendResponse"],
  "internal_dependencies": [
    {
      "name": "ParseData",
      "signature": "bool ParseData(const char* data, int len)",
      "source_code": "完整源代码",
      "location": "parser.cpp:15"
    }
  ],
  "data_structures": [
    {
      "name": "MessageHeader",
      "type": "struct",
      "definition": "struct MessageHeader { ... }",
      "location": "types.h:10"
    }
  ],
  "call_chain": "树状调用链文本表示"
}
```

---

## 3. 项目结构

```
/app
├── simple_ast/              # 现有核心库（不改动）
│   └── ...
├── mcp_server/              # 新增 MCP 服务器模块
│   ├── __init__.py
│   ├── server.py            # FastMCP 服务器入口
│   ├── tools.py             # MCP 工具实现
│   └── utils.py             # 结果转换工具
├── analyze.py               # 现有 CLI（保持不变）
├── mcp_server.py            # MCP 启动脚本
└── requirements.txt         # 添加 fastmcp 依赖
```

---

## 4. 技术实现

### 4.1 异步适配

```python
@mcp.tool()
async def get_function_test_context(...) -> dict:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        _sync_analyze,
        project_root, target_file, function_name, trace_depth
    )
    return result
```

### 4.2 结果转换

```python
def _extract_structured_data(result: AnalysisResult, func_name: str) -> dict:
    """将分析结果转换为 MCP 友好的 JSON 格式"""
    return {
        "function_name": func_name,
        "signature": _get_signature(result, func_name),
        "source_code": _get_source_code(result, func_name),
        "mock_list": _get_mock_list(result, func_name),
        "internal_dependencies": _get_internal_deps(result, func_name),
        "data_structures": _get_data_structures(result, func_name),
        # ...
    }
```

### 4.3 错误处理

```python
try:
    if not Path(project_root).exists():
        return {"error": f"项目目录不存在: {project_root}"}

    result = await _do_analysis(...)
    return result

except Exception as e:
    return {"error": f"分析失败: {str(e)}"}
```

---

## 5. 传输协议支持

### 5.1 Stdio 模式（默认，推荐）

**用途**：本地集成，Claude Desktop 等桌面客户端

**启动**：
```python
# mcp_server.py
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**配置**（claude_desktop_config.json）：
```json
{
  "mcpServers": {
    "simple-ast": {
      "command": "python",
      "args": ["/app/mcp_server.py"]
    }
  }
}
```

### 5.2 SSE 模式（可选）

**用途**：远程服务、团队共享

**启动**：
```python
# mcp_server.py
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--sse":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        mcp.run(transport="sse", port=port)
    else:
        mcp.run(transport="stdio")
```

```bash
python mcp_server.py --sse 8000
```

**配置**：
```json
{
  "mcpServers": {
    "simple-ast": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## 6. 部署配置

### 6.1 依赖安装

```bash
# requirements.txt
fastmcp>=0.1.0

# 安装
pip install -r requirements.txt
```

### 6.2 本地调试

```bash
# Stdio 模式
npx @modelcontextprotocol/inspector python /app/mcp_server.py

# SSE 模式
python mcp_server.py --sse 8000
npx @modelcontextprotocol/inspector http://localhost:8000/sse
```

---

## 7. 开发步骤

### Phase 1: MVP（必须）
- [ ] 创建 `mcp_server/` 目录结构
- [ ] 实现 `get_function_test_context` 工具
- [ ] 实现结果转换函数
- [ ] 支持 Stdio 模式
- [ ] 使用 MCP Inspector 测试

### Phase 2: SSE 支持（可选）
- [ ] 添加 SSE 模式支持
- [ ] 实现命令行参数解析
- [ ] 测试两种模式切换

### Phase 3: 完善（按需）
- [ ] 优化错误处理
- [ ] 添加输入验证
- [ ] 性能优化（缓存）

---

## 8. 安全考虑

### 8.1 基础安全（必须）

1. **路径验证**：验证 `project_root` 存在
2. **路径遍历防护**：检查 `target_file` 不含 `..`
3. **错误隔离**：捕获异常，返回错误信息

### 8.2 SSE 模式额外安全（如果使用）

1. **路径白名单**：限制可访问的项目路径
2. **HTTPS**：生产环境使用 HTTPS
3. **认证**：添加 API Key 或其他认证机制（按需）

---

## 9. 使用示例

### 9.1 在 Claude Desktop 中使用

```
用户: 帮我为 ProcessMessage 函数生成单元测试

Claude: 让我先分析这个函数的测试上下文
[调用 get_function_test_context]

根据分析结果，这个函数需要 Mock：
- ValidateInput
- LogError
- SendResponse

内部依赖函数：
- ParseData

我来为你生成完整的单元测试代码...
```

### 9.2 返回数据示例

```json
{
  "function_name": "ProcessMessage",
  "signature": "int ProcessMessage(int type, const char* data)",
  "source_code": "int ProcessMessage(...) { ... }",
  "mock_list": ["ValidateInput", "LogError", "SendResponse"],
  "internal_dependencies": [
    {
      "name": "ParseData",
      "source_code": "bool ParseData(...) { ... }"
    }
  ],
  "complexity": {
    "cyclomatic": 8,
    "description": "中等复杂度"
  }
}
```

---

## 10. 未来扩展（暂不实现）

- `get_function_list` - 获取文件中的函数列表
- `analyze_file_boundary` - 分析整个文件的边界信息
- Resources - 提供配置和历史分析结果
- Prompts - 预定义的测试生成提示词模板
