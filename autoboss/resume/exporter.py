"""最终 JSON 只保留简历业务字段，内部引用不进入交付结果。"""

from pydantic import BaseModel

from autoboss.models.evidence import Fact
from autoboss.models.resume import ResumeProfile


def resume_to_dict(profile: ResumeProfile) -> dict:
    def convert(value):
        if isinstance(value, Fact):
            return value.value
        if isinstance(value, BaseModel):
            return {name: convert(getattr(value, name)) for name in type(value).model_fields}
        if isinstance(value, list):
            return [convert(item) for item in value]
        return value

    # 待核对项和来源只在内部处理，最终结果不再增加技术或诊断字段。
    return {name: convert(getattr(profile, name)) for name in (
        "identity", "intent", "summary", "employment", "projects",
        "skills", "education", "certifications", "other",
    )}
