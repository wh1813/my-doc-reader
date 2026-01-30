# 1. 基础镜像
FROM python:3.9-slim

# ======================================================
# 🔑 这里填入你本地测试成功的 Cookie
# ======================================================
ENV COOKIE_BOOK118="把你的Book118_Cookie填在这里"
ENV COOKIE_RENREN1="把你的Renren1_Cookie填在这里"
ENV COOKIE_RENREN2="把你的Renren2_Cookie填在这里"
# ======================================================

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 工作目录
WORKDIR /app

# 2. 安装基础工具 和 Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 安装最新版 Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 3. 安装 Python 依赖
# 为了方便，这里直接写死依赖，不用 requirements.txt 了
RUN pip install --no-cache-dir \
    requests \
    selenium \
    undetected-chromedriver \
    lxml

# 4. 复制代码
COPY main.py .

# 5. 启动命令
CMD ["python", "main.py"]
