# SimpleAST 文档导航

最后更新: 2025-12-19

## 📚 核心文档

### [ARCHITECTURE.md](ARCHITECTURE.md)
完整的代码架构文档，包含：
- 分层架构设计
- 核心模块详解
- 数据流转说明
- 设计模式应用

### [SEARCH_STRATEGY.md](SEARCH_STRATEGY.md) 🌟 最新
**全局搜索实现文档** (2025-12-19 更新)
- ✅ 脚本文件方式避免参数传递问题
- ✅ 优先级 + 评分筛选机制
- ✅ 支持 5 种 typedef 定义形式
- ✅ 已验证：能找到深层目录中的结构体

### [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md)
重构总结文档，记录：
- 重构目标和原则（实用性优先）
- 消除的代码重复（~150行）
- 新增模块结构
- 验证结果

---

## 📖 参考文档

### [EXTERNAL_CLASSIFICATION.md](EXTERNAL_CLASSIFICATION.md)
外部函数分类规则，用于 Mock 生成：
- 标准库函数识别
- 日志函数过滤
- 业务函数提取

### [LOGGING_REFERENCE.md](LOGGING_REFERENCE.md)
日志系统使用参考：
- 日志配置
- 日志级别
- 输出位置

### [PRD.md](PRD.md)
产品需求文档（历史记录）

### [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
项目结构说明（可能部分过时）

---

## 🗂️ 已移除文档

- ~~`REFACTORING_PROPOSAL.md`~~ - 重构建议已完成，文档已删除

---

## 🚀 快速开始

1. **了解架构**: 先读 [ARCHITECTURE.md](ARCHITECTURE.md)
2. **理解搜索**: 读 [SEARCH_STRATEGY.md](SEARCH_STRATEGY.md) 了解全局搜索实现
3. **参考重构**: 读 [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) 了解重构历史

---

## 📝 文档维护

- 代码变更时请同步更新相关文档
- 标注更新日期
- 删除过时文档时请在此 README 中记录
