"""PDF 提取与文字分析的独立服务入口。"""

import hashlib
import logging
import re
from pathlib import Path

from autoboss.common.llm import JSONClient
from autoboss.common.storage import json_text, write_files
from autoboss.models.evidence import Block, Page, Source

from .ai_parser import analyze_text
from .exporter import resume_to_dict
from .pdf_reader import extract_pdf
from .validator import validate_profile, validate_source
from .repair import repair_references


def extract_to_files(pdf: Path, output_dir: Path, *, password=None, force=False) -> Source:
    source = extract_pdf(pdf, password=password)
    validate_source(source)
    pages = []
    for page in source.pages:
        text = "\n".join(b.text for b in source.blocks if b.page == page.number)
        pages.append(f"[第 {page.number} 页]\n{text}")
    write_files({output_dir / "source.json": json_text(source),
                 output_dir / "text.txt": "\n\n".join(pages) + "\n"}, force=force)
    return source


def load_source(path: Path) -> Source:
    if path.suffix.lower() == ".json":
        try:
            source = Source.model_validate_json(path.read_text(encoding="utf-8-sig"))
        except ValueError:
            raise ValueError("输入 JSON 不是有效的 PDF 文字提取结果，请使用 extract 生成的 source.json。") from None
    elif path.suffix.lower() == ".txt":
        raw = path.read_text(encoding="utf-8-sig")
        sections = re.split(r"(?m)^\[第\s*(\d+)\s*页\]\s*$", raw)
        if len(sections) > 1:
            if sections[0].strip():
                raise ValueError("分页文字开头应为 [第 1 页]，或使用不含分页标记的普通 TXT。")
            chunks = [(int(sections[i]), sections[i + 1]) for i in range(1, len(sections), 2)]
        else:
            chunks = list(enumerate(raw.split("\f"), 1))
        blocks, pages = [], []
        for number, chunk in chunks:
            lines = [line.strip() for line in chunk.splitlines() if line.strip()]
            pages.append(Page(number=number, width=0, height=0, status="text" if lines else "needs_ocr", layout="unknown"))
            for line in lines:
                blocks.append(Block(id=f"b{len(blocks) + 1:05d}", page=number, text=line))
        source = Source(file_name=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        page_count=len(pages), pages=pages, blocks=blocks)
    else:
        raise ValueError("AI 步骤只接收 source.json 或 UTF-8 TXT，不直接接收 PDF。")
    validate_source(source)
    return source


def analyze_to_file(source: Source, output: Path, client: JSONClient, *, force=False, allow_partial=False) -> dict:
    validate_source(source)
    if output.exists() and not force:
        raise ValueError(f"输出已存在：{output}；如需覆盖，请加 --force。")
    missing = [p.number for p in source.pages if p.status == "needs_ocr"]
    if missing and not allow_partial:
        raise ValueError(f"第 {missing} 页缺少可用文字，请先 OCR 后重做文字提取；如仅分析已有文字，可加 --allow-partial。")
    if not source.blocks or not any(b.text.strip() for b in source.blocks):
        raise ValueError("输入没有可分析的文字，不会调用 AI。")
    profile = analyze_text(source, client)
    try:
        validate_profile(profile, source)
    except ValueError:
        # 只修正引用问题；修正后仍须通过原文校验，失败不输出业务 JSON。
        repair_references(profile, source, client)
        validate_profile(profile, source)
    if missing:
        logging.getLogger(__name__).warning("第 %s 页未识别，本次仅分析已提取的部分。", missing)
    result = resume_to_dict(profile)
    write_files({output: json_text(result)}, force=force)
    return result
