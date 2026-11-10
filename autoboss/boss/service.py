"""在当前 AutoBOSS 环境构建搜索计划、采集岗位并核验结果。"""

import json
import signal
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from autoboss.common.storage import json_text, write_files
from autoboss.models.jobs import CompanyRecord, JobRecord
from .network import check_direct_network, direct_environment
from .plan import build_search_plan
from .runtime import browser_python


@dataclass
class CollectOptions:
    max_jobs_per_search: int = 5
    max_jobs_total: int = 30
    max_searches: int = 20
    max_scroll_rounds: int = 3
    include_secondary: bool = False
    include_additional_experience: bool = True
    browser_channel: str = "chrome"
    timeout_seconds: int = 25
    manual_wait_seconds: int = 180
    request_delay_seconds: float = 2
    collect_company_details: bool = False
    keep_browser_open: bool = True

    def __post_init__(self):
        if min(self.max_jobs_per_search, self.max_jobs_total, self.max_searches, self.timeout_seconds) < 1:
            raise ValueError("采集数量和页面等待时间必须大于0。")
        if self.max_scroll_rounds < 0 or self.manual_wait_seconds < 0 or self.request_delay_seconds < 1:
            raise ValueError("滚动、人工等待次数不能为负，相邻访问间隔至少1秒。")


def collect_jobs(profile_file: Path, output_root: Path, profile_dir: Path, *, options=None) -> dict:
    options = options or CollectOptions()
    interpreter = browser_python()
    check_direct_network()
    output_root = Path(output_root)
    tasks = build_search_plan(profile_file, output_root / "city-data.json",
                              include_secondary=options.include_secondary,
                              include_additional_experience=options.include_additional_experience)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_root / f"run-{stamp}-{uuid4().hex[:6]}"
    settings = {"tasks": [t.model_dump(mode="json") for t in tasks], "options": asdict(options),
                "output_dir": str(output.resolve()), "profile_dir": str(Path(profile_dir).resolve())}
    write_files({output / "settings.json": json_text(settings), output / "search-plan.json": json_text(settings["tasks"])})
    print(f"搜索计划 {len(tasks)} 轮，本次最多执行 {options.max_searches} 轮、采集 {options.max_jobs_total} 个岗位。", flush=True)
    print(f"运行环境：{interpreter}（Patchright 1.62.1）\nBOSS 使用直连网络，结果目录：{output.resolve()}", flush=True)
    root = Path(__file__).resolve().parents[2]
    process = subprocess.Popen([interpreter, "-u", "-m", "autoboss.boss.worker", str((output / "settings.json").resolve())],
                               cwd=root, env=direct_environment())
    try:
        returncode = process.wait()
    except KeyboardInterrupt:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=8)
        raise
    run_file = output / "run.json"
    if not run_file.exists():
        raise ValueError(f"浏览器驱动退出（代码{returncode}），尚未生成采集结果。")
    report = json.loads(run_file.read_text(encoding="utf-8"))
    for record in json.loads((output / "jobs.json").read_text(encoding="utf-8")):
        JobRecord.model_validate(record, strict=True)
    for record in json.loads((output / "companies.json").read_text(encoding="utf-8")):
        CompanyRecord.model_validate(record, strict=True)
    report["output_dir"] = str(output.resolve())
    return report
