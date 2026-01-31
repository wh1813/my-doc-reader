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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from http.server import HTTPServer, BaseHTTPRequestHandler

# ================= 配置区域 =================
# 1. 网址列表的 GitHub Raw 地址
REMOTE_URLS_PATH = "https://raw.githubusercontent.com/wh1813/workflows/main/urls.txt"

# 2. 节点列表的 GitHub Raw 地址 (一行一个 vless:// 链接)
REMOTE_XRAY_PATH = "https://raw.githubusercontent.com/wh1813/workflows/main/xray.txt"

# 3. 每访问多少个网页切换一次 IP (防止IP被风控)
RESTART_INTERVAL = 50
# ===========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# --- 模块1: VLESS 链接解析器 ---
def parse_vless(url):
    """将 vless:// 字符串解析为 Xray 配置字典"""
    try:
        if not url.startswith("vless://"): return None
        main_part = url.split("://")[1].split("?")[0].split("#")[0]
        query_part = url.split("?")[1].split("#")[0] if "?" in url else ""
        user_info, host_port = main_part.split("@")
        host, port = host_port.split(":")
        params = dict(urllib.parse.parse_qsl(query_part))
        return {
            "uuid": user_info,
            "address": host,
            "port": int(port),
            "type": params.get("type", "tcp"),
            "security": params.get("security", "none"),
            "sni": params.get("sni", ""),
            "path": params.get("path", "/"),
            "host": params.get("host", ""),
            "fp": params.get("fp", "")
        }
    except Exception as e:
        logging.error(f"解析节点链接失败: {e}")
        return None

# --- 模块2: 代理服务管理 (Xray) ---
def check_proxy_connectivity():
    """测试当前代理是否通畅 (访问百度)"""
    try:
        proxies = {
            "http": "http://127.0.0.1:10808",
            "https": "http://127.0.0.1:10808"
        }
        r = requests.get("https://www.baidu.com", proxies=proxies, timeout=5)
        if r.status_code == 200:
            return True
    except:
        return False
    return False

def start_xray_with_node(node_url):
    """配置并启动 Xray，返回是否成功"""
    node = parse_vless(node_url)
    if not node: return False
    
    config = {
        "log": {"loglevel": "error"},
        "inbounds": [{"port": 10808, "listen": "127.0.0.1", "protocol": "http", "settings": {"udp": True}}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": node["address"],
                    "port": node["port"],
                    "users": [{"id": node["uuid"], "encryption": "none"}]
                }]
            },
            "streamSettings": {
                "network": node["type"],
                "security": node["security"],
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
            logging.info(f"    -> [节点切换成功] 目标地址: {node['address']}")
            return True
        else:
            logging.warning(f"    -> [节点不可用] 无法联网，跳过: {node['address']}")
            return False
    except Exception as e:
        logging.error(f"Xray 启动错误: {e}")
        return False

def rotate_proxy():
    """读取文件并轮换到一个可用的节点"""
    if not os.path.exists("xray.txt"):
        logging.error("未找到 xray.txt，无法启动代理")
        return False

    with open("xray.txt", "r") as f:
        nodes = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not nodes:
        logging.error("xray.txt 是空的")
        return False

    random.shuffle(nodes)
    logging.info(f">>> [代理] 正在从 {len(nodes)} 个节点中寻找可用节点...")

    for node_url in nodes:
        if start_xray_with_node(node_url):
            return True
    
    logging.error("!!! 所有节点均测试失败，请检查 xray.txt !!!")
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

# --- 模块4: 强力清理 ---
def force_kill_chrome():
    subprocess.run("pkill -9 -f chrome", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("pkill -9 -f undetected_chromedriver", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("rm -rf /tmp/.org.chromium.*", shell=True, stderr=subprocess.DEVNULL)

# --- 模块5: 浏览器配置 (带点击能力) ---
def get_driver():
    force_kill_chrome()
    data_dir = "/tmp/chrome_user_data"
    if os.path.exists(data_dir): shutil.rmtree(data_dir, ignore_errors=True)

    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-data-dir={data_dir}")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    
    # 强制走本地 Xray 代理
    options.add_argument("--proxy-server=http://127.0.0.1:10808")

    # 伪装
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

    try:
        # 指定版本防止不兼容
        driver = uc.Chrome(options=options, version_main=144, use_subprocess=True, headless=True)
        driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": {"Referer": "https://www.baidu.com/link?url=KkKS"}})
        driver.set_page_load_timeout(60)
        return driver
    except Exception as e:
        logging.error(f"浏览器启动失败: {e}")
        force_kill_chrome()
        return None

# --- 模拟点击逻辑 ---
def simulate_interaction(driver):
    """在页面上寻找元素并点击，模拟真实行为"""
    try:
        # 1. 随机滚动一下，装作在看
        driver.execute_script(f"window.scrollTo(0, {random.randint(300, 800)});")
        time.sleep(1)

        # 2. 尝试寻找可点击的元素
        # 这里你可以修改为你特定的目标，比如:
        # target = driver.find_element(By.XPATH, "//a[contains(text(), '下载')]")
        
        # 下面是一个通用的“随便点点”逻辑，它会找页面里正文区域的链接
        # 优先找 p 标签里的 a 链接，或者 list 里的链接
        potential_links = driver.find_elements(By.CSS_SELECTOR, "p a, li a, .btn, button")
        
        if potential_links:
            # 随机选一个看着顺眼的
            target = random.choice(potential_links)
            
            # 确保元素可见
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target)
            time.sleep(1)
            
            logging.info(f"    🖱️ 模拟点击元素: {target.text[:10]}...")
            
            # 使用 JS 点击防止被遮挡
            driver.execute_script("arguments[0].click();", target)
            
            # 点击后稍微等一下，让新请求发出去
            time.sleep(3)
        else:
            logging.info("    👀 页面没找到明显的按钮，跳过点击")

    except Exception as e:
        logging.warning(f"    ⚠️ 模拟交互时出错 (不影响主流程): {e}")

# --- 主逻辑 ---
def run_automation():
    update_remote_files()

    # 检查代理
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

            # 轮换 IP 逻辑
            if index % RESTART_INTERVAL == 0:
                logging.info(f">>> [维护] 已访问 {index} 个，正在切换节点并重启...")
                try: driver.quit()
                except: pass
                if not rotate_proxy():
                    logging.error("没有可用节点")
                    break 
                driver = get_driver()
                if not driver: break

            # 访问页面
            logging.info(f"[{index}/{len(urls)}] 访问: {url}")
            driver.get(url)
            
            # === 这里插入了模拟点击逻辑 ===
            simulate_interaction(driver)
            # ==========================
            
            logging.info(f"    ✅ 完成")

        except Exception as e:
            logging.error(f"    -> 错误: {e}")
            # 出错可能是代理挂了，尝试换个节点
            try: driver.quit()
            except: pass
            logging.warning(">>> 异常恢复中，切换节点...")
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
    if not rotate_proxy():
        logging.error("启动失败：无可用节点")
        time.sleep(60)
    
    while True:
        try: run_automation()
        except: pass
        # 跑完一轮 urls.txt 后，休息 10 分钟再跑
        logging.info("💤 本轮结束，休息 10 分钟...")
        time.sleep(600)
