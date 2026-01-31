import os
import time
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ================= 配置区域 (从环境变量读取) =================
COOKIE_BOOK118 = os.environ.get("COOKIE_BOOK118", "")
COOKIE_RENREN1 = os.environ.get("COOKIE_RENREN1", "")
COOKIE_RENREN2 = os.environ.get("COOKIE_RENREN2", "")
# ===========================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_driver():
    """启动浏览器 (云端配置)"""
    options = uc.ChromeOptions()
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    logging.info("🚀 正在启动 Chrome 浏览器 (Cloud Mode)...")
    try:
        # 【关键修改】强制指定 version_main=144，解决 Docker 内版本冲突
        driver = uc.Chrome(options=options, version_main=144, use_subprocess=True)
        return driver
    except Exception as e:
        logging.error(f"❌ 浏览器启动失败: {e}")
        return None

# ==================== Book118 任务 ====================
def task_book118(cookie_str):
    if not cookie_str:
        logging.warning("⚠️ [Book118] Cookie 未配置，跳过")
        return []

    driver = get_driver()
    if not driver: return []
    
    urls = []
    base_domain = "https://max.book118.com"

    try:
        logging.info(">>> [Book118] 开始任务...")
        driver.get("https://max.book118.com/")
        driver.delete_all_cookies()
        
        for item in cookie_str.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                driver.add_cookie({'name': k.strip(), 'value': v.strip()})
        
        target_url = "https://max.book118.com/user_center_v1/doc/index/index.html#audited"
        driver.get(target_url)
        
        time.sleep(3) 
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            logging.info("   [Book118] 检测到 iframe，切换...")
            driver.switch_to.frame(0)

        last_page_first_link = None
        
        for page in range(1, 5): 
            logging.info(f"   [Book118] 正在分析第 {page} 页...")
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.title")))
            except: 
                logging.warning("   ⚠️ 等待超时：页面未加载或无数据")

            link_elements = driver.find_elements(By.CSS_SELECTOR, "a.title")
            current_page_links = []
            
            for link_elm in link_elements:
                try:
                    href = link_elm.get_attribute("href")
                    if not href or "javascript" in href: continue
                    if "http" not in href: full_url = base_domain + href
                    else: full_url = href
                    if ".shtm" in full_url or ".html" in full_url:
                        current_page_links.append(full_url)
                except: continue

            if not current_page_links:
                logging.info("⚠️ 本页无有效链接")
                break
            if current_page_links[0] == last_page_first_link:
                logging.info("🛑 页面重复，停止")
                break
            last_page_first_link = current_page_links[0]
            
            urls.extend(current_page_links)
            logging.info(f"   -> 本页捕获 {len(current_page_links)} 条")

            try:
                next_btns = driver.find_elements(By.XPATH, "//a[contains(text(), '下一页')] | //li[contains(@class, 'next')]/a")
                if not next_btns: break
                driver.execute_script("arguments[0].click();", next_btns[0])
                time.sleep(5)
            except: break

    except Exception as e:
        logging.error(f"❌ [Book118] 出错: {e}")
    finally:
        try: driver.quit()
        except: pass
    
    return urls

# ==================== Renren 任务 ====================
def task_renren(account_name, cookie_value):
    if not cookie_value: 
        logging.warning(f"⚠️ [{account_name}] Cookie 未配置，跳过")
        return []

    driver = get_driver()
    if not driver: return []
    
    urls = []
    
    try:
        logging.info(f">>> [{account_name}] 开始任务...")
        driver.get("https://www.renrendoc.com/")
        driver.delete_all_cookies()
        
        for item in cookie_value.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                driver.add_cookie({'name': k.strip(), 'value': v.strip()})

        driver.get("https://www.renrendoc.com/renrendoc_v1/MCBookList/published.html")
        time.sleep(5)

        last_page_links_set = set()

        for page in range(1, 5): 
            logging.info(f"   [{account_name}] 正在分析第 {page} 页...")
            
            links = driver.find_elements(By.TAG_NAME, "a")
            current_page_found = []
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href and ("renrendoc.com/paper/" in href or "renrendoc.com/p-" in href):
                        current_page_found.append(href)
                except: continue
            
            current_set = set(current_page_found)
            if not current_set:
                logging.info("   本页无数据")
                break
            if current_set == last_page_links_set:
                logging.info("🛑 页面重复，停止")
                break
            last_page_links_set = current_set
            
            urls.extend(current_page_found)
            logging.info(f"   -> 本页捕获 {len(current_page_found)} 条")
            
            try:
                next_btn = driver.find_element(By.XPATH, "//a[contains(text(), '下一页')]")
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(4)
            except: break
                
    except Exception as e:
        logging.error(f"❌ [{account_name}] 出错: {e}")
    finally:
        try: driver.quit()
        except: pass
    
    return urls

# ==================== 主程序 ====================
if __name__ == "__main__":
    logging.info("=== ☁️ 云端爬虫任务启动 ===")
    
    final_urls = []
    
    # 1. Book118
    final_urls.extend(task_book118(COOKIE_BOOK118))
    time.sleep(3)

    # 2. Renren 1
    final_urls.extend(task_renren("人人账号1", COOKIE_RENREN1))
    time.sleep(3)

    # 3. Renren 2
    final_urls.extend(task_renren("人人账号2", COOKIE_RENREN2))

    # 4. 保存
    logging.info("💾 正在保存...")
    unique_urls = list(set(final_urls))
    
    if unique_urls:
        with open("urls.txt", "w", encoding="utf-8") as f:
            for url in unique_urls:
                f.write(url + "\n")
        logging.info(f"✅ 成功！共保存 {len(unique_urls)} 个链接")
        
        # 简单打印出来看看
        with open("urls.txt", "r", encoding="utf-8") as f:
            print(f.read())
            
    else:
        logging.warning("⚠️ 未抓取到任何链接，请检查Cookie是否过期")
        
    # 保持运行一分钟方便看日志
    time.sleep(60)
