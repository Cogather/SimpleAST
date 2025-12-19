"""
数据结构搜索器

用于查找 struct、class、typedef、using 等数据结构定义
"""
import re
from typing import Optional
from .grep_searcher import GrepSearcher


class StructureSearcher:
    """数据结构定义搜索器"""

    def __init__(self, project_root: str):
        """
        Args:
            project_root: 项目根目录路径
        """
        self.grep = GrepSearcher(project_root)

    def search(self, struct_name: str) -> Optional[str]:
        """
        搜索数据结构定义

        策略：按优先级依次尝试不同模式，确保找到真实定义而非使用声明

        Args:
            struct_name: 结构体名称（如 'MsgBlock', 'DiamAppMsg'）

        Returns:
            完整的结构体定义文本，未找到返回 None
        """
        # 按优先级依次尝试不同的模式（从最精确到最宽松）
        pattern_groups = self._build_prioritized_patterns(struct_name)

        for priority, patterns in pattern_groups:
            combined = '|'.join(patterns)

            # 搜索所有匹配项
            matches = self.grep.search_content(
                pattern=combined,
                file_glob='*.h',
                max_results=10  # 获取前10个候选
            )

            if not matches:
                continue

            # 筛选最可能是真实定义的匹配项
            best_match = self._select_best_definition(matches, struct_name)
            if best_match:
                file_path, line_num, content = best_match

                # 提取完整定义
                result = self._extract_definition_from_file(
                    file_path, line_num, content, struct_name
                )
                if result:
                    return result

        return None

    def _build_prioritized_patterns(self, struct_name: str) -> list:
        """
        构造按优先级分组的搜索模式

        优先级从高到低：
        1. 完整结构体定义开头（struct/class Name { 或 typedef struct _Name）
        2. typedef 结尾（} Name;）
        3. 单行 typedef
        4. using 语句

        Args:
            struct_name: 结构体名称

        Returns:
            [(优先级, [模式列表]), ...] 列表
        """
        name = re.escape(struct_name)

        return [
            # 优先级1: 最精确 - typedef struct _Name 或 struct Name {
            (1, [
                rf'typedef\s+struct\s+\w*{name}',  # typedef struct _Name 或 typedef struct Name
                rf'(struct|class)\s+{name}\s*\{{',  # struct Name {
            ]),

            # 优先级2: typedef 结尾形式（} Name;）
            (2, [
                rf'\}}\s*\w*,?\s*{name}\s*;',  # } MSG_CB, Name; 或 } Name;
            ]),

            # 优先级3: 单行 typedef 或 using
            (3, [
                rf'typedef\s+\w+\s+{name}\s*;',  # typedef Type Name;
                rf'using\s+{name}\s*=',  # using Name = ...
            ]),
        ]

    def _select_best_definition(self, matches: list, struct_name: str) -> Optional[tuple]:
        """
        从多个匹配项中选择最可能是真实定义的那个

        规则：
        1. 排除明显是变量声明的行（如 Type *var; 或 Type var;）
        2. 优先选择包含 typedef、struct、class 关键字的行
        3. 优先选择包含 { 的行（结构体定义开始）
        4. 优先选择行内容更长的（更可能是完整定义）

        Args:
            matches: [(文件路径, 行号, 内容), ...] 列表
            struct_name: 结构体名称

        Returns:
            最佳匹配 (文件路径, 行号, 内容) 或 None
        """
        if not matches:
            return None

        scored_matches = []
        for file_path, line_num, content in matches:
            score = 0
            content_stripped = content.strip()

            # 规则1: 排除明显是变量声明的行
            # 如果行是 "Type *varname;" 或 "Type varname;" 的形式，且不包含 typedef/struct/class
            if re.match(rf'^\s*{struct_name}\s+[\*&]?\w+\s*[;,]', content_stripped):
                if 'typedef' not in content_stripped and 'struct' not in content_stripped and 'class' not in content_stripped:
                    continue  # 跳过这种变量声明

            # 规则2: 包含关键定义关键字加分
            if 'typedef' in content_stripped:
                score += 100
            if 'struct' in content_stripped or 'class' in content_stripped:
                score += 50
            if 'using' in content_stripped:
                score += 30

            # 规则3: 包含花括号加分（结构体定义开始）
            if '{' in content_stripped:
                score += 80

            # 规则4: 以 } 开头的行（typedef 结尾形式）
            if content_stripped.startswith('}'):
                score += 70

            # 规则5: 行内容长度（更长可能是定义而非声明）
            score += min(len(content_stripped), 100)

            scored_matches.append((score, file_path, line_num, content))

        if not scored_matches:
            return None

        # 按分数降序排序，返回最高分
        scored_matches.sort(key=lambda x: x[0], reverse=True)
        _, best_file, best_line, best_content = scored_matches[0]
        return (best_file, best_line, best_content)

    def _extract_definition_from_file(
        self,
        file_path,
        line_num: int,
        content: str,
        struct_name: str
    ) -> Optional[str]:
        """
        从文件中提取完整的结构体定义

        Args:
            file_path: 文件路径
            line_num: 匹配行号
            content: 匹配行内容
            struct_name: 结构体名称

        Returns:
            完整定义文本或 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            match_idx = line_num - 1
            max_lines = 60

            # 情况1: 匹配行以 } 开头（typedef 结尾形式）
            if content.strip().startswith('}'):
                start_idx = self._find_struct_start_backward(lines, match_idx)
                if start_idx is None:
                    return None

                definition_lines = []
                for i in range(start_idx, match_idx + 1):
                    definition_lines.append(lines[i].rstrip())

                definition = '\n'.join(definition_lines)
                return f"// 来自: {file_path.name}:{start_idx + 1}\n{definition}"

            # 情况2: 匹配行包含 typedef struct 或 struct Name {
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

                definition = '\n'.join(definition_lines)
                return f"// 来自: {file_path.name}:{start_idx + 1}\n{definition}"

        except Exception as e:
            return None

    def _find_struct_start_backward(self, lines: list, end_idx: int) -> Optional[int]:
        """
        从 } Name; 行向上查找 typedef struct 或 struct 的开始

        Args:
            lines: 文件所有行
            end_idx: 结束行索引

        Returns:
            开始行索引或 None
        """
        brace_count = 0
        found_close_brace = False

        for i in range(end_idx, max(0, end_idx - 100), -1):
            line = lines[i]

            if not found_close_brace and '}' in line:
                found_close_brace = True

            # 反向计算括号
            brace_count += line.count('}') - line.count('{')

            # 如果找到匹配的 { 且括号平衡
            if found_close_brace and brace_count == 0 and '{' in line:
                # 继续向上查找 typedef struct 或 struct
                for j in range(i, max(0, i - 5), -1):
                    test_line = lines[j].strip()
                    if test_line.startswith('typedef') or test_line.startswith('struct') or test_line.startswith('class'):
                        return j
                return i

        return None

    def _build_patterns(self, struct_name: str) -> list:
        """
        构造搜索模式

        支持多种定义形式：
        - struct MsgBlock { ... };
        - class MsgBlock { ... };
        - typedef struct { ... } MsgBlock;
        - typedef struct MsgCB { ... } MSG_CB, MsgBlock;
        - using MsgBlock = ...;

        Args:
            struct_name: 结构体名称

        Returns:
            正则表达式模式列表
        """
        name = re.escape(struct_name)

        return [
            # 形式1: struct MsgBlock { 或 struct MsgBlock;
            rf'(struct|class)[[:space:]]+{name}[[:space:]]*[{{;]',

            # 形式2: typedef ... MsgBlock;
            rf'typedef.*[[:space:]]+{name}[[:space:]]*;',

            # 形式3: } MSG_CB, MsgBlock; (typedef 多别名)
            # 使用宽松模式
            rf'}}.*{name}[[:space:]]*;',

            # 形式4: using MsgBlock = ... (C++11)
            rf'using[[:space:]]+{name}[[:space:]]*=',
        ]


# 测试代码
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("用法: python structure_searcher.py <项目根目录> <结构体名称>")
        sys.exit(1)

    project_root = sys.argv[1]
    struct_name = sys.argv[2]

    searcher = StructureSearcher(project_root)
    result = searcher.search(struct_name)

    if result:
        print(f"找到 {struct_name} 的定义：")
        print("=" * 60)
        print(result)
    else:
        print(f"未找到 {struct_name} 的定义")
