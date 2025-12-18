"""
外部函数分类器 - 根据配置区分业务依赖、标准库、日志函数
"""
import json
from pathlib import Path
from typing import Set, Dict, List
import fnmatch


class ExternalFunctionClassifier:
    """外部函数分类器"""

    def __init__(self, config_path: str = None):
        """
        初始化分类器

        Args:
            config_path: 配置文件路径，如果为None则使用默认配置
        """
        self.config = self._load_config(config_path)
        self.standard_lib_patterns = self.config.get('standard_library', {}).get('patterns', [])
        self.logging_patterns = self.config.get('logging_utility', {}).get('patterns', [])
        self.custom_exclusions = self.config.get('custom_exclusions', {}).get('patterns', [])

    def _load_config(self, config_path: str = None) -> Dict:
        """加载配置文件"""
        if config_path is None:
            # 尝试从项目根目录加载默认配置
            default_config_path = Path('.simple_ast_config.json')
            if default_config_path.exists():
                config_path = str(default_config_path)

        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('external_function_classification', {})
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")

        # 返回默认配置
        return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """获取默认配置（内置）"""
        return {
            'standard_library': {
                'patterns': [
                    'std::*', 'memset*', 'memcpy*', 'strcpy*', 'strlen*',
                    'malloc*', 'free*', 'printf*', 'sprintf*'
                ]
            },
            'logging_utility': {
                'patterns': [
                    '*LOG*', '*log*', '*PRINT*', '*Print*',
                    '*ASSERT*', '*CHECK*', '*TRACE*'
                ]
            },
            'custom_exclusions': {
                'patterns': []
            }
        }

    def _matches_patterns(self, func_name: str, patterns: List[str]) -> bool:
        """检查函数名是否匹配任一模式"""
        for pattern in patterns:
            if fnmatch.fnmatch(func_name, pattern):
                return True
        return False

    def classify(self, external_functions: Set[str]) -> Dict[str, Set[str]]:
        """
        分类外部函数

        Args:
            external_functions: 外部函数名称集合

        Returns:
            Dict包含三个分类：
            - 'business': 业务外部依赖（需要Mock）
            - 'standard_library': 标准库函数（通常不需要Mock）
            - 'logging_utility': 日志/工具函数（可选Mock）
        """
        result = {
            'business': set(),
            'standard_library': set(),
            'logging_utility': set()
        }

        for func in external_functions:
            # 优先级：custom_exclusions > standard_library > logging_utility > business

            if self._matches_patterns(func, self.custom_exclusions):
                # 用户自定义排除的，根据配置归类
                # 默认归入logging_utility（因为通常是项目特定的工具函数）
                result['logging_utility'].add(func)
            elif self._matches_patterns(func, self.standard_lib_patterns):
                result['standard_library'].add(func)
            elif self._matches_patterns(func, self.logging_patterns):
                result['logging_utility'].add(func)
            else:
                # 无法匹配任何模式，归类为业务依赖
                result['business'].add(func)

        return result

    def get_config_info(self) -> str:
        """获取配置信息（用于显示）"""
        lines = []
        lines.append("当前外部函数分类配置：")
        lines.append(f"  标准库模式: {len(self.standard_lib_patterns)} 个")
        lines.append(f"  日志工具模式: {len(self.logging_patterns)} 个")
        lines.append(f"  自定义排除: {len(self.custom_exclusions)} 个")
        return "\n".join(lines)


def format_classified_externals(classified: Dict[str, Set[str]]) -> str:
    """
    格式化分类后的外部函数清单

    Args:
        classified: classify()返回的分类结果

    Returns:
        格式化的文本
    """
    lines = []

    # 业务外部依赖（最重要，放最前面）
    if classified['business']:
        lines.append(f"业务外部依赖（需要Mock）: {len(classified['business'])} 个")
        for func in sorted(classified['business']):
            lines.append(f"- {func}")
        lines.append("")

    # 日志/工具函数
    if classified['logging_utility']:
        lines.append(f"日志/工具函数（可选Mock）: {len(classified['logging_utility'])} 个")
        for func in sorted(classified['logging_utility']):
            lines.append(f"- {func}")
        lines.append("")

    # 标准库函数
    if classified['standard_library']:
        lines.append(f"标准库函数（通常不需要Mock）: {len(classified['standard_library'])} 个")
        for func in sorted(classified['standard_library']):
            lines.append(f"- {func}")
        lines.append("")

    return "\n".join(lines)
