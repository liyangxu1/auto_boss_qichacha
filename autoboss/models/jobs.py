"""岗位、公司与搜索来源的数据结构。"""

from typing import Literal

from pydantic import Field

from .evidence import Model


class SearchTask(Model):
    city: str
    city_code: str
    keyword: str
    experience: str
    experience_code: str | None
    url: str


class JobRecord(Model):
    id: str
    url: str
    title: str | None = None
    salary: str | None = None
    city: str | None = None
    area: str | None = None
    address: str | None = None
    experience: str | None = None
    education: str | None = None
    description: str | None = None
    recruitment_status: str | None = None
    tags: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    company_id: str | None = None
    company_name: str | None = None
    company: "CompanyRecord | None" = None
    source_kind: Literal["detail_response", "page", "list"] = "list"
    access_limited: bool = False
    detail_status: Literal["complete", "list_only", "unavailable"] = "list_only"
    collected_at: str
    source_text_file: str | None = None
    searches: list[SearchTask] = Field(default_factory=list)


class CompanyRecord(Model):
    id: str
    name: str | None = None
    anonymous: bool = False
    url: str | None = None
    industry: str | None = None
    financing: str | None = None
    size: str | None = None
    description: str | None = None
    address: str | None = None
    website: str | None = None
    business_info: dict[str, str] = Field(default_factory=dict)
    job_ids: list[str] = Field(default_factory=list)
    detail_status: Literal["complete", "summary_only", "unavailable"] = "summary_only"
    collected_at: str
    source_text_file: str | None = None
