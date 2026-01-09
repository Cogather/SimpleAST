#!/usr/bin/env python3
"""
SimpleAST MCP Server 启动脚本

支持 Stdio 和 SSE 两种传输模式
"""
import sys
from mcp_server.server import mcp


def main():
    """启动 MCP 服务器"""
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--sse":
        # SSE 模式
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        print(f"启动 SimpleAST MCP Server (SSE 模式) 在端口 {port}...", file=sys.stderr)
        mcp.run(transport="sse", port=port)
    else:
        # Stdio 模式（默认）
        print("启动 SimpleAST MCP Server (Stdio 模式)...", file=sys.stderr)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
