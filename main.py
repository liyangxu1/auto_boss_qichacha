#!/usr/bin/env python3
"""
主程序入口，实现完整的Boss直聘职位搜索流程

核心流程：
1. 登录Boss直聘
2. 解析简历
3. 用AI提取简历内容生成搜索关键词
4. 根据关键词搜索职位并保存前20个职位的详细信息
"""

import os
import sys
import logging
from modules.boss_zhipin import BossZhipinClient
from modules.resume_parser import parse_resume
from modules.ai_keyword_extractor import AIKeywordExtractor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    主程序入口
    """
    logger.info('开始执行Boss直聘职位搜索流程')
    exit_code = 0
    boss_client = None
    
    # 1. 登录Boss直聘
    logger.info('步骤1: 登录Boss直聘')
    boss_client = BossZhipinClient(headless=False)  # 不使用无头模式，便于用户手动登录
    
    try:
        login_success = boss_client.login()
        if not login_success:
            logger.error('登录失败，程序终止')
            exit_code = 1
        else:
            # 2. 解析简历（暂时注释）
            # logger.info('步骤2: 解析简历')
            # resume_path = os.path.join(os.path.dirname(__file__), 'data', 'jianli', '李阳旭-AI应用开发工程师-1年.pdf')
            # if not os.path.exists(resume_path):
            #     logger.error(f'简历文件不存在: {resume_path}')
            #     exit_code = 2
            # else:
            #     resume_info = parse_resume(resume_path)
            #     if not resume_info or 'content' not in resume_info:
            #         logger.error('解析简历失败')
            #         exit_code = 3
            #     else:
            #         # 3. 用AI提取简历内容生成搜索关键词（暂时注释）
            #         logger.info('步骤3: AI提取搜索关键词')
            #         try:
            #             extractor = AIKeywordExtractor()
            #             keywords = extractor.extract_keywords(resume_info['content'])
            #             if not keywords:
            #                 logger.warning('未提取到关键词，使用默认关键词')
            #             keywords = ['Python开发工程师', 'AI应用开发', '机器学习', 'RAG']
            #             logger.info(f'提取的关键词: {keywords}')
            #         except Exception as e:
            #             logger.error(f'AI关键词提取失败，使用默认关键词: {e}')
            #             keywords = ['Python开发工程师', 'AI应用开发', '机器学习', 'RAG']
                    
                    # 4. 根据关键词搜索职位并保存前20个职位的详细信息
                    logger.info('步骤4: 搜索职位并保存详情')
                    
                    # 只搜索RAG关键词
                    search_keywords = 'RAG'
                    logger.info(f'搜索关键词: {search_keywords}')
                    
                    # 搜索职位
                    jobs = boss_client.search_jobs(search_keywords, city="北京", page=1)
                    if not jobs:
                        logger.error('未搜索到职位')
                        exit_code = 4
                    else:
                        # 获取前20个职位的详情
                        job_details = []
                        max_jobs = min(20, len(jobs))
                        logger.info(f'开始获取前{max_jobs}个职位的详情')
                        
                        for i in range(max_jobs):
                            job = jobs[i]
                            logger.info(f'获取第{i+1}/{max_jobs}个职位详情: {job["title"]}')
                            detail = boss_client.get_job_detail(job["link"])
                            if detail:
                                job_details.append(detail)
                            
                            # 避免请求过快
                            if i < max_jobs - 1:
                                import time
                                time.sleep(2)
                        
                        # 保存职位详情到本地文件
                        output_dir = os.path.join(os.path.dirname(__file__), 'data', 'jobs')
                        os.makedirs(output_dir, exist_ok=True)
                        output_file = os.path.join(output_dir, 'boss_zhipin_jobs.json')
                        
                        if boss_client.save_job_details(job_details, output_file):
                            logger.info(f'成功保存{len(job_details)}个职位详情到: {output_file}')
                        else:
                            logger.error('保存职位详情失败')
                            exit_code = 5
                    
                    logger.info('所有流程执行完成！')
        
    except Exception as e:
        logger.error(f'程序执行出错: {e}')
        exit_code = -1
    
    # 无论程序执行结果如何，都会执行以下代码
    logger.info('浏览器保持打开状态，请手动关闭')
    logger.info('程序已完成所有操作，按回车键退出...')
    
    # 使用input等待用户输入，不需要额外安装模块
    try:
        input()
    except KeyboardInterrupt:
        pass
    
    logger.info('用户已手动退出程序')
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())

