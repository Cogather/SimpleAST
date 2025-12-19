"""测试 GrepSearcher 构建的命令"""
from simple_ast.searchers import GrepSearcher
import subprocess

project_root = "projects/ince_diam"
searcher = GrepSearcher(project_root)

pattern = r'typedef\s+struct\s+[^{;]*DiamAppMsg'

# 获取构建的命令
cmd = searcher.config.build_search_command(
    pattern=pattern,
    path=str(searcher.project_root),
    file_glob='*.h',
    show_files_only=False,
    show_line_numbers=True
)

print("构建的命令:")
print(' '.join(cmd))
print()

# 执行命令看看输出
print("执行结果:")
try:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10,
        encoding='utf-8',
        errors='ignore'
    )
    print(f"返回码: {result.returncode}")
    print(f"stdout: {result.stdout[:500]}")
    if result.stderr:
        print(f"stderr: {result.stderr[:500]}")
except Exception as e:
    print(f"错误: {e}")
