#!/usr/bin/env python3
"""
职位匹配器模块

功能：
1. 使用大模型直接评估简历与职位的匹配度
2. 通过AI分析简历内容和职位描述的相关性
3. 提供详细的匹配分析和建议
"""

import re
import logging
from typing import Dict, List, Any
import openai
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)  # 强制重新加载环境变量

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class JobMatcher:
    """
    职位匹配器类 - 使用大模型进行智能匹配
    """
    
    def __init__(self, api_key: str = None, model_name: str = None):
        """
        初始化职位匹配器
        
        Args:
            api_key: API密钥，如果为None则从环境变量读取
            model_name: 模型名称，如果为None则从环境变量读取
        """
        # 从环境变量获取配置
        self.api_key = api_key or os.getenv('API_KEY') or os.getenv('OPENAI_API_KEY')
        self.model_name = model_name or os.getenv('MODEL_NAME') or os.getenv('OPENAI_MODEL') or 'gpt-3.5-turbo'
        
        # 根据模型名称选择合适的客户端
        if 'qwen' in self.model_name.lower():
            # 使用通义千问模型
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.tokenpony.cn/v1"
            )
        else:
            # 使用OpenAI模型
            self.client = openai.OpenAI(api_key=self.api_key)
        
        logger.info(f"使用模型: {self.model_name}")
    
    def get_ai_match_score(self, resume_content: str, job_content: str) -> Dict[str, Any]:
        """
        使用大模型评估简历与职位的匹配度
        
        Args:
            resume_content: 简历内容
            job_content: 职位描述内容
            
        Returns:
            Dict[str, Any]: 匹配结果，包含分数和详细分析
        """
        try:
            prompt = f"""
            你是一个专业的HR和招聘专家，请评估以下简历与职位的匹配度。
            
            简历内容：
            {resume_content}
            
            职位描述：
            {job_content}
            
            请按照以下JSON格式返回评估结果：
            {{
                "match_score": 0-100的整数，表示整体匹配度,
                "skill_match": 0-100的整数，表示技能匹配度,
                "experience_match": 0-100的整数，表示经验匹配度,
                "education_match": 0-100的整数，表示学历匹配度,
                "analysis": "详细的匹配分析，说明匹配和不匹配的地方",
                "recommendation": "是否推荐投递该职位，以及原因",
                "matched_skills": ["匹配的技能1", "匹配的技能2", ...],
                "missing_skills": ["缺失的技能1", "缺失的技能2", ...],
                "strengths": ["优势1", "优势2", ...],
                "weaknesses": ["不足1", "不足2", ...]
            }}
            
            评估标准：
            - 90-100分：非常匹配，强烈推荐
            - 80-89分：很匹配，推荐投递
            - 70-79分：比较匹配，可以考虑
            - 60-69分：一般匹配，需要权衡
            - 60分以下：不太匹配，不建议投递
            """
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的HR招聘专家，擅长评估简历与职位的匹配度。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            # 解析AI响应
            result_text = response.choices[0].message.content.strip()
            logger.info(f"AI匹配分析结果: {result_text}")
            
            # 尝试解析JSON格式
            try:
                result = json.loads(result_text)
                return result
            except json.JSONDecodeError:
                # 如果AI返回的不是标准JSON，尝试提取数字作为匹配度
                import re
                score_match = re.search(r'(\d+)', result_text)
                if score_match:
                    score = int(score_match.group(1))
                    return {
                        'match_score': score,
                        'skill_match': score,
                        'experience_match': score,
                        'education_match': score,
                        'analysis': result_text,
                        'recommendation': 'AI评估完成',
                        'matched_skills': [],
                        'missing_skills': [],
                        'strengths': [],
                        'weaknesses': []
                    }
                else:
                    return {
                        'match_score': 50,
                        'skill_match': 50,
                        'experience_match': 50,
                        'education_match': 50,
                        'analysis': 'AI分析结果格式异常，使用默认分数',
                        'recommendation': '需要人工评估',
                        'matched_skills': [],
                        'missing_skills': [],
                        'strengths': [],
                        'weaknesses': []
                    }
                    
        except Exception as e:
            logger.error(f"AI匹配分析失败: {str(e)}")
            return {
                'match_score': 0,
                'skill_match': 0,
                'experience_match': 0,
                'education_match': 0,
                'analysis': f'AI分析失败: {str(e)}',
                'recommendation': '分析失败，需要人工评估',
                'matched_skills': [],
                'missing_skills': [],
                'strengths': [],
                'weaknesses': []
            }
    
    def calculate_overall_match(self, resume_info: Dict[str, Any], job_detail: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算整体匹配度（使用大模型）
        
        Args:
            resume_info: 简历信息
            job_detail: 职位详情
            
        Returns:
            Dict[str, Any]: 匹配结果
        """
        resume_content = resume_info.get('content', '')
        job_requirements = job_detail.get('requirements', '') + ' ' + job_detail.get('work_content', '')
        
        if not resume_content or not job_requirements:
            logger.warning("简历内容或职位要求为空，无法计算匹配度")
            return {
                'overall_score': 0,
                'skill_match': 0,
                'experience_match': 0,
                'education_match': 0,
                'recommendation': '信息不足，无法评估',
                'analysis': '缺少简历或职位信息',
                'matched_skills': [],
                'missing_skills': [],
                'strengths': [],
                'weaknesses': []
            }
        
        # 使用大模型进行匹配度评估
        ai_result = self.get_ai_match_score(resume_content, job_requirements)
        
        # 格式化结果
        result = {
            'overall_score': ai_result.get('match_score', 0),
            'skill_match': ai_result.get('skill_match', 0),
            'experience_match': ai_result.get('experience_match', 0),
            'education_match': ai_result.get('education_match', 0),
            'recommendation': ai_result.get('recommendation', '无法提供建议'),
            'analysis': ai_result.get('analysis', '无分析结果'),
            'matched_skills': ai_result.get('matched_skills', []),
            'missing_skills': ai_result.get('missing_skills', []),
            'strengths': ai_result.get('strengths', []),
            'weaknesses': ai_result.get('weaknesses', []),
            'ai_full_result': ai_result  # 保存完整的AI分析结果
        }
        
        logger.info(f"AI匹配完成: 总体匹配度={result['overall_score']}%, 建议={result['recommendation']}")
        return result


def test_job_matcher():
    """
    测试职位匹配器
    """
    matcher = JobMatcher()
    
    # 测试简历
    test_resume = {
        'content': '''
        李阳旭，AI应用开发工程师，1年工作经验。
        教育背景：2023年毕业于清华大学计算机科学与技术专业，本科学历。
        
        技能专长：
        - 编程语言：Python、Java、C++
        - 机器学习：熟悉TensorFlow、PyTorch框架，掌握常用机器学习算法
        - 深度学习：了解CNN、RNN、Transformer等网络结构
        - 自然语言处理：熟悉文本分类、情感分析、命名实体识别等任务
        - 推荐系统：了解协同过滤、内容推荐等算法原理
        - 数据库：MySQL、Redis使用经验
        - 工具：Git、Docker、Linux
        
        项目经验：
        1. 智能推荐系统开发
           - 使用Python和TensorFlow构建推荐算法
           - 实现用户画像建模和物品特征提取
           - 提升推荐准确率15%
        
        2. 图像识别应用
           - 使用PyTorch实现图像分类模型
           - 在CIFAR-10数据集上达到85%准确率
           - 部署到生产环境，服务日均请求10万次
        
        个人特点：
        - 学习能力强，能够快速掌握新技术
        - 具备良好的团队合作精神
        - 对AI技术有浓厚兴趣，关注行业最新发展
        '''
    }
    
    # 测试职位
    test_job = {
        'requirements': '''
        岗位职责：
        1. 负责AI算法的设计、开发和优化
        2. 参与推荐系统的架构设计和算法实现
        3. 使用机器学习技术解决业务问题
        4. 跟踪AI领域最新技术，推动技术创新
        
        任职要求：
        1. 计算机、数学、统计学等相关专业，本科及以上学历
        2. 熟悉Python编程，有扎实的编程基础
        3. 熟悉机器学习、深度学习算法和框架（如TensorFlow、PyTorch）
        4. 有推荐系统、NLP或计算机视觉相关经验者优先
        5. 具备良好的数学基础和算法能力
        6. 1-3年相关工作经验，优秀的应届生也可考虑
        7. 具备良好的沟通能力和团队合作精神
        ''',
        'work_content': '主要工作内容包括AI算法研发、推荐系统开发、数据分析与建模等'
    }
    
    print("开始AI匹配分析...")
    result = matcher.calculate_overall_match(test_resume, test_job)
    print(f"\n匹配结果:")
    print(f"整体匹配度: {result['overall_score']}%")
    print(f"技能匹配度: {result['skill_match']}%")
    print(f"经验匹配度: {result['experience_match']}%")
    print(f"学历匹配度: {result['education_match']}%")
    print(f"\nAI分析: {result['analysis']}")
    print(f"\n推荐建议: {result['recommendation']}")
    
    if result['matched_skills']:
        print(f"\n匹配的技能: {', '.join(result['matched_skills'])}")
    if result['missing_skills']:
        print(f"缺失的技能: {', '.join(result['missing_skills'])}")
    if result['strengths']:
        print(f"优势: {', '.join(result['strengths'])}")
    if result['weaknesses']:
        print(f"不足: {', '.join(result['weaknesses'])}")


if __name__ == "__main__":
    test_job_matcher()