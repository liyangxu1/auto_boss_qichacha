"""可编辑的评分规则与模型逐项分析结果。"""

import math
from typing import Literal

from pydantic import Field, model_validator
from autoboss.models.evidence import Model


class Dimension(Model):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,29}$")
    name: str = Field(min_length=1, max_length=30)
    weight: float = Field(ge=0, le=100)
    rubric: str = Field(min_length=1, max_length=1500)


class MatchingRules(Model):
    dimensions: list[Dimension] = Field(min_length=1, max_length=12)
    prompt: str = Field(min_length=10, max_length=12000)
    minimum_coverage: float = Field(default=70, ge=0, le=100)

    @model_validator(mode="after")
    def check_weights(self):
        if not math.isclose(sum(d.weight for d in self.dimensions), 100, abs_tol=0.01):
            raise ValueError("评分权重合计必须为100%。")
        if len({d.id for d in self.dimensions}) != len(self.dimensions):
            raise ValueError("评分维度标识不能重复。")
        return self


class Evidence(Model):
    path: str = Field(max_length=250)
    quote: str = Field(min_length=1, max_length=1000)


class DimensionAssessment(Model):
    id: str
    status: Literal["matched", "partial", "unmatched", "unknown"]
    score: float | None = Field(ge=0, le=5)
    requirement: str
    evidence: list[Evidence] = Field(max_length=8)
    explanation: str
    gaps: list[str] = Field(max_length=8)
    uncertainties: list[str] = Field(default_factory=list, max_length=8)


class Assessment(Model):
    dimensions: list[DimensionAssessment]
    summary: str = Field(max_length=1500)


def default_rules() -> MatchingRules:
    rows = [
        ("direction", "岗位方向", 20, "实际职责与用户确认的求职方向是否一致，区分应用工程与模型算法研究。"),
        ("skills", "核心技能", 20, "比较岗位必需技术、简历实际使用情况和掌握深度，不能仅凭关键词计分。"),
        ("projects", "项目经历", 20, "比较项目内容、复杂度、个人贡献、成果与岗位实际职责的相似度。"),
        ("experience", "相关经验", 15, "比较相关工作经验与要求；区分全职和实习，不累加重叠经历。"),
        ("education", "学历要求", 15, "仅比较岗位明确的学历和专业要求，不推测年龄、性别等无关信息。"),
        ("company", "公司业务", 5, "比较公司业务与简历行业经历；匿名公司不推测身份，资料不足则待确认。"),
        ("preferences", "个人偏好", 5, "比较用户明确的城市、薪资等偏好；没有表达的偏好不臆测。"),
    ]
    return MatchingRules(dimensions=[Dimension(id=i, name=n, weight=w, rubric=r) for i,n,w,r in rows], prompt=(
        "仅依据简历、岗位和公司资料逐项比较。列出岗位要求、简历证据和能力差距。\n"
        "信息不足时标记待确认，不虚构事实。实习与全职分开，不累计重叠经历。\n"
        "每个维度给出0—5分：0为明确不符，1为弱相关，2为部分基础，3为基本符合，4为较强符合，5为充分符合。\n"
        "证据不足时score为null，status为unknown；不能把未写明等同不会。权重由系统计算。"))
