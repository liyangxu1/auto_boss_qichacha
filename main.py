"""项目启动入口，保留简历解析与采集函数供手动调试。"""

import json
import os
import time
from pathlib import Path

from autoboss.common.config import AIConfig, read_env_file
from autoboss.common.llm import JSONClient
from autoboss.boss.service import CollectOptions, collect_jobs
from autoboss.resume.markdown import resume_to_markdown
from autoboss.resume.search_profile import generate_search_to_files
from autoboss.resume.service import analyze_to_file, extract_to_files, load_source


PROJECT_DIR = Path(__file__).resolve().parent
PDF_FILE = Path(os.environ.get("AUTOBOSS_PDF_FILE", PROJECT_DIR / "input/resume.pdf"))
OUTPUT_DIR = PROJECT_DIR / "data" / "test-resume"
TEXT_FILE = OUTPUT_DIR / "extracted" / "text.txt"
JSON_FILE = OUTPUT_DIR / "resume.json"
SEARCH_FILE = OUTPUT_DIR / "boss-search.ai.json"
SEARCH_PREFERENCES_FILE = OUTPUT_DIR / "search-preferences.json"
BOSS_OUTPUT_DIR = PROJECT_DIR / "data" / "boss"
BOSS_PROFILE_DIR = PROJECT_DIR / "data" / "browser" / "boss"
# 每轮和单次总量设上限，先采集岗位与公司信息。
BOSS_OPTIONS = CollectOptions(max_jobs_per_search=5, max_jobs_total=30)

# 环境变量优先，其次读取项目根目录的 .env；也可以直接修改下面的变量。
ENV_FILE = PROJECT_DIR / ".env"
MODEL_ENV = {**(read_env_file(ENV_FILE) if ENV_FILE.is_file() else {}), **os.environ}
API_KEY = MODEL_ENV.get("OPENAI_API_KEY", "")
MODEL = MODEL_ENV.get("OPENAI_MODEL", "")
BASE_URL = MODEL_ENV.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
API_FORMAT = MODEL_ENV.get("OPENAI_API_FORMAT", "responses")
# 兼容接口不支持严格结构化输出时，在 .env 中开启 OPENAI_JSON_MODE。
JSON_MODE = MODEL_ENV.get("OPENAI_JSON_MODE", "false").lower() in {"true", "1", "yes"}
TIMEOUT = float(MODEL_ENV.get("OPENAI_TIMEOUT", "300"))


def pdf_to_text() -> str:
    """第一步：只读取 PDF 文字，保存到本地，不调用 AI。"""
    source = extract_to_files(PDF_FILE, TEXT_FILE.parent, force=True)
    text = TEXT_FILE.read_text(encoding="utf-8")
    print(f"已提取 {source.page_count} 页，文字保存在：{TEXT_FILE}")
    print(text)
    return text


def text_to_json() -> dict:
    """第二步：读取已有文字，由 AI 分析后保存简历 JSON。"""
    if not TEXT_FILE.is_file():
        raise ValueError("还没有简历文字，请先运行 pdf_to_text()。")
    if not API_KEY or not MODEL:
        raise ValueError("请先在 .env 或 main.py 中填写 API_KEY 和 MODEL。")
    source = load_source(TEXT_FILE)
    config = AIConfig(key=API_KEY, model=MODEL, base_url=BASE_URL,
                      api_format=API_FORMAT, json_mode=JSON_MODE, timeout=TIMEOUT)
    print(f"正在调用 {MODEL} 分析 {source.page_count} 页简历，等待限制 {TIMEOUT:g} 秒……", flush=True)
    started = time.perf_counter()
    result = analyze_to_file(source, JSON_FILE, JSONClient(config), force=True)
    print(f"AI 分析与校验完成，耗时 {time.perf_counter() - started:.1f} 秒。", flush=True)
    print(f"简历 JSON 保存在：{JSON_FILE}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def generate_boss_search(json_file: Path = JSON_FILE) -> dict:
    """由 AI 读取已有简历 JSON，生成城市、关键词和经验筛选。"""
    preferences = (json.loads(SEARCH_PREFERENCES_FILE.read_text(encoding="utf-8-sig"))
                   if SEARCH_PREFERENCES_FILE.is_file() else {})
    config = AIConfig(key=API_KEY, model=MODEL, base_url=BASE_URL,
                      api_format=API_FORMAT, json_mode=JSON_MODE, timeout=TIMEOUT)
    if not config.key or not config.model:
        raise ValueError("请先在 .env 或 main.py 中填写 API_KEY 和 MODEL。")
    print(f"正在调用 {MODEL} 生成 BOSS 搜索条件……", flush=True)
    started = time.perf_counter()
    result = generate_search_to_files(json_file, SEARCH_FILE, JSONClient(config),
                                      preferences=preferences, force=True)
    print(f"搜索条件生成完成，耗时 {time.perf_counter() - started:.1f} 秒。", flush=True)
    print(f"搜索 JSON：{SEARCH_FILE}\n填写清单：{SEARCH_FILE.with_suffix('.md')}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def collect_boss_jobs(options: CollectOptions | None = None) -> list[dict]:
    """读取 AI 搜索条件，在 BOSS 搜索并采集岗位、公司，不执行沟通或投递。"""
    report = collect_jobs(SEARCH_FILE, BOSS_OUTPUT_DIR, BOSS_PROFILE_DIR, options=options or BOSS_OPTIONS)
    print(f"BOSS 采集状态：{report['status']}；岗位 {report['job_count']}；公司 {report['company_count']}")
    print(f"结果目录：{report['output_dir']}")
    jobs_file = Path(report["output_dir"]) / "jobs.json"
    print(f"岗位列表：{jobs_file}")
    return json.loads(jobs_file.read_text(encoding="utf-8"))


def json_to_markdown(json_file: Path = JSON_FILE) -> str:
    """第三步：把已有 JSON 转成 方便 阅读的 Markdown，不调用 AI。"""
    json_file = Path(json_file)
    resume = json.loads(json_file.read_text(encoding="utf-8-sig"))
    text = resume_to_markdown(resume)
    output = json_file.with_suffix(".md")
    output.write_text(text, encoding="utf-8")
    print(f"Markdown文档保存在：{output}")
    return text


def start_app() -> None:
    """启动后台工作台；已经运行时复用服务并显示访问地址。"""
    from autoboss.web.server import main as manage_web

    manage_web(["start"])


if __name__ == "__main__":
    start_app()

    # 单独调试时，注释掉上面的启动调用，再按需运行以下函数。
    # pdf_to_text()
    # text_to_json()
    # generate_boss_search()
    # collect_boss_jobs()
    # json_to_markdown()
