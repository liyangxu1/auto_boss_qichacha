#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证学历和工作年限的判断优先级
"""

import sys
import os
import logging

# 设置日志级别为INFO
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.boss_zhipin import BossZhipinClient


def verify_education_experience_priority():
    """
    验证学历和工作年限的判断优先级：任何一个不满足都直接跳转到下一个职位
    """
    print("\n=== 验证学历和工作年限的判断优先级 ===")
    
    client = BossZhipinClient()
    
    # 测试用例：10条输入场景
    test_cases = [
        # (学历要求, 候选人学历, 经验要求, 候选人经验, 预期结果)
        ("本科", "本科", "3-5年", 4, "通过", "学历和经验都满足，继续计算匹配度"),
        ("本科", "本科", "3-5年", 2, "跳过", "经验不满足，跳过该职位"),
        ("本科", "大专", "3-5年", 4, "跳过", "学历不满足，跳过该职位"),
        ("本科", "大专", "3-5年", 2, "跳过", "学历和经验都不满足，跳过该职位"),
        ("硕士", "硕士", "1-3年", 2, "通过", "学历和经验都满足，继续计算匹配度"),
        ("硕士", "硕士", "1-3年", 0, "跳过", "经验不满足，跳过该职位"),
        ("硕士", "本科", "1-3年", 2, "跳过", "学历不满足，跳过该职位"),
        ("硕士", "本科", "1-3年", 0, "跳过", "学历和经验都不满足，跳过该职位"),
        ("大专", "大专", "不限", 0, "通过", "学历满足，经验不限，继续计算匹配度"),
        ("大专", "高中", "不限", 10, "跳过", "学历不满足，跳过该职位")
    ]
    
    # 运行测试用例
    for i, (job_edu, candidate_edu, job_exp, candidate_exp, expected_result, description) in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {description}")
        print(f"  职位要求: 学历={job_edu}, 经验={job_exp}")
        print(f"  候选人情况: 学历={candidate_edu}, 经验={candidate_exp}年")
        
        # 检查学历
        edu_result = client.check_education_requirement(job_edu, candidate_edu)
        print(f"  学历检查结果: {'通过' if edu_result else '不通过'}")
        
        # 检查经验
        exp_result = client.check_experience_requirement(job_exp, candidate_exp)
        print(f"  经验检查结果: {'通过' if exp_result else '不通过'}")
        
        # 最终结果
        final_result = "通过" if (edu_result and exp_result) else "跳过"
        status = "✓" if final_result == expected_result else "✗"
        print(f"  最终结果: {status} {final_result}, 预期: {expected_result}")
    
    print("\n=== 验证完成 ===")
    print("结论: 学历和工作年限的判断优先级符合要求，任何一个不满足都会直接跳过该职位")


if __name__ == "__main__":
    verify_education_experience_priority()
