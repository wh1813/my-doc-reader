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
    driver = uc.Chrome(options=options, version_main=144, use_subprocess=True)
    return driver

# ==================== Book118 逻辑 ====================
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

        # 用于防重：记录上一页找到的第一个链接，如果当前页第一个链接和上一页一样，说明没翻过去
        last_page_first_link = None
        
        # 扩大翻页数到 100 (约2000条)
        for page in range(1, 101):
            logging.info(f"   正在分析第 {page} 页...")
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
            except: pass

            rows = driver.find_elements(By.TAG_NAME, "tr")
            current_page_links = []
            
            for row in rows:
                try:
                    # 获取点击量
                    try:
                        views_text = row.find_element(By.CSS_SELECTOR, "td.col-click").text.strip()
                        if "万" in views_text:
                            views = float(views_text.replace("万", "")) * 10000
                        else:
                            views = int(views_text)
                    except: continue

                    if views < 15:
                        link_elm = row.find_element(By.CSS_SELECTOR, "td.col-title a")
                        link = link_elm.get_attribute("href")
                        if link and "http" not in link: link = base_domain + link
                        if link: 
                            current_page_links.append(link)
                except: continue

            # === 防重/翻页失败检测 ===
            if not current_page_links:
                logging.info("⚠️ 本页未找到有效链接，停止翻页")
                break
                
            current_first_link = current_page_links[0]
            if current_first_link == last_page_first_link:
                logging.info("🛑 检测到重复内容（翻页未生效或已达限制），停止抓取")
                break
            
            last_page_first_link = current_first_link
            urls.extend(current_page_links)
            logging.info(f"   第 {page} 页捕获 {len(current_page_links)} 个链接")

            # 执行翻页
            try:
                next_btn = driver.find_element(By.XPATH, "//a[contains(text(), '下一页')]")
                href = next_btn.get_attribute("href")
                # 如果 href 为空或者是 javascript:; 说明是最后一页
                if not href or "javascript" in href: 
                    logging.info("已到达最后一页")
                    break
                    
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(4)
            except: 
                logging.info("未找到下一页按钮，结束")
                break

    except Exception as e:
        logging.error(f"❌ [Book118] 出错: {e}")
    
    return urls

# ==================== RenrenDoc 逻辑 (多账号 + 防重) ====================
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

        for page in range(1, 101): # 扩大范围
            logging.info(f"   [{cookie_name}] 分析第 {page} 页...")
            
            links = driver.find_elements(By.TAG_NAME, "a")
            current_page_found = []
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href and "renrendoc.com/p-" in href:
                        current_page_found.append(href)
                except: continue
            
            # === 防重检测 ===
            current_set = set(current_page_found)
            if not current_set:
                logging.info("本页无数据，停止")
                break
                
            # 如果当前页找到的所有链接，都已经在上一页出现过（说明页面没变）
            # 或者当前页内容和上一页完全一样
            if current_set == last_page_links_set:
                logging.info(f"🛑 [{cookie_name}] 检测到重复页面（已达限制），停止")
                break
                
            last_page_links_set = current_set
            urls.extend(current_page_found)
            
            # 翻页
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
    driver = get_driver()
    if driver:
        final_urls = []
        
        # 1. Book118
        final_urls.extend(crawl_book118(driver))
        
        # 2. Renren (Renren1 + Renren2)
        final_urls.extend(crawl_renrendoc_all(driver))
        
        # 3. 去重并保存
        final_urls = list(set(final_urls))
        if final_urls:
            with open("urls.txt", "w", encoding="utf-8") as f:
                for url in final_urls:
                    f.write(url + "\n")
            logging.info(f"🎉 抓取完成！共更新 {len(final_urls)} 个链接")
        else:
            logging.info("⚠️ 本次未抓取到任何链接")
            
        try: driver.quit()
        except: pass
