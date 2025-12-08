#!/usr/bin/env python3
"""
AI关键词提取模块

功能：
1. 使用OpenAI API从简历内容中提取搜索关键词
2. 支持配置API密钥和模型参数
"""

import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
import openai

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class AIKeywordExtractor:
    """
    AI关键词提取器类，用于从简历内容中提取搜索关键词
    """
    
    def __init__(self):
        # 初始化OpenAI客户端
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY环境变量未设置")
            raise ValueError("OPENAI_API_KEY环境变量未设置")
        
        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    def extract_keywords(self, resume_content: str) -> List[str]:
        """
        从简历内容中提取搜索关键词
        
        Args:
            resume_content: 简历文本内容
            
        Returns:
            List[str]: 提取的搜索关键词列表
        """
        try:
            # 构建提示词
            prompt = f"""请从以下简历内容中提取用于Boss直聘职位搜索的关键词，
            仅返回关键词列表，每个关键词之间用逗号分隔，不要添加任何解释：
            
            {resume_content[:1000]}...  # 限制简历内容长度
            """
            
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的简历分析助手，擅长提取职位搜索关键词。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 降低随机性
                max_tokens=50,  # 限制返回长度
            )
            
            # 解析响应
            keywords_text = response.choices[0].message.content.strip()
            keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
            
            logger.info(f"成功提取关键词: {keywords}")
            return keywords
        except Exception as e:
            logger.error(f"提取关键词失败: {e}")
            # 如果AI提取失败，返回默认关键词
            return ["Python", "开发工程师", "经验"]


# 测试代码
if __name__ == "__main__":
    try:
        extractor = AIKeywordExtractor()
        test_resume = """李阳旭，AI应用开发工程师，1年工作经验，熟悉Python、TensorFlow、PyTorch，
        参与过推荐系统和图像识别项目，掌握机器学习算法，了解前端开发技术"""
        keywords = extractor.extract_keywords(test_resume)
        print(f"测试提取的关键词: {keywords}")
    except Exception as e:
        print(f"测试失败: {e}")
