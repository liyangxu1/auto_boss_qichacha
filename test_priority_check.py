#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试学历和工作年限的判断优先级
验证两个条件任何一个不满足都直接跳转到下一个职位
"""

import sys
import os
import logging

# 设置日志级别为INFO
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.boss_zhipin import BossZhipinClient


def test_education_experience_priority():
    """测试学历和工作经验的判断优先级"""
    print("\n=== 测试学历和工作经验的判断优先级 ===")
    
    client = BossZhipinClient()
    
    # 模拟职位详情
    mock_job_detail = {
        'title': 'AI工程师',
        'education': '本科',
        'experience': '3-5年',
        'description': '招聘AI工程师，要求本科及以上学历，3-5年工作经验'
    }
    
    # 模拟简历信息
    resume_info = {
        'name': '张三',
        'education': '本科',
        'experience_years': 1
    }
    
    # 模拟matcher对象
    class MockMatcher:
        def calculate_overall_match(self, resume, job):
            return {'overall_score': 90}
    
    matcher = MockMatcher()
    
    # 测试1：学历满足，经验不满足 -> 应该跳过
    print("\n测试1：学历满足，经验不满足")
    result1 = client.get_job_detail_and_match("test_url", resume_info, matcher)
    print(f"结果: {result1}")
    print(f"预期: None (跳过该职位)")
    
    # 测试2：学历不满足，经验满足 -> 应该跳过
    print("\n测试2：学历不满足，经验满足")
    resume_info2 = {'name': '张三', 'education': '大专', 'experience_years': 4}
    result2 = client.get_job_detail_and_match("test_url", resume_info2, matcher)
    print(f"结果: {result2}")
    print(f"预期: None (跳过该职位)")
    
    # 测试3：学历和经验都不满足 -> 应该跳过
    print("\n测试3：学历和经验都不满足")
    resume_info3 = {'name': '张三', 'education': '大专', 'experience_years': 1}
    result3 = client.get_job_detail_and_match("test_url", resume_info3, matcher)
    print(f"结果: {result3}")
    print(f"预期: None (跳过该职位)")
    
    # 测试4：学历和经验都满足 -> 应该继续计算匹配度
    print("\n测试4：学历和经验都满足")
    resume_info4 = {'name': '张三', 'education': '本科', 'experience_years': 4}
    result4 = client.get_job_detail_and_match("test_url", resume_info4, matcher)
    print(f"结果: {'继续计算匹配度' if result4 else '跳过该职位'}")
    print(f"预期: 继续计算匹配度")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    # 注意：此测试需要模拟get_job_detail方法
    # 我们先修改BossZhipinClient类来支持测试
    
    # 保存原始的get_job_detail方法
    original_get_job_detail = BossZhipinClient.get_job_detail
    
    # 替换为测试用的模拟方法
    def mock_get_job_detail(self, job_link):
        return {
            'title': 'AI工程师',
            'education': '本科',
            'experience': '3-5年',
            'description': '招聘AI工程师，要求本科及以上学历，3-5年工作经验'
        }
    
    try:
        # 应用模拟方法
        BossZhipinClient.get_job_detail = mock_get_job_detail
        
        # 运行测试
        test_education_experience_priority()
        
    finally:
        # 恢复原始方法
        BossZhipinClient.get_job_detail = original_get_job_detail
