#!/usr/bin/env python3
"""
测试Boss直聘搜索页面结构
"""

import logging
from modules.boss_zhipin import BossZhipinClient

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_search_page():
    """
    测试搜索页面结构
    """
    client = BossZhipinClient(headless=False)
    try:
        # 登录
        if not client.login():
            logger.error('登录失败')
            return
        
        # 搜索职位
        search_url = 'https://www.zhipin.com/beijing/?query=Python%20开发工程师&page=1'
        client.page.goto(search_url, wait_until='networkidle')
        
        # 保存页面HTML到文件
        html_content = client.page.content()
        with open('search_page.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info('搜索页面HTML已保存到 search_page.html')
        
        # 尝试不同的选择器
        selectors_to_test = [
            '//div[contains(@class, "job-card")]',
            '//div[contains(@class, "job-primary")]',
            '//li[contains(@class, "job-card-wrapper")]',
            '//div[@class="job-list"]//div[@class="job-card"]',
            '//div[@class="job-list"]//div[@class="job-primary"]'
        ]
        
        for selector in selectors_to_test:
            elements = client.page.locator(selector)
            count = elements.count()
            logger.info(f'选择器 {selector} 找到 {count} 个元素')
            
    except Exception as e:
        logger.error(f'测试失败: {e}')
    finally:
        client.close()

if __name__ == '__main__':
    test_search_page()
