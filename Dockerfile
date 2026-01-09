# SimpleAST 最小运行环境
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 更换 apt 源为阿里云
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖（tree-sitter 需要 gcc）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 更换 pip 源为阿里云
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# 默认命令
CMD ["python", "analyze.py", "--help"]
