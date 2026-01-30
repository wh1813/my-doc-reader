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

# ================= 配置区域 (请修改这里) =================
# 【TODO: 请将 user123/my-doc-reader 替换为你真实的新仓库地址】
REPO_PATH = "wh1813/my-doc-reader" 

# 1. 网址列表的 GitHub Raw 地址
REMOTE_URLS_PATH = f"https://raw.githubusercontent.com/{REPO_PATH}/main/urls.txt"

# 2. 节点列表的 GitHub Raw 地址
REMOTE_XRAY_PATH = f"https://raw.githubusercontent.com/{REPO_PATH}/main/xray.txt"

# 3. 每访问多少个网页切换一次 IP
RESTART_INTERVAL = 50
# ========================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

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
    except Exception as e:
        return None

# --- 模块2: 代理服务管理 (Xray) ---
def check_proxy_connectivity():
    try:
        proxies = {"http": "http://127.0.0.1:10808", "https": "http://127.0.0.1:10808"}
        r = requests.get("https://www.baidu.com", proxies=proxies, timeout=5)
        if r.status_code == 200: return True
    except: return False
    return False

def start_xray_with_node(node_url):
    node = parse_vless(node_url)
    if not node: return False
    
    config = {
        "log": {"loglevel": "error"},
        "inbounds": [{"port": 10808, "listen": "127.0.0.1", "protocol": "http", "settings": {"udp": True}}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "vnext": [{"address": node["address"], "port": node["port"], "users": [{"id": node["uuid"], "encryption": "none"}]}]
            },
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
        else:
            return False
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
    files = {"urls.txt": REMOTE_URLS_PATH, "xray.txt": REMOTE_XRAY_PATH}
    for filename, url in files.items():
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(filename, "w", encoding="utf-8") as f: f.write(r.text)
                logging.info(f"✅ {filename} 更新成功")
        except: pass

# --- 模块4: 浏览器配置 ---
def force_kill_chrome():
    subprocess.run("pkill -9 -f chrome", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("pkill -9 -f undetected_chromedriver", shell=True, stderr=subprocess.DEVNULL)

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
    update_remote_files()
    if subprocess.call("pgrep -f xray > /dev/null", shell=True) != 0:
        if not rotate_proxy(): return 
    if not os.path.exists("urls.txt"): return
    with open("urls.txt", "r") as f: urls = [l.strip() for l in f if l.strip()]
    if not urls: return

    driver = get_driver()
    if not driver: return
    logging.info(f">>> 任务开始，共 {len(urls)} 个链接")

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
    update_remote_files()
    if not rotate_proxy(): time.sleep(60)
    while True:
        try: run_automation()
        except: pass

        time.sleep(600)
