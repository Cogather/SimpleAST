# SimpleAST 产品需求文档（PRD）

**文档版本**: v1.2
**更新日期**: 2025-12-18
**项目名称**: SimpleAST - C++ 单元测试上下文生成工具

---

## 📑 目录

1. [产品概述](#1-产品概述)
2. [核心价值](#2-核心价值)
3. [核心功能](#3-核心功能)
4. [使用场景](#4-使用场景)
5. [技术限制](#5-技术限制)

---

## 1. 产品概述

### 1.1 产品定位

SimpleAST 是一款**无需编译环境**的 C++ 静态代码分析工具，专注于为单元测试生成完整的测试上下文。

### 1.2 核心特性

- **🧪 测试上下文生成**：自动生成完整Mock清单和内部依赖信息
- **🚀 零编译依赖**：基于 AST 解析，无需配置编译环境
- **⚡ 快速分析**：单文件分析，秒级启动
- **🎯 递归展开**：自动追踪所有内部依赖，直到外部函数边界

### 1.3 解决的痛点

| 痛点 | SimpleAST 方案 |
|------|---------------|
| 不知道需要Mock哪些函数 | 自动生成完整Mock清单 |
| 不清楚内部依赖关系 | 递归展开所有内部函数 |
| 手动追踪调用链费时 | 自动分析并生成独立文件 |
| AI生成测试需多轮对话 | 一次提供完整测试上下文 |

---

## 2. 核心价值

### 2.1 对单元测试的价值

1. **完整测试上下文**：一个函数一个文件，包含所有测试所需信息
2. **自动Mock识别**：递归展开后自动识别所有外部依赖
3. **AI测试生成友好**：提供结构化上下文，一次生成完整测试代码
4. **提高测试覆盖率**：清晰展示内部依赖，避免遗漏测试点

---

## 3. 核心功能

### 3.1 单元测试上下文生成

**功能描述**：为每个函数生成完整的测试上下文，递归展开所有内部依赖，自动识别需要Mock的外部函数。

#### 设计原则

1. **信息完整性**：每个函数文件包含完整测试上下文，无需跨文件查找
2. **接受信息冗余**：不同函数文件可能包含相同依赖信息，但保证独立完整
3. **递归展开**：追踪所有内部依赖链，直到外部函数边界
4. **防止循环依赖**：使用visited集合防止无限递归

#### 输出格式示例

**文件结构**（functions/AddCircle.txt）：
```
[主函数] AddCircle

void ImDrawList::AddCircle(const ImVec2& center, float radius, ImU32 col, int num_segments, float thickness)
位置: imgui_draw.cpp:1584

[统计]
依赖内部函数: 5 个
需要Mock外部函数: 14 个

[Mock清单]
- IM_ARRAYSIZE
- IM_ASSERT_PARANOID
- ImCos
- ImSin
... (共14个)

[内部依赖详情]

>> PathArcTo
void ImDrawList::PathArcTo(const ImVec2& center, float radius, float a_min, float a_max, int num_segments)
imgui_draw.cpp:1267
  调用内部: push_back, _PathArcToN
  调用外部: ImFloor, ImCeil, reserve

>> _CalcCircleAutoSegmentCount
int ImDrawList::_CalcCircleAutoSegmentCount(float radius) const
imgui_draw.cpp:645
  调用外部: IM_ARRAYSIZE

[数据结构]
内部: ImTriangulator, ImTriangulatorNode
外部: ImDrawList, ImU32, ImVec2
```

#### 应用价值

**对AI辅助测试生成的价值**：

| 方面 | 传统手工 | 使用测试上下文 |
|------|---------|---------------|
| 了解依赖 | 需要手动追踪代码 | 自动递归展开 |
| Mock识别 | 容易遗漏外部依赖 | 完整清单自动生成 |
| AI对话轮数 | 5-10轮（补充信息） | 1轮（信息完整） |
| 测试覆盖率 | 容易遗漏边界情况 | 基于完整依赖生成 |

### 3.2 可配置输出目录

**使用方式**：
```bash
# 使用默认输出目录 ./output
python analyze.py . main.cpp

# 自定义输出目录
python analyze.py . main.cpp --output ./test_results
```

**应用场景**：
- CI/CD集成：输出到构建目录
- 多项目分析：不同项目输出到不同目录
- 批量分析：脚本化分析多个文件

---

## 4. 使用场景

### 4.1 AI辅助单元测试生成

**背景**：使用AI工具（如Claude Code、Cursor）为C++函数生成单元测试，需要提供完整的测试上下文。

**操作**：
```bash
# 分析目标文件，生成所有函数的测试上下文
python analyze.py . src/graphics.cpp single 15

# 针对特定函数生成测试上下文
python analyze.py . src/graphics.cpp single 15 DrawCircle --output ./test_context
```

**AI工作流**：
```
1. 开发者运行分析工具
   → 生成 output/_graphics_<timestamp>/functions/DrawCircle.txt

2. 将 DrawCircle.txt 提供给AI
   AI可以获得：
   ✓ 主函数签名和位置
   ✓ 完整Mock清单（所有外部依赖）
   ✓ 所有内部依赖的详细信息
   ✓ 相关数据结构（内部+外部）

3. AI一次性生成完整测试代码：
   - TEST_F fixture定义
   - Mock对象setup
   - 测试用例（正常/边界/异常）
   - 内部依赖的验证逻辑
```

**实际效果示例**：
```cpp
// 输入：functions/AddCircle.txt
// AI输出：

class AddCircleTest : public ::testing::Test {
protected:
    MockImDrawList mock_draw_list;
    MockMath mock_math;  // 从Mock清单生成

    void SetUp() override {
        // 从Mock清单知道需要Mock这些函数
        EXPECT_CALL(mock_math, ImCos(_)).WillRepeatedly(Return(1.0f));
        EXPECT_CALL(mock_math, ImSin(_)).WillRepeatedly(Return(0.0f));
    }
};

TEST_F(AddCircleTest, BasicCircle) {
    ImVec2 center(100, 100);
    float radius = 50.0f;

    // 从函数签名直接生成调用
    AddCircle(center, radius, 0xFF00FF00, 32, 1.0f);

    // 从内部依赖知道会调用 PathArcTo
    ASSERT_EQ(path_size, 32);
}
```

---

## 5. 技术限制

### 5.1 当前限制

| 限制项 | 说明 | 影响 |
|--------|------|------|
| **宏展开** | 不展开宏 | 宏定义的函数无法追踪 |
| **模板实例化** | 不进行模板推导 | 模板函数调用可能缺失 |
| **虚函数** | 无法追踪运行时多态 | 虚函数调用标记为外部 |
| **函数指针** | 无法分析间接调用 | 回调函数不可见 |

### 5.2 适用场景

✅ **适合**：
- 为普通C++函数生成单元测试上下文
- 静态分析函数依赖关系
- Mock清单生成

❌ **不适合**：
- 复杂模板元编程
- 运行时多态分析
- 需要精确类型推导的场景

---

**文档维护者**: SimpleAST Team
**反馈渠道**: GitHub Issues
**更新频率**: 每个版本发布时更新
