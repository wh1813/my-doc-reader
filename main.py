import os
import time
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_driver():
    options = uc.ChromeOptions()
    # 生产环境/GitHub Actions 请务必开启 headless
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    driver = uc.Chrome(options=options, version_main=144, use_subprocess=True)
    return driver

# ==================== Book118 爬虫 (基于已验证的 HTML) ====================
def crawl_book118(driver):
    urls = []
    base_domain = "https://max.book118.com"
    logging.info(">>> [Book118] 开始抓取...")

    try:
        # 1. 登录
        driver.get("https://max.book118.com/")
        cookie_str = os.environ.get("COOKIE_BOOK118")
        if not cookie_str:
            logging.error("❌ [Book118] 未配置 Cookie！")
            return []
        
        driver.delete_all_cookies()
        for item in cookie_str.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                driver.add_cookie({'name': k.strip(), 'value': v.strip()})
        
        # 2. 访问新版后台
        # 注意：这里使用你提供的新版后台地址
        start_url = "https://max.book118.com/user_center_v1/doc/index/index.html#audited"
        driver.get(start_url)
        time.sleep(5) 

        # 3. 循环翻页
        for page in range(1, 6): # 爬取前 5 页
            logging.info(f"--- [Book118] 分析第 {page} 页 ---")
            
            # 等待列表加载 (防止网络慢导致抓空)
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
            except:
                logging.warning("等待表格超时或页面为空")

            # A. 分析当前页数据
            rows = driver.find_elements(By.TAG_NAME, "tr")
            found_count = 0
            for row in rows:
                try:
                    # 获取点击量 (基于之前的 HTML: td.col-click)
                    try:
                        views_elm = row.find_element(By.CSS_SELECTOR, "td.col-click")
                        views_text = views_elm.text.strip()
                        if "万" in views_text:
                            views = float(views_text.replace("万", "")) * 10000
                        else:
                            views = int(views_text)
                    except:
                        continue # 没找到点击量，可能是表头
                    
                    # 筛选点击量 < 15
                    if views < 15:
                        # 获取链接 (基于之前的 HTML: td.col-title a)
                        title_elm = row.find_element(By.CSS_SELECTOR, "td.col-title a")
                        link = title_elm.get_attribute("href")
                        
                        # 补全链接
                        if link and "http" not in link: 
                            link = base_domain + link
                        
                        if link:
                            urls.append(link)
                            logging.info(f"✅ [Book118] 捕获: {link}")
                            found_count += 1
                except:
                    continue

            # B. 执行翻页 (基于你提供的 HTML)
            # HTML: <a href="/user_center_v1/...">下一页</a>
            try:
                # 使用 XPath 精准查找文字为"下一页"的链接
                next_btn = driver.find_element(By.XPATH, "//a[contains(text(), '下一页')]")
                
                # 检查是否还有下一页 (如果 href 是当前页或者 javascript:; 可能就是没了)
                href = next_btn.get_attribute("href")
                if not href or "javascript" in href:
                    logging.info("没有下一页了")
                    break
                    
                logging.info("正在点击下一页...")
                # 直接点击比 get(href) 更稳，因为它能保持 Session 上下文
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(5) # 等待新页面加载
            except Exception as e:
                logging.info(f"未找到下一页按钮，爬取结束。")
                break

    except Exception as e:
        logging.error(f"❌ [Book118] 异常: {e}")

    return urls

# ==================== RenrenDoc 爬虫 (基于已验证的翻页) ====================
def crawl_renrendoc(driver):
    urls = []
    logging.info(">>> [RenrenDoc] 开始抓取...")

    try:
        # 1. 登录
        driver.get("https://www.renrendoc.com/")
        cookie_str = os.environ.get("COOKIE_RENRENDOC")
        if not cookie_str:
            logging.warning("⚠️ [RenrenDoc] 未配置 Cookie，跳过。")
            return []
        
        driver.delete_all_cookies()
        for item in cookie_str.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                driver.add_cookie({'name': k.strip(), 'value': v.strip()})

        # 2. 访问后台
        start_url = "https://www.renrendoc.com/renrendoc_v1/MCBookList/published.html"
        driver.get(start_url)
        time.sleep(5)

        # 3. 循环翻页
        for page in range(1, 6):
            logging.info(f"--- [RenrenDoc] 分析第 {page} 页 ---")
            
            # A. 分析当前页数据 (暂时使用通用抓取，因缺少列表 HTML)
            # 策略：抓取页面主要内容区的所有文档链接
            # 人人文档的链接特征通常包含 /p-
            links = driver.find_elements(By.TAG_NAME, "a")
            found_count = 0
            for link in links:
                try:
                    href = link.get_attribute("href")
                    # 简单筛选：必须包含 renrendoc.com 且包含文档 ID 特征
                    if href and "renrendoc.com/p-" in href:
                        urls.append(href)
                        found_count += 1
                        # logging.info(f"✅ [RenrenDoc] 捕获: {href}") # 链接太多可以关掉日志
                except:
                    continue
            logging.info(f"    本页提取到 {found_count} 个潜在文档链接")

            # B. 执行翻页 (基于你提供的 HTML)
            # HTML: <a class="paginator" href="...?page=7">下一页</a>
            try:
                # 使用 CSS 选择器定位 class="paginator" 且文字包含"下一页"
                # 这里用 XPATH 最稳，因为 paginator 可能有多个(上一页/页码)
                next_btn = driver.find_element(By.XPATH, "//a[contains(@class, 'paginator') and contains(text(), '下一页')]")
                
                logging.info("点击下一页...")
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(4)
            except:
                logging.info("未找到下一页按钮，爬取结束。")
                break

    except Exception as e:
        logging.error(f"❌ [RenrenDoc] 异常: {e}")
    
    return urls

# ==================== 主程序 ====================
def save_urls(urls):
    if not urls: return
    urls = list(set(urls)) # 去重
    with open("urls.txt", "w", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")
    logging.info(f"🎉 任务完成！urls.txt 已更新，共 {len(urls)} 个链接。")

if __name__ == "__main__":
    driver = get_driver()
    if driver:
        all_urls = []
        all_urls.extend(crawl_book118(driver))
        all_urls.extend(crawl_renrendoc(driver))
        save_urls(all_urls)
        try: driver.quit()
        except: pass
