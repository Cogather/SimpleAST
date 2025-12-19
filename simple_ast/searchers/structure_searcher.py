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

        Args:
            struct_name: 结构体名称（如 'MsgBlock', 'DiamAppMsg'）

        Returns:
            完整的结构体定义文本，未找到返回 None
        """
        # 构造搜索模式
        patterns = self._build_patterns(struct_name)
        combined = '|'.join(patterns)

        # 使用 grep 搜索并提取多行定义
        result = self.grep.extract_multiline_definition(
            start_pattern=combined,
            struct_name=struct_name,
            file_glob='*.h',
            max_lines=60
        )

        return result

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
