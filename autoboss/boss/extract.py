"""解析浏览器自然返回的岗位详情，页面文字作为补充来源。"""

import hashlib
import json
import re
from urllib.parse import urlsplit


CARD_SELECTOR = "li.job-card-box, li.job-card-wrapper"
DETAIL_PATH = "/wapi/zpgeek/job/detail.json"
HELPERS = """
const txt=(r,s)=>{for(const q of s.split(',')){const e=r.querySelector(q.trim());if(e?.innerText?.trim())return e.innerText.trim()}return null};
const texts=(r,s)=>[...new Set([...r.querySelectorAll(s)].map(e=>e.innerText.trim()).filter(Boolean))];
const link=(r,s)=>{const a=r.querySelector(s);return a?.href || null};
const sections=[...document.querySelectorAll('.job-sec, .company-sec, .detail-section, .company-section')];
const section=(name)=>{const e=sections.find(e=>{const h=e.querySelector('h2,h3,.title');return h?.innerText?.includes(name)});return e ? txt(e,'.job-sec-text,.text,.content,.intro') || e.innerText.replace(name,'').trim() : null};
"""


def is_detail_response(response):
    parsed = urlsplit(response.url)
    return (parsed.scheme == "https" and parsed.hostname == "www.zhipin.com"
            and parsed.path == DETAIL_PATH and response.request.method == "GET")


def parse_detail_response(payload):
    """对应原项目的 jobInfo、brandComInfo；不主动构造或调用私有接口。"""
    if not isinstance(payload, dict) or payload.get("code") != 0:
        return None
    data = payload.get("zpData")
    if not isinstance(data, dict) or not isinstance(data.get("jobInfo"), dict):
        return None
    job = data["jobInfo"]
    brand = data.get("brandComInfo") or {}
    if not isinstance(brand, dict):
        brand = {}

    def text(value):
        return (str(value).strip() or None) if isinstance(value, (str, int, float)) and not isinstance(value, bool) else None

    def values(items):
        if not isinstance(items, list):
            return []
        result = []
        for item in items:
            value = text(item.get("name") or item.get("label")) if isinstance(item, dict) else text(item)
            if value and value not in result:
                result.append(value)
        return result

    def encrypted(value):
        return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]+", value) else None

    job_id = encrypted(job.get("encryptId"))
    brand_id = encrypted(brand.get("encryptBrandId") or job.get("encryptBrandId"))
    company = {"name": text(brand.get("brandName")),
               "url": f"https://www.zhipin.com/gongsi/{brand_id}.html" if brand_id else None,
               "industry": text(brand.get("industryName")), "financing": text(brand.get("stageName")),
               "size": text(brand.get("scaleName")), "description": text(brand.get("introduce")),
               "address": text(brand.get("address"))}
    title = text(job.get("jobName"))
    if not title:
        return None
    salary = text(job.get("salaryDesc"))
    limited = bool(salary and "*" in salary)
    if limited:
        salary = None
    # 仅保留岗位和公司内容，不复制接口中与采集无关的 HR、沟通资料。
    source = {"jobInfo": {key: job[key] for key in (
        "encryptId", "jobName", "salaryDesc", "locationName", "experienceName", "degreeName",
        "postDescription", "jobStatusDesc", "address", "jobLabels", "welfareList") if key in job},
        "brandComInfo": {key: brand[key] for key in (
            "encryptBrandId", "brandName", "industryName", "introduce", "stageName", "scaleName", "address") if key in brand}}
    return {"url": f"https://www.zhipin.com/job_detail/{job_id}.html" if job_id else None,
            "title": title, "salary": salary, "city": text(job.get("locationName")),
            "experience": text(job.get("experienceName")), "education": text(job.get("degreeName")),
            "description": text(job.get("postDescription")), "address": text(job.get("address")),
            "recruitment_status": text(job.get("jobStatusDesc")),
            "tags": values(job.get("jobLabels")), "benefits": values(job.get("welfareList")),
            "company_name": company["name"], "company_url": company["url"], "company": company,
            "company_description": company["description"], "source_kind": "detail_response",
            "access_limited": limited,
            "response_data": source, "text": json.dumps(source, ensure_ascii=False, indent=2)}


