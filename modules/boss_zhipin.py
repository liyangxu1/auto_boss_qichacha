#!/usr/bin/env python3
"""
Boss直聘客户端模块

功能：
1. 登录信息管理
2. 扫码登录功能
3. 职位搜索
4. 职位详情获取
"""

import os
import json
import time
import logging
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright

# 配置日志
# 创建logs目录（如果不存在）
import os
os.makedirs('logs', exist_ok=True)

# 配置日志，同时输出到控制台和文件
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/boss_zhipin.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BossZhipinClient:
    """
    Boss直聘客户端类
    """
    
    def __init__(self, headless=False):
        self.config_dir = os.path.join(os.path.dirname(__file__), '../config')
        self.login_info_file = os.path.join(self.config_dir, 'login_info.json')
        self.playwright = None
        self.browser = None
        self.page = None
        self.login_status = False
        self.headless = headless
        
        # 创建配置目录
        os.makedirs(self.config_dir, exist_ok=True)
        
    def save_login_info(self):
        """
        保存登录信息（包括Cookie）到本地文件
        
        Returns:
            bool: 保存是否成功
        """
        try:
            if not self.browser or not self.page:
                logger.error('浏览器未初始化，无法保存登录信息')
                return False
            
            # 获取当前页面的Cookie
            cookies = self.page.context.cookies()
            
            # 获取当前URL，用于检查是否已登录
            current_url = self.page.url
            
            login_info = {
                'cookies': cookies,
                'last_login_url': current_url,
                'save_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.login_info_file, 'w', encoding='utf-8') as f:
                json.dump(login_info, f, ensure_ascii=False, indent=2)
            
            logger.info('登录信息（Cookie）保存成功')
            return True
        except Exception as e:
            logger.error(f'保存登录信息失败: {e}')
            return False
    
    def load_login_info(self):
        """
        从本地文件加载登录信息
        
        Returns:
            dict or None: 登录信息字典（包含Cookie），如果文件不存在或读取失败则返回None
        """
        try:
            if os.path.exists(self.login_info_file):
                with open(self.login_info_file, 'r', encoding='utf-8') as f:
                    login_info = json.load(f)
                    logger.info('登录信息（Cookie）加载成功')
                    return login_info
            else:
                logger.warning('登录信息文件不存在')
                return None
        except Exception as e:
            logger.error(f'加载登录信息失败: {e}')
            return None
    
    def init_driver(self):
        """
        初始化Playwright浏览器
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 启动Playwright
            self.playwright = sync_playwright().start()
            
            # 启动Chrome浏览器
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,  # 使用传入的headless参数
                args=[
                    '--start-maximized',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # 创建新页面
            self.page = self.browser.new_page(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            logger.info('Playwright浏览器初始化成功')
            return True
        except Exception as e:
            logger.error(f'Playwright浏览器初始化失败: {e}')
            return False
    
    def open_login_page(self):
        """
        打开Boss直聘登录页面，让用户手动完成登录
        
        Returns:
            bool: 登录页面是否成功打开
        """
        try:
            # 初始化浏览器
            if not self.browser:
                init_success = self.init_driver()
                if not init_success:
                    return False
            
            # 打开Boss直聘登录页面
            self.page.goto('https://login.zhipin.com/?ka=header-login', wait_until='networkidle')
            logger.info('打开Boss直聘登录页面成功')
            
            # 等待页面加载完成
            time.sleep(3)
            
            logger.info('请在浏览器中手动完成登录操作（扫码或输入账号密码）')
            logger.info('登录完成后，请按回车键继续...')
            
            # 等待用户输入，确认登录完成
            input()
            
            # 检查登录状态
            if self.check_login_status():
                logger.info('登录成功！正在保存登录信息...')
                # 保存登录信息
                if self.save_login_info():
                    logger.info('登录信息已保存，下次可以直接使用')
                else:
                    logger.warning('保存登录信息失败')
                return True
            else:
                logger.error('登录失败，请检查登录状态')
                return False
                
        except Exception as e:
            logger.error(f'打开登录页面失败: {e}')
            self.login_status = False
            return False
    
    def check_login_status(self):
        """
        检查登录状态
        
        Returns:
            bool: 登录是否成功
        """
        try:
            if not self.browser:
                logger.error('浏览器未初始化')
                return False
            
            current_url = self.page.url
            logger.debug(f'当前URL: {current_url}')
            
            # 检查方法1: URL不包含login且包含zhipin.com
            if 'zhipin.com' in current_url and 'login' not in current_url:
                logger.info('登录成功（URL检查通过）')
                self.login_status = True
                return True
            
            # 检查方法2: 尝试查找登录后的元素（如个人中心、用户头像等）
            try:
                # 查找个人中心或用户头像等登录后才会出现的元素
                user_elements = [
                    '//div[@class="user-avatar"]',  # 用户头像
                    '//a[@ka="header-user-center"]',  # 个人中心链接
                    '//div[@class="nav-user"]',  # 用户导航栏
                    '//span[contains(@class, "user-name")]'  # 用户名
                ]
                
                for selector in user_elements:
                    element = self.page.locator(selector)
                    if element.count() > 0:
                        logger.info('登录成功（找到登录后元素）')
                        self.login_status = True
                        return True
            except Exception as e:
                logger.debug(f'查找登录后元素失败: {e}')
            
            # 检查方法3: 检查页面标题
            page_title = self.page.title()
            if '登录' not in page_title:
                logger.info('登录成功（页面标题不包含登录）')
                self.login_status = True
                return True
            
            logger.info('尚未登录成功')
            self.login_status = False
            return False
        except Exception as e:
            logger.error(f'检查登录状态失败: {e}')
            return False
    
    def login(self):
        """
        登录Boss直聘（先尝试加载保存的Cookie，失败则让用户手动登录）
        
        Returns:
            bool: 登录是否成功
        """
        try:
            # 初始化浏览器
            if not self.browser:
                init_success = self.init_driver()
                if not init_success:
                    return False
            
            # 先尝试加载保存的登录信息（Cookie）
            login_info = self.load_login_info()
            if login_info and 'cookies' in login_info:
                logger.info('检测到保存的登录Cookie，尝试恢复登录状态')
                
                # 打开Boss直聘首页
                self.page.goto('https://www.zhipin.com/', wait_until='networkidle')
                logger.info('打开Boss直聘首页成功')
                
                # 添加保存的Cookie到当前页面
                try:
                    self.page.context.add_cookies(login_info['cookies'])
                    logger.info('已添加保存的Cookie')
                    
                    # 重新加载页面以应用Cookie
                    self.page.reload(wait_until='networkidle')
                    time.sleep(3)
                    
                    # 检查是否已登录
                    if 'login' not in self.page.url:
                        logger.info('登录成功（使用保存的Cookie）')
                        self.login_status = True
                        return True
                    else:
                        logger.warning('保存的Cookie已失效，需要重新登录')
                except Exception as e:
                    logger.error(f'使用保存的Cookie登录失败: {e}')
            
            # 如果没有保存的登录信息或登录信息失效，让用户手动登录
            logger.info('开始手动登录流程')
            success = self.open_login_page()
            if success:
                self.login_status = True
            return success
        except Exception as e:
            logger.error(f'登录失败: {e}')
            self.login_status = False
            return False
    

    
    def search_jobs(self, keywords: str, city: str = "北京", page: int = 1) -> List[Dict[str, Any]]:
        """
        根据关键词搜索职位，模拟真实用户输入
        
        Args:
            keywords: 搜索关键词
            city: 城市名称，默认为"北京"
            page: 页码，默认为1
            
        Returns:
            List[Dict[str, Any]]: 职位列表，每个职位包含标题、公司、薪资、位置等信息
        """
        try:
            if not self.login_status:
                logger.error('尚未登录，无法搜索职位')
                return []
            
            logger.info(f'开始搜索职位，关键词: {keywords}，城市: {city}，页码: {page}')
            
            # 访问Boss直聘搜索页面
            self.page.goto('https://www.zhipin.com/web/geek/job', wait_until='domcontentloaded', timeout=60000)
            time.sleep(5)  # 给页面更多加载时间
            
            # 找到搜索输入框并输入关键词（模拟真实用户逐字输入）
            logger.info('模拟用户逐字输入关键词...')
            # 尝试多种定位方式
            search_input = None
            input_locators = [
                '//input[@placeholder="搜索职位、公司"]',
                '//input[@name="query"]',
                '//input[@class="search-input"]'
            ]
            
            for locator in input_locators:
                if self.page.locator(locator).count() > 0:
                    search_input = self.page.locator(locator)
                    logger.info(f'使用定位器 {locator} 找到搜索输入框')
                    break
            
            if search_input:
                # 先清空输入框
                search_input.clear()
                time.sleep(0.5)
                # 使用type方法模拟逐字输入，每个字符间隔100-300ms
                search_input.type(keywords, delay=150)
                time.sleep(1)  # 模拟用户输入后的思考时间
            else:
                logger.error('未找到搜索输入框')
                return []
            
            # 点击搜索按钮
            logger.info('模拟用户点击搜索按钮...')
            # 尝试多种定位方式
            search_button = None
            
            # 方法1: 使用ka属性（最稳定）
            button_locators = [
                '//a[@ka="job_search_btn_click"]',
                '//button[@ka="job_search_btn_click"]',
                '//a[@class="search-btn"]',
                '//button[@class="search-btn"]',
                '//*[text()="搜索"]',
                '//*[@type="submit"]'
            ]
            
            for locator in button_locators:
                if self.page.locator(locator).count() > 0:
                    search_button = self.page.locator(locator)
                    logger.info(f'使用定位器 {locator} 找到搜索按钮')
                    break
            
            if search_button:
                search_button.click()
                time.sleep(5)  # 等待搜索结果加载
                # 尝试滚动页面以触发更多职位加载
                self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(2)
            else:
                logger.error('未找到搜索按钮')
                return []
            
            # 提取搜索结果
            logger.info('提取搜索结果...')
            job_list = []
            
            # 直接查找所有职位卡片，不依赖容器
            card_locators = [
                'li.job-card-box',
                '.job-card-wrapper',
                '.job-card',
                '.job-item',
                '//li[contains(@class, "job-card")]',
                '//div[contains(@class, "job-card")]'
            ]
            
            job_cards = []
            for locator in card_locators:
                cards = self.page.locator(locator).all()
                if len(cards) > 0:
                    job_cards = cards
                    logger.info(f'使用定位器 {locator} 找到 {len(job_cards)} 个职位卡片')
                    break
            
            if not job_cards:
                logger.warning('未找到职位卡片')
                # 保存当前页面HTML用于调试
                with open('search_page_debug.html', 'w', encoding='utf-8') as f:
                    f.write(self.page.content())
                logger.info('已保存搜索页面HTML到search_page_debug.html，用于调试')
                return []
            
            for i, card in enumerate(job_cards):
                try:
                    # 提取职位标题和链接
                    title = ""
                    link = ""
                    title_locators = [
                        'a.job-name',
                        '.job-title a',
                        'a[ka*="job_name"]'
                    ]
                    
                    for locator in title_locators:
                        title_element = card.locator(locator)
                        if title_element.count() > 0:
                            title = title_element.inner_text().strip()
                            link = title_element.get_attribute('href')
                            if link and not link.startswith('http'):
                                link = f'https://www.zhipin.com{link}'
                            logger.debug(f'使用定位器 {locator} 提取职位标题和链接')
                            break
                    
                    if not title:
                        logger.warning(f'未找到职位标题，跳过职位{i+1}')
                        continue
                    
                    # 提取公司名称
                    company = ""
                    company_locators = [
                        '.boss-name',
                        '.company-name',
                        'a[ka*="company_name"]'
                    ]
                    
                    for locator in company_locators:
                        company_element = card.locator(locator)
                        if company_element.count() > 0:
                            company = company_element.inner_text().strip()
                            logger.debug(f'使用定位器 {locator} 提取公司名称')
                            break
                    
                    # 提取薪资
                    salary = ""
                    salary_locators = [
                        '.job-salary',
                        '.salary',
                        '//span[contains(text(), "K")]'
                    ]
                    
                    for locator in salary_locators:
                        salary_element = card.locator(locator)
                        if salary_element.count() > 0:
                            salary = salary_element.inner_text().strip()
                            logger.debug(f'使用定位器 {locator} 提取薪资')
                            break
                    
                    # 提取位置
                    location = ""
                    location_locators = [
                        '.company-location',
                        '.location',
                        '//span[contains(@class, "location")]'
                    ]
                    
                    for locator in location_locators:
                        location_element = card.locator(locator)
                        if location_element.count() > 0:
                            location = location_element.inner_text().strip()
                            logger.debug(f'使用定位器 {locator} 提取位置')
                            break
                    
                    job = {
                        "title": title,
                        "company": company,
                        "salary": salary,
                        "location": location,
                        "link": link
                    }
                    
                    job_list.append(job)
                    logger.info(f'提取职位: {job["title"]} - {job["company"]}')
                except Exception as e:
                    logger.error(f'提取职位{i+1}信息失败: {e}', exc_info=True)
                    continue
            
            logger.info(f'搜索完成，找到{len(job_list)}个相关职位')
            return job_list
            
        except Exception as e:
            logger.error(f'搜索职位失败: {e}', exc_info=True)
            return []
    
    def get_job_detail(self, job_link: str) -> Dict[str, Any]:
        """
        获取职位详情信息
        
        Args:
            job_link: 职位链接
            
        Returns:
            Dict[str, Any]: 职位详情信息
        """
        try:
            if not self.login_status:
                logger.error('尚未登录，无法获取职位详情')
                return {}
            
            logger.info(f'打开职位详情页面: {job_link}')
            
            # 打开职位详情页面，增加超时时间并优化等待条件
            self.page.goto(job_link, wait_until='domcontentloaded', timeout=60000)
            time.sleep(5)  # 增加等待时间，确保页面充分加载
            
            # 提取职位详情
            detail = {
                'link': job_link,
                'title': "",
                'company': "",
                'salary': "",
                'location': "",
                'job_description': "",
                'work_content': "",
                'requirements': "",
                'company_description': ""
            }
            
            # 使用用户提供的精确定位器提取职位描述，只选择第一个元素
            logger.info('使用精确定位器提取职位描述...')
            try:
                job_desc_element = self.page.locator('div.job-box div.inner.home-inner div.job-detail div.job-detail-section div.job-sec-text').first
                # 获取原始HTML内容，保留换行信息
                html_content = job_desc_element.inner_html()
                logger.info('获取到职位描述HTML内容')
                
                # 处理HTML标签，保留换行
                import re
                text_content = re.sub(r'<br\s*/?>', '\n', html_content)
                text_content = re.sub(r'<[^>]+>', '', text_content)
                detail['job_description'] = text_content.strip()
                logger.info('成功提取并处理职位描述')
                
                # 提取职位标题
                title_element = self.page.locator('h1')
                if title_element.count() > 0:
                    detail['title'] = title_element.inner_text().strip()
                    logger.info(f'提取到职位标题: {detail["title"]}')
                
                # 提取公司名称
                company_element = self.page.locator('h3.company-name')
                if company_element.count() > 0:
                    detail['company'] = company_element.inner_text().strip()
                    logger.info(f'提取到公司名称: {detail["company"]}')
                
                # 提取薪资
                salary_element = self.page.locator('span.salary')
                if salary_element.count() > 0:
                    detail['salary'] = salary_element.inner_text().strip()
                    logger.info(f'提取到薪资: {detail["salary"]}')
                
                # 提取位置
                location_element = self.page.locator('span.job-location')
                if location_element.count() > 0:
                    detail['location'] = location_element.inner_text().strip()
                    logger.info(f'提取到位置: {detail["location"]}')
                
                # 分离工作内容和岗位要求
                if detail['job_description']:
                    logger.info('开始分离工作内容和岗位要求...')
                    job_desc = detail['job_description']
                    
                    # 分离工作内容
                    work_content_match = re.search(r'工作内容[：:](.*?)(职位要求|任职要求|$)', job_desc, re.DOTALL)
                    if work_content_match:
                        detail['work_content'] = work_content_match.group(1).strip()
                        logger.info('成功分离工作内容')
                    
                    # 分离岗位要求
                    requirement_match = re.search(r'(职位要求|任职要求)[：:](.*?)$', job_desc, re.DOTALL)
                    if requirement_match:
                        detail['requirements'] = requirement_match.group(2).strip()
                        logger.info('成功分离岗位要求')
            except Exception as e:
                logger.warning(f'提取职位描述失败: {e}')
                # 保存当前页面HTML用于调试
                with open('detail_page_debug.html', 'w', encoding='utf-8') as f:
                    f.write(self.page.content())
                logger.info('已保存详情页面HTML到detail_page_debug.html，用于调试')
            
            logger.info(f'成功提取职位详情: {detail["title"]} - {detail["company"]}')
            return detail
            
        except Exception as e:
            logger.error(f'获取职位详情失败: {e}', exc_info=True)
            # 保存当前页面HTML用于调试
            try:
                with open('error_detail_page.html', 'w', encoding='utf-8') as f:
                    f.write(self.page.content())
                logger.info('已保存错误页面HTML到error_detail_page.html，用于调试')
            except:
                pass
            return {}
    
    def save_job_details(self, job_details: List[Dict[str, Any]], file_path: str) -> bool:
        """
        保存职位详情到本地文件
        
        Args:
            job_details: 职位详情列表
            file_path: 保存文件路径
            
        Returns:
            bool: 保存是否成功
        """
        try:
            import json
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(job_details, f, ensure_ascii=False, indent=2)
            
            logger.info(f'成功保存{len(job_details)}个职位详情到: {file_path}')
            return True
            
        except Exception as e:
            logger.error(f'保存职位详情失败: {e}')
            return False
    
    def click_start_chat(self, match_score: float = 0) -> bool:
        """
        点击"立即沟通"按钮
        
        Args:
            match_score: 匹配度分数，用于日志记录
            
        Returns:
            bool: 是否成功点击
        """
        try:
            logger.info(f"匹配度为{match_score:.2f}%，尝试点击'立即沟通'按钮...")
            
            # 等待页面加载完成
            self.page.wait_for_load_state('domcontentloaded')
            time.sleep(2)  # 额外等待确保按钮可点击
            
            # 查找"立即沟通"按钮
            # 根据用户提供的HTML结构，使用多种选择器尝试
            selectors = [
                'div.btn.btn-startchat-wrap a.btn.btn-startchat',
                'a.btn.btn-startchat',
                '.btn-startchat',
                '[ka*="go_chat_done"]',
                'a:has-text("立即沟通")',
                'text="立即沟通"'
            ]
            
            button_found = False
            for selector in selectors:
                try:
                    button = self.page.locator(selector).first
                    if button.count() > 0 and button.is_visible():
                        logger.info(f"找到'立即沟通'按钮，使用选择器: {selector}")
                        button_found = True
                        
                        # 滚动到按钮位置
                        button.scroll_into_view_if_needed()
                        time.sleep(1)
                        
                        # 点击按钮
                        button.click()
                        logger.info(f"成功点击'立即沟通'按钮！匹配度: {match_score:.2f}%")
                        
                        # 等待页面响应
                        time.sleep(3)
                        
                        # 检查是否成功（可以添加更多的成功验证逻辑）
                        return True
                        
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue
            
            if not button_found:
                logger.warning("未找到'立即沟通'按钮，可能页面结构已变化")
                # 保存页面HTML用于调试
                try:
                    with open('chat_button_debug.html', 'w', encoding='utf-8') as f:
                        f.write(self.page.content())
                    logger.info("已保存页面HTML到chat_button_debug.html")
                except:
                    pass
                
            return False
            
        except Exception as e:
            logger.error(f"点击'立即沟通'按钮失败: {e}")
            return False
    
    def get_job_detail_and_match(self, job_link: str, resume_info: Dict[str, Any], matcher) -> Dict[str, Any]:
        """
        获取职位详情并计算匹配度，如果匹配度高则自动点击"立即沟通"
        
        Args:
            job_link: 职位链接
            resume_info: 简历信息
            matcher: 职位匹配器实例
            
        Returns:
            Dict[str, Any]: 包含职位详情和匹配结果的信息
        """
        try:
            # 获取职位详情
            job_detail = self.get_job_detail(job_link)
            if not job_detail:
                logger.error("获取职位详情失败")
                return None
            
            # 计算匹配度
            match_result = matcher.calculate_overall_match(resume_info, job_detail)
            
            # 将匹配结果添加到职位详情中
            job_detail['match_result'] = match_result
            
            # 如果匹配度>=80%，自动点击"立即沟通"
            if match_result['overall_score'] >= 80:
                logger.info(f"匹配度达到{match_result['overall_score']:.2f}%，符合自动沟通条件")
                chat_success = self.click_start_chat(match_result['overall_score'])
                job_detail['auto_chat_clicked'] = chat_success
                
                if chat_success:
                    logger.info("已成功发起沟通！")
                else:
                    logger.warning("自动发起沟通失败，可能需要手动操作")
            else:
                logger.info(f"匹配度为{match_result['overall_score']:.2f}%，未达到自动沟通标准(80%)")
                job_detail['auto_chat_clicked'] = False
            
            return job_detail
            
        except Exception as e:
            logger.error(f"获取职位详情并匹配失败: {e}")
            return None
    
    def close(self):
        """
        关闭Playwright浏览器资源
        注意：根据用户要求，此方法不再自动关闭浏览器，由用户手动关闭
        """
        # 不再自动关闭浏览器资源，由用户手动关闭
        logger.info('浏览器保持打开状态，请手动关闭')
        # 以下代码已注释，如需恢复自动关闭功能可取消注释
        # if self.page:
        #     self.page.close()
        # if self.browser:
        #     self.browser.close()
        # if self.playwright:
        #     self.playwright.stop()
        # logger.info('Playwright浏览器资源已关闭')


if __name__ == "__main__":
    """
    程序入口点
    """
    try:
        # 创建Boss直聘客户端实例
        client = BossZhipinClient(headless=False)
        
        # 打开登录页面，让用户扫码登录
        logger.info("正在打开Boss直聘登录页面，请手动完成登录...")
        client.open_login_page()
        
        # 等待用户完成登录
        logger.info("请在浏览器中完成登录操作...")
        input("登录完成后，请按回车键继续...")
        
        # 保存登录信息
        client.save_login_info()
        
        # 搜索职位
        logger.info("开始搜索职位...")
        keyword = "人工智能"
        jobs = client.search_jobs(keyword)
        
        if jobs:
            logger.info(f"找到{len(jobs)}个职位")
            
            # 获取职位详情
            job_details = []
            for i, job in enumerate(jobs, 1):
                logger.info(f"正在获取第{i}/{len(jobs)}个职位的详情: {job['title']}")
                detail = client.get_job_detail(job['link'])
                if detail:
                    job_details.append(detail)
                    time.sleep(1)  # 防止请求过于频繁
            
            # 保存职位详情
            if job_details:
                output_file = "output.json"
                client.save_job_details(job_details, output_file)
                logger.info(f"已将{len(job_details)}个职位的详情保存到{output_file}")
            else:
                logger.warning("没有获取到职位详情")
        else:
            logger.warning("没有找到职位")
            
        # 保持浏览器打开
        logger.info("程序执行完成，浏览器将保持打开状态")
        
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行出错: {e}", exc_info=True)


