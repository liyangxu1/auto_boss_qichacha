#!/usr/bin/env python3
"""
主程序入口，实现完整的Boss直聘职位搜索和自动沟通流程

核心流程：
1. 登录Boss直聘
2. 解析简历
3. 用AI提取简历内容生成搜索关键词
4. 根据关键词搜索职位
5. 计算简历与职位的匹配度
6. 匹配度>=80%的职位自动点击"立即沟通"
7. 保存所有结果到文件
"""

import os
import sys
import logging
import json
import time
from modules.boss_zhipin import BossZhipinClient
from modules.resume_parser import parse_resume
from modules.ai_keyword_extractor import AIKeywordExtractor
from modules.job_matcher import JobMatcher

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    主程序入口 - 完整自动化流程
    """
    logger.info('开始执行Boss直聘职位搜索和自动沟通流程')
    exit_code = 0
    boss_client = None
    
    try:
        # 1. 登录Boss直聘
        logger.info('步骤1: 登录Boss直聘')
        boss_client = BossZhipinClient(headless=False)  # 不使用无头模式，便于用户手动登录
        
        login_success = boss_client.login()
        if not login_success:
            logger.error('登录失败，程序终止')
            return 1
        
        # 2. 解析简历
        logger.info('步骤2: 解析简历')
        resume_path = os.path.join(os.path.dirname(__file__), 'data', 'jianli', '李阳旭-AI应用开发工程师-1年.pdf')
        if not os.path.exists(resume_path):
            logger.error(f'简历文件不存在: {resume_path}')
            return 2
        
        resume_info = parse_resume(resume_path)
        if not resume_info or 'content' not in resume_info:
            logger.error('解析简历失败')
            return 3
        
        logger.info(f'成功解析简历: {resume_info["file_path"]}')
        
        # 3. 用AI提取简历内容生成搜索关键词
        logger.info('步骤3: AI提取搜索关键词')
        try:
            extractor = AIKeywordExtractor()
            keywords = extractor.extract_keywords(resume_info['content'])
            if not keywords:
                logger.warning('未提取到关键词，使用大模型相关默认关键词')
                keywords = ['RAG', 'Agent', 'AI工程师', '大模型', 'LLM', 'AIGC', '人工智能', '机器学习工程师', '深度学习', '自然语言处理', 'NLP']
            else:
                # 确保包含大模型相关关键词
                ai_keywords = ['RAG', 'Agent', 'AI工程师', '大模型', 'LLM', 'AIGC', '人工智能', '机器学习工程师', '深度学习', '自然语言处理', 'NLP']
                keywords.extend([kw for kw in ai_keywords if kw not in keywords])
            logger.info(f'AI提取的关键词: {keywords}')
        except Exception as e:
            logger.error(f'AI关键词提取失败，使用大模型相关默认关键词: {e}')
            keywords = ['RAG', 'Agent', 'AI工程师', '大模型', 'LLM', 'AIGC', '人工智能', '机器学习工程师', '深度学习', '自然语言处理', 'NLP']
        
        # 4. 创建职位匹配器
        logger.info('步骤4: 创建职位匹配器')
        job_matcher = JobMatcher()
        
        # 5. 搜索职位并计算匹配度
        logger.info('步骤5: 搜索职位并计算匹配度')
        
        all_job_details = []
        auto_chat_count = 0
        
        # 使用多个关键词搜索 - 使用大模型相关关键词
        for keyword in keywords[:3]:  # 只使用前3个关键词
            logger.info(f'搜索关键词: {keyword}')
            jobs = boss_client.search_jobs(keyword, city="北京", page=1)
            
            if not jobs:
                logger.warning(f'关键词"{keyword}"未搜索到职位')
                continue
            
            logger.info(f'关键词"{keyword}"找到{len(jobs)}个职位')
            
            # 处理每个职位
            max_jobs = min(2, len(jobs))  # 每个关键词最多处理2个职位（测试用）
            logger.info(f'开始处理前{max_jobs}个职位')
            
            for i in range(max_jobs):
                job = jobs[i]
                logger.info(f'处理第{i+1}/{max_jobs}个职位: {job["title"]}')
                
                try:
                    # 获取职位详情并计算匹配度
                    detail = boss_client.get_job_detail_and_match(job["link"], resume_info, job_matcher)
                    if detail:
                        all_job_details.append(detail)
                        
                        # 统计自动沟通次数
                        if detail.get('auto_chat_clicked', False):
                            auto_chat_count += 1
                            logger.info(f'已自动发起沟通，当前总计: {auto_chat_count}个职位')
                    
                    # 避免请求过快
                    if i < max_jobs - 1:
                        time.sleep(2)
                        
                except Exception as e:
                    logger.error(f'处理职位失败: {e}')
                    continue
        
        # 6. 保存结果
        logger.info('步骤6: 保存结果')
        output_dir = os.path.join(os.path.dirname(__file__), 'data', 'jobs')
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存详细结果
        detailed_output_file = os.path.join(output_dir, 'boss_zhipin_jobs_with_match.json')
        if boss_client.save_job_details(all_job_details, detailed_output_file):
            logger.info(f'成功保存{len(all_job_details)}个职位详情到: {detailed_output_file}')
        else:
            logger.error('保存职位详情失败')
            exit_code = 5
        
        # 保存统计结果
        stats = {
            'total_jobs_processed': len(all_job_details),
            'auto_chat_initiated': auto_chat_count,
            'high_match_jobs': len([job for job in all_job_details if job.get('match_result', {}).get('overall_score', 0) >= 80]),
            'medium_match_jobs': len([job for job in all_job_details if 60 <= job.get('match_result', {}).get('overall_score', 0) < 80]),
            'low_match_jobs': len([job for job in all_job_details if job.get('match_result', {}).get('overall_score', 0) < 60])
        }
        
        stats_output_file = os.path.join(output_dir, 'job_match_stats.json')
        with open(stats_output_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info('=== 执行结果统计 ===')
        logger.info(f'处理职位总数: {stats["total_jobs_processed"]}')
        logger.info(f'自动发起沟通: {stats["auto_chat_initiated"]}')
        logger.info(f'高匹配度职位(>=80%): {stats["high_match_jobs"]}')
        logger.info(f'中等匹配度职位(60-80%): {stats["medium_match_jobs"]}')
        logger.info(f'低匹配度职位(<60%): {stats["low_match_jobs"]}')
        
        logger.info('所有流程执行完成！')
        
    except Exception as e:
        logger.error(f'程序执行出错: {e}', exc_info=True)
        exit_code = -1
    
    finally:
        # 清理资源
        if boss_client:
            logger.info('浏览器保持打开状态，请手动关闭')
            logger.info('程序已完成所有操作，按回车键退出...')
            
            try:
                input()
            except KeyboardInterrupt:
                pass
            
            logger.info('用户已手动退出程序')
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())

