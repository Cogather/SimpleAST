"""
数据结构提取器 - 从头文件中读取数据结构定义

原位置：AnalysisResult._try_read_external_data_structure()
"""
import re
import sys
from typing import Optional
from ..searchers import HeaderSearcher


class StructureExtractor:
    """数据结构提取器"""

    def __init__(self, header_searcher: Optional[HeaderSearcher] = None):
        self.header_searcher = header_searcher or HeaderSearcher()

    def extract(self, struct_name: str, target_file: str) -> Optional[str]:
        """
        尝试从头文件中读取外部数据结构的定义

        Args:
            struct_name: 数据结构名称
            target_file: 目标文件路径

        Returns:
            数据结构定义，未找到返回 None
        """
        possible_headers = self.header_searcher.find_headers(target_file)

        for header_file in possible_headers:
            try:
                with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                definition = self._search_struct_by_text(content, struct_name, header_file.name)
                if definition:
                    return definition

            except Exception:
                continue

        return None

    def _search_struct_by_text(self, content: str, struct_name: str, filename: str) -> Optional[str]:
        """用文本搜索查找数据结构定义"""
        lines = content.split('\n')

        # 搜索模式（按优先级）
        patterns = [
            # 1. struct/class 定义: struct Name { 或 struct Name\n{
            (rf'^\s*(struct|class)\s+{re.escape(struct_name)}\s*$', 'struct'),
            (rf'^\s*(struct|class)\s+{re.escape(struct_name)}\s*\{{', 'struct'),

            # 2. typedef: typedef ... Name;
            (rf'^\s*typedef\s+.*\s+{re.escape(struct_name)}\s*;', 'typedef'),

            # 3. using (C++11): using Name = ...;
            (rf'^\s*using\s+{re.escape(struct_name)}\s*=', 'using'),
        ]

        for line_num, line in enumerate(lines):
            for pattern, def_type in patterns:
                match = re.search(pattern, line)
                if match:
                    # 找到了，提取完整定义
                    if def_type == 'typedef' or def_type == 'using':
                        # typedef/using 通常是单行
                        return f"// 来自: {filename}\n{line.strip()}"

                    elif def_type == 'struct':
                        # struct/class 需要找到完整的 body
                        definition_lines = [line]
                        brace_count = line.count('{') - line.count('}')

                        # 如果第一行没有 {，继续找
                        if '{' not in line:
                            for next_line in lines[line_num + 1:line_num + 5]:
                                definition_lines.append(next_line)
                                if '{' in next_line:
                                    brace_count = next_line.count('{') - next_line.count('}')
                                    break

                        # 继续读取直到找到匹配的 }
                        start_idx = line_num + len(definition_lines)
                        for i, next_line in enumerate(lines[start_idx:], start=start_idx):
                            definition_lines.append(next_line)
                            brace_count += next_line.count('{') - next_line.count('}')

                            if brace_count == 0 and '}' in next_line:
                                # 找到结束
                                break

                            # 限制最大行数
                            if len(definition_lines) >= 60:
                                definition_lines.append(f"    // ... (省略剩余部分)")
                                definition_lines.append("};")
                                break

                        definition = '\n'.join(definition_lines)
                        return f"// 来自: {filename}\n{definition}"

        return None
