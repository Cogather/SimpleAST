"""测试 rg --version 的返回情况"""
import subprocess

print("测试 shell=True 时的详细输出:")
result = subprocess.run(
    ['rg', '--version'],
    capture_output=True,
    timeout=5,
    shell=True
)

print(f"Return code: {result.returncode}")
print(f"Stdout length: {len(result.stdout)}")
print(f"Stderr length: {len(result.stderr)}")
print()
print("Stdout:")
print(result.stdout.decode('utf-8', errors='ignore'))
print()
print("Stderr:")
print(result.stderr.decode('utf-8', errors='ignore'))
