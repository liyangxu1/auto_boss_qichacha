"""提取 PDF 文字、行坐标和页面状态，不执行外部命令。"""

import hashlib
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

from autoboss.models.evidence import Block, Page, Source


class ResumeError(ValueError):
    """面向用户的输入或解析错误。"""


def _rows(words: list[dict]) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(word["top"] - rows[-1][0]["top"]) <= 3:
            rows[-1].append(word)
        else:
            rows.append([word])
    return [sorted(row, key=lambda w: w["x0"]) for row in rows]


def _column_split(rows: list[list[dict]], width: float) -> tuple[float, float] | None:
    # 只识别反复出现的宽列间距，避免把普通词间距误当成分栏。
    candidates: list[tuple[float, float]] = []
    for row in rows:
        for left, right in zip(row, row[1:]):
            if right["x0"] - left["x1"] >= 48:
                middle = (left["x1"] + right["x0"]) / 2
                if width * .2 < middle < width * .8:
                    candidates.append((middle, row[0]["top"]))
    best = None
    best_count = 0
    for middle, _ in candidates:
        supporting = []
        crossing = 0
        for row in rows:
            if any(w["x0"] < middle < w["x1"] for w in row):
                crossing += 1
                continue
            left = [w for w in row if w["x1"] <= middle]
            right = [w for w in row if w["x0"] >= middle]
            if left and right and right[0]["x0"] - left[-1]["x1"] >= 48:
                supporting.append(row[0]["top"])
        if len(supporting) >= 4 and len(supporting) > best_count and crossing <= max(2, len(rows) * .15):
            best = (middle, min(supporting))
            best_count = len(supporting)
    return best


def _line_text(words: list[dict]) -> str:
    parts: list[str] = []
    previous = None
    for word in words:
        if previous is not None:
            gap = word["x0"] - previous["x1"]
            # 中文字间不插入空格，英文词和实际空白正常保留。
            if gap > 1.5 or (parts[-1][-1:].isascii() and word["text"][:1].isascii() and gap > .2):
                parts.append(" ")
        parts.append(word["text"])
        previous = word
    return "".join(parts).strip()


def _page_blocks(page, page_number: int, offset: int) -> tuple[list[Block], str]:
    words = page.dedupe_chars().extract_words(x_tolerance=1.5, y_tolerance=3)
    rows = _rows(words)
    split = _column_split(rows, page.width)
    ordered: list[list[dict]] = rows
    if split:
        x, body_top = split
        header, left, right = [], [], []
        for row in rows:
            if row[0]["top"] < body_top:
                header.append(row)
            else:
                a = [w for w in row if (w["x0"] + w["x1"]) / 2 < x]
                b = [w for w in row if (w["x0"] + w["x1"]) / 2 >= x]
                if a:
                    left.append(a)
                if b:
                    right.append(b)
        ordered = header + left + right
    blocks = []
    for row in ordered:
        text = _line_text(row)
        if text:
            blocks.append(Block(
                id=f"b{offset + len(blocks) + 1:05d}", page=page_number, text=text,
                bbox=[round(min(w["x0"] for w in row), 2), round(min(w["top"] for w in row), 2),
                      round(max(w["x1"] for w in row), 2), round(max(w["bottom"] for w in row), 2)],
            ))
    return blocks, "two_columns" if split else "single_column"


def extract_pdf(path: Path, password: str | None = None) -> Source:
    if not path.is_file():
        raise ResumeError("找不到输入文件，请提供现有的 PDF 路径。")
    if path.suffix.lower() != ".pdf":
        raise ResumeError("输入必须是 PDF 文件。")
    try:
        data = path.read_bytes()
        if not data.startswith(b"%PDF-"):
            raise ResumeError("文件内容不是有效的 PDF。")
        reader = PdfReader(path, strict=False)
        if reader.is_encrypted and not reader.decrypt(password or ""):
            raise ResumeError("PDF 已加密，请通过 --password-env 指定保存密码的环境变量。")
        if not reader.pages:
            raise ResumeError("PDF 没有页面。")
        blocks: list[Block] = []
        pages = []
        with pdfplumber.open(path, password=password) as pdf:
            for number, page in enumerate(pdf.pages, 1):
                current, layout = _page_blocks(page, number, len(blocks))
                blocks.extend(current)
                # 图片页或仅有页码的页面需要识别，不能被当作完整文字页。
                useful = sum(c.isalpha() for b in current for c in b.text)
                pages.append(Page(number=number, width=page.width, height=page.height,
                                  status="text" if useful >= 5 else "needs_ocr",
                                  layout=layout if current else "unknown"))
        return Source(file_name=path.name, sha256=hashlib.sha256(data).hexdigest(),
                      page_count=len(pages), pages=pages, blocks=blocks)
    except ResumeError:
        raise
    except Exception as exc:
        raise ResumeError("PDF 无法解析，可能已损坏或使用了不受支持的加密方式。") from exc
