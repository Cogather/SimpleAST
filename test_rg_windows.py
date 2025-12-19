"""测试 Windows 下直接调用 rg"""
import subprocess

print("测试方式1: 使用 shell=True 的字符串命令")
try:
    result = subprocess.run(
        'rg --version',
        capture_output=True,
        timeout=5,
        shell=True
    )
    print(f"Return code: {result.returncode}")
    if result.returncode == 0:
        print("成功! 输出:")
        print(result.stdout.decode('utf-8', errors='ignore'))
    else:
        print("失败! 错误:")
        print(result.stderr.decode('gbk', errors='ignore'))
except Exception as e:
    print(f"异常: {e}")

print("\n" + "=" * 60)
print("测试方式2: 尝试 PowerShell")
try:
    result = subprocess.run(
        ['powershell', '-Command', 'rg --version'],
        capture_output=True,
        timeout=5
    )
    print(f"Return code: {result.returncode}")
    if result.returncode == 0:
        print("成功! 输出:")
        print(result.stdout.decode('utf-8', errors='ignore'))
    else:
        print("失败! 错误:")
        print(result.stderr.decode('utf-8', errors='ignore'))
except Exception as e:
    print(f"异常: {e}")
