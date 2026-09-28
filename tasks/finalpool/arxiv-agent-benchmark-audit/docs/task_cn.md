我在为一篇综述整理 LLM agent 基准（benchmark）的阅读清单，但对这些论文只有模糊的印象。请帮我在 arXiv 上找到下面四篇论文：

1. 最初的 WebArena 论文：一个真实、可自行部署的网页环境，用于构建自主 agent，首次发布于 2023 年 7 月（不是后来的 VisualWebArena）。
2. 最初的 SWE-bench 论文，标题是一个问句，问语言模型能否解决真实世界的 GitHub issue，首次发布于 2023 年 10 月（不是 SWE-bench Multimodal 或其他 SWE-bench 衍生论文）。
3. 面向通用 AI 助手的 GAIA 基准论文，首次发布于 2023 年 11 月。
4. The Tool Decathlon 论文，它在多样、真实、长程的任务执行上评测语言 agent，首次发布于 2025 年 10 月。

对每篇论文，请以 arXiv 当前（截至今天）的状态为准，记录：`arxiv_id`（不带版本后缀）、`title`（最新版本的标题）、`first_author`（第一作者）、`num_authors`（最新版本的作者人数）、`v1_date`（第一版提交日期，UTC，格式 YYYY-MM-DD）、`latest_version`（整数，例如 v3 记为 3）、`latest_version_date`（最新版本提交日期，UTC，格式 YYYY-MM-DD）、`primary_category`（例如 cs.CL）。同时把每篇论文最新版本的 PDF 下载到工作区的 `papers/` 文件夹中，命名为 `{arxiv_id}v{latest_version}.pdf`。

请严格按照 `audit_spec.md` 中的格式，把以上内容保存到工作区的 `arxiv_audit.json` 中，四篇论文按 `v1_date` 从早到晚排序。最后，请按同样的顺序把四篇论文的标题回复给我，每行一个，使用纯文本，不要使用 markdown。
