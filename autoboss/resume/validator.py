"""核对结构化结果的引用及原文摘录，并保留遗漏内容。"""

import re
import unicodedata

from pydantic import BaseModel

from autoboss.models.evidence import Fact, Source
from autoboss.models.resume import OtherContent, ResumeProfile


def compact(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def validate_source(source: Source) -> None:
    pages = [p.number for p in source.pages]
    if pages != list(range(1, source.page_count + 1)):
        raise ValueError("文字提取结果的页码不连续或页数不一致。")
    ids = [b.id for b in source.blocks]
    if len(ids) != len(set(ids)):
        raise ValueError("文字提取结果包含重复块编号。")
    if any(b.page not in pages or not b.text.strip() for b in source.blocks):
        raise ValueError("文字块缺少内容或引用了不存在的页码。")
    if any(b.bbox is not None and len(b.bbox) != 4 for b in source.blocks):
        raise ValueError("文字块位置应为四个坐标。")


def validate_profile(profile: ResumeProfile, source: Source) -> tuple[list[str], list[str]]:
    blocks = {block.id: block for block in source.blocks}
    covered = set()

    def visit(value, path="profile"):
        if isinstance(value, Fact):
            if value.value is None:
                if value.source_ids or value.normalized_value is not None:
                    raise ValueError(f"{path} 的空值不能包含引用或标准化值。")
                return
            if not value.value.strip() or not value.source_ids:
                raise ValueError(f"{path} 缺少有效原文或来源引用。")
            if any(key not in blocks for key in value.source_ids):
                raise ValueError(f"{path} 引用了不存在的文字块。")
            quote = compact(value.value)
            # 引用顺序影响跨页拼接，按原文顺序核对，防止引用重排掩盖改写。
            refs = sorted(set(value.source_ids), key=lambda key: list(blocks).index(key))
            evidence = compact("\n".join(blocks[key].text for key in refs))
            if quote not in evidence:
                raise ValueError(f"{path} 的摘录在引用原文中不存在，未保存分析结果。")
            covered.update(value.source_ids)
        elif isinstance(value, BaseModel):
            for name in type(value).model_fields:
                visit(getattr(value, name), f"{path}.{name}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")

    visit(profile)
    for note in profile.review_notes:
        if any(key not in blocks for key in note.source_ids):
            raise ValueError("待核对项引用了不存在的文字块。")
    uncovered = [block.id for block in source.blocks if block.id not in covered]
    if uncovered:
        # 模型遗漏的原文也必须进入“其他”，但明确说明尚未分类。
        profile.other.append(OtherContent(content=[Fact(value=blocks[key].text, source_ids=[key]) for key in uncovered]))
    warnings = ["结果只反映简历原文声明，尚未核实真实性；标准化值与待核对项需要人工检查。"]
    if uncovered:
        warnings.append(f"有 {len(uncovered)} 个未被事实字段引用的文字块，已原样保存在 other 的末项；请人工分类。")
    return uncovered, warnings
