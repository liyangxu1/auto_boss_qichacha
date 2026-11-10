# Autoboss 代码结构

项目分为简历解析、BOSS 自动化、岗位与公司分析三个业务模块。当前实现简历解析、搜索条件生成及 BOSS 只读采集，尚未实现岗位匹配评分。

## 依赖方向

`main.py → resume/service.py → pdf_reader.py 或 ai_parser.py → models / common`

- `main.py`：手动配置文件路径和模型，分别调用文字提取、AI 分析。
- `models/evidence.py`：PDF 页、文字块、原文事实与来源。
- `models/resume.py`：简历字段、量化指标、其他内容、待核对项。
- `models/search.py`：AI 搜索条件与可选的城市、经历补充偏好。
- `models/jobs.py`：搜索组合、岗位、公司及采集来源字段。
- `boss/plan.py`：AI 搜索条件转换为城市、关键词、经验组合，解析官方城市编码。
- `boss/network.py`：BOSS 直连配置与 Clash TUN 检查，不修改全局网络设置。
- `boss/runtime.py`：要求当前为 AutoBOSS 环境，核对 Patchright 1.62.1，不切换解释器。
- `boss/browser.py`：参照 get_jobs 管理持久化 Chrome 会话，关闭启动空白页，提供登录页识别及显式二维码切换；不另外连接 CDP。
- `boss/capture.py`：监听浏览器自然返回的岗位详情响应，按岗位匹配，避免重名误绑定。
- `boss/extract.py`：解析详情响应中的岗位、公司字段，页面文字作为补充。
- `boss/worker.py`：按计划采集、去重、保存进度和异常诊断。
- `boss/service.py`：在同一个 AutoBOSS 环境调度采集子进程并核验数据结构。
- `resume/pdf_reader.py`：只提取 PDF 文字和布局，不请求网络。
- `resume/ai_parser.py`：只将已提取文字交给 AI，不读 PDF 图片，不控制浏览器。
- `resume/validator.py`：检查来源编号、摘录和遗漏文字。
- `resume/exporter.py`：只输出约定的简历业务字段，去掉内部来源和诊断信息。
- `resume/markdown.py`：把已有业务 JSON 转为 HR 阅读版，不调用模型。
- `resume/search_profile.py`：读取简历业务 JSON，调用 AI 生成搜索条件，核对城市范围并独立保存。
- `resume/service.py`：组织输入、处理与输出，不承担模型协议细节。
- `common/config.py`：环境变量和显式配置文件。
- `common/llm.py`：Responses、Chat Completions 的结构化输出适配。
- `common/storage.py`：原子文件写入和覆盖保护。
- `environment.yml`：定义 AutoBOSS Conda 环境，业务依赖引用 `pyproject.toml`。
- `scripts/run-local.sh`：使用 AutoBOSS Conda 环境执行 `main.py`，不在运行时安装依赖。

## 独立阶段

1. `pdf_to_text()`：PDF → `text.txt` 与中间来源记录 `source.json`。
2. `text_to_json()`：TXT → AI 分析 → 只有业务字段的 `resume.json`。
3. `generate_boss_search()`：简历 JSON → AI 分析 → 城市、关键词、经验筛选和填写清单。
4. `json_to_markdown()`：已有 JSON → HR 阅读版 Markdown，作为可选导出步骤。
5. `collect_boss_jobs()`：AI 搜索条件 → BOSS 搜索 → 岗位、公司及采集状态，不进行投递。

Markdown 只负责呈现已有 JSON，不加入规则解析替代 AI。`source.json` 保留原 PDF 文件名、SHA-256、页数、页状态、文字块编号与位置。普通 TXT 输入没有 PDF 坐标，来源记录为 TXT 自身。

最终 JSON 顶层只保留 `identity`、`intent`、`summary`、`employment`、`projects`、`skills`、`education`、`certifications`、`other`。事实直接输出原文值或 null；来源、标准化候选和诊断不再附加到最终结果中。

## 后续边界

- BOSS 模块采集原始岗位、公司信息，执行已经指定的操作，不负责评分。
- 分析模块读取简历、岗位、公司档案，输出匹配结果，不控制浏览器。
- 业务模块共用 `models`，后续统一流程放入 `workflows.py`。
- `get_jobs/` 是独立参考仓库，不复制其业务代码。
- 个人简历、提取文本、结果、模型密钥和浏览器状态不提交 Git。
