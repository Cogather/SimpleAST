"""直接测试 rg 命令"""
import subprocess

print("测试 rg --version 使用字符串 + shell=True:")
result = subprocess.run(
    'rg --version',
    capture_output=True,
    timeout=5,
    shell=True
)

print(f"Return code: {result.returncode}")
print(f"Stdout: {result.stdout.decode('utf-8', errors='ignore')}")
print(f"Stderr: {repr(result.stderr)}")
