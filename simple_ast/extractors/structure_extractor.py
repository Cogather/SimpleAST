"""
数据结构提取器 - 从头文件中读取数据结构定义

原位置：AnalysisResult._try_read_external_data_structure()

重构说明：使用 StructureSearcher 进行全局搜索，而不是 HeaderSearcher 的路径遍历
"""
import re
import sys
from typing import Optional
from pathlib import Path


class StructureExtractor:
    """数据结构提取器 - 使用全局搜索"""

    def __init__(self, project_root: str = None):
        """
        Args:
            project_root: 项目根目录，用于全局搜索
        """
        self.project_root = project_root

    def extract(self, struct_name: str, target_file: str) -> Optional[str]:
        """
        尝试从头文件中读取外部数据结构的定义

        策略：
        1. 优先使用 StructureSearcher 全局搜索（准确性优先）
        2. 降级到 HeaderSearcher 路径搜索（兼容性）

        Args:
            struct_name: 数据结构名称
            target_file: 目标文件路径（用于推断项目根目录）

        Returns:
            数据结构定义，未找到返回 None
        """
        # 推断项目根目录
        if not self.project_root:
            # 从 target_file 向上查找，找到包含 .git 或合理的项目根
            target_path = Path(target_file)
            if target_path.is_absolute():
                # 向上找到合适的项目根（简单策略：向上3层）
                self.project_root = str(target_path.parent.parent.parent)
            else:
                self.project_root = "."

        # 尝试使用 StructureSearcher 全局搜索
        try:
            from ..searchers import StructureSearcher

            searcher = StructureSearcher(self.project_root)
            result = searcher.search(struct_name)
            if result:
                return result
        except Exception as e:
            # 如果全局搜索失败，降级到旧方法
            pass

        # 降级：使用 HeaderSearcher 路径搜索（保持兼容性）
        try:
            from ..searchers import HeaderSearcher

            header_searcher = HeaderSearcher()
            possible_headers = header_searcher.find_headers(target_file)

            for header_file in possible_headers:
                try:
                    with open(header_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # 使用绝对路径
                    abs_path = str(header_file.resolve()) if hasattr(header_file, 'resolve') else str(header_file)
                    definition = self._search_struct_by_text(content, struct_name, abs_path)
                    if definition:
                        return definition

                except Exception:
                    continue
        except Exception:
            pass

        return None

    def _search_struct_by_text(self, content: str, struct_name: str, filename: str) -> Optional[str]:
        """用文本搜索查找数据结构定义"""
        lines = content.split('\n')

        # 搜索模式（按优先级）
        patterns = [
            # 1. struct/class 定义: struct Name { 或 struct Name\n{
            (rf'^\s*(struct|class)\s+{re.escape(struct_name)}\s*$', 'struct'),
            (rf'^\s*(struct|class)\s+{re.escape(struct_name)}\s*\{{', 'struct'),

            # 2. typedef 单行: typedef ... Name;
            (rf'^\s*typedef\s+.*\s+{re.escape(struct_name)}\s*;', 'typedef_single'),

            # 3. typedef 多行结尾: } Name; (用于 typedef struct { ... } Name;)
            (rf'\}}\s*\w*,?\s*{re.escape(struct_name)}\s*;', 'typedef_multi'),

            # 4. using (C++11): using Name = ...;
            (rf'^\s*using\s+{re.escape(struct_name)}\s*=', 'using'),
        ]

        for line_num, line in enumerate(lines):
            for pattern, def_type in patterns:
                match = re.search(pattern, line)
                if match:
                    # 找到了，提取完整定义
                    if def_type == 'typedef_single' or def_type == 'using':
                        # typedef/using 通常是单行
                        return f"// 来自: {filename}\n{line.strip()}"

                    elif def_type == 'typedef_multi':
                        # typedef struct { ... } Name; 的结尾行
                        # 需要向上查找 typedef struct 开始
                        definition_lines = []
                        brace_count = 0

                        # 向上查找，找到匹配的 typedef struct {
                        for i in range(line_num, -1, -1):
                            prev_line = lines[i]
                            definition_lines.insert(0, prev_line)

                            # 计算大括号平衡
                            brace_count += prev_line.count('}') - prev_line.count('{')

                            # 如果找到了 typedef 开头且大括号平衡，说明找到了开始
                            if brace_count == 0 and re.match(r'^\s*typedef\s+(struct|union|enum)', prev_line):
                                break

                            # 限制最大向上查找行数
                            if len(definition_lines) >= 60:
                                definition_lines.insert(0, "// ... (省略前面部分)")
                                break

                        definition = '\n'.join(definition_lines)
                        return f"// 来自: {filename}\n{definition}"

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
