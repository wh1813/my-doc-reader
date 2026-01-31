import os
import time
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # 强制指定版本 144
    driver = uc.Chrome(options=options, version_main=144, use_subprocess=True)
    return driver

# ==================== Book118 逻辑 (保持不变) ====================
def crawl_book118(driver):
    urls = []
    base_domain = "https://max.book118.com"
    cookie_str = os.environ.get("COOKIE_BOOK118")
    
    if not cookie_str:
        logging.warning("⚠️ [Book118] 未配置 COOKIE_BOOK118，跳过")
        return []

    try:
        logging.info(">>> [Book118] 开始抓取...")
        driver.get("https://max.book118.com/")
        driver.delete_all_cookies()
        for item in cookie_str.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                driver.add_cookie({'name': k.strip(), 'value': v.strip()})
        
        target_url = "https://max.book118.com/user_center_v1/doc/index/index.html#audited"
        driver.get(target_url)
        time.sleep(5)

        last_page_first_link = None
        
        for page in range(1, 101):
            logging.info(f"   [Book118] 分析第 {page} 页...")
            try: WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
            except: pass

            rows = driver.find_elements(By.TAG_NAME, "tr")
            current_page_links = []
            
            for row in rows:
                try:
                    try:
                        views_text = row.find_element(By.CSS_SELECTOR, "td.col-click").text.strip()
                        if "万" in views_text: views = float(views_text.replace("万", "")) * 10000
                        else: views = int(views_text)
                    except: continue

                    if views < 15:
                        link_elm = row.find_element(By.CSS_SELECTOR, "td.col-title a")
                        link = link_elm.get_attribute("href")
                        if link and "http" not in link: link = base_domain + link
                        if link: current_page_links.append(link)
                except: continue

            if not current_page_links:
                logging.info("   本页无符合条件的低热度链接")
                if not rows: break # 连行都没找到，说明可能出错了或到底了
            
            # 防重
            if current_page_links and current_page_links[0] == last_page_first_link:
                logging.info("🛑 检测到重复页面，停止")
                break
            if current_page_links: last_page_first_link = current_page_links[0]
            
            urls.extend(current_page_links)
            logging.info(f"      -> 捕获 {len(current_page_links)} 个低热度链接")

            try:
                next_btn = driver.find_element(By.XPATH, "//a[contains(text(), '下一页')]")
                href = next_btn.get_attribute("href")
                if not href or "javascript" in href: break
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(4)
            except: break

    except Exception as e:
        logging.error(f"❌ [Book118] 出错: {e}")
    
    return urls

# ==================== RenrenDoc 逻辑 (深度修复版) ====================
def crawl_renrendoc_single(driver, cookie_name, cookie_value):
    urls = []
    if not cookie_value: return []
    
    logging.info(f">>> [{cookie_name}] 开始抓取...")
    try:
        driver.get("https://www.renrendoc.com/")
        driver.delete_all_cookies()
        for item in cookie_value.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                driver.add_cookie({'name': k.strip(), 'value': v.strip()})

        driver.get("https://www.renrendoc.com/renrendoc_v1/MCBookList/published.html")
        time.sleep(5)

        last_page_links_set = set()

        for page in range(1, 101):
            logging.info(f"   [{cookie_name}] 分析第 {page} 页...")
            
            # 1. 查找所有表格行 (TR)
            rows = driver.find_elements(By.TAG_NAME, "tr")
            if not rows:
                logging.warning("   ⚠️ 未找到表格行，尝试查找列表容器...")
                # 备用方案：有些页面可能是 div 列表，这里保留扩充空间
            
            current_page_found = []
            
            for row in rows:
                try:
                    # 2. 在每一行中寻找 "数字/数字" 格式的单元格
                    # 获取该行所有单元格
                    cols = row.find_elements(By.TAG_NAME, "td")
                    
                    is_low_view = False
                    link_found = None
                    
                    for col in cols:
                        text = col.text.strip()
                        
                        # --- 核心识别逻辑 ---
                        # 检查是否包含 "/" 且被分割的两部分都是数字
                        if "/" in text:
                            parts = text.split("/")
                            if len(parts) == 2 and parts[0].isdigit():
                                views = int(parts[0]) # 提取斜杠左边的浏览量
                                
                                if views < 15:
                                    is_low_view = True
                                else:
                                    # 如果浏览量 >= 15，这行直接跳过，不用找链接了
                                    break 
                        
                        # 同时在这个循环里找链接 (通常在标题列)
                        # 为了保险，我们找该行内所有含有 "renrendoc.com/p-" 的链接
                        if not link_found:
                            try:
                                # 只找这一个单元格里的链接
                                sub_links = col.find_elements(By.TAG_NAME, "a")
                                for sub_link in sub_links:
                                    href = sub_link.get_attribute("href")
                                    if href and ("renrendoc.com/p-" in href or "renrendoc.com/paper/" in href):
                                        link_found = href
                                        break
                            except: pass

                    # 3. 只有当：是低浏览量 AND 找到了链接，才加入列表
                    if is_low_view and link_found:
                        current_page_found.append(link_found)
                        
                except Exception as row_e:
                    continue
            
            # === 防重与翻页 ===
            current_set = set(current_page_found)
            if not current_page_found and not rows:
                logging.info("   本页无数据，停止")
                break
                
            if current_set and current_set == last_page_links_set:
                logging.info(f"🛑 [{cookie_name}] 页面重复，停止")
                break
                
            last_page_links_set = current_set
            urls.extend(current_page_found)
            logging.info(f"      -> 捕获 {len(current_page_found)} 个低热度链接")
            
            try:
                next_btn = driver.find_element(By.XPATH, "//a[contains(@class, 'paginator') and contains(text(), '下一页')]")
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(4)
            except: 
                logging.info(f"   [{cookie_name}] 翻页结束")
                break
                
    except Exception as e:
        logging.error(f"❌ [{cookie_name}] 出错: {e}")
    
    return urls

def crawl_renrendoc_all(driver):
    all_renren_urls = []
    # 优先从环境变量读，如果本地测试没配置环境变量，可以手动填
    renren_keys = ["COOKIE_RENREN1", "COOKIE_RENREN2"]
    
    for key in renren_keys:
        val = os.environ.get(key)
        if val:
            all_renren_urls.extend(crawl_renrendoc_single(driver, key, val))
        else:
            logging.info(f"ℹ️ {key} 未配置，跳过")
            
    return all_renren_urls

# ==================== 主程序 ====================
if __name__ == "__main__":
    logging.info("🚀 启动智能筛选爬虫 (仅抓取阅读量 < 15)...")
    
    driver = get_driver()
    if driver:
        final_urls = []
        
        # 1. Book118
        final_urls.extend(crawl_book118(driver))
        time.sleep(3)
        
        # 2. Renren
        final_urls.extend(crawl_renrendoc_all(driver))
        
        # 3. 保存
        # 注意：这里是覆盖写入 ('w')，这意味着每次生成都是全新的“待处理名单”
        final_urls = list(set(final_urls))
        
        if final_urls:
            with open("urls.txt", "w", encoding="utf-8") as f:
                for url in final_urls:
                    f.write(url + "\n")
            logging.info(f"🎉 抓取完成！共生成 {len(final_urls)} 个【低热度】链接")
            logging.info("💾 结果已保存至 urls.txt，请推送到 GitHub")
        else:
            logging.warning("⚠️ 本次未抓取到任何 < 15 阅读量的链接 (可能是都刷上去了，或者Cookie失效)")
            
        try: driver.quit()
        except: pass
