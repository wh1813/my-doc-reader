# 1. 基础镜像
FROM python:3.9-slim

# ==============================================================================
# 【核心修改】直接将 Cookie 注入到镜像的环境变量中
# 注意：这会让你的 Cookie 存在于镜像里，请确保你的 GitHub 仓库是 Private (私有) 的，以免泄露
# ==============================================================================
ENV COOKIE_BOOK118="DOC_INFORM=read; UPLOAD_AGREEMENT_CHECKED=1; CLIENT_SYS_UN_ID=wKh2E2isHB1RcIduBKwbAg==; doc_782367374=3940640; 40443fac74509483=3940640; doc_781051995=3940640; 0ab7d33081eeb=2025%E5%B9%B48%E6%9C%88%E9%87%91%E8%82%A1%E7%BB%84%E5%90%88; input_search_logs=%5B%7B%22keywords%22%3A%222025%5Cu5e748%5Cu6708%5Cu91d1%5Cu80a1%5Cu7ec4%5Cu5408%22%2C%22time%22%3A1756890637%7D%5D; Hm_lvt_90eba6da4a0cf4f7f07614e930242936=1756890638; doc_781054464=3940640; upload_platform=1; upload_platform_from=top; f3da6324d61140db0d6c9edc078c577a=1760950664%2C2; Hm_lvt_af8c54428f2dd7308990f5dd456fae6d=1766918372; d6b93d63cc960c878126=1766918417%2C6; doc_818225850=3940640; Hm_lvt_ed4f006fba260fb55ee1dfcb3e754e1c=1767666260,1767851092; PREVIEWHISTORYPAGES=769621358_5,820456517_1,825725550_5; 94ca48fd8a42333b_code_getgraphcode=1769330742%2C1; 94ca48fd8a42333b_login_passwordlogin=1769330744%2C1; max_u_token=4d5a1b714f31f055ff1181081748c36b; PHPSESSID=67v5bmh2lilem0pfmsnkfrt8f1; Hm_lvt_f32e81852cb54f29133561587adb93c1=1769513197,1769671464,1769675115,1769699552; HMACCOUNT=04695825FE18F733; detail_show_similar=0; a_8056043140010041=1; ef7656dc08a0f1cf4c78acb87d97a1b9=1769761558%2C1; c4da14928424747de8b677208095de01=1769763729%2C1; operation_user_center=1; Hm_lpvt_f32e81852cb54f29133561587adb93c1=1769769654"

ENV COOKIE_RENREN1="6c6de0691ee16338_SearchKeywordCompletion=1758876189%2C5; 6c6de0691ee16338_SearchApiSearchV2=1758876189%2C5; 6c6de0691ee16338_Member_getUserTotalScore=1767576264%2C1; 6c6de0691ee16338_Ajax_getSimilarDocNew=1769351178%2C2; 585ca0f783c538407119f6ece093cd59=83c538407119f6ec; PHPSESSID=904248895100a8974161325b102df1a7; Hm_lvt_6a5c78ee0a40875a43251c84c5625146=1769351067,1769513230,1769672603,1769706749; HMACCOUNT=04695825FE18F733; 6c6de0691ee16338_72d92c793d3cc4ba7b447f876c97efd4=1769739076%2C1; currentUrl=https://www.renrendoc.com/renrendoc_v1/MCBookList/published.html; e4d982b2-ace5-4626-b819-0a4f6fdb0ced=E4D982B2ACE54626B8190A4F6FDB0CEDPTYHN6138YUHJNKI=aMMNCAZ5DgXVtd3TybK49LWbwJyBmJJjrS6lqGyNeX9Hyx6L7Blkz6sQribNF/DrFmErj1nA9VDG/EH+O99o0XHgK/ijmkB8jPe5/EjP+OksaTUdKmw4e3A1LvnGbtqc&E4D982B2ACE54626B8190A4F6FDB0CEDPTIUHKLPOIUY652NKI=UhDTteMrwZnbmCP/Tgd1L6XkqZB7ieYDme/e2DwDVcisycsljVROVnu73WgXe5kW87a9KSbLsgJv4wKaNTbcOGQHIUs5zohkJoVzbkmSpHrPu0fS7Tki12y3/wNmWgb2ZpAnsiiSCWiBi8OsQag/H7fFUcUawMnl79h8Q834wbo=; Hm_lpvt_6a5c78ee0a40875a43251c84c5625146=1769765180"

ENV COOKIE_RENREN2="6c6de0691ee16338_SearchKeywordCompletion=1758876189%2C5; 6c6de0691ee16338_SearchApiSearchV2=1758876189%2C5; 6c6de0691ee16338_Member_getUserTotalScore=1767576264%2C1; 6c6de0691ee16338_Ajax_getSimilarDocNew=1769351178%2C2; 585ca0f783c538407119f6ece093cd59=83c538407119f6ec; PHPSESSID=904248895100a8974161325b102df1a7; Hm_lvt_6a5c78ee0a40875a43251c84c5625146=1769351067,1769513230,1769672603,1769706749; HMACCOUNT=04695825FE18F733; 6c6de0691ee16338_72d92c793d3cc4ba7b447f876c97efd4=1769739076%2C1; e4d982b2-ace5-4626-b819-0a4f6fdb0ced=E4D982B2ACE54626B8190A4F6FDB0CEDPTYHN6138YUHJNKI=rRXk5KHDIiwdRoozGns5aShQpU4N59aqWAEdpoIZl4iEod5+QQvIFpP6l0AxASw122ZhlprZQs9ALkvmU+XKqyD6aVok9RhQDBNYVnM4lcsSgv9ZP0/EpN3rj0h5BfJn&E4D982B2ACE54626B8190A4F6FDB0CEDPTIUHKLPOIUY652NKI=SQch/jPUTuBWKzi1O0g8pw0MfwbJZK65Q9jn/mLjO3URXmx1kdiUWZKmJM5DvCIvgOdkbC94eJoG1DgAa261ykJCZvylEJ8be0cylsPLYS9H/5eZWLIG5iUClrPi/29/7QxZzYql+89CcsxHID9tXqsADy88tx1usYtBcmRJsLc=; Hm_lpvt_6a5c78ee0a40875a43251c84c5625146=1769770998;"
# ==============================================================================

# 设置环境变量，防止 Python 生成 .pyc 文件和缓冲输出
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 设置工作目录
WORKDIR /app

# 2. 安装基础工具
# 包含 wget, unzip 等，用于后续下载 Chrome 和 Xray
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    procps \
    unzip \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 3. 安装 Chrome 浏览器
# 直接从 Google 官方下载最新稳定版
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# 4. 下载并安装 Xray (v1.8.4)
# 用于节点代理功能
RUN wget -q https://github.com/XTLS/Xray-core/releases/download/v1.8.4/Xray-linux-64.zip \
    && unzip Xray-linux-64.zip \
    && mv xray /usr/bin/xray \
    && chmod +x /usr/bin/xray \
    && rm Xray-linux-64.zip

# 5. 安装 Python 依赖
# 先复制 requirements.txt 以利用 Docker 缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 复制所有代码到镜像中
COPY . .

# 7. 暴露端口 (用于保活检查)
EXPOSE 80

# 8. 启动命令
CMD ["python", "main.py"]
