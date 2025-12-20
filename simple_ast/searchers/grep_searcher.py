"""
基于 grep 命令的搜索器

使用系统的 grep 命令（Git Bash 自带）或 ripgrep 进行快速文本搜索
"""
import subprocess
import re
import tempfile
import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import sys
from .search_config import get_search_config
from ..logger import get_logger

logger = get_logger()


class GrepSearcher:
    """基于 grep/ripgrep 命令的通用搜索器"""

    def __init__(self, project_root: str):
        """
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root).resolve()
        self.config = get_search_config()  # 获取全局配置

    def search_files(
        self,
        pattern: str,
        file_glob: str = '*.h',
        max_results: int = 10,
        ignore_case: bool = False
    ) -> List[Path]:
        """
        搜索包含指定模式的文件

        Args:
            pattern: 正则表达式模式
            file_glob: 文件匹配模式（如 '*.h', '*.cpp'）
            max_results: 最多返回文件数
            ignore_case: 是否忽略大小写

        Returns:
            匹配的文件路径列表
        """
        # 使用配置构建命令
        cmd = self.config.build_search_command(
            pattern=pattern,
            path=str(self.project_root),
            file_glob=file_glob,
            show_files_only=True,
            ignore_case=ignore_case
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='ignore'  # 忽略编码错误
            )

            if result.returncode == 0:
                files = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
                return files[:max_results]
            else:
                # returncode = 1 表示没找到，2 表示错误
                if result.returncode == 1:
                    return []  # 没找到
                else:
                    logger.error(f"grep错误: {result.stderr}")
                    return []

        except subprocess.TimeoutExpired:
            logger.error(f"grep超时: 搜索 {pattern} 超时")
            return []
        except Exception as e:
            logger.error(f"grep异常: {e}")
            return []

    def search_content(
        self,
        pattern: str,
        file_glob: str = '*.h',
        max_results: int = 10,
        show_line_numbers: bool = True,
        context_lines: int = 0
    ) -> List[Tuple[Path, int, str]]:
        """
        搜索匹配的内容（带行号）

        Args:
            pattern: 正则表达式模式
            file_glob: 文件匹配模式
            max_results: 最多返回结果数
            show_line_numbers: 是否显示行号
            context_lines: 上下文行数（0 表示不显示上下文）

        Returns:
            列表：[(文件路径, 行号, 匹配的行内容), ...]
        """
        # 使用脚本文件方式执行，避免参数传递问题
        return self._search_via_script(
            pattern=pattern,
            file_glob=file_glob,
            max_results=max_results,
            show_line_numbers=show_line_numbers
        )

    def search_content_batch(
        self,
        patterns: List[str],
        file_glob: str = '*.h',
        max_results_per_pattern: int = 10
    ) -> Dict[str, List[Tuple[Path, int, str]]]:
        """
        批量搜索多个模式（性能优化版本）

        Args:
            patterns: 正则表达式模式列表
            file_glob: 文件匹配模式
            max_results_per_pattern: 每个模式最多返回结果数

        Returns:
            字典：{pattern: [(文件路径, 行号, 匹配的行内容), ...], ...}
        """
        if not patterns:
            return {}

        try:
            # 根据操作系统选择脚本类型
            is_windows = sys.platform == 'win32'
            suffix = '.bat' if is_windows else '.sh'

            # 创建临时脚本文件
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=suffix,
                delete=False,
                encoding='utf-8'
            ) as script_file:
                script_path = script_file.name

                # 构建批量搜索命令
                if self.config.command == 'rg':
                    # ripgrep 支持多个 -e 参数
                    pattern_args = ' '.join([f'-e "{p}"' for p in patterns])
                    cmd = f'rg -n --glob="{file_glob}" {pattern_args} "{self.project_root}"'
                elif self.config.command == 'grep':
                    # grep 使用 -e 参数
                    pattern_args = ' '.join([f'-e "{p}"' for p in patterns])
                    cmd = f'grep -r -E -n --include="{file_glob}" {pattern_args} "{self.project_root}"'
                else:
                    return {}

                # 写入脚本
                if is_windows:
                    script_file.write('@echo off\n')
                    script_file.write('chcp 65001 >nul\n')
                    script_file.write(cmd + '\n')
                else:
                    script_file.write('#!/bin/bash\n')
                    script_file.write(cmd + '\n')

            # 执行脚本
            if is_windows:
                result = subprocess.run(
                    [script_path],
                    capture_output=True,
                    text=True,
                    timeout=60,  # 批量搜索可能需要更长时间
                    encoding='utf-8',
                    errors='ignore',
                    shell=True
                )
            else:
                result = subprocess.run(
                    ['bash', script_path],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    encoding='utf-8',
                    errors='ignore'
                )

            # 删除临时脚本
            try:
                os.unlink(script_path)
            except:
                pass

            if result.returncode != 0 and result.returncode != 1:
                logger.error(f"批量搜索错误: {result.stderr}")
                return {}

            # 解析输出并按模式分组
            results_by_pattern = {p: [] for p in patterns}

            for line in result.stdout.splitlines():
                parsed = self._parse_grep_line(line)
                if not parsed:
                    continue

                file_path, line_num, content = parsed

                # 判断这行匹配哪个模式
                for pattern in patterns:
                    try:
                        if re.search(pattern, content):
                            if len(results_by_pattern[pattern]) < max_results_per_pattern:
                                results_by_pattern[pattern].append((file_path, line_num, content))
                    except re.error:
                        continue

            return results_by_pattern

        except Exception as e:
            logger.error(f"批量搜索异常: {e}")
            return {}

    def _search_via_script(
        self,
        pattern: str,
        file_glob: str,
        max_results: int,
        show_line_numbers: bool
    ) -> List[Tuple[Path, int, str]]:
        """
        通过临时脚本文件执行搜索，避免参数传递和转义问题

        Args:
            pattern: 搜索模式
            file_glob: 文件通配符
            max_results: 最大结果数
            show_line_numbers: 是否显示行号

        Returns:
            匹配结果列表
        """
        try:
            # 根据操作系统选择脚本类型
            is_windows = sys.platform == 'win32'
            suffix = '.bat' if is_windows else '.sh'

            # 创建临时脚本文件
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix=suffix,
                delete=False,
                encoding='utf-8'
            ) as script_file:
                script_path = script_file.name

                # 根据工具类型构建命令
                if self.config.command == 'grep':
                    cmd = f'grep -r -E -n --include="{file_glob}" "{pattern}" "{self.project_root}"'
                elif self.config.command == 'rg':
                    cmd = f'rg -n --glob="{file_glob}" "{pattern}" "{self.project_root}"'
                else:
                    return []

                # 写入脚本
                if is_windows:
                    # Windows 批处理脚本
                    script_file.write('@echo off\n')
                    script_file.write('chcp 65001 >nul\n')  # 设置 UTF-8 编码
                    script_file.write(cmd + '\n')
                else:
                    # Linux/Mac bash 脚本
                    script_file.write('#!/bin/bash\n')
                    script_file.write(cmd + '\n')

            # 执行脚本
            if is_windows:
                # Windows 上直接执行批处理文件
                result = subprocess.run(
                    [script_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding='utf-8',
                    errors='ignore',
                    shell=True
                )
            else:
                # Linux/Mac 上使用 bash 执行
                result = subprocess.run(
                    ['bash', script_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding='utf-8',
                    errors='ignore'
                )

            # 删除临时脚本
            try:
                os.unlink(script_path)
            except:
                pass

            if result.returncode != 0 and result.returncode != 1:
                # returncode=1 表示没找到（正常），其他非0是错误
                logger.error(f"搜索错误: {result.stderr}")
                return []

            # 解析输出
            matches = []
            for line in result.stdout.splitlines()[:max_results]:
                parsed = self._parse_grep_line(line)
                if parsed:
                    matches.append(parsed)

            return matches

        except Exception as e:
            logger.error(f"脚本搜索异常: {e}")
            return []

    def _parse_grep_line(self, line: str) -> Optional[Tuple[Path, int, str]]:
        """
        解析 grep 输出的一行

        Args:
            line: grep 输出行

        Returns:
            (文件路径, 行号, 内容) 或 None
        """
        # Windows路径处理：检查是否以盘符开头 (如 D:\)
        if len(line) > 2 and line[1] == ':' and line[2] in ('\\', '/'):
            # Windows绝对路径，找第3个冒号(文件路径后的冒号)
            # 格式: D:\path\file.h:123:content
            colon_positions = [i for i, c in enumerate(line) if c == ':']
            if len(colon_positions) >= 2:
                # 第一个冒号是盘符，第二个是行号前，第三个（如果有）是content前
                file_path_end = colon_positions[1]
                file_path = Path(line[:file_path_end])

                remaining = line[file_path_end + 1:]  # 跳过第二个冒号
                parts = remaining.split(':', 1)  # 分成 line_num 和 content

                if len(parts) >= 2:
                    try:
                        line_num = int(parts[0])
                        content = parts[1]
                        return (file_path, line_num, content)
                    except ValueError:
                        pass
        else:
            # Unix路径或相对路径，使用原有逻辑
            parts = line.split(':', 2)
            if len(parts) >= 3:
                file_path = Path(parts[0])
                try:
                    line_num = int(parts[1])
                    content = parts[2]
                    return (file_path, line_num, content)
                except ValueError:
                    pass

        return None

    def search_content_old(
        self,
        pattern: str,
        file_glob: str = '*.h',
        max_results: int = 10,
        show_line_numbers: bool = True,
        context_lines: int = 0
    ) -> List[Tuple[Path, int, str]]:
        """
        搜索匹配的内容（带行号）- 原始方法（保留作为备份）

        Args:
            pattern: 正则表达式模式
            file_glob: 文件匹配模式
            max_results: 最多返回结果数
            show_line_numbers: 是否显示行号
            context_lines: 上下文行数（0 表示不显示上下文）

        Returns:
            列表：[(文件路径, 行号, 匹配的行内容), ...]
        """
        # 使用配置构建命令
        cmd = self.config.build_search_command(
            pattern=pattern,
            path=str(self.project_root),
            file_glob=file_glob,
            show_files_only=False,
            show_line_numbers=show_line_numbers
        )

        # 添加上下文行数（如果需要）
        if context_lines > 0:
            if self.config.command == 'grep':
                cmd.insert(-2, f'-C{context_lines}')
            elif self.config.command == 'rg':
                cmd.insert(-2, f'-C{context_lines}')

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='ignore'
            )

            if result.returncode != 0:
                return []

            # 解析输出: file.h:123:content
            # 注意：Windows路径包含盘符冒号(如 D:\path)，需要特殊处理
            matches = []
            for line in result.stdout.splitlines()[:max_results]:
                # Windows路径处理：检查是否以盘符开头 (如 D:\)
                if len(line) > 2 and line[1] == ':' and line[2] in ('\\', '/'):
                    # Windows绝对路径，找第3个冒号(文件路径后的冒号)
                    # 格式: D:\path\file.h:123:content
                    colon_positions = [i for i, c in enumerate(line) if c == ':']
                    if len(colon_positions) >= 2:
                        # 第一个冒号是盘符，第二个是行号前，第三个（如果有）是content前
                        file_path_end = colon_positions[1]
                        file_path = Path(line[:file_path_end])

                        remaining = line[file_path_end + 1:]  # 跳过第二个冒号
                        parts = remaining.split(':', 1)  # 分成 line_num 和 content

                        if len(parts) >= 2:
                            try:
                                line_num = int(parts[0])
                                content = parts[1]
                                matches.append((file_path, line_num, content))
                            except ValueError:
                                pass
                else:
                    # Unix路径或相对路径，使用原有逻辑
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        file_path = Path(parts[0])
                        try:
                            line_num = int(parts[1])
                            content = parts[2]
                            matches.append((file_path, line_num, content))
                        except ValueError:
                            continue

            return matches

        except Exception as e:
            logger.error(f"grep异常: {e}")
            return []

    def search_first_match(
        self,
        pattern: str,
        file_glob: str = '*.h'
    ) -> Optional[Tuple[Path, int]]:
        """
        搜索第一个匹配（最快）

        Args:
            pattern: 正则表达式模式
            file_glob: 文件匹配模式

        Returns:
            (文件路径, 行号) 或 None
        """
        matches = self.search_content(pattern, file_glob, max_results=1)
        if matches:
            file_path, line_num, _ = matches[0]
            return (file_path, line_num)
        return None

    def extract_multiline_definition(
        self,
        start_pattern: str,
        struct_name: str,
        file_glob: str = '*.h',
        max_lines: int = 60
    ) -> Optional[str]:
        """
        提取多行定义（如结构体定义）

        Args:
            start_pattern: 开始行的匹配模式
            struct_name: 结构体名称（用于验证）
            file_glob: 文件匹配模式
            max_lines: 最多提取行数

        Returns:
            完整定义文本，未找到返回 None
        """
        # 1. 找到第一个匹配的文件和行号
        first_match = self.search_first_match(start_pattern, file_glob)
        if not first_match:
            return None

        file_path, match_line = first_match

        # 2. 读取文件，提取完整定义
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # 检查匹配行的内容
            match_idx = match_line - 1
            match_content = lines[match_idx].strip()

            # 情况1: 匹配行是 } MSG_CB, MsgBlock; 形式（typedef 结尾）
            # 需要向上查找 typedef struct 的开始
            if match_content.startswith('}'):
                # 向上查找 typedef struct 或 struct 开始
                start_idx = self._find_struct_start(lines, match_idx)
                if start_idx is None:
                    return None

                # 提取从开始到结束
                definition_lines = []
                for i in range(start_idx, match_idx + 1):
                    definition_lines.append(lines[i].rstrip())

                definition = '\n'.join(definition_lines)
                return f"// 来自: {file_path.name}:{start_idx + 1}\n{definition}"

            # 情况2: 匹配行是 struct MsgBlock { 形式
            # 向下查找结束
            else:
                start_idx = match_idx
                definition_lines = []
                brace_count = 0
                found_brace = False

                for i in range(start_idx, min(start_idx + max_lines, len(lines))):
                    line = lines[i]
                    definition_lines.append(line.rstrip())

                    # 计算花括号
                    brace_count += line.count('{') - line.count('}')
                    if '{' in line:
                        found_brace = True

                    # 如果找到了开始的 { 且括号匹配完成
                    if found_brace and brace_count == 0 and '}' in line:
                        break

                    # 或者遇到分号（单行 typedef）
                    if not found_brace and ';' in line:
                        break

                    # 安全限制
                    if len(definition_lines) >= max_lines:
                        definition_lines.append("    // ... (定义过长，已截断)")
                        break

                # 格式化输出
                definition = '\n'.join(definition_lines)
                return f"// 来自: {file_path.name}:{start_idx + 1}\n{definition}"

        except Exception as e:
            logger.error(f"文件读取错误 {file_path}: {e}")
            return None

    def _find_struct_start(self, lines: list, end_idx: int) -> Optional[int]:
        """
        从结束行向上查找 struct/typedef 定义的开始

        Args:
            lines: 文件所有行
            end_idx: 结束行索引（} MSG_CB, MsgBlock; 所在行）

        Returns:
            开始行索引，未找到返回 None
        """
        brace_count = 0
        found_close_brace = False

        # 从结束行向上查找
        for i in range(end_idx, max(0, end_idx - 100), -1):
            line = lines[i]

            # 首先处理当前行
            if not found_close_brace and '}' in line:
                found_close_brace = True

            # 反向计算括号（向上走时，} 增加计数，{ 减少计数）
            brace_count += line.count('}') - line.count('{')

            # 如果找到了匹配的 { 且括号平衡
            if found_close_brace and brace_count == 0 and '{' in line:
                # 继续向上查找 typedef struct 或 struct
                for j in range(i, max(0, i - 5), -1):
                    test_line = lines[j].strip()
                    if test_line.startswith('typedef') or test_line.startswith('struct') or test_line.startswith('class'):
                        return j

                # 如果没找到 typedef，返回 { 所在行
                return i

        return None


# 测试代码
if __name__ == '__main__':
    # 简单测试
    searcher = GrepSearcher('.')

    print("测试1: 搜索文件")
    files = searcher.search_files(r'\bMsgBlock\b', '*.h', max_results=3)
    for f in files:
        print(f"  {f}")

    print("\n测试2: 搜索内容")
    matches = searcher.search_content(r'typedef.*MsgBlock', '*.h', max_results=3)
    for file_path, line_num, content in matches:
        print(f"  {file_path.name}:{line_num}: {content}")

    print("\n测试3: 提取定义")
    definition = searcher.extract_multiline_definition(
        r'typedef.*MsgBlock',
        'MsgBlock',
        '*.h'
    )
    if definition:
        print(definition)
