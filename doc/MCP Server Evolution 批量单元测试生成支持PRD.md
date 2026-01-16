# MCP Server Evolution: 批量单元测试生成支持 PRD v2

## 1. 核心目标

将 MCP Server 升级为支持 **异步初始化**、**持久化缓存** 和 **快速查询** 的有状态服务，实现：

1. **异步初始化**: 后台分析整个项目，不阻塞 Agent 交互
2. **毫秒级查询**: 基于本地缓存 (`.simple_ast_cache`) 提供瞬时响应
3. **文本预处理**: 分析时生成 `context_text`，查询时直接返回
4. **鲁棒性**: 内部支持断点续传、错误重试（不暴露为MCP工具）

---

## 2. 核心场景

### 场景 A: 首次使用
用户请求生成单元测试 → Agent 发现未初始化 → 启动后台分析 → 轮询进度 → 查询函数信息 → 生成测试

### 场景 B: 快速生成
已初始化项目 → 直接查询函数信息（毫秒级） → 生成测试

### 场景 C: 批量生成
Agent 用 Grep 发现多个函数 → 并行查询函数信息 → 批量生成测试

---

## 3. MCP 工具定义

系统提供 **3 个核心 MCP 工具**。

### 3.1 `initialize_project` - 项目初始化

启动项目分析任务，同时提供状态查询。

**参数**:
```python
project_root: str                      # 项目根目录绝对路径
target_paths: List[str] = ["."]       # 要分析的目录
exclude_patterns: List[str] = None    # 排除模式（如 ["build/", "*.pb.cc"]）
force_reanalyze: bool = False         # 强制重新分析
```

**返回**:

已初始化:
```json
{
  "status": "already_initialized",
  "initialized": true,
  "cache_info": {
    "total_functions": 1523,
    "last_analysis_time": "2026-01-16T10:30:00Z"
  }
}
```

启动新任务:
```json
{
  "status": "started",
  "task_id": "task_abc123",
  "estimated_files": 245
}
```

---

### 3.2 `get_analysis_progress` - 查询进度

**参数**:
```python
project_root: str  # 项目根目录绝对路径
```

**返回**:

分析中:
```json
{
  "status": "running",
  "progress": {
    "percentage": 48.9,
    "processed_files": 120,
    "total_files": 245,
    "current_file": "src/handler.cpp"
  },
  "errors": {
    "count": 2,
    "failed_files": ["src/broken.cpp", "src/invalid.cpp"]
  },
  "estimated_remaining_seconds": 180
}
```

已完成:
```json
{
  "status": "completed",
  "progress": {"percentage": 100.0},
  "summary": {
    "total_functions": 1523,
    "success_files": 243,
    "failed_files": 2
  }
}
```

---

### 3.3 `get_function_info` - 获取函数测试上下文

**参数**:
```python
project_root: str           # 项目根目录绝对路径
function_name: str          # 函数名
file_path: str = None       # 可选，用于解决重名冲突
```

**返回**:

成功:
```json
{
  "success": true,
  "function_name": "ProcessMessage",
  "signature": "int ProcessMessage(int type, const char* data)",
  "location": "src/handler.cpp:42",
  "source_code": "完整源代码...",
  "mock_list": ["ValidateInput", "LogError", "SendResponse"],
  "internal_dependencies": [
    {
      "name": "ParseData",
      "signature": "bool ParseData(const char* data, int len)",
      "location": "src/parser.cpp:15",
      "source_code": "..."
    }
  ],
  "data_structures": [
    {
      "name": "MessageHeader",
      "type": "struct",
      "location": "src/types.h:10",
      "definition": "struct MessageHeader { ... };"
    }
  ],
  "call_chain": "ProcessMessage -> ParseData -> ValidateInput [EXTERNAL]",
  "context_text": "======= Function: ProcessMessage =======\n[Source Code]\n...\n[Mock List]\n...\n[Dependencies]\n...\n[Call Chain]\n..."
}
```

失败:
```json
{
  "success": false,
  "error": "project_not_initialized",
  "message": "项目尚未初始化，请先调用 initialize_project"
}
```

**注意**: `context_text` 是预处理好的完整文本，可直接输入给 LLM。

---

## 4. 端到端演示

### 演示 1: 首次使用

```
User: "帮我生成 HandleRequest 函数的单元测试"

Agent -> initialize_project(root)
=> {"status": "started", "task_id": "task_123", "estimated_files": 245}

Agent: "项目正在分析中，预计需要 3 分钟..."

Agent -> get_analysis_progress(root)  // 轮询
=> {"status": "running", "progress": {"percentage": 20}}

Agent -> get_analysis_progress(root)
=> {"status": "running", "progress": {"percentage": 65}}

Agent -> get_analysis_progress(root)
=> {"status": "completed", "summary": {"total_functions": 1523}}

Agent: "分析完成！共 1523 个函数"

Agent -> get_function_info(root, "HandleRequest")
=> { 完整的函数信息，包含 context_text }

Agent: 基于 context_text 生成单元测试代码
```

### 演示 2: 已初始化项目（快速路径）

```
User: "帮我生成 ProcessData 函数的单元测试"

Agent -> initialize_project(root)
=> {"status": "already_initialized", "cache_info": {"total_functions": 1523}}

Agent -> get_function_info(root, "ProcessData")
=> { 完整的函数信息 }  // 毫秒级响应

Agent: 直接生成单元测试代码
```

### 演示 3: 批量生成

```
User: "给 src/utils.cpp 下的所有函数生成测试"

Agent: 用 Grep 搜索函数
=> 发现: TimeNow, StringSplit, HashCalc

Agent -> initialize_project(root)
=> {"status": "already_initialized"}

Agent (并行查询):
-> get_function_info(root, "TimeNow", file_path="src/utils.cpp")
-> get_function_info(root, "StringSplit", file_path="src/utils.cpp")
-> get_function_info(root, "HashCalc", file_path="src/utils.cpp")
// 3个查询几乎同时返回（毫秒级）

Agent: 生成测试文件
```

---

## 5. 缓存结构

```
.simple_ast_cache/
├── config.json              # 分析配置
├── metadata.json            # 元数据（总函数数、最后分析时间等）
├── progress.json            # 运行时进度（实时更新）
├── errors.json              # 失败文件列表
└── functions/               # 函数数据（按文件分片）
    ├── src_main_cpp.json
    └── src_utils_cpp.json
```

每个函数缓存包含:
- 函数签名、源代码、位置
- Mock 清单、内部依赖、数据结构
- 调用链、复杂度统计
- **预处理好的 `context_text`**

---

## 6. 内部机制（不暴露为MCP工具）

- **断点续传**: `progress.json` 记录 checkpoint，重启后继续
- **错误重试**: 失败文件记录到 `errors.json`，`force_reanalyze=true` 时优先重试
- **缓存失效**: 检测文件修改时间，自动标记过期缓存
- **并发分析**: 使用线程池并发处理多个文件
- **增量更新**: 只重新分析变更的文件

---

## 7. 实现优先级

### Phase 1: 核心缓存（必须）
- 实现 `CacheManager` - 缓存读写
- 实现 `ContextTextFormatter` - 文本预处理
- 修改 `get_function_info` - 支持缓存查询

### Phase 2: 异步任务（必须）
- 实现 `AnalysisTask` - 任务管理
- 实现 `initialize_project` 和 `get_analysis_progress`
- 实现进度持久化

### Phase 3: 鲁棒性（重要）
- 断点续传、错误重试、缓存失效检测
