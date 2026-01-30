import os
import time
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

# 设置日志格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_driver():
    """启动浏览器配置"""
    options = uc.ChromeOptions()
    # 在 GitHub Actions 或服务器后台运行时必须开启 headless
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # 保持与 main.py 一致的驱动版本逻辑
    driver = uc.Chrome(options=options, version_main=144, use_subprocess=True)
    return driver

def crawl_book118_user_center(driver):
    target_urls = []
    base_domain = "https://max.book118.com" # 用于补全相对路径
    
    try:
        logging.info(">>> [爬虫] 正在初始化 Book118...")
        driver.get("https://max.book118.com/")
        
        # 1. 注入 Cookie (从环境变量获取)
        cookie_str = os.environ.get("COOKIE_BOOK118")
        if not cookie_str:
            logging.error("❌ 未检测到 Cookie，请检查 GitHub Secrets (COOKIE_BOOK118)！")
            return []
            
        logging.info("正在注入登录凭证...")
        driver.delete_all_cookies()
        for item in cookie_str.split(';'):
            if '=' in item:
                key_val = item.strip().split('=', 1)
                if len(key_val) == 2:
                    driver.add_cookie({'name': key_val[0], 'value': key_val[1]})
        
        # 2. 跳转到文档管理后台
        user_center_url = "https://max.book118.com/user_center/doc_manage" 
        logging.info(f"正在跳转后台: {user_center_url}")
        driver.get(user_center_url)
        time.sleep(5) # 等待页面加载
        
        # 简单检查是否登录成功
        if "login" in driver.current_url:
            logging.error("❌ 登录失败，Cookie 可能已过期，请重新获取！")
            return []

        # 3. 循环爬取前 5 页 (可根据需要修改范围)
        for page in range(1, 6):
            logging.info(f"--- 正在分析第 {page} 页 ---")
            
            rows = driver.find_elements(By.TAG_NAME, "tr")
            found_count = 0
            
            for row in rows:
                try:
                    # --- A. 获取点击量 ---
                    try:
                        views_element = row.find_element(By.CSS_SELECTOR, "td.col-click")
                        views_text = views_element.text.strip()
                    except:
                        continue # 跳过非文档行
                    
                    # 统一转换为数字
                    views = 0
                    if "万" in views_text:
                        views = float(views_text.replace("万", "")) * 10000
                    elif views_text.isdigit():
                        views = int(views_text)
                    else:
                        continue 

                    # --- B. 筛选条件：点击量 < 15 ---
                    if views < 15:
                        # --- C. 获取链接 ---
                        title_elem = row.find_element(By.CSS_SELECTOR, "td.col-title a.title")
                        link_href = title_elem.get_attribute("href")
                        doc_title = title_elem.get_attribute("title") or "无标题"
                        
                        # 补全链接
                        if link_href and not link_href.startswith("http"):
                            link_href = base_domain + link_href
                        
                        if link_href:
                            target_urls.append(link_href)
                            logging.info(f"✅ 捕获: [{views}次] {doc_title}")
                            found_count += 1
                            
                except Exception:
                    continue 
            
            if found_count == 0:
                logging.info("本页没有符合条件的低频文档")
            
            # --- D. 翻页 ---
            if page < 5:
                next_url = f"{user_center_url}?page={page+1}"
                driver.get(next_url)
                time.sleep(3)

    except Exception as e:
        logging.error(f"❌ 运行出错: {e}")

    return target_urls

def save_urls(urls):
    if not urls:
        logging.info("本次没有抓取到链接，不更新文件。")
        return
    
    logging.info(f"正在保存 {len(urls)} 个链接到 urls.txt...")
    # 覆盖写入 urls.txt
    with open("urls.txt", "w", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")
    logging.info("🎉 保存成功！")

if __name__ == "__main__":
    driver = get_driver()
    if driver:
        urls = crawl_book118_user_center(driver)
        save_urls(urls)
        try:
            driver.quit()
        except:
            pass