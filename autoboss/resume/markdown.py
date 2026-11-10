"""将简历业务 JSON 排版为 HR 阅读的 Markdown，不调用模型。"""

import re


def _plain(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    # PDF 的换行通常是排版折行，英文单词之间保留空格。
    text = re.sub(r"(?<=[A-Za-z0-9])\s*\n\s*(?=[A-Za-z0-9])", " ", text)
    text = "".join(line.strip() for line in text.splitlines())
    return re.sub(r"^(?:[•●▪]\s*|\d+、\s*|\d+\.(?!\d)\s*)", "", text)


def _escape(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>#|])", r"\\\1", text)


def _key(text: str) -> str:
    return re.sub(r"\s+", "", text)


def resume_to_markdown(resume: dict) -> str:
    """只使用已有字段，省略空值，并合并重复展示的原文。"""
    identity = resume.get("identity") or {}
    intent = resume.get("intent") or {}
    lines = ["# " + _escape(_plain(identity.get("name")) or "个人简历"), ""]

    def row(values):
        values = [_escape(_plain(v)) for v in values if _plain(v)]
        if values:
            lines.extend([" · ".join(values), ""])

    def labeled(label, value):
        text = _plain(value)
        return f"{label}：{text}" if text else ""

    def period(item):
        return " — ".join(_plain(item.get(k)) for k in ("start_date", "end_date") if item.get(k))

    def details(label, values, seen):
        selected = []
        for value in values or []:
            text = _plain(value)
            key = _key(text)
            if not key or any(key in old for old in seen):
                continue
            selected.append(text)
            seen.append(key)
        if selected:
            lines.extend([f"**{label}**", ""])
            lines.extend("- " + _escape(text) for text in selected)
            lines.append("")

    def metrics(items, seen):
        selected = []
        for item in items or []:
            value = _plain(item.get("value"))
            if not value or any(_key(value) in old for old in seen):
                continue
            name = _plain(item.get("name"))
            text = f"{name}：{value}" if name else value
            # 优先保留原文上下文，避免把“降低百分比”误写成最终数值。
            context = _plain(item.get("context"))
            if context:
                text = context
            else:
                baseline = _plain(item.get("baseline"))
                if baseline:
                    text += f"（基线：{baseline}）"
                unit = _plain(item.get("unit"))
                if unit and unit not in value:
                    text += f"，单位：{unit}"
                for key, label in [("sample_size", "样本"), ("evaluation_method", "评估方法")]:
                    if item.get(key):
                        text += f"；{label}：{_plain(item[key])}"
            selected.append(text)
        details("量化结果", selected, seen)

    row([labeled("求职方向", intent.get("target_role")),
         labeled("期望城市", "、".join(intent.get("expected_cities") or [])),
         intent.get("declared_experience")])
    row([identity.get("gender"), identity.get("age"), labeled("现居地", identity.get("location")),
         labeled("电话", identity.get("phone")), labeled("邮箱", identity.get("email"))])
    row([labeled(label, intent.get(key)) for key, label in [
        ("expected_salary", "期望薪资"), ("availability", "到岗时间"), ("employment_type", "工作性质")]])
    row(identity.get("links") or [])

    if resume.get("summary"):
        lines.extend(["## 个人优势", ""])
        details("优势概览", resume["summary"], [])

    categories = {"language": "编程语言", "framework": "开发框架", "model": "模型与算法",
                  "data": "数据与检索", "method": "方法与协议", "platform": "开发平台",
                  "deployment": "部署", "tool": "工具", "business": "业务能力", "other": "其他技能"}
    if resume.get("skills"):
        lines.extend(["## 专业技能", ""])
        groups = {}
        for item in resume["skills"]:
            name = _plain(item.get("name"))
            if not name:
                continue
            level = _plain(item.get("stated_proficiency"))
            text = name + (f"（{level}）" if level else "")
            groups.setdefault(categories.get(item.get("category"), "其他技能"), [])
            group = groups[categories.get(item.get("category"), "其他技能")]
            if text not in group:
                group.append(text)
        for category, names in groups.items():
            lines.append(f"- **{category}：** " + "、".join(_escape(name) for name in names))
        lines.append("")

    for key, title, heading in [("employment", "工作经历", "company"), ("projects", "项目经历", "name")]:
        if not resume.get(key):
            continue
        lines.extend([f"## {title}", ""])
        for item in resume[key]:
            lines.extend(["### " + _escape(_plain(item.get(heading)) or title), ""])
            row([item.get("role"), period(item), item.get("company") if key == "projects" else None])
            seen = []
            if key == "projects":
                stack = list(dict.fromkeys(_plain(v) for v in (item.get("technologies") or []) +
                                            (item.get("models") or []) if _plain(v)))
                row([labeled("技术栈", "、".join(stack))])
            details("主要成果", item.get("achievements"), seen)
            for field, label in [("background", "项目背景"), ("goals", "项目目标"),
                                 ("responsibilities", "个人职责"), ("technical_approach", "技术方案"),
                                 ("datasets", "数据"), ("evaluation", "效果评估"), ("deployment", "部署落地")]:
                details(label, item.get(field), seen)
            metrics(item.get("metrics"), seen)

    if resume.get("education"):
        lines.extend(["## 教育经历", ""])
        for item in resume["education"]:
            row([item.get("school"), item.get("degree"), item.get("major"), period(item)])
            # 完整重复学校、学历、专业、学年的原文行无需再列一次。
            header = "".join(_plain(item.get(k)) for k in ("school", "degree", "major", "start_date", "end_date"))
            extra = [v for v in item.get("details") or []
                     if re.sub(r"[\s—-]", "", _plain(v)) != re.sub(r"[\s—-]", "", header)]
            details("补充信息", extra, [])

    if resume.get("certifications"):
        lines.extend(["## 资格证书", ""])
        for item in resume["certifications"]:
            name = _plain(item.get("name"))
            if not name:
                continue
            suffix = [_plain(item.get(k)) for k in ("level", "obtained_at")
                      if item.get(k) and _plain(item[k]) not in name]
            lines.append("- " + _escape(name + ("（" + " · ".join(suffix) + "）" if suffix else "")))
        lines.append("")

    if resume.get("other"):
        lines.extend(["## 其他", ""])
        for item in resume["other"]:
            details(_plain(item.get("title")) or "补充内容", item.get("content"), [])

    return "\n".join(lines).rstrip() + "\n"
