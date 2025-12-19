"""
批量转换日志输出 - 将 print(file=sys.stderr) 改为 logger 调用
"""
import re
from pathlib import Path

# 需要处理的文件列表
FILES = [
    "simple_ast/branch_analyzer.py",
    "simple_ast/extractors/constant_extractor.py",
    "simple_ast/reporters/function_reporter.py",
    "simple_ast/cpp_analyzer.py",
    "simple_ast/searchers/grep_searcher.py",
]

def convert_file(file_path: Path):
    """转换单个文件"""
    print(f"处理: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已经导入了 logger
    has_logger_import = 'from .logger import get_logger' in content or 'from ..logger import get_logger' in content

    # 如果没有导入，添加导入语句
    if not has_logger_import and 'print(' in content and 'file=sys.stderr' in content:
        # 找到第一个 import 语句后插入
        lines = content.split('\n')
        import_end = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_end = i + 1

        # 确定导入路径
        if 'searchers' in str(file_path):
            logger_import = 'from ..logger import get_logger'
        elif 'extractors' in str(file_path) or 'reporters' in str(file_path):
            logger_import = 'from ..logger import get_logger'
        else:
            logger_import = 'from .logger import get_logger'

        lines.insert(import_end, logger_import)
        lines.insert(import_end + 1, '\nlogger = get_logger()')
        content = '\n'.join(lines)

    # 转换 print 语句为 logger 调用
    # 匹配模式: print(f"[标签] 内容", file=sys.stderr)
    patterns = [
        # [标签] 开头的信息日志
        (r'print\(f?"?\[([^\]]+)\]\s+([^"]*)"?,?\s*file=sys\.stderr\)', r'logger.info("\2")'),
        # 没有标签的普通日志
        (r'print\(f?"?([^"]*)"?,?\s*file=sys\.stderr\)', r'logger.info("\1")'),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    # 特殊处理：将特定前缀映射到日志级别
    content = content.replace('logger.info("✗', 'logger.warning("')
    content = content.replace('logger.info("警告', 'logger.warning("')
    content = content.replace('logger.info("错误', 'logger.error("')

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  完成")

def main():
    """主函数"""
    print("开始转换日志输出...")
    print("=" * 60)

    for file_path in FILES:
        path = Path(file_path)
        if path.exists():
            convert_file(path)
        else:
            print(f"跳过（文件不存在）: {file_path}")

    print("=" * 60)
    print("转换完成！")

if __name__ == '__main__':
    main()