def read_cards(page):
    return page.evaluate("""() => {""" + HELPERS + """
      return [...document.querySelectorAll('li.job-card-box, li.job-card-wrapper')].map((e,index)=>({
        index, url:link(e,'a[href*="/job_detail/"]'),
        title:txt(e,'.job-name,.job-title,.job-card-name'),
        salary:txt(e,'.salary,.job-salary'), area:txt(e,'.job-area,.company-location,.job-location'),
        company_name:txt(e,'.company-name,.company-info .name,.boss-name'),
        company_url:link(e,'a[href*="/gongsi/"]'),
        tags:texts(e,'.tag-list li,.job-labels span,.job-tag'),
        text:e.innerText.trim()
      })).filter(e=>e.title);
    }""")


def read_job(page):
    return page.evaluate("""() => {""" + HELPERS + """
      const p=document.querySelector('.job-banner .info-primary,.info-primary,.job-detail-header') || document;
      const c=document.querySelector('.sider-company,.job-company,.company-info') || document;
      return {url:location.href, title:txt(p,'h1,.name,.job-name'), salary:txt(p,'.salary,.job-salary'),
        primary_text:p===document ? null : p.innerText,
        city:txt(p,'.text-city,.job-area'), experience:txt(p,'.text-experience'), education:txt(p,'.text-degree'),
        description:section('职位描述') || txt(document,'.job-detail-section .job-sec-text,.job-sec-text'),
        address:txt(document,'.job-location .location-address,.location-address,.job-address'),
        tags:texts(document,'.job-tags span,.job-tags a,.job-detail .tag-list li'),
        benefits:texts(document,'.job-banner .job-labels span,.job-banner .job-labels a,.job-benefits span'),
        company_name:txt(c,'a[ka*="company"],.company-name,.name'),
        company_url:link(c,'a[href*="/gongsi/"]') || link(document,'a[ka*="company"][href*="/gongsi/"]'),
        company_text:c===document ? null : c.innerText,
        company_description:section('公司介绍'), text:document.body.innerText
      };
    }""")


def read_company(page):
    return page.evaluate("""() => {""" + HELPERS + """
      const primary=document.querySelector('.company-banner,.company-info') || document;
      const business={};
      for(const e of document.querySelectorAll('.business-detail li,.business-info li,.company-business-info li')){
        const t=e.innerText.trim();const m=t.match(/^([^：:]{1,20})[：:]\\s*([\\s\\S]+)$/);
        if(m)business[m[1]]=m[2].trim();
        else {const parts=t.split('\\n').map(x=>x.trim()).filter(Boolean);if(parts.length>1 && parts[0].length<20)business[parts[0]]=parts.slice(1).join(' ')}
      }
      return {url:location.href, name:txt(primary,'h1,.company-name,.name'),
        primary_text:primary===document ? null : primary.innerText,
        description:section('公司简介') || section('公司介绍') || txt(document,'.company-introduction .text,.company-introduction,.company-profile .text'),
        address:txt(document,'.company-address,.location-address'),
        industry:txt(primary,'.industry,.company-industry'), financing:txt(primary,'.financing,.company-stage'),
        size:txt(primary,'.scale,.company-scale'), website:txt(document,'.company-website'),
        business_info:business, text:document.body.innerText};
    }""")


def record_id(url, fallback):
    path = urlsplit(url or "").path
    if path.startswith(("/job_detail/", "/gongsi/")):
        return path.rsplit("/", 1)[-1].removesuffix(".html")
    return hashlib.sha256(fallback.encode()).hexdigest()[:24]


def qualification(text):
    text = text or ""
    experience = re.search(r"(?:\d+-\d+年|\d+年以上|\d+年以内|经验不限|在校/应届|应届生|在校生)", text)
    education = re.search(r"(?:博士|硕士|本科|大专|高中|中专/中技|学历不限)", text)
    return (experience.group() if experience else None, education.group() if education else None)


def company_summary(text):
    text = text or ""
    stage = re.search(r"(?:不需要融资|未融资|天使轮|Pre-[A-Z]轮|[A-Z]\+?轮(?:及以上)?|已上市)", text)
    size = re.search(r"(?:\d+-\d+人|\d+人以上|少于\d+人)", text)
    return (stage.group() if stage else None, size.group() if size else None)
