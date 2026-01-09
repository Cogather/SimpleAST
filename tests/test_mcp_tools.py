"""
MCP Server 单元测试

测试 MCP 工具的核心功能
"""
import pytest
import asyncio
from pathlib import Path
import json

from mcp_server.tools import get_function_test_context


class TestMCPTools:
    """MCP 工具测试类"""

    @pytest.fixture
    def imgui_project(self):
        """imgui 测试项目 fixture"""
        project_root = "/app/projects/imgui-master"
        if not Path(project_root).exists():
            pytest.skip(f"测试项目不存在: {project_root}")
        return {
            "project_root": project_root,
            "target_file": "backends/imgui_impl_glfw.cpp",
            "function_name": "ImGui_ImplGlfw_InitForOpenGL"
        }

    @pytest.mark.asyncio
    async def test_basic_function_analysis(self, imgui_project):
        """测试基本的函数分析功能"""
        result = await get_function_test_context(
            project_root=imgui_project["project_root"],
            target_file=imgui_project["target_file"],
            function_name=imgui_project["function_name"],
            trace_depth=50
        )

        # 验证没有错误
        assert "error" not in result, f"分析失败: {result.get('error')}"

        # 验证必需字段存在
        assert "function_name" in result
        assert "signature" in result
        assert "location" in result
        assert "source_code" in result
        assert "statistics" in result
        assert "complexity" in result
        assert "mock_list" in result
        assert "internal_dependencies" in result
        assert "data_structures" in result
        assert "call_chain" in result

        # 验证函数名正确
        assert result["function_name"] == imgui_project["function_name"]

        # 验证签名不为空
        assert len(result["signature"]) > 0

        # 验证源代码（可能为空，取决于分析模式）
        assert "source_code" in result

    @pytest.mark.asyncio
    async def test_statistics(self, imgui_project):
        """测试统计信息"""
        result = await get_function_test_context(
            project_root=imgui_project["project_root"],
            target_file=imgui_project["target_file"],
            function_name=imgui_project["function_name"],
            trace_depth=50
        )

        assert "error" not in result
        stats = result["statistics"]

        # 验证统计字段
        assert "internal_functions" in stats
        assert "external_functions" in stats
        assert "data_structures" in stats

        # 验证统计值为非负整数
        assert isinstance(stats["internal_functions"], int)
        assert isinstance(stats["external_functions"], int)
        assert isinstance(stats["data_structures"], int)
        assert stats["internal_functions"] >= 0
        assert stats["external_functions"] >= 0
        assert stats["data_structures"] >= 0

    @pytest.mark.asyncio
    async def test_complexity_analysis(self, imgui_project):
        """测试复杂度分析"""
        result = await get_function_test_context(
            project_root=imgui_project["project_root"],
            target_file=imgui_project["target_file"],
            function_name=imgui_project["function_name"],
            trace_depth=50
        )

        assert "error" not in result
        complexity = result["complexity"]

        # 验证复杂度字段
        assert "cyclomatic" in complexity
        assert "description" in complexity

        # 验证圈复杂度为非负整数
        assert isinstance(complexity["cyclomatic"], int)
        assert complexity["cyclomatic"] >= 0

        # 验证描述不为空
        assert len(complexity["description"]) > 0

    @pytest.mark.asyncio
    async def test_mock_list(self, imgui_project):
        """测试 Mock 清单生成"""
        result = await get_function_test_context(
            project_root=imgui_project["project_root"],
            target_file=imgui_project["target_file"],
            function_name=imgui_project["function_name"],
            trace_depth=50
        )

        assert "error" not in result
        mock_list = result["mock_list"]

        # 验证 Mock 清单是列表
        assert isinstance(mock_list, list)

        # 验证列表中的元素都是字符串
        for func_name in mock_list:
            assert isinstance(func_name, str)
            assert len(func_name) > 0

    @pytest.mark.asyncio
    async def test_internal_dependencies(self, imgui_project):
        """测试内部依赖分析"""
        result = await get_function_test_context(
            project_root=imgui_project["project_root"],
            target_file=imgui_project["target_file"],
            function_name=imgui_project["function_name"],
            trace_depth=50
        )

        assert "error" not in result
        internal_deps = result["internal_dependencies"]

        # 验证内部依赖是列表
        assert isinstance(internal_deps, list)

        # 验证每个依赖的结构
        for dep in internal_deps:
            assert "name" in dep
            assert "signature" in dep
            assert "location" in dep
            assert "source_code" in dep
            assert isinstance(dep["name"], str)
            assert len(dep["name"]) > 0

    @pytest.mark.asyncio
    async def test_json_serialization(self, imgui_project):
        """测试 JSON 序列化"""
        result = await get_function_test_context(
            project_root=imgui_project["project_root"],
            target_file=imgui_project["target_file"],
            function_name=imgui_project["function_name"],
            trace_depth=50
        )

        assert "error" not in result

        # 验证可以序列化为 JSON
        json_str = json.dumps(result)
        assert len(json_str) > 0

        # 验证可以反序列化
        parsed = json.loads(json_str)
        assert parsed["function_name"] == result["function_name"]


