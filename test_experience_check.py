#!/usr/bin/env python3
"""
测试工作经验检查逻辑
"""
import re
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_experience_check():
    """测试工作经验检查逻辑"""
    
    # 测试数据：候选人只有1年经验
    candidate_experience = 1
    
    # 各种经验要求格式
    test_cases = [
        ("5-10年", False),      # 应该不匹配
        ("1-3年", True),        # 应该匹配
        ("3年以上", False),     # 应该不匹配
        ("1年以上", True),      # 应该匹配
        ("不限", True),         # 应该匹配
        ("应届生", True),       # 应该匹配
        ("", True),             # 应该匹配（空值默认通过）
        ("经验不限", True),     # 应该匹配
        ("5年及以上", False),   # 应该不匹配
    ]
    
    for experience_text, expected_match in test_cases:
        result = check_experience_requirement(experience_text, candidate_experience)
        status = "✅ 通过" if result == expected_match else "❌ 失败"
        print(f"{status} 经验要求：'{experience_text}' -> 预期：{expected_match}，实际：{result}")

def check_experience_requirement(experience_text, candidate_experience):
    """检查工作经验要求"""
    
    # 记录原始经验文本用于调试
    logger.info(f"开始检查工作经验：职位经验要求文本='{experience_text}'，候选人经验{candidate_experience}年")
    
    # 匹配各种经验格式：3-5年、1年以上、不限、应届生等
    if not experience_text or '不限' in experience_text or '应届生' in experience_text:
        logger.info("职位经验要求为'不限'或'应届生'，跳过经验检查")
        return True
    else:
        # 尝试匹配范围格式：3-5年、1-3年等
        range_match = re.search(r'(\d+)-\s*(\d+)', experience_text)
        if range_match:
            min_years = int(range_match.group(1))
            max_years = int(range_match.group(2))
            logger.info(f"职位经验要求范围：{min_years}-{max_years}年")
            
            if candidate_experience < min_years:
                logger.info(f"经验不匹配：职位要求至少{min_years}年，候选人经验{candidate_experience}年")
                return False
            return True
        else:
            # 匹配单个数字：3年以上、5年经验等
            single_match = re.search(r'(\d+)', experience_text)
            if single_match:
                required_years = int(single_match.group(1))
                logger.info(f"职位经验要求：至少{required_years}年")
                
                if candidate_experience < required_years:
                    logger.info(f"经验不匹配：职位要求{required_years}年，候选人经验{candidate_experience}年")
                    return False
                return True
            else:
                logger.warning(f"无法从经验文本'{experience_text}'中提取工作年限要求，跳过经验检查")
                return True

if __name__ == "__main__":
    print("🧪 开始测试工作经验检查逻辑...")
    print("候选人工作经验：1年")
    print("=" * 50)
    test_experience_check()
    print("=" * 50)
    print("测试完成！")