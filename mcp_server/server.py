"""
FastMCP 服务器入口

使用 FastMCP 框架创建 MCP 服务器
"""
from fastmcp import FastMCP
from .tools import get_function_test_context

# 创建 MCP 服务器实例
mcp = FastMCP("SimpleAST")

# 注册工具
mcp.tool()(get_function_test_context)
