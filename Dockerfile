# 1. 基础镜像
FROM python:3.9-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 2. 安装系统依赖 + Chrome + Xray (核心步骤)
# 这一步非常关键，必须包含 Xray 的安装脚本
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    procps \
    --no-install-recommends \
    && \
    # --- A. 安装 Chrome ---
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && \
    rm google-chrome-stable_current_amd64.deb \
    && \
    # --- B. 安装 Xray (这就是你缺失的部分) ---
    # 使用官方脚本自动安装 Xray 到系统路径
    bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install \
    && \
    # 清理缓存
    rm -rf /var/lib/apt/lists/*

# 3. 安装 Python 依赖
RUN pip install --no-cache-dir requests selenium undetected-chromedriver

# 4. 复制代码
# 这一步会把你本地的 main.py 复制进去
COPY main.py .

# 5. 启动
CMD ["python", "main.py"]
