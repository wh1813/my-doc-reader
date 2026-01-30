import os
import time
import logging
import random
import sys
import shutil
import threading
import subprocess
import json
import requests
import urllib.parse
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from http.server import HTTPServer, BaseHTTPRequestHandler

# ================= 配置区域 =================
# 仓库地址
REPO_PATH = "wh1813/my-doc-reader"

# 远程文件地址
REMOTE_URLS_PATH = f"https://raw.githubusercontent.com/{REPO_PATH}/main/urls.txt"
REMOTE_XRAY_PATH = f"https://raw.githubusercontent.com/{REPO_PATH}/main/xray.txt"

# 爬虫定时器：每隔多少秒运行一次爬虫 (默认 12 小时 = 43200 秒)
# 如果你希望只依赖 GitHub Actions 更新，可以把这个设得非常大
SPIDER_INTERVAL = 43200 

# 重启间隔 (每访问多少个网页重启浏览器)
RESTART_INTERVAL = 50
# ===========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 全局变量：记录上次爬虫运行时间
last_spider_time = 0

# --- 模块: 调用本地爬虫 ---
def run_spider_task():
    """运行本地 spider.py 并更新 urls.txt"""
    global last_spider_time
    logging.info("🕷️ >>> [爬虫任务] 正在启动本地爬虫...")
    
    # 检查是否有 Cookie 环境变量 (否则爬虫跑了也没用)
    if not os.environ.get("COOKIE_BOOK118") and not os.environ.get("COOKIE_RENREN1"):
        logging.warning("⚠️ 未检测到 Cookie 环境变量，跳过本地爬取 (将尝试使用远程 urls.txt)")
        return

    try:
        # 调用 spider.py
        result = subprocess.run(["python", "spider.py"], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("✅ [爬虫任务] 执行成功，urls.txt 已更新")
            # 打印爬虫的部分输出以便调试
            print(result.stderr) 
        else:
            logging.error(f"❌ [爬虫任务] 执行失败: {result.stderr}")
            
        last_spider_time = time.time()
        
    except Exception as e:
        logging.error(f"❌ [爬虫任务] 调用异常: {e}")

# --- 模块1: VLESS 链接解析器 ---
def parse_vless(url):
    try:
        if not url.startswith("vless://"): return None
        main_part = url.split("://")[1].split("?")[0].split("#")[0]
        query_part = url.split("?")[1].split("#")[0] if "?" in url else ""
        user_info, host_port = main_part.split("@")
        host, port = host_port.split(":")
        params = dict(urllib.parse.parse_qsl(query_part))
        return {
            "uuid": user_info, "address": host, "port": int(port),
            "type": params.get("type", "tcp"), "security": params.get("security", "none"),
            "sni": params.get("sni", ""), "path": params.get("path", "/"),
            "host": params.get("host", ""), "fp": params.get("fp", "")
        }
    except: return None

# --- 模块2: 代理服务管理 (Xray) ---
def check_proxy_connectivity():
    try:
        proxies = {"http": "http://127.0.0.1:10808", "https": "http://127.0.0.1:10808"}
        r = requests.get("https://www.baidu.com", proxies=proxies, timeout=5)
        return r.status_code == 200
    except: return False

def start_xray_with_node(node_url):
    node = parse_vless(node_url)
    if not node: return False
    config = {
        "log": {"loglevel": "error"},
        "inbounds": [{"port": 10808, "listen": "127.0.0.1", "protocol": "http", "settings": {"udp": True}}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {"vnext": [{"address": node["address"], "port": node["port"], "users": [{"id": node["uuid"], "encryption": "none"}]}]},
            "streamSettings": {
                "network": node["type"], "security": node["security"],
                "tlsSettings": {"serverName": node["sni"], "fingerprint": node["fp"]} if node["security"] == "tls" else None,
                "wsSettings": {"path": node["path"], "headers": {"Host": node["host"]}} if node["type"] == "ws" else None
            }
        }]
    }
    with open("config.json", "w") as f: json.dump(config, f)
    subprocess.run("pkill -9 -f xray", shell=True, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        subprocess.Popen(["xray", "-c", "config.json"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        if check_proxy_connectivity():
            logging.info(f"    -> [节点切换成功] 目标: {node['address']}")
            return True
        else: return False
    except: return False

def rotate_proxy():
    if not os.path.exists("xray.txt"): return False
    with open("xray.txt", "r") as f:
        nodes = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    if not nodes: return False
    random.shuffle(nodes)
    for node_url in nodes:
        if start_xray_with_node(node_url): return True
    return False

# --- 模块3: 自动更新 ---
def update_remote_files():
    # 只有当本地没有 urls.txt 或者文件为空时，才强制从远程拉取
    # 避免覆盖了本地爬虫刚抓到的新鲜数据
    should_update_urls = True
    if os.path.exists("urls.txt") and os.path.getsize("urls.txt") > 0:
        # 简单策略：如果本地有数据，暂时不从远程覆盖，除非你想合并
        # 这里为了配合“本地爬虫优先”，我们仅更新 xray.txt
        should_update_urls = False 

    try:
        if should_update_urls:
            r = requests.get(REMOTE_URLS_PATH, timeout=10)
            if r.status_code == 200:
                with open("urls.txt", "w", encoding="utf-8") as f: f.write(r.text)
                logging.info("✅ urls.txt 从远程更新成功")
        
        # Xray 节点列表总是更新
        r = requests.get(REMOTE_XRAY_PATH, timeout=10)
        if r.status_code == 200:
            with open("xray.txt", "w", encoding="utf-8") as f: f.write(r.text)
            logging.info("✅ xray.txt 从远程更新成功")
    except: pass

# --- 模块4: 浏览器配置 ---
def force_kill_chrome():
    subprocess.run("pkill -9 -f chrome", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("pkill -9 -f undetected_chromedriver", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("rm -rf /tmp/.org.chromium.*", shell=True, stderr=subprocess.DEVNULL)

def get_driver():
    force_kill_chrome()
    data_dir = "/tmp/chrome_user_data"
    if os.path.exists(data_dir): shutil.rmtree(data_dir, ignore_errors=True)
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-data-dir={data_dir}")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--proxy-server=http://127.0.0.1:10808")
    try:
        driver = uc.Chrome(options=options, version_main=144, use_subprocess=True, headless=True)
        driver.set_page_load_timeout(60)
        return driver
    except:
        force_kill_chrome()
        return None

# --- 主逻辑 ---
def run_automation():
    global last_spider_time
    
    # 1. 检查是否需要运行爬虫 (启动时必跑，之后按 SPIDER_INTERVAL 跑)
    current_time = time.time()
    if last_spider_time == 0 or (current_time - last_spider_time > SPIDER_INTERVAL):
        run_spider_task()

    # 2. 如果本地爬虫没跑成，尝试从 GitHub 拉取保底
    if not os.path.exists("urls.txt") or os.path.getsize("urls.txt") == 0:
        update_remote_files()

    # 3. 检查代理
    if subprocess.call("pgrep -f xray > /dev/null", shell=True) != 0:
        if not rotate_proxy(): return 

    # 4. 读取 URL
    if not os.path.exists("urls.txt"): return
    with open("urls.txt", "r") as f: urls = [l.strip() for l in f if l.strip()]
    if not urls: 
        logging.warning("⚠️ urls.txt 为空，等待下一次循环...")
        return

    driver = get_driver()
    if not driver: return
    logging.info(f">>> 任务开始，本轮共 {len(urls)} 个链接")

    for index, url in enumerate(urls, 1):
        try:
            if not url.startswith('http'): url = 'https://' + url
            if index % RESTART_INTERVAL == 0:
                try: driver.quit()
                except: pass
                if not rotate_proxy(): break 
                driver = get_driver()
                if not driver: break

            logging.info(f"[{index}/{len(urls)}] 访问: {url}")
            driver.get(url)
            sleep_time = random.uniform(5, 8)
            time.sleep(sleep_time)
            logging.info(f"    -> 成功 (停留 {sleep_time:.1f}s)")
        except:
            try: driver.quit()
            except: pass
            rotate_proxy()
            driver = get_driver()
            if not driver: break
    try: driver.quit()
    except: pass
    force_kill_chrome()

# --- 保活 Web Server ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Alive")
    def log_message(self, format, *args): pass

if __name__ == "__main__":
    threading.Thread(target=HTTPServer(('0.0.0.0', 80), HealthCheckHandler).serve_forever, daemon=True).start()
    
    # 初始化代理
    update_remote_files() # 先拉取 xray.txt
    if not rotate_proxy(): time.sleep(10)
    
    while True:
        try: run_automation()
        except Exception as e: 
            logging.error(f"主循环异常: {e}")
        
        # 休息 10 分钟后进入下一轮 (如果是爬虫刚跑完，这里也会休息，防止频繁请求)
        logging.info("💤 休息 10 分钟...")
        time.sleep(600)
