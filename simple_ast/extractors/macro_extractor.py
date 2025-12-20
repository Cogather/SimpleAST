"""
宏定义展开提取器

功能：
1. 搜索宏定义
2. 展开多行宏定义
3. 处理宏的嵌套引用
"""
import re
from typing import Dict, Optional, Set
from ..searchers import GrepSearcher
from ..logger import get_logger

logger = get_logger()


class MacroExtractor:
    """宏定义展开提取器"""

    def __init__(self, project_root: str):
        """
        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root
        self.grep_searcher = GrepSearcher(project_root=project_root)
        self._macro_cache: Dict[str, str] = {}  # 缓存已查找的宏

    def extract_macro_definition(self, macro_name: str, context_file: str = None) -> Optional[str]:
        """
        提取宏的完整定义

        Args:
            macro_name: 宏名称（可能包含参数，如 "GET_DOPRA_MSG_LEN(msgPtr)"）
            context_file: 上下文文件路径（用于日志）

        Returns:
            完整的宏定义，如果未找到返回None
        """
        # 提取纯宏名（去掉参数）
        pure_macro_name = macro_name.split('(')[0].strip()

        # 检查缓存
        if pure_macro_name in self._macro_cache:
            logger.debug(f"[宏展开] {pure_macro_name}: 使用缓存")
            return self._macro_cache[pure_macro_name]

        logger.info(f"[宏展开] 开始搜索宏: {pure_macro_name}")

        # 搜索宏定义
        # 宏定义模式：#define MACRO_NAME ...
        pattern = rf'^\s*#\s*define\s+{re.escape(pure_macro_name)}\b'

        try:
            # 使用 search_content 方法
            # 搜索所有C/C++头文件和源文件
            results = self.grep_searcher.search_content(
                pattern=pattern,
                file_glob='*',  # 搜索所有文件
                max_results=5  # 最多返回5个结果
            )

            if not results:
                logger.info(f"[宏展开] 未找到宏定义: {pure_macro_name}")
                return None

            # results 是 (file_path, line_num, content) 的列表
            if not isinstance(results, list) or len(results) == 0:
                return None

            # 获取第一个匹配
            file_path, line_num, content = results[0]
            logger.info(f"[宏展开] 找到宏定义: {file_path}:{line_num}")

            # 提取宏定义内容
            macro_def = self._extract_macro_content(content)

            # 检查是否是多行宏（以反斜杠结尾）
            if macro_def and macro_def.rstrip().endswith('\\'):
                # 读取完整的多行宏定义
                macro_def = self._read_multiline_macro(str(file_path), int(line_num))

            # 缓存结果
            if macro_def:
                self._macro_cache[pure_macro_name] = macro_def
                logger.info(f"[宏展开] ✓ {pure_macro_name}: 提取成功")

            return macro_def

        except Exception as e:
            logger.error(f"[宏展开] 搜索宏定义失败: {e}")
            return None

    def _extract_macro_content(self, define_line: str) -> Optional[str]:
        """
        从 #define 行中提取宏定义内容

        Args:
            define_line: #define 行内容

        Returns:
            宏定义内容（不含#define关键字）
        """
        # 匹配 #define 行
        # 格式: #define MACRO_NAME value 或 #define MACRO_NAME(params) body
        match = re.match(r'^\s*#\s*define\s+(\w+)(\([^)]*\))?\s*(.*?)$', define_line)
        if not match:
            return None

        macro_name, params, body = match.groups()

        # 构建完整定义
        if params:
            # 函数宏
            return f"#define {macro_name}{params} {body}".strip()
        else:
            # 对象宏
            return f"#define {macro_name} {body}".strip()

    def _read_multiline_macro(self, file_path: str, start_line: int) -> Optional[str]:
        """
        读取多行宏定义

        Args:
            file_path: 文件路径
            start_line: 起始行号（1-based）

        Returns:
            完整的多行宏定义
        """
        try:
            from pathlib import Path
            full_path = Path(self.project_root) / file_path

            if not full_path.exists():
                # 尝试作为绝对路径
                full_path = Path(file_path)
                if not full_path.exists():
                    logger.warning(f"[宏展开] 文件不存在: {file_path}")
                    return None

            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # 读取多行宏（以 \ 结尾）
            macro_lines = []
            for i in range(start_line - 1, len(lines)):
                line = lines[i].rstrip('\n\r')
                macro_lines.append(line)

                # 如果不以 \ 结尾，宏定义结束
                if not line.rstrip().endswith('\\'):
                    break

            # 合并多行（移除续行符和缩进）
            result = []
            for line in macro_lines:
                # 移除行末的 \
                line = line.rstrip()
                if line.endswith('\\'):
                    line = line[:-1].rstrip()
                result.append(line)

            return '\n'.join(result)

        except Exception as e:
            logger.error(f"[宏展开] 读取多行宏失败: {e}")
            return None

    def extract_struct_macro(self, macro_name: str) -> Optional[str]:
        """
        提取结构体成员宏的展开定义

        用于展开类似 VOS_MSG_HEADER 这样的结构体成员宏

        Args:
            macro_name: 宏名称

        Returns:
            展开的成员定义（多行），如果未找到返回None
        """
        macro_def = self.extract_macro_definition(macro_name)

        if not macro_def:
            return None

        # 提取宏定义的主体部分（去掉 #define 和宏名）
        # 格式: #define MACRO_NAME body
        match = re.match(r'^\s*#\s*define\s+\w+\s+(.*?)$', macro_def, re.DOTALL)
        if not match:
            return None

        body = match.group(1)

        # 移除多行宏的续行符和格式化
        # 将 \ 换行符处理为实际换行
        body = body.replace('\\\n', '\n')
        body = body.replace('\\', '')

        # 清理空白
        lines = [line.strip() for line in body.split('\n') if line.strip()]

        return '\n    '.join(lines)  # 添加缩进

    def is_likely_macro(self, identifier: str) -> bool:
        """
        判断标识符是否可能是宏

        启发式规则：
        - 全大写字母
        - 包含下划线
        - 不是纯数字

        Args:
            identifier: 标识符

        Returns:
            是否可能是宏
        """
        if not identifier:
            return False

        # 全大写且包含下划线
        if identifier.isupper() and '_' in identifier:
            return True

        # 全大写且长度>2
        if identifier.isupper() and len(identifier) > 2:
            return True

        return False
