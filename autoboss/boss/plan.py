"""将 AI 搜索建议转换成明确的城市、关键词、经验组合。"""

import json
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

from autoboss.common.storage import json_text, write_files
from autoboss.models.jobs import SearchTask
from autoboss.models.search import BossSearchProfile
from .network import check_direct_network, direct_opener


CITY_DATA_URL = "https://www.zhipin.com/wapi/zpCommon/data/city.json"
# BOSS 职位列表使用的工作经验筛选编码，未知标签明确报错，不降级为不限。
# 与页面 sel-job-rec-exp-* 选项对应；“经验不限”不是清除全部筛选。
EXPERIENCE_CODES = {"经验不限": "101", "在校/应届": "108,102", "1年以内": "103", "1-3年": "104",
                    "3-5年": "105", "5-10年": "106", "10年以上": "107"}


def city_codes(cache_file: Path) -> dict[str, str]:
    if cache_file.exists():
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        check_direct_network()
        with direct_opener().open(CITY_DATA_URL, timeout=20) as response:
            data = json.load(response)
        if data.get("code") != 0:
            raise ValueError("BOSS 城市数据暂时不可用，未执行搜索。")
        write_files({cache_file: json_text(data)})
    result = {}

    def visit(node):
        if isinstance(node, dict):
            if node.get("name") and node.get("code"):
                result[node["name"].removesuffix("市")] = str(node["code"])
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(data.get("zpData", {}).get("cityList", []))
    if not result:
        raise ValueError("BOSS 城市数据结构不符合预期，未执行搜索。")
    return result


def build_search_plan(profile_file: Path, cache_file: Path, *, include_secondary=False,
                      include_additional_experience=True) -> list[SearchTask]:
    profile = BossSearchProfile.model_validate_json(Path(profile_file).read_text(encoding="utf-8-sig"), strict=True)
    if not profile.cities or profile.experience_filter is None:
        raise ValueError("AI 结果缺少城市或工作经验筛选，请先补充偏好并重新生成。")
    codes = city_codes(Path(cache_file))
    keywords = profile.primary_search_keywords + (profile.secondary_search_keywords if include_secondary else [])
    experiences = [profile.experience_filter]
    if include_additional_experience:
        experiences += profile.additional_experience_filters
    tasks = []
    for city in profile.cities:
        code = codes.get(city.removesuffix("市"))
        if not code:
            raise ValueError(f"无法识别求职城市：{city}；请核对城市名称，未执行搜索。")
        for experience in dict.fromkeys(experiences):
            if experience not in EXPERIENCE_CODES:
                raise ValueError(f"暂不支持工作经验筛选：{experience}")
            for keyword in dict.fromkeys(keywords):
                params = {"city": code, "query": keyword}
                exp_code = EXPERIENCE_CODES[experience]
                if exp_code:
                    params["experience"] = exp_code
                tasks.append(SearchTask(city=city, city_code=code, keyword=keyword, experience=experience,
                                        experience_code=exp_code,
                                        url="https://www.zhipin.com/web/geek/jobs?" + urlencode(params)))
    return tasks
