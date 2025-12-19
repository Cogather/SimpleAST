"""
函数签名搜索器

用于在头文件中查找函数声明
"""
import re
from typing import Optional, List, Tuple
from pathlib import Path
from .grep_searcher import GrepSearcher


class SignatureSearcher:
    """函数签名搜索器"""

    def __init__(self, project_root: str):
        """
        Args:
            project_root: 项目根目录路径
        """
        self.grep = GrepSearcher(project_root)

    def search(self, func_name: str) -> Optional[str]:
        """
        搜索函数签名

        Args:
            func_name: 函数名（如 'CheckPidDiamMsg'）

        Returns:
            函数签名文本，未找到返回 None
        """
        # 构造搜索模式（宽松模式，后续过滤）
        pattern = rf'\b{re.escape(func_name)}\s*\('

        # 搜索匹配的内容
        matches = self.grep.search_content(
            pattern=pattern,
            file_glob='*.h',
            max_results=20,
            show_line_numbers=True
        )

        if not matches:
            return None

        # 过滤调用，找到声明
        for file_path, line_num, line_content in matches:
            if self._is_declaration(line_content, func_name):
                # 提取完整签名（可能多行）
                signature = self._extract_signature(file_path, line_num)
                if signature:
                    return f"// 来自: {file_path.name}:{line_num}\n{signature}"

        return None

    def _is_declaration(self, line: str, func_name: str) -> bool:
        """
        判断是否为函数声明（而非调用）

        特征：
        - 行首有返回类型
        - 函数名前面不是 if/while/return/= 等

        Args:
            line: 代码行
            func_name: 函数名

        Returns:
            True 表示可能是声明
        """
        line = line.strip()

        # 排除：明显是调用的情况
        exclude_keywords = ['if', 'while', 'for', 'return', '=', ',', '(', '&&', '||']

        # 找到函数名位置
        idx = line.find(func_name)
        if idx == -1:
            return False

        # 检查前面的内容
        prefix = line[:idx].strip()

        # 如果前面是排除关键字结尾，很可能是调用
        for keyword in exclude_keywords:
            if prefix.endswith(keyword):
                return False

        # 简单启发：如果前面有类型关键字，可能是声明
        type_keywords = ['void', 'int', 'char', 'bool', 'static', 'inline',
                        'const', 'unsigned', 'VOS_', 'DIAM_']
        for keyword in type_keywords:
            if keyword in prefix:
                return True

        return True

    def _extract_signature(self, file_path: Path, start_line: int) -> Optional[str]:
        """
        提取完整函数签名（可能多行）

        Args:
            file_path: 文件路径
            start_line: 开始行号

        Returns:
            完整签名，失败返回 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # 从匹配行开始提取
            start_idx = start_line - 1
            signature_lines = []

            # 最多读取 5 行（函数签名一般不会太长）
            for i in range(start_idx, min(start_idx + 5, len(lines))):
                line = lines[i].rstrip()
                signature_lines.append(line)

                # 如果遇到 ; 或 {，签名结束
                if ';' in line or '{' in line:
                    break

            # 拼接并清理
            signature = '\n'.join(signature_lines)
            signature = self._clean_signature(signature)

            return signature

        except Exception:
            return None

    def _clean_signature(self, signature: str) -> str:
        """
        清理函数签名（移除注释等）

        Args:
            signature: 原始签名

        Returns:
            清理后的签名
        """
        # 移除单行注释
        signature = re.sub(r'//.*', '', signature)

        # 移除多行注释
        signature = re.sub(r'/\*.*?\*/', '', signature, flags=re.DOTALL)

        return signature.strip()


# 测试代码
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("用法: python signature_searcher.py <项目根目录> <函数名>")
        sys.exit(1)

    project_root = sys.argv[1]
    func_name = sys.argv[2]

    searcher = SignatureSearcher(project_root)
    result = searcher.search(func_name)

    if result:
        print(f"找到 {func_name} 的签名：")
        print("=" * 60)
        print(result)
    else:
        print(f"未找到 {func_name} 的签名")
