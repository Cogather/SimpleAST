"""
基于函数名自动分类 - 支持驼峰命名解析
"""
import re
from typing import Dict, List, Set
from collections import defaultdict, Counter


class AutoClassifier:
    """自动分类器：基于函数名前缀和词根分类"""

    def __init__(self, min_group_size: int = 3):
        """
        Args:
            min_group_size: 最小分组大小，小于此数量的归入 'other'
        """
        self.min_group_size = min_group_size

    @staticmethod
    def split_camel_case(name: str) -> List[str]:
        """
        将驼峰命名分词

        Examples:
            AddCircle → ['Add', 'Circle']
            ImDrawList → ['Im', 'Draw', 'List']
            _OnChangedClipRect → ['On', 'Changed', 'Clip', 'Rect']
            GetTexDataAsRGBA32 → ['Get', 'Tex', 'Data', 'As', 'RGBA', '32']
        """
        # 移除前缀下划线和类名前缀（如 ImDrawList::）
        name = re.sub(r'^[_]+', '', name)
        name = re.sub(r'^[A-Z][a-z]*::', '', name)

        # 处理驼峰命名：在大写字母前插入分隔符
        # AddCircle → Add_Circle
        # RGBA32 → RGBA_32
        words = re.sub(r'([a-z])([A-Z])', r'\1_\2', name)
        words = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', words)

        # 分割并过滤空字符串
        return [w for w in words.split('_') if w]

    def extract_prefix(self, func_name: str) -> str:
        """
        提取函数名前缀（第一个单词）

        Examples:
            AddCircle → Add
            GetTexDataAsRGBA32 → Get
            CalcTextSize → Calc
            _OnChangedClipRect → On
        """
        words = self.split_camel_case(func_name)
        if not words:
            return 'unknown'
        return words[0]

    def classify_by_prefix(self, function_names: List[str]) -> Dict[str, List[str]]:
        """
        按函数名前缀分类

        Returns:
            {
                'Add': ['AddCircle', 'AddRect', ...],
                'Get': ['GetTexData', 'GetGlyph', ...],
                'other': [小分类函数]
            }
        """
        # 统计每个前缀的函数数量
        prefix_groups = defaultdict(list)

        for func_name in function_names:
            prefix = self.extract_prefix(func_name)
            prefix_groups[prefix].append(func_name)

        # 合并小分类到 other
        result = {}
        other_funcs = []

        for prefix, funcs in prefix_groups.items():
            if len(funcs) >= self.min_group_size:
                result[prefix] = sorted(funcs)
            else:
                other_funcs.extend(funcs)

        if other_funcs:
            result['other'] = sorted(other_funcs)

        return result

    def extract_keywords(self, function_names: List[str], top_n: int = 10) -> List[str]:
        """
        提取最常见的关键词（用于分析项目特征）

        Returns:
            ['Add', 'Get', 'Set', 'Draw', 'Font', ...]
        """
        all_words = []
        for func_name in function_names:
            words = self.split_camel_case(func_name)
            all_words.extend(words)

        # 统计词频
        word_counts = Counter(all_words)

        # 返回 Top N
        return [word for word, count in word_counts.most_common(top_n)]

    def classify_by_semantic(self, function_names: List[str]) -> Dict[str, List[str]]:
        """
        按语义分类（根据常见词根）

        分类逻辑：
        - 操作类：Add, Remove, Delete, Insert, Update, Set, Clear
        - 查询类：Get, Find, Search, Calc, Compute, Estimate
        - 构建类：Build, Create, Init, Construct, Make
        - 绘制类：Draw, Render, Paint, Fill
        - 状态类：Push, Pop, Begin, End, Start, Stop
        """
        semantic_rules = {
            'create': ['Add', 'Create', 'Build', 'Init', 'Construct', 'Make', 'New'],
            'query': ['Get', 'Find', 'Search', 'Calc', 'Compute', 'Estimate', 'Measure'],
            'modify': ['Set', 'Update', 'Change', 'Modify', 'Adjust'],
            'delete': ['Remove', 'Delete', 'Clear', 'Destroy', 'Free'],
            'render': ['Draw', 'Render', 'Paint', 'Fill', 'Shade'],
            'state': ['Push', 'Pop', 'Begin', 'End', 'Start', 'Stop'],
            'path': ['Path', 'Arc', 'Bezier', 'Line', 'Curve'],
        }

        result = defaultdict(list)

        for func_name in function_names:
            prefix = self.extract_prefix(func_name)

            classified = False
            for category, keywords in semantic_rules.items():
                if prefix in keywords:
                    result[category].append(func_name)
                    classified = True
                    break

            if not classified:
                result['other'].append(func_name)

        # 排序并移除空分类
        return {k: sorted(v) for k, v in result.items() if v}

    def suggest_classification(self, function_names: List[str]) -> Dict[str, any]:
        """
        分析函数名并建议分类方案

        Returns:
            {
                'total_functions': 208,
                'unique_prefixes': 45,
                'top_prefixes': [('Add', 25), ('Get', 18), ...],
                'recommended_strategy': 'prefix',  # 'prefix' or 'semantic'
                'preview': {分类预览}
            }
        """
        # 提取所有前缀
        prefixes = [self.extract_prefix(name) for name in function_names]
        prefix_counts = Counter(prefixes)

        # 统计信息
        total = len(function_names)
        unique_prefixes = len(prefix_counts)
        top_prefixes = prefix_counts.most_common(10)

        # 判断推荐策略
        # 如果前缀集中度高（Top 5 占 60%+），用前缀分类
        top5_count = sum(count for _, count in prefix_counts.most_common(5))
        concentration = top5_count / total if total > 0 else 0

        strategy = 'prefix' if concentration > 0.6 else 'semantic'

        # 生成预览
        if strategy == 'prefix':
            preview = self.classify_by_prefix(function_names)
        else:
            preview = self.classify_by_semantic(function_names)

        return {
            'total_functions': total,
            'unique_prefixes': unique_prefixes,
            'top_prefixes': top_prefixes,
            'prefix_concentration': f"{concentration:.1%}",
            'recommended_strategy': strategy,
            'preview': {k: len(v) for k, v in preview.items()},
            'classification': preview
        }


