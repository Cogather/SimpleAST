"""测试搜索工具的检测和使用"""
import subprocess
from simple_ast.searchers.search_config import SearchConfig, SearchTool, get_search_config

print("=" * 60)
print("1. 直接测试命令可用性")
print("=" * 60)

# 测试 rg 命令
try:
    result = subprocess.run(['rg', '--version'], capture_output=True, timeout=5)
    print(f"rg 可用: returncode={result.returncode}")
    print(f"输出: {result.stdout.decode('utf-8', errors='ignore')[:100]}")
except Exception as e:
    print(f"rg 不可用: {e}")

print()

# 测试 grep 命令
try:
    result = subprocess.run(['grep', '--version'], capture_output=True, timeout=5)
    print(f"grep 可用: returncode={result.returncode}")
    print(f"输出: {result.stdout.decode('utf-8', errors='ignore')[:100]}")
except Exception as e:
    print(f"grep 不可用: {e}")

print()
print("=" * 60)
print("2. 测试自动检测（AUTO模式）")
print("=" * 60)

try:
    config = SearchConfig(tool=SearchTool.AUTO)
    print(f"自动检测结果: {config.tool.value}")
    print(f"使用命令: {config.command}")
except Exception as e:
    print(f"自动检测失败: {e}")

print()
print("=" * 60)
print("3. 使用全局配置")
print("=" * 60)

try:
    config = get_search_config()
    print(f"全局配置: {config.tool.value}")
    print(f"使用命令: {config.command}")

    # 测试构建命令
    cmd = config.build_search_command(
        pattern=r'\btest\b',
        path='.',
        file_glob='*.py',
        show_files_only=True
    )
    print(f"示例命令: {' '.join(cmd)}")
except Exception as e:
    print(f"全局配置失败: {e}")
