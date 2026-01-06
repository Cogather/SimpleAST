"""诊断 ripgrep 可用性"""
import subprocess
import sys
import os

print("=" * 60)
print("系统信息")
print("=" * 60)
print(f"Platform: {sys.platform}")
print(f"Python: {sys.version}")
print()

print("=" * 60)
print("环境变量 PATH")
print("=" * 60)
print(os.environ.get('PATH', 'PATH not found')[:500])
print()

print("=" * 60)
print("测试1: 不使用 shell")
print("=" * 60)
try:
    result = subprocess.run(
        ['rg', '--version'],
        capture_output=True,
        timeout=5,
        shell=False
    )
    print(f"成功! returncode={result.returncode}")
    print(result.stdout.decode('utf-8', errors='ignore')[:200])
except Exception as e:
    print(f"失败: {e}")

print()
print("=" * 60)
print("测试2: 使用 shell=True")
print("=" * 60)
try:
    result = subprocess.run(
        ['rg', '--version'],
        capture_output=True,
        timeout=5,
        shell=True
    )
    print(f"成功! returncode={result.returncode}")
    print(result.stdout.decode('utf-8', errors='ignore')[:200])
except Exception as e:
    print(f"失败: {e}")

print()
print("=" * 60)
print("测试3: 使用完整命令字符串 + shell")
print("=" * 60)
try:
    result = subprocess.run(
        'rg --version',
        capture_output=True,
        timeout=5,
        shell=True
    )
    print(f"成功! returncode={result.returncode}")
    print(result.stdout.decode('utf-8', errors='ignore')[:200])
except Exception as e:
    print(f"失败: {e}")

print()
print("=" * 60)
print("测试4: 尝试 where 命令查找 rg")
print("=" * 60)
try:
    result = subprocess.run(
        'where rg',
        capture_output=True,
        timeout=5,
        shell=True
    )
    if result.returncode == 0:
        print(f"找到 rg:")
        print(result.stdout.decode('utf-8', errors='ignore'))
    else:
        print("未找到 rg")
except Exception as e:
    print(f"失败: {e}")
