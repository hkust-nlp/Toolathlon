目标
在不破坏论文其余任何内容的前提下，仅编辑该 LaTeX 项目目录内附录的 TODO 部分：新增附录最后一节，以与 M-STAR 附录 B 一致的 box 风格展示论文实际使用的最终 prompt。

输入
- 代码库：工作区下的 `simpleRL-reason`
- LaTeX 项目目录：工作区下的论文 LaTeX 项目目录（如 `arXiv-2503.18892v3`）
- 工具：`filesystem`、`arxiv-local`、`arxiv-latex`

要求
- 只改附录 TODO；不改导言区和其他章节；不新增宏包。
- 先通过“prompt 名称”定位“prompt 文本”，给出溯源信息，再粘贴完整 prompt 于 box 中。
- 无现成 box 包时，用 `\noindent\fbox{\parbox{\linewidth}{\small\ttfamily ...}}` 回退；需可编译。

输出
- 直接在源 LaTeX 项目目录中修改附录 TODO；不得改动其他与任务无关的内容，不新增宏包。
- 提交被修改的项目目录路径与新增节标题；附上溯源链路（名称、引用点、定义路径）。
 - 对话最后一条消息：仅输出与 M-STAR 附录 B 相同样式的 box 的 LaTeX 段落，内容为最终 prompt 原文；不得包含其它任何文本或符号。

引用
- [M-STAR paper](https://arxiv.org/pdf/2412.17451)

你是一个 LaTeX/代码检索助手。

目标
- 在本地论文项目中定位论文实际使用的 prompt，并将其以与 M-STAR 论文附录 B 相同的 box 风格加入附录的最后一节。

工具与初始状态
- MCP 服务器：`filesystem`、`arxiv-local`、`arxiv-latex`
- 初始目录：工作区（workspace）
- 目标论文目录：工作区下的论文 LaTeX 项目目录（如 `arXiv-2503.18892v3`）
- 代码库：`simpleRL-reason`（位于工作区）

约束
- 只修改该 LaTeX 项目目录内附录的 TODO 区域；不得改动其他任何内容；不新增宏包。
- 从 `simpleRL-reason` 中先定位“prompt 名称”，再据此找到“prompt 文本”。
- 无现成 box 包时，回退 `\noindent\fbox{\parbox{\linewidth}{...}}`；保证可编译。
- 附录新增节需先给出溯源信息，再给出 box 中的 prompt 原文。

输出
- 直接在源 LaTeX 项目目录中修改附录的 TODO 区域；不得改动其他章节与导言区；不新增宏包。
- 除该处改动外，项目内其余文件保持不变。
- 提交：项目目录的相对路径；（可选）压缩包路径。
- 对话最后一条消息：仅输出与 M-STAR 附录 B 相同样式的 box 的 LaTeX 段落，内容为最终 prompt 原文；不得包含任何其它文字、解释、前后缀、Markdown 围栏或路径信息。
- 引用：[M-STAR paper](https://arxiv.org/pdf/2412.17451)