def test():
    """测试用例"""
    # 模拟 imgui_draw.cpp 的函数名
    test_functions = [
        'AddCircle', 'AddRect', 'AddLine', 'AddText', 'AddBezierCubic',
        'GetTexData', 'GetGlyph', 'GetFontSize',
        'CalcTextSize', 'CalcTextWidth',
        'BuildLookupTable', 'BuildRanges',
        'PushClipRect', 'PopClipRect',
        '_OnChangedClipRect', '_CalcCircleAutoSegmentCount',
        'SetTexID', 'SetDrawListFlags',
    ]

    classifier = AutoClassifier(min_group_size=2)

    print("=== 测试驼峰分词 ===")
    for name in test_functions[:5]:
        words = classifier.split_camel_case(name)
        print(f"{name:30} → {words}")

    print("\n=== 前缀分类 ===")
    prefix_result = classifier.classify_by_prefix(test_functions)
    for category, funcs in sorted(prefix_result.items()):
        print(f"\n{category} ({len(funcs)} 个):")
        for func in funcs[:5]:
            print(f"  • {func}")
        if len(funcs) > 5:
            print(f"  ... 还有 {len(funcs) - 5} 个")

    print("\n=== 语义分类 ===")
    semantic_result = classifier.classify_by_semantic(test_functions)
    for category, funcs in sorted(semantic_result.items()):
        print(f"\n{category} ({len(funcs)} 个):")
        for func in funcs:
            print(f"  • {func}")

    print("\n=== 自动分析 ===")
    analysis = classifier.suggest_classification(test_functions)
    print(f"总函数数: {analysis['total_functions']}")
    print(f"唯一前缀数: {analysis['unique_prefixes']}")
    print(f"前缀集中度: {analysis['prefix_concentration']}")
    print(f"推荐策略: {analysis['recommended_strategy']}")
    print(f"\n分类预览:")
    for cat, count in analysis['preview'].items():
        print(f"  {cat}: {count} 个函数")


if __name__ == '__main__':
    test()
