#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试学历和工作经验检查函数的正确性
"""

import sys
import os
import logging

# 设置日志级别为INFO
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.boss_zhipin import BossZhipinClient


def test_education_check():
    """测试学历检查功能"""
    print("\n=== 测试学历检查功能 ===")
    
    client = BossZhipinClient()
    
    # 测试用例：学历层级比较
    test_cases = [
        # (职位要求, 候选人学历, 预期结果)
        ("本科", "本科", True),
        ("本科", "硕士", True),
        ("本科", "大专", False),
        ("硕士", "本科", False),
        ("大专", "高中", False),
        ("大专", "大专", True),
        ("不限", "高中", True),
        ("博士", "硕士", False),
        ("硕士", "研究生", True),  # 同义词测试
        ("专科", "大专", True),    # 同义词测试
    ]
    
    for job_edu, candidate_edu, expected in test_cases:
        result = client.check_education_requirement(job_edu, candidate_edu)
        status = "✓" if result == expected else "✗"
        print(f"{status} 职位要求: {job_edu}, 候选人学历: {candidate_edu}, 结果: {result}, 预期: {expected}")


def test_experience_check():
    """测试工作经验检查功能"""
    print("\n=== 测试工作经验检查功能 ===")
    
    client = BossZhipinClient()
    candidate_experience = 1  # 候选人只有1年经验
    
    # 测试用例：各种经验格式
    test_cases = [
        # (职位经验要求, 候选人经验, 预期结果)
        ("1-3年", 1, True),      # 范围格式，刚好满足
        ("1-3年", 0.5, False),   # 范围格式，不满足最低要求
        ("3-5年", 1, False),      # 范围格式，不满足最低要求
        ("5-10年", 1, False),     # 范围格式，不满足最低要求
        ("1年以上", 1, True),     # 单数字格式，刚好满足
        ("3年以上", 1, False),     # 单数字格式，不满足
        ("不限", 1, True),        # 不限格式
        ("应届生", 0, True),      # 应届生格式
        ("熟练使用Python", 1, True),  # 不包含年限
        ("", 1, True),            # 空字符串
        ("2年", 1, False),         # 简单数字格式
    ]
    
    for experience_text, cand_exp, expected in test_cases:
        result = client.check_experience_requirement(experience_text, cand_exp)
        status = "✓" if result == expected else "✗"
        print(f"{status} 职位要求: '{experience_text}', 候选人经验: {cand_exp}年, 结果: {result}, 预期: {expected}")


if __name__ == "__main__":
    print("开始测试学历和工作经验检查函数...")
    
    test_education_check()
    test_experience_check()
    
    print("\n=== 测试完成 ===")
