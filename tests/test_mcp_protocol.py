"""
MCP 协议集成测试

测试完整的 MCP 协议通信
"""
import pytest
import asyncio
import json
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


@pytest.mark.skipif(not MCP_AVAILABLE, reason="MCP SDK 未安装")
class TestMCPProtocol:
    """MCP 协议测试类"""

    @pytest.fixture
    def server_params(self):
        """服务器参数 fixture"""
        return StdioServerParameters(
            command="python",
            args=["/app/mcp_server.py"],
            env=None
        )

    @pytest.fixture
    def imgui_params(self):
        """imgui 测试参数 fixture"""
        project_root = "/app/projects/imgui-master"
        if not Path(project_root).exists():
            pytest.skip(f"测试项目不存在: {project_root}")
        return {
            "project_root": project_root,
            "target_file": "backends/imgui_impl_glfw.cpp",
            "function_name": "ImGui_ImplGlfw_InitForOpenGL"
        }

    @pytest.mark.asyncio
    async def test_server_connection(self, server_params):
        """测试服务器连接"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # 连接成功
                assert session is not None

    @pytest.mark.asyncio
    async def test_list_tools(self, server_params):
        """测试列出工具"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()

                # 验证工具列表
                assert len(tools.tools) > 0
                assert tools.tools[0].name == "get_function_test_context"

    @pytest.mark.asyncio
    async def test_tool_schema(self, server_params):
        """测试工具 Schema"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()

                tool = tools.tools[0]

                # 验证工具名称和描述
                assert tool.name == "get_function_test_context"
                assert len(tool.description) > 0

                # 验证 Schema
                if hasattr(tool, 'inputSchema'):
                    schema = tool.inputSchema
                    assert schema.get('type') == 'object'
                    assert 'properties' in schema
                    assert 'required' in schema

                    # 验证必需参数
                    required = schema['required']
                    assert 'project_root' in required
                    assert 'target_file' in required
                    assert 'function_name' in required

    @pytest.mark.asyncio
    async def test_call_tool_success(self, server_params, imgui_params):
        """测试成功调用工具"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get_function_test_context",
                    arguments={
                        "project_root": imgui_params["project_root"],
                        "target_file": imgui_params["target_file"],
                        "function_name": imgui_params["function_name"],
                        "trace_depth": 50
                    }
                )

                # 验证返回结果
                assert result.content is not None
                assert len(result.content) > 0

                content = result.content[0]
                assert hasattr(content, 'text')

                data = json.loads(content.text)
                assert "error" not in data
                assert data["function_name"] == imgui_params["function_name"]

    @pytest.mark.asyncio
    async def test_call_tool_error(self, server_params):
        """测试工具调用错误处理"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get_function_test_context",
                    arguments={
                        "project_root": "/nonexistent/path",
                        "target_file": "test.cpp",
                        "function_name": "TestFunc"
                    }
                )

                # 验证错误返回
                assert result.content is not None
                content = result.content[0]
                data = json.loads(content.text)

                assert "error" in data
                assert "项目目录不存在" in data["error"]

    @pytest.mark.asyncio
    async def test_path_traversal_protection(self, server_params):
        """测试路径遍历防护"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "get_function_test_context",
                    arguments={
                        "project_root": "/app",
                        "target_file": "../etc/passwd",
                        "function_name": "TestFunc"
                    }
                )

                content = result.content[0]
                data = json.loads(content.text)

                assert "error" in data
                assert "非法" in data["error"]

    @pytest.mark.asyncio
    async def test_multiple_calls(self, server_params, imgui_params):
        """测试多次调用"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 第一次调用
                result1 = await session.call_tool(
                    "get_function_test_context",
                    arguments={
                        "project_root": imgui_params["project_root"],
                        "target_file": imgui_params["target_file"],
                        "function_name": imgui_params["function_name"],
                        "trace_depth": 50
                    }
                )

                data1 = json.loads(result1.content[0].text)
                assert "error" not in data1

                # 第二次调用
                result2 = await session.call_tool(
                    "get_function_test_context",
                    arguments={
                        "project_root": imgui_params["project_root"],
                        "target_file": imgui_params["target_file"],
                        "function_name": imgui_params["function_name"],
                        "trace_depth": 50
                    }
                )

                data2 = json.loads(result2.content[0].text)
                assert "error" not in data2

                # 验证两次结果一致
                assert data1["function_name"] == data2["function_name"]
                assert data1["signature"] == data2["signature"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
