"""
常量/宏定义搜索器

用于查找 #define、enum、const 等常量定义
"""
import re
from typing import Optional
from .grep_searcher import GrepSearcher


class ConstantSearcher:
    """常量/宏定义搜索器"""

    def __init__(self, project_root: str):
        """
        Args:
            project_root: 项目根目录路径
        """
        self.grep = GrepSearcher(project_root)

    def search(self, const_name: str) -> Optional[str]:
        """
        搜索常量定义

        Args:
            const_name: 常量名（如 'PID_DIAM', 'DIAM_SUCCESS'）

        Returns:
            常量定义文本，未找到返回 None
        """
        # 构造搜索模式
        patterns = self._build_patterns(const_name)
        combined = '|'.join(patterns)

        # 搜索匹配的内容
        matches = self.grep.search_content(
            pattern=combined,
            file_glob='*.h',
            max_results=5,
            show_line_numbers=True
        )

        if not matches:
            return None

        # 返回第一个匹配（常量定义一般只有一个）
        file_path, line_num, content = matches[0]

        # 如果是 enum 成员，可能需要提取更多上下文
        if self._is_enum_member(content):
            return self._extract_enum_context(file_path, line_num, const_name)
        else:
            return f"// 来自: {file_path.name}:{line_num}\n{content.strip()}"

    def _build_patterns(self, const_name: str) -> list:
        """
        构造搜索模式

        支持多种定义形式：
        - #define PID_DIAM 306
        - #define GET_MSG_LEN(x) (...)
        - PID_DIAM = 306, (enum 成员)
        - const int PID_DIAM = 306;
        - constexpr int PID_DIAM = 306;

        Args:
            const_name: 常量名

        Returns:
            正则表达式模式列表
        """
        name = re.escape(const_name)

        return [
            # 形式1: #define PID_DIAM 或 #define GET_MSG(x)
            rf'^[[:space:]]*#define[[:space:]]+{name}([[:space:](]|$)',

            # 形式2: PID_DIAM = 306 (enum 成员或赋值)
            rf'^[[:space:]]*{name}[[:space:]]*=',

            # 形式3: const int PID_DIAM = 306;
            rf'^[[:space:]]*(const|constexpr)[[:space:]]+[[:alnum:]_]+[[:space:]]+{name}[[:space:]]*=',
        ]

    def _is_enum_member(self, line: str) -> bool:
        """
        判断是否为 enum 成员

        Args:
            line: 代码行

        Returns:
            True 表示可能是 enum 成员
        """
        # 简单启发：没有 # 且有 = 且没有分号结尾
        line = line.strip()
        return '=' in line and not line.startswith('#') and not line.endswith(';')

    def _extract_enum_context(self, file_path, line_num: int, const_name: str) -> Optional[str]:
        """
        提取 enum 上下文（可选：提取整个 enum 定义）

        当前实现：只返回该行

        Args:
            file_path: 文件路径
            line_num: 行号
            const_name: 常量名

        Returns:
            带上下文的定义
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            line = lines[line_num - 1].strip()
            return f"// 来自: {file_path.name}:{line_num}\n{line}"

        except Exception:
            return None


# 测试代码
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("用法: python constant_searcher.py <项目根目录> <常量名>")
        sys.exit(1)

    project_root = sys.argv[1]
    const_name = sys.argv[2]

    searcher = ConstantSearcher(project_root)
    result = searcher.search(const_name)

    if result:
        print(f"找到 {const_name} 的定义：")
        print("=" * 60)
        print(result)
    else:
        print(f"未找到 {const_name} 的定义")
