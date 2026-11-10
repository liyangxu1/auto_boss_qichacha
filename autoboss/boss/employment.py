"""从明确的招聘文字识别兼职和实习，不把未标注冒充已确认全职。"""

import re


def employment_info(job):
    title = str(job.get("title") or "")
    description = str(job.get("description") or "")
    # “不招兼职”等排除语句不代表这个岗位是兼职。
    negatives = r"(?:不(?:接受|招收|招|考虑|支持|提供)|非|谢绝)\s*(?:任何)?\s*(?:兼职|实习生?|part[- ]?time)"
    title = re.sub(negatives, "", title, flags=re.I)
    description = re.sub(negatives, "", description, flags=re.I)
    for tag in job.get("tags") or []:
        if tag in {"兼职", "实习", "全职"}:
            description += f"\n工作性质：{tag}"
    checks = [
        ("part_time", title, r"兼职|非全职|part[-\s]?time|自由职业"),
        ("internship", title, r"实习|intern(?:ship)?\b"),
        ("part_time", description, r"(?:远程|周末|招聘|诚聘|长期|短期)\s*兼职|兼职(?:岗位|工作|职位|合作)|(?:工作性质|用工类型|职位性质|职位类型|合作方式)\s*[：:]?\s*(?:远程)?兼职|\bpart[-\s]?time\b"),
        ("internship", description, r"(?:招聘|诚聘)\s*实习生|实习(?:岗位|职位)|(?:工作性质|用工类型|职位性质)\s*[：:]\s*实习"),
        ("full_time", title + "\n" + description, r"全职(?:岗位|工作|职位)|(?:工作性质|用工类型|职位性质|职位类型)\s*[：:]\s*全职|\bfull[-\s]?time\b"),
    ]
    for kind, text, pattern in checks:
        found = re.search(pattern, text, re.I)
        if found:
            return {"employment_type": kind, "employment_evidence": found.group(0)}
    return {"employment_type": "unknown", "employment_evidence": None}


def apply_preference(job, preferences):
    info = employment_info(job)
    excluded = preferences.get("employment_type", "全职") == "全职" and info["employment_type"] in {"part_time", "internship"}
    names = {"part_time": "兼职岗位", "internship": "实习岗位"}
    return {**job, **info, "excluded": excluded,
            "exclusion_reason": names.get(info["employment_type"]) if excluded else None}