class TestMCPErrorHandling:
    """MCP 错误处理测试类"""

    @pytest.mark.asyncio
    async def test_nonexistent_project(self):
        """测试不存在的项目目录"""
        result = await get_function_test_context(
            project_root="/nonexistent/path",
            target_file="test.cpp",
            function_name="TestFunc"
        )

        # 应该返回错误
        assert "error" in result
        assert "项目目录不存在" in result["error"]
        assert result["error_type"] == "PathNotFound"

    @pytest.mark.asyncio
    async def test_nonexistent_file(self):
        """测试不存在的文件"""
        result = await get_function_test_context(
            project_root="/app",
            target_file="nonexistent.cpp",
            function_name="TestFunc"
        )

        # 应该返回错误
        assert "error" in result
        assert "文件不存在" in result["error"]
        assert result["error_type"] == "FileNotFound"

    @pytest.mark.asyncio
    async def test_path_traversal_attack(self):
        """测试路径遍历攻击防护"""
        result = await get_function_test_context(
            project_root="/app",
            target_file="../etc/passwd",
            function_name="TestFunc"
        )

        # 应该被阻止
        assert "error" in result
        assert "非法" in result["error"]
        assert result["error_type"] == "InvalidPath"

    @pytest.mark.asyncio
    async def test_absolute_path_attack(self):
        """测试绝对路径攻击防护"""
        result = await get_function_test_context(
            project_root="/app",
            target_file="/etc/passwd",
            function_name="TestFunc"
        )

        # 应该被阻止
        assert "error" in result
        assert "非法" in result["error"]
        assert result["error_type"] == "InvalidPath"

    @pytest.mark.asyncio
    async def test_nonexistent_function(self):
        """测试不存在的函数"""
        # 使用存在的项目和文件，但不存在的函数
        project_root = "/app/projects/imgui-master"
        if not Path(project_root).exists():
            pytest.skip(f"测试项目不存在: {project_root}")

        result = await get_function_test_context(
            project_root=project_root,
            target_file="backends/imgui_impl_glfw.cpp",
            function_name="NonExistentFunction12345",
            trace_depth=50
        )

        # 应该返回错误
        assert "error" in result
        assert "未找到" in result["error"]


class TestMCPEdgeCases:
    """MCP 边界情况测试类"""

    @pytest.mark.asyncio
    async def test_zero_trace_depth(self):
        """测试追踪深度为 0"""
        project_root = "/app/projects/imgui-master"
        if not Path(project_root).exists():
            pytest.skip(f"测试项目不存在: {project_root}")

        result = await get_function_test_context(
            project_root=project_root,
            target_file="backends/imgui_impl_glfw.cpp",
            function_name="ImGui_ImplGlfw_InitForOpenGL",
            trace_depth=0
        )

        # 深度为 0 可能导致无法追踪，这是预期行为
        # 只要不崩溃就算通过
        assert "function_name" in result or "error" in result

    @pytest.mark.asyncio
    async def test_large_trace_depth(self):
        """测试很大的追踪深度"""
        project_root = "/app/projects/imgui-master"
        if not Path(project_root).exists():
            pytest.skip(f"测试项目不存在: {project_root}")

        result = await get_function_test_context(
            project_root=project_root,
            target_file="backends/imgui_impl_glfw.cpp",
            function_name="ImGui_ImplGlfw_InitForOpenGL",
            trace_depth=1000
        )

        # 应该成功
        assert "error" not in result
        assert "function_name" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
