"""AI 生成的 BOSS 搜索条件与用户补充偏好。"""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from .evidence import Model


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
ExperienceFilter = Literal["经验不限", "在校/应届", "1年以内", "1-3年", "3-5年", "5-10年", "10年以上"]


class SearchPreferences(Model):
    cities: list[ShortText] = Field(default_factory=list, max_length=10)
    experience_note: str = Field(default="", max_length=500)
    target_directions: str = Field(default="", max_length=300)
    employment_type: Literal["全职", "不限"] = "全职"


class BossSearchProfile(Model):
    cities: list[ShortText] = Field(max_length=10)
    primary_search_keywords: list[ShortText] = Field(min_length=1, max_length=6)
    secondary_search_keywords: list[ShortText] = Field(max_length=8)
    experience_filter: ExperienceFilter | None
    additional_experience_filters: list[ExperienceFilter] = Field(max_length=2)
    resume_keywords: list[ShortText] = Field(min_length=1, max_length=12)
    short_headline: str = Field(min_length=1, max_length=100)
    short_experience: str = Field(min_length=1, max_length=150)
    experience_note: str = Field(max_length=500)

    @field_validator("cities", "primary_search_keywords", "secondary_search_keywords",
                     "resume_keywords", "additional_experience_filters")
    @classmethod
    def unique_items(cls, values):
        keys = ["".join(value.split()).casefold() for value in values]
        if len(keys) != len(set(keys)):
            raise ValueError("同一列表不能包含重复条件。")
        return values
