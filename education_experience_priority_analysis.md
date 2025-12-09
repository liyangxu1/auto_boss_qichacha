# 学历和工作经验判断优先级分析

## 1. 代码实现分析

在 `BossZhipinClient` 类的 `get_job_detail_and_match` 方法中，学历和工作经验的判断逻辑如下：

```python
def get_job_detail_and_match(self, job_link: str, resume_info: Dict[str, Any], matcher) -> Dict[str, Any]:
    # 获取职位详情
    job_detail = self.get_job_detail(job_link)
    if not job_detail:
        return None
    
    # 优先检查学历要求
    education_requirement = job_detail.get('education', '').lower()
    candidate_education = resume_info.get('education', '').lower()
    
    if not self.check_education_requirement(education_requirement, candidate_education):
        logger.info("学历不匹配，跳过该职位")
        return None
    
    # 检查工作经验要求
    experience_text = job_detail.get('experience', '')
    candidate_experience = resume_info.get('experience_years', 0)
    
    if not self.check_experience_requirement(experience_text, candidate_experience):
        logger.info("经验不匹配，跳过该职位")
        return None
    
    # 学历和经验都满足，继续计算匹配度
    logger.info("学历和经验要求满足，继续计算详细匹配度")
    # ... 后续匹配度计算和自动沟通逻辑
```

## 2. 判断优先级流程图

```mermaid
flowchart TD
    A[开始处理职位] --> B[获取职位详情]
    B --> C{职位详情获取成功?}
    C -->|否| D[返回None，处理下一个职位]
    C -->|是| E[检查学历要求]
    E --> F{学历是否满足?}
    F -->|否| G[记录日志: 学历不匹配]
    G --> D
    F -->|是| H[检查工作经验要求]
    H --> I{经验是否满足?}
    I -->|否| J[记录日志: 经验不匹配]
    J --> D
    I -->|是| K[继续计算匹配度]
    K --> L{匹配度>=80%?}
    L -->|是| M[自动点击"立即沟通"]
    L -->|否| N[记录日志: 匹配度未达标]
    M --> O[返回职位详情和匹配结果]
    N --> O
    O --> P[结束处理，返回结果]
```

## 3. 独立检查函数实现

### 学历检查函数
```python
def check_education_requirement(self, education_requirement: str, candidate_education: str) -> bool:
    # 定义学历层级，数值越大学历越高
    education_levels = {
        '不限': 0,
        '高中': 0.5,
        '中专': 0.5,
        '中技': 0.5,
        '大专': 1, '专科': 1,
        '本科': 2, '学士': 2,
        '硕士': 3, '研究生': 3,
        '博士': 4
    }
    
    # 获取职位和候选人的学历层级
    job_education_level = education_levels.get(education_requirement, 2)  # 默认本科
    candidate_education_level = education_levels.get(candidate_education, 0.5)  # 默认高中及以下
    
    # 检查学历是否满足要求
    if candidate_education_level < job_education_level:
        logger.info(f"学历不匹配：职位要求{education_requirement}，候选人学历{candidate_education}")
        return False
    
    logger.info(f"学历匹配：职位要求{education_requirement}，候选人学历{candidate_education}")
    return True
```

### 工作经验检查函数
```python
def check_experience_requirement(self, experience_text: str, candidate_experience: float) -> bool:
    import re
    
    # 记录原始经验文本用于调试
    logger.info(f"开始检查工作经验：职位经验要求文本='{experience_text}'，候选人经验{candidate_experience}年")
    
    # 匹配各种经验格式
    if not experience_text or '不限' in experience_text or '应届生' in experience_text:
        logger.info("职位经验要求为'不限'或'应届生'，跳过经验检查")
        return True
    
    # 尝试匹配范围格式：3-5年、1-3年等
    range_match = re.search(r'(\d+)-\s*(\d+)', experience_text)
    if range_match:
        min_years = int(range_match.group(1))
        max_years = int(range_match.group(2))
        logger.info(f"职位经验要求范围：{min_years}-{max_years}年")
        
        if candidate_experience < min_years:
            logger.info(f"经验不匹配：职位要求至少{min_years}年，候选人经验{candidate_experience}年")
            return False
        
        logger.info(f"经验匹配：职位要求至少{min_years}年，候选人经验{candidate_experience}年")
        return True
    
    # 匹配单个数字：3年以上、5年经验等
    single_match = re.search(r'(\d+)', experience_text)
    if single_match:
        required_years = int(single_match.group(1))
        logger.info(f"职位经验要求：至少{required_years}年")
        
        if candidate_experience < required_years:
            logger.info(f"经验不匹配：职位要求{required_years}年，候选人经验{candidate_experience}年")
            return False
        
        logger.info(f"经验匹配：职位要求至少{required_years}年，候选人经验{candidate_experience}年")
        return True
    
    logger.warning(f"无法从经验文本'{experience_text}'中提取工作年限要求，跳过经验检查")
    return True
```

## 4. 测试验证结果

使用10个测试用例验证了学历和工作经验的判断优先级：

| 测试用例 | 职位要求 | 候选人情况 | 结果 |
|---------|---------|-----------|------|
| 1 | 本科/3-5年 | 本科/4年 | 通过 |
| 2 | 本科/3-5年 | 本科/2年 | 跳过 |
| 3 | 本科/3-5年 | 大专/4年 | 跳过 |
| 4 | 本科/3-5年 | 大专/2年 | 跳过 |
| 5 | 硕士/1-3年 | 硕士/2年 | 通过 |
| 6 | 硕士/1-3年 | 硕士/0年 | 跳过 |
| 7 | 硕士/1-3年 | 本科/2年 | 跳过 |
| 8 | 硕士/1-3年 | 本科/0年 | 跳过 |
| 9 | 大专/不限 | 大专/0年 | 通过 |
| 10 | 大专/不限 | 高中/10年 | 跳过 |

## 5. 结论

1. **判断优先级**：学历检查优先于工作经验检查
2. **跳过逻辑**：任何一个条件不满足都会直接跳过该职位，返回None
3. **处理顺序**：
   - 先检查学历要求，如果不满足直接跳过
   - 如果学历满足，再检查工作经验要求
   - 只有两者都满足，才会继续计算匹配度

该实现符合需求：学历和工作年限的判断中，任何一个不满足都直接跳转到下一个职位。
