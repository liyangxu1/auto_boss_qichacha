# Autoboss：求职工作台

在现有 `AutoBOSS` 环境运行 `python main.py` 即可启动工作台。页面支持 **PDF → 简历 JSON → 搜索条件 → BOSS 采集 → 自动匹配排序**；原来的手动调用函数仍保留在 `main.py`。

## 浏览器操作

运行 `python main.py`（或调用 `start_app()`），然后访问 [本地求职工作台](http://127.0.0.1:8765)。启动器使用当前环境在后台运行服务，主脚本退出后服务继续运行；重复运行会复用已有服务。也保留 `./scripts/web.sh start/status/stop` 管理方式。支持 PDF 上传解析、AI 搜索建议、手动编辑条件、BOSS 岗位与公司采集、提示词与权重编辑、匹配评分及排序。只采集，不沟通或投递。登录目录统一复用 `data/browser/boss`，会话仍有效时不重复扫码。

操作步骤、代码结构、数据路径和评分方法见 [Web 工作台说明](docs/web-workbench.md)。

## 手动运行

`main.py` 中有五个独立函数：

```python
# 第一步：PDF 提取文字，不联网。
pdf_to_text()

# 第二步：读取文字，用 AI 分析成 JSON。
text_to_json()

# 第三步：由 AI 生成城市、关键词和经验筛选。
generate_boss_search()

# 可选：根据已有搜索条件采集 BOSS 岗位和公司资料。
collect_boss_jobs()

# 可选：把已有 JSON 转为 HR 阅读版，不联网。
json_to_markdown()
```

`main.py` 自动读取项目根目录的 `.env`，同名环境变量优先。默认只启动工作台，不自动采集或调用模型。单独调试时，在文件底部注释 `start_app()`，再按需调用上面的函数。提取结果可在 `data/test-resume/extracted/text.txt` 中检查。

配置示例使用 TokenPony 的 `deepseek-v4.1-flash-1017`，接口地址为 `https://api.tokenpony.cn/v1`，协议为 `chat-completions`。密钥仅保存在被 Git 忽略的 `.env` 中；新配置可参考 `.env.example`。

`OPENAI_API_FORMAT` 可填 `responses` 或 `chat-completions`。兼容接口不支持严格 JSON Schema 时，将 `OPENAI_JSON_MODE` 设为 `true`，仍会在本地校验返回字段。

`OPENAI_TIMEOUT` 控制接口连接和读取的等待限制，默认 300 秒。完整简历输出比短连接测试更耗时；运行时会显示正在调用的模型与分析耗时。超时不自动重试，可调整此配置后手动重试。

只转换已有 JSON 时，注释掉其他调用，在入口调用 `json_to_markdown()`。默认读取 `JSON_FILE`，Markdown 保存在 JSON 旁边，扩展名为 `.md`。也可以传入其他文件，例如 `json_to_markdown(OUTPUT_DIR / "resume.codex.json")`。此步骤按固定模板排版，保留原文成果和指标，不调用模型。

## AI 生成 BOSS 搜索条件

已有简历 JSON 后，可以只运行 `generate_boss_search()`。它读取 `JSON_FILE`，复用 `.env` 中的模型配置，生成 `boss-search.ai.json` 和同名 Markdown 填写清单。城市、首轮和扩展关键词、职位经验筛选、技能标签、简短介绍均由模型分析生成，代码不预设城市或职位关键词。搜索条件独立保存，不修改简历的9类字段。

城市限定为简历明确的求职城市；没有明确城市时返回空列表。可在 `SEARCH_PREFERENCES_FILE` 指定的本地 JSON 中补充 `cities`（城市数组，优先于简历）和 `experience_note`（例如全职/实习说明）。该文件可省略，个人补充信息不提交 Git。

模型只接收与岗位搜索相关的意向、优势、经历、技能和学历信息，排除姓名、联系方式、年龄、性别及重复证据。经验筛选是职位要求的建议；不会自动修改个人资料或在 BOSS 上执行搜索、沟通和投递。

## BOSS 搜索与采集

单独运行 `collect_boss_jobs()`，读取 `SEARCH_FILE` 中 AI 生成的城市、关键词和工作经验筛选。默认遍历首轮关键词及补充经验条件，扩展关键词由 `BOSS_OPTIONS.include_secondary` 控制。城市编码读取 BOSS 官方城市数据并缓存在 `data/boss/city-data.json`；无法识别城市或经验标签时停止，不自动扩大范围。

主程序和浏览器子进程统一使用 Conda `AutoBOSS`，依赖固定为与原项目相同的 `patchright==1.62.1`，复用本机已有 Chrome。不再查找或借用 `script` 等其他环境。程序运行时不安装依赖或浏览器，也不读取日常浏览器的登录目录。独立目录为 `data/browser/boss`，首次使用需要在专用浏览器中手动登录。手动调用 `collect_boss_jobs()` 时返回岗位列表；直接运行 `main.py` 则只启动工作台。

BOSS 默认直连：专用 Chrome 使用 `--no-proxy-server`，采集子进程清除代理变量，城市元数据请求也禁用代理。Codex 和模型请求的代理不变，不切换 Clash 节点或系统代理。使用 Clash 系统代理模式时可以同时让 Codex 走代理、BOSS 走原网络；检测到当前 Clash 开启 TUN 时会停止，因为浏览器参数不能绕过透明路由。检测路径可通过 `BOSS_CLASH_CONFIG` 指向实际生效配置。

默认每个搜索组合最多5个岗位、单次最多30个、最多20轮。`BOSS_OPTIONS` 可以调整数量、滚动轮次、访问间隔、浏览器和人工登录等待时间。每个岗位保存一次进度，相同岗位和公司去重，并保留命中的全部搜索组合。遇到登录或验证时提示人工处理；等待后仍未恢复则保留结果并停止。验证不会自动处理。

默认 `keep_browser_open=True`：采集结束后立即保存并打印结果路径，保留搜索结果和当前岗位详情，程序继续运行以维持浏览器连接；手动关闭专用窗口后程序退出。需要采集后立即退出时才设为 `False`。

每次采集建立独立 `data/boss/run-…` 目录：

- `search-plan.json`：本次城市、关键词、经验筛选及搜索地址。
- `jobs.json`：JSON 列表，每条为一个岗位，包含名称、薪资、地点、经验、学历、描述、标签、福利、招聘状态、来源与详情状态，以及对应的 `company` 公司对象。
- `companies.json`：公司名称、行业、规模、融资、介绍、地址、工商信息及关联岗位；缺失字段保留空值。
- `run.json`：各轮状态、数量、错误和网络模式。达到上限或采集不完整时会明确标记。
- `pages/`：岗位详情响应的岗位和公司数据（不复制 HR、沟通资料），或页面文字，便于后续核对。
- `diagnostics/`：异常页面的截图和文字。

代码只打开搜索、岗位和公司页面、滚动列表及点击职位标题，不包含沟通、发送简历或投递功能；浏览器另外拦截已知的沟通、投递接口。采集结果和登录目录均被 Git 忽略。

浏览器生命周期参照本地 `get_jobs/src/main/java/com/getjobs/worker/manager/PlaywrightManager.java`：使用本机 Chrome 的持久化上下文，新建业务标签页并关闭启动空白页；先进入 `/web/geek/jobs`，再执行搜索筛选。浏览器始终由同一个连接串行控制，不额外启动 CDP 调试端口。人工查看登录页后，可显式调用 `switch_to_qr_login(page)` 切换二维码入口，优先选择器为 `.btn-sign-switch.ewm-switch`；程序不自动代为登录。

原项目通过 Java 客户端连接 Patchright driver，我们直接使用同版本的 Python Patchright。采集流程参照 `get_jobs/.../worker/boss/Boss.java`：监听点击岗位卡片后自然返回的 `job/detail.json` 响应，读取 `jobInfo` 与 `brandComInfo`。原项目将公司名称、行业、简介、融资、规模与岗位一起存入 `boss_data`，我们存为 JSON 列表并附带公司对象；缺失字段为空，不由 AI 补写。`collect_company_details` 默认关闭，公司信息来自该岗位详情响应；后续需要公司主页资料时再显式开启。直连参数依据 [Chromium 网络设置](https://www.chromium.org/developers/design-documents/network-settings/)。

页面已核对“1-3年”编码为 `104`、“经验不限”为 `101`，不再把经验不限当成清除筛选。每条岗位另核对实际城市和经验。匿名公司标记 `anonymous: true`，没有可靠公司链接时不按同名占位名称合并。详情响应中的薪资为明文；页面字体混淆值不作为有效薪资保存。

2026-10-22 已在扫码登录后逐步采集并校验2条真实岗位及关联公司信息；尚未验证长期无人值守采集和公司主页补充采集。

路径也都放在 `main.py` 顶部：

- `PDF_FILE`（默认 `input/resume.pdf`，可用 `AUTOBOSS_PDF_FILE` 覆盖）：输入 PDF。
- `TEXT_FILE`：提取的文字，也可以手动修改后单独分析。
- `JSON_FILE`：最终 JSON，默认 `data/test-resume/resume.json`。
- `SEARCH_FILE`：AI 搜索条件，默认 `data/test-resume/boss-search.ai.json`。
- `SEARCH_PREFERENCES_FILE`：可选的城市、经历补充偏好文件。

反复手动运行会覆盖上述输出。模型分析只发送文字，不上传原 PDF。扫描件需要先 OCR；空白或未提取到文字的页面默认不进入 AI 分析。

## Python 环境

项目使用本机 Miniconda 管理的 `AutoBOSS` 环境，Python 3.12。在 PyCharm 中将解释器选为：

```text
<Conda 安装目录>/envs/AutoBOSS/bin/python
```

然后直接运行 `main.py`。该环境统一安装项目和 pdfplumber、pypdf、Pydantic、Patchright 等依赖。

终端也可以直接运行：

```sh
conda activate AutoBOSS
python main.py
```

或者运行 `./scripts/run-local.sh`，脚本默认使用 `AutoBOSS` 环境，不在运行时安装软件。

`environment.yml` 保存环境定义，业务依赖统一维护在 `pyproject.toml`。在其他电脑上，从项目根目录执行 `conda env create -f environment.yml` 即可创建同名环境。更新业务依赖后，在激活的环境中执行 `python -m pip install -e .`。

## 最终 JSON

最终文件顶层只有约定的业务字段：

```json
{
  "identity": {},
  "intent": {},
  "summary": [],
  "employment": [],
  "projects": [],
  "skills": [],
  "education": [],
  "certifications": [],
  "other": []
}
```

以上仅展示顶层形状。`identity` 是基本信息，`intent` 是求职意向，`summary` 是个人优势；工作、项目中包含职责、技术和量化指标，其余分别为技能、教育、证书和其他内容。

字段直接使用字符串、`null` 或数组，不再套 `value`、`normalized_value`、`source_ids`。例如姓名为 `"name": "示例姓名"`；缺失电话为 `"phone": null`。最终文件不包含 `profile` 包装，也不包含版本、模型名、解析状态、警告、待核对项或原文副本。

来源和校验只在解析内部使用。未归类的原文放入 `other`，个人材料与生成结果放在 Git 忽略的 `data/` 目录。

## 代码位置

- `main.py`：工作台启动入口与手动调试函数。
- `autoboss/resume/pdf_reader.py`：提取 PDF 文字。
- `autoboss/resume/ai_parser.py`：AI 分析和提示词。
- `autoboss/resume/exporter.py`：生成简洁 JSON。
- `autoboss/resume/markdown.py`：将业务 JSON 排版为 HR 阅读版。
- `autoboss/resume/search_profile.py`：由 AI 生成 BOSS 搜索条件并校验城市范围。
- `autoboss/resume/service.py`：串联两个步骤。
- `autoboss/models/`：约定的字段结构。
- `autoboss/common/`：模型调用、配置和文件保存。

不再使用自动测试目录，后续手动验证都从 `main.py` 调用。
