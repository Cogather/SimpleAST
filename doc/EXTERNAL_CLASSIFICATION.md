# 外部函数分类配置说明

## 配置文件位置

默认配置文件：`.simple_ast_config.json`（项目根目录）

## 配置结构

```json
{
  "external_function_classification": {
    "standard_library": {
      "description": "标准库函数（通常不需要Mock）",
      "patterns": ["memset*", "strcpy*", "std::*", ...]
    },
    "logging_utility": {
      "description": "日志/工具函数（可选Mock）",
      "patterns": ["*LOG*", "*log*", "*ASSERT*", ...]
    },
    "custom_exclusions": {
      "description": "用户自定义排除的函数（项目特定）",
      "patterns": ["FE_LOG", "MY_PROJECT_LOG", ...]
    }
  }
}
```

## 模式匹配规则

使用 Unix shell 风格的通配符：
- `*` - 匹配任意字符（0个或多个）
- `?` - 匹配单个字符
- `[abc]` - 匹配字符集中的任意一个

**示例**：
- `memset*` - 匹配 `memset`, `memset_s`, `memset_explicit`
- `*LOG*` - 匹配 `FE_LOG`, `DEBUG_LOG`, `MyLog`
- `std::*` - 匹配所有 C++ 标准库函数

## 自定义配置

### 1. 添加项目特定的日志函数

```json
"custom_exclusions": {
  "patterns": [
    "FE_LOG",           // 项目日志宏
    "MY_LOG_*",         // 所有以 MY_LOG_ 开头的函数
    "USE",              // 特定的工具宏
    "TRACE_*"           // 追踪相关函数
  ]
}
```

### 2. 添加项目使用的库函数

如果你的项目使用特定的库（如 OpenSSL、Boost），可以添加到 `standard_library`：

```json
"standard_library": {
  "patterns": [
    "memset*",
    "strcpy*",
    // 添加 OpenSSL 函数
    "OPENSSL_*",
    "EVP_*",
    "SSL_*",
    // 添加 Boost 函数
    "boost::*"
  ]
}
```

### 3. 配置优先级

分类按以下优先级进行：
1. `custom_exclusions` - 最高优先级
2. `standard_library`
3. `logging_utility`
4. 无匹配 → 归类为**业务外部依赖**（需要Mock）

## 输出效果

配置后，Mock清单会分类显示：

```
[Mock清单]
业务外部依赖（需要Mock）: 3 个
- DiamProcAppMsg
- DiamQueryLocalInfo
- DiamModifyLocalInfo

日志/工具函数（可选Mock）: 2 个
- FE_LOG
- TRACE_FUNCTION

标准库函数（通常不需要Mock）: 5 个
- memset_s
- memcpy_s
- strcpy_s
```

## 配置建议

### 初次使用

1. 使用默认配置运行分析
2. 查看生成的Mock清单
3. 将项目特定的日志/工具函数添加到 `custom_exclusions`

### 配置示例（典型C++项目）

```json
{
  "external_function_classification": {
    "standard_library": {
      "patterns": [
        "std::*",
        "memset*", "memcpy*", "strcpy*", "strlen*",
        "malloc*", "free*",
        "printf*", "sprintf*", "fprintf*",
        "pthread_*",
        "socket*", "send*", "recv*"
      ]
    },
    "logging_utility": {
      "patterns": [
        "*LOG*", "*log*", "*Log*",
        "*PRINT*", "*Print*",
        "*DEBUG*", "*Debug*",
        "*TRACE*", "*Trace*",
        "*ASSERT*", "*Assert*",
        "*CHECK*", "*Verify*"
      ]
    },
    "custom_exclusions": {
      "patterns": [
        "FE_LOG",
        "USE",
        "IM_ASSERT*",
        "MY_PROJECT_*"
      ]
    }
  }
}
```

## 常见问题

### Q: 某个函数分类错误怎么办？

A: 在 `custom_exclusions` 中添加该函数的模式，会覆盖默认分类。

### Q: 标准库函数被归类为业务依赖？

A: 检查函数名是否匹配 `standard_library` 中的模式，如果没有则添加相应模式。

### Q: 如何禁用某个分类？

A: 将该分类的 `patterns` 数组清空：`"patterns": []`

### Q: 配置文件不生效？

A: 确保：
1. 配置文件名为 `.simple_ast_config.json`
2. 文件位于项目根目录
3. JSON 格式正确（可用工具验证）
