# 开发脚本

本目录包含开发过程中使用的各种脚本和工具。

## 📁 目录结构

```
scripts/
├── debug/          # 调试脚本，用于排查特定问题
├── tools/          # 实用工具脚本
└── experiments/    # 实验性脚本，用于测试新功能
```

## 🔧 使用说明

这些脚本主要用于开发和调试，**不是项目的核心功能**。

### 调试脚本 (`debug/`)

用于排查和诊断特定问题的脚本：

- **`debug_priority.py`** - 调试优先级相关问题
- **`debug_switch_ast.py`** - 调试 switch 语句的 AST 解析
- **`diagnose_rg.py`** - 诊断 ripgrep 配置和路径问题

**使用方式**:
```bash
cd scripts/debug
python debug_switch_ast.py
```

### 工具脚本 (`tools/`)

实用工具和辅助脚本：

- **`convert_logs.py`** - 转换日志格式
- **`extract_function.py`** - 提取函数实现（早期版本，已整合到核心功能）

**使用方式**:
```bash
cd scripts/tools
python convert_logs.py
```

### 实验性脚本 (`experiments/`)

用于测试新功能和验证想法的实验性脚本：

#### 搜索功能测试
- **`test_comprehensive_search.py`** - 综合搜索功能测试
- **`test_grep_command.py`** - grep 命令测试
- **`test_grep_diamappmsg.py`** - 特定数据结构搜索测试
- **`test_simple_grep.py`** - 简单 grep 测试
- **`test_structure_search.py`** - 结构搜索测试

#### Ripgrep 测试
- **`test_rg_direct.py`** - ripgrep 直接调用测试
- **`test_rg_version.py`** - ripgrep 版本检测测试
- **`test_rg_windows.py`** - Windows 平台 ripgrep 测试
- **`test_ripgrep.py`** - ripgrep 集成测试

#### 提取器测试
- **`test_extractor.py`** - 提取器功能测试
- **`test_search_tool.py`** - 搜索工具配置测试

**使用方式**:
```bash
cd scripts/experiments
python test_ripgrep.py
```

## ⚠️ 注意事项

1. **环境依赖**: 这些脚本可能依赖特定的环境或测试数据
2. **不保证运行**: 不保证所有脚本都能正常运行（可能是临时测试）
3. **可以删除**: 如果脚本不再需要，可以安全删除
4. **不要依赖**: 正式功能不应依赖这些脚本

## 🧪 从实验到正式功能

如果实验性脚本验证了有价值的功能，应该：

1. 将逻辑整合到核心代码 (`simple_ast/`)
2. 添加正式的单元测试 (`tests/unit/`)
3. 更新文档
4. 删除或归档实验性脚本

## 📝 添加新脚本

如果需要添加新的开发脚本：

```bash
# 调试脚本
touch scripts/debug/debug_new_feature.py

# 工具脚本
touch scripts/tools/my_tool.py

# 实验性脚本
touch scripts/experiments/test_new_idea.py
```

**不要在项目根目录创建临时脚本！**

## 🗑️ 清理建议

定期审查此目录，删除不再需要的脚本：

```bash
# 查看最近未修改的脚本
find scripts/ -name "*.py" -mtime +90  # 90天未修改

# 删除不需要的脚本
git rm scripts/experiments/old_test.py
```

---

**最后更新**: 2026-01-06
**维护者**: SimpleAST 开发团队
