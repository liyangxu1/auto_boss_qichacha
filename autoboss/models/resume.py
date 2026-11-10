"""简历原文声明、量化指标与其他内容的数据结构。"""

from typing import Literal

from pydantic import Field

from .evidence import Fact, Model


class Identity(Model):
    name: Fact = Field(default_factory=Fact)
    email: Fact = Field(default_factory=Fact)
    phone: Fact = Field(default_factory=Fact)
    location: Fact = Field(default_factory=Fact)
    age: Fact = Field(default_factory=Fact)
    gender: Fact = Field(default_factory=Fact)
    links: list[Fact] = Field(default_factory=list)


class Intent(Model):
    target_role: Fact = Field(default_factory=Fact)
    expected_cities: list[Fact] = Field(default_factory=list)
    declared_experience: Fact = Field(default_factory=Fact)
    expected_salary: Fact = Field(default_factory=Fact)
    availability: Fact = Field(default_factory=Fact)
    employment_type: Fact = Field(default_factory=Fact)


class Metric(Model):
    category: Literal["data_size", "evaluation", "latency", "throughput", "business", "other"]
    name: Fact
    value: Fact
    baseline: Fact = Field(default_factory=Fact)
    unit: Fact = Field(default_factory=Fact)
    sample_size: Fact = Field(default_factory=Fact)
    evaluation_method: Fact = Field(default_factory=Fact)
    context: Fact = Field(default_factory=Fact)


class Education(Model):
    school: Fact = Field(default_factory=Fact)
    degree: Fact = Field(default_factory=Fact)
    major: Fact = Field(default_factory=Fact)
    start_date: Fact = Field(default_factory=Fact)
    end_date: Fact = Field(default_factory=Fact)
    details: list[Fact] = Field(default_factory=list)


class Employment(Model):
    company: Fact = Field(default_factory=Fact)
    role: Fact = Field(default_factory=Fact)
    start_date: Fact = Field(default_factory=Fact)
    end_date: Fact = Field(default_factory=Fact)
    responsibilities: list[Fact] = Field(default_factory=list)
    achievements: list[Fact] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)


class Project(Model):
    name: Fact = Field(default_factory=Fact)
    role: Fact = Field(default_factory=Fact)
    company: Fact = Field(default_factory=Fact)
    start_date: Fact = Field(default_factory=Fact)
    end_date: Fact = Field(default_factory=Fact)
    background: list[Fact] = Field(default_factory=list)
    goals: list[Fact] = Field(default_factory=list)
    responsibilities: list[Fact] = Field(default_factory=list)
    technical_approach: list[Fact] = Field(default_factory=list)
    technologies: list[Fact] = Field(default_factory=list)
    models: list[Fact] = Field(default_factory=list)
    datasets: list[Fact] = Field(default_factory=list)
    evaluation: list[Fact] = Field(default_factory=list)
    deployment: list[Fact] = Field(default_factory=list)
    achievements: list[Fact] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)


class Skill(Model):
    name: Fact
    category: Literal["language", "framework", "model", "data", "method", "platform", "deployment", "tool", "business", "other"]
    stated_proficiency: Fact = Field(default_factory=Fact)
    evidence: list[Fact] = Field(default_factory=list)


class Certification(Model):
    name: Fact
    level: Fact = Field(default_factory=Fact)
    obtained_at: Fact = Field(default_factory=Fact)


class OtherContent(Model):
    title: Fact = Field(default_factory=Fact)
    content: list[Fact]


class ReviewNote(Model):
    category: Literal["missing", "ambiguous", "inconsistent", "normalization", "other"]
    description: str
    source_ids: list[str]


class ResumeProfile(Model):
    identity: Identity = Field(default_factory=Identity)
    intent: Intent = Field(default_factory=Intent)
    summary: list[Fact] = Field(default_factory=list)
    employment: list[Employment] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    other: list[OtherContent] = Field(default_factory=list)
    review_notes: list[ReviewNote] = Field(default_factory=list)
