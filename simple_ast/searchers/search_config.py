"""
搜索工具配置

支持不同的搜索工具：grep (Git Bash)、ripgrep (rg)
"""
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Optional
from ..logger import get_logger

logger = get_logger()


class SearchTool(Enum):
    """可用的搜索工具"""
    GREP = "grep"           # Git Bash 自带
    RIPGREP = "rg"          # 需要安装 ripgrep
    AUTO = "auto"           # 自动检测


class SearchConfig:
    """搜索配置类"""

    def __init__(self, tool: SearchTool = SearchTool.AUTO):
        """
        Args:
            tool: 指定使用的搜索工具（默认自动检测）
        """
        self.tool = tool
        self.command = None
        self._detect_tool()

    def _detect_tool(self):
        """检测可用的搜索工具"""
        if self.tool == SearchTool.AUTO:
            # 优先使用 ripgrep（更快）
            if self._check_tool_available('rg'):
                self.tool = SearchTool.RIPGREP
                self.command = 'rg'
                logger.info("检测到 ripgrep，使用: rg")
            # 其次使用 grep
            elif self._check_tool_available('grep'):
                self.tool = SearchTool.GREP
                self.command = 'grep'
                logger.info("检测到 grep，使用: grep")
            else:
                raise RuntimeError("未检测到可用的搜索工具 (grep 或 ripgrep)")
        else:
            # 使用指定工具
            cmd = self.tool.value
            if not self._check_tool_available(cmd):
                raise RuntimeError(f"指定的搜索工具不可用: {cmd}")
            self.command = cmd
            logger.info(f"使用指定的搜索工具: {cmd}")

    def _check_tool_available(self, cmd: str) -> bool:
        """
        检查工具是否可用

        Args:
            cmd: 命令名（如 'grep', 'rg'）

        Returns:
            True 表示可用
        """
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def build_search_command(
        self,
        pattern: str,
        path: str,
        file_glob: Optional[str] = None,
        show_files_only: bool = False,
        show_line_numbers: bool = False,
        ignore_case: bool = False
    ) -> list:
        """
        构建搜索命令

        Args:
            pattern: 搜索模式
            path: 搜索路径
            file_glob: 文件匹配模式（如 '*.h'）
            show_files_only: 只显示文件名
            show_line_numbers: 显示行号
            ignore_case: 忽略大小写

        Returns:
            命令列表
        """
        if self.tool == SearchTool.GREP:
            return self._build_grep_command(
                pattern, path, file_glob,
                show_files_only, show_line_numbers, ignore_case
            )
        elif self.tool == SearchTool.RIPGREP:
            return self._build_ripgrep_command(
                pattern, path, file_glob,
                show_files_only, show_line_numbers, ignore_case
            )
        else:
            raise RuntimeError(f"不支持的搜索工具: {self.tool}")

    def _build_grep_command(
        self,
        pattern: str,
        path: str,
        file_glob: Optional[str],
        show_files_only: bool,
        show_line_numbers: bool,
        ignore_case: bool
    ) -> list:
        """构建 grep 命令"""
        cmd = ['grep', '-r', '-E']  # 递归搜索，使用扩展正则表达式

        if show_files_only:
            cmd.append('-l')  # 只显示文件名
        else:
            if show_line_numbers:
                cmd.append('-n')  # 显示行号

        if ignore_case:
            cmd.append('-i')  # 忽略大小写

        if file_glob:
            cmd.append(f'--include={file_glob}')  # 文件过滤

        cmd.append(pattern)
        cmd.append(path)

        return cmd

    def _build_ripgrep_command(
        self,
        pattern: str,
        path: str,
        file_glob: Optional[str],
        show_files_only: bool,
        show_line_numbers: bool,
        ignore_case: bool
    ) -> list:
        """构建 ripgrep 命令"""
        cmd = ['rg']

        if show_files_only:
            cmd.append('-l')  # 只显示文件名
        else:
            if show_line_numbers:
                cmd.append('-n')  # 显示行号（ripgrep 默认显示）

        if ignore_case:
            cmd.append('-i')  # 忽略大小写

        if file_glob:
            cmd.append(f'--glob={file_glob}')  # 文件过滤

        cmd.append(pattern)
        cmd.append(path)

        return cmd


# 全局配置实例
_global_config: Optional[SearchConfig] = None


def get_search_config() -> SearchConfig:
    """
    获取全局搜索配置

    Returns:
        SearchConfig 实例
    """
    global _global_config
    if _global_config is None:
        # 首次调用时创建（自动检测）
        _global_config = SearchConfig(tool=SearchTool.AUTO)
    return _global_config


def set_search_tool(tool: SearchTool):
    """
    设置全局搜索工具

    Args:
        tool: 搜索工具类型
    """
    global _global_config
    _global_config = SearchConfig(tool=tool)


# 测试代码
if __name__ == '__main__':
    print("测试搜索工具配置")
    print("=" * 60)

    # 测试自动检测
    config = SearchConfig(SearchTool.AUTO)
    print(f"自动检测结果: {config.tool.value} -> {config.command}")

    # 测试构建命令
    cmd = config.build_search_command(
        pattern=r'\bMsgBlock\b',
        path='.',
        file_glob='*.h',
        show_files_only=True
    )
    print(f"示例命令: {' '.join(cmd)}")
