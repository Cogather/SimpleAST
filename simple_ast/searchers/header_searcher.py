"""
头文件搜索器 - 统一的头文件查找策略

消除原有的三处重复代码：
- _extract_constants_from_function() 中的头文件搜索
- _search_function_signature() 中的头文件搜索
- _try_read_external_data_structure() 中的头文件搜索
"""
from pathlib import Path
from typing import List


class HeaderSearcher:
    """头文件搜索器 - 简单实用，不过度设计"""

    def __init__(self, max_files: int = 50, max_depth: int = 3):
        """
        Args:
            max_files: 最多搜索的文件数量
            max_depth: 向上搜索的最大层级
        """
        self.max_files = max_files
        self.max_depth = max_depth

    def find_headers(self, target_file: str) -> List[Path]:
        """
        查找所有相关的头文件

        搜索策略：
        1. 当前 .cpp 文件本身（枚举可能在文件内部）
        2. 同目录的同名 .h 文件
        3. 同目录的所有 .h 文件
        4. 向上搜索 include/ 目录（最多3层）
           - 保持子目录结构（source/diam -> include/diam）
           - include 根目录
           - include 下所有子目录（递归）

        Args:
            target_file: 目标源文件路径

        Returns:
            头文件路径列表（去重，限制数量）
        """
        target_path = Path(target_file)
        headers = []

        # 1. 当前文件本身
        headers.append(target_path)

        # 2. 同目录同名头文件
        header_same_name = target_path.with_suffix('.h')
        if header_same_name.exists():
            headers.append(header_same_name)

        # 3. 同目录所有头文件
        header_dir = target_path.parent
        if header_dir.exists():
            for h_file in header_dir.glob('*.h'):
                if h_file not in headers:
                    headers.append(h_file)

        # 4. 搜索 include 目录（向上最多 max_depth 层）
        current_dir = target_path.parent
        for _ in range(self.max_depth):
            include_dir = current_dir.parent / 'include'

            if include_dir.exists():
                # 保持相同的子目录结构
                # 如: common/source/diam -> common/include/diam
                rel_path = current_dir.relative_to(current_dir.parent) if current_dir.parent else None
                if rel_path:
                    sub_include_dir = include_dir / rel_path.name
                    if sub_include_dir.exists():
                        for h_file in sub_include_dir.glob('*.h'):
                            if h_file not in headers:
                                headers.append(h_file)

                # include 根目录
                for h_file in include_dir.glob('*.h'):
                    if h_file not in headers:
                        headers.append(h_file)

                # 递归搜索 include 下的所有子目录
                for h_file in include_dir.rglob('*.h'):
                    if h_file not in headers:
                        headers.append(h_file)

            # 向上一层
            current_dir = current_dir.parent
            if current_dir == current_dir.parent:
                break

        # 去重并限制数量
        return headers[:self.max_files]
