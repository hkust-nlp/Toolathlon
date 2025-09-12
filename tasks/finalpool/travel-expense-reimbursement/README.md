下面是一份**面向评测（eval）的可操作分解**。按“输入→动作→可自动判定的输出/指标”的思路，把这个端到端任务拆成模块化步骤，方便逐步打分与定位误差。

<!-- 1. 提交包识别

* 输入：员工提交的文件夹/ZIP（报销单 PDF + 若干票据 PDF/图片 + 制度 PDF 链接或副本）
* 动作：文件枚举与类型判定（报销单/票据/制度）。
* 输出：清单（每个文件的类型、页数、可读性）；指标：文件分类准确率。 -->

2. PDF/OCR结构化抽取

* 输入：报销单 PDF。
* 动作：页级/表格级解析；字段标准化（日期/金额/城市/类别/供应商）。
* 输出：

  * 报销单行项目表（claim\_id, line\_id, date, city, country, category, amount, …）
  * 票据表（receipt\_id, date, vendor, city, amount, 税额/房晚/里程等元数据）
* 指标：关键字段抽取F1、金额数值误差（MAE/绝对差=0比例）、日期解析准确率。

3. 票据-行项目配对（材料完整性映射）

* 输入：行项目表与票据表。
* 动作：基于金额±阈值、日期邻近、地点/商户相似度、多对一/一对多拆并规则进行匹配。
* 输出：映射表（line\_id ↔ receipt\_id\[\*]，匹配置信度）；
* 指标：配对准确率、覆盖率（有票据的行占比）、一对多拆分正确率。

4. 材料完整性检查（规则①）

* 输入：映射表。
* 动作：逐行检查“报销单上的每一项是否有至少一张有效票据”。
* 输出：完整/不完整标记 + 缺失清单（line\_id, 缺失原因）；
* 指标：判定准确率（与金标一致）。

5. 金额一致性校验（规则②）

* 输入：映射表 + 票据表。
* 动作：行项目金额与所配对票据金额（或汇总）一致性、小数/四舍五入规则。
* 输出：一致/不一致标记 + 差额；
* 指标：判定准确率、差额分布。

6. 员工/主管信息检索

* 输入：claim\_id、员工姓名/工号；企业通讯录/人事表。
* 动作：查员工邮箱与直属主管邮箱，异常时的回退策略（多匹配/未匹配）。
* 输出：{employee\_email, manager\_email}；
* 指标：邮箱检索准确率、未命中率。

7. 合格/不合格分流与邮件模版生成（规则①/②未通过时）

* 输入：规则①/②结果 + 邮箱信息。
* 动作：组装邮件正文与主题（包含 claim\_id、问题类型）；生成抄送对象。
* 输出：邮件草稿（to/cc/subject/body）
* 指标：模版要素完整性、收件人与抄送正确率、文案正确性（包含问题点与编号）。

8. 合格单据信息抽取与汇总

* 输入：报销单结构化结果。
* 动作：解析姓名、出差日期（起止/天数）、目的地（国/省/市）、报销总额、费用类型（分类汇总）。
* 输出：标准化记录（便于落库）；
* 指标：字段级准确率、分类汇总一致性。

9. 制度规则定位（政策PDF解析/检索）

* 输入：差旅政策PDF（固定且清晰）。
* 动作：根据“目的地国家/城市 + 员工级别”检索对应上限（每日补贴、酒店上限、机票/交通规则等），解决表格/脚注的解析。
* 输出：规则快照（rule\_id, 条款标题, 上限数值, 计量单位, 生效范围）；
* 指标：条款定位准确率、数值抽取准确率。

10. 合规判定（是否超标 flag）

* 输入：第8步汇总 + 第9步规则快照。
* 动作：逐项对比（按天/房晚/城市/类别），考虑跨日与房晚计数；计算超标幅度与原因。
* 输出：flag ∈ {0,1}，以及违规明细列表（line\_id, rule\_id, 超额金额/比例）。
* 指标：判定准确率、超标金额误差。

11. 超标通知邮件生成（通过但超标的情况）

* 输入：第10步结果 + 邮箱信息 + 财务部门邮箱。
* 动作：套用“费用超标”模板（含 claim\_id、超标类别/幅度、财务邮箱）。
* 输出：邮件草稿（to/cc/subject/body）
* 指标：与金标草稿的一致性（收件人/抄送/关键信息）。

12. Snowflake入库（仅满足①②的合格单据；可带flag列）

* 输入：标准化记录 + flag + 违规明细JSON（可选）。
* 动作：生成并校验INSERT语句/批量写入；目标表：`2025Q3报销表`（固定schema）。
* 输出：成功/失败状态 + 行数；
* 指标：写入成功率、schema一致性、去重/幂等正确性。

13. 审计与可追溯产物

* 输入：前述各步的中间结果。
* 动作：生成审计包（提取的表格、匹配关系、规则快照、决定与邮件草稿）。
* 输出：`audit.jsonl`/`audit.zip`；
* 指标：审计产物完整性（便于复现与人工抽查）。

14. 端到端决策一致性

* 输入：全流程输出。
* 动作：对每个用例判定最终动作是否与金标一致（发什么邮件/是否入库/flag值）。
* 输出：E2E正确/错误；
* 指标：E2E准确率（主指标）。

——

# 最小金标与评分建议

* **数据包**：每个用例包含

  1. `claim.pdf`（报销单）、`receipts/`（票据若干）、`policy.pdf`（制度固定版）、`hr.csv`（员工—主管—邮箱—级别）
  2. `gold.json`（含：抽取字段金标、配对金标、合规金标、应发送邮件金标、应入库记录金标）。
* **分步分数**（示例）：抽取20%，配对15%，规则检索与解析15%，合规判定20%，动作生成（邮件+入库）20%，E2E 10%。
* **容错/难例设计**：

 * 同额不同日/同日不同额、拆分票据（两张合一行）、币种与汇率、扫描件OCR噪声、城市/国家别名、周末/跨月行程房晚计算、重复票据、缺页/错传文件等。

——

# 建议的目标表（示例）

`2025Q3报销表`（核心字段）：
 `claim_id, employee_id, employee_name, level, dept, trip_start, trip_end, nights, dest_country, dest_city, currency, total_claimed, total_approved, category_breakdown_json, flag, flag_reasons_json, created_at`

以上拆解把评测流程做成**可独立计分的阶段任务**，既能衡量工具使用与规划能力，也能对错误来源进行细粒度定位。需要的话，我可以基于这14步给你生成一套**用例模板与gold.json模式**，直接接到你的评测框架里用。

——

# 预处理（Preprocess）与第6步初始化说明

- 本任务已提供预处理脚本来完成步骤2–5（PDF/结构化/配对/一致性注入错误），并集成第6步（企业通讯录 Snowflake 初始化）：

  - 脚本位置：`tasks/fan/travel-expense-reimbursement/preprocess/main.py`
  - 作用：
    - 加载 groundtruth 并随机注入三类错误：`amount_mismatch`、`missing_receipts|incomplete_receipts`、`total_mismatch`（仅控制台打印，PDF不直白暴露）
    - 生成报销单 PDF 到 `--agent_workspace/files/`
    - 保存含错误的结构化数据：`groundtruth_workspace/expense_claims_with_errors.json`
    - 可选：初始化 Snowflake 数据库 `TRAVEL_EXPENSE_REIMBURSEMENT` 并创建/填充企业通讯录表 `PUBLIC.ENTERPRISE_CONTACTS`

- 一键执行（固定流程，无可选参数）：

  `uv run -m tasks.fan.travel-expense-reimbursement.preprocess.main --agent_workspace <YOUR_WORKSPACE_DIR> --launch_time <ISO8601_TIMESTAMP>`

  - 行为：
    - 基于 `groundtruth_workspace/policy_standards_en.json` 重新生成 `expense_claims.json`（同一员工可多单，混入“政策超标”案例；金额=票据=总额一致）
    - 生成 `files/policy_en.pdf` 与各 `files/expense_claim_*.pdf`
    - 默认执行 Snowflake 初始化，创建并填充 `TRAVEL_EXPENSE_REIMBURSEMENT.PUBLIC.ENTERPRISE_CONTACTS`

——

## 英文补贴标准（Policy PDF）生成

- 已添加英文版差旅补贴标准（覆盖本数据集中出现的目的地/级别）：
  - 结构化标准：`tasks/fan/travel-expense-reimbursement/groundtruth_workspace/policy_standards_en.json`
  - PDF 生成脚本：`tasks/fan/travel-expense-reimbursement/preprocess/generate_policy_pdf.py`（主入口 `preprocess/main.py` 已会自动生成）

- 单独使用（可选）：
  - `uv run -m tasks.fan.travel-expense-reimbursement.preprocess.generate_policy_pdf --agent_workspace <YOUR_WORKSPACE_DIR> --launch_time <ISO8601_TIMESTAMP>`
  - 输出：`<YOUR_WORKSPACE_DIR>/files/policy_en.pdf`

- 内容说明：
  - 覆盖目的地：纽约（美国）、东京（日本）、伦敦（英国）、新加坡（新加坡）
  - 覆盖级别：L1–L4
  - 类别上限：住宿（每晚）、餐饮（每日）、本地交通（每日）、通讯（每次出差）、杂项（每次出差）
  - 货币单位：CNY
  - 机票规则：默认经济舱，L4 以上经审批可乘坐商务舱

——

## 基于政策的 groundtruth 重生成（已内置于 main）

- 生成器脚本：`tasks/fan/travel-expense-reimbursement/preprocess/generate_groundtruth_from_policy.py`（主入口 `preprocess/main.py` 已调用）
- 说明：
  - 重新生成的 JSON 仍为“claim 列表”，同一员工可出现多条 `claim_id`，与 PDF 生成兼容。

——

## Evaluation（政策合规最小评测）

- 命令：

  `uv run -m tasks.fan.travel-expense-reimbursement.evaluation.main --agent_workspace tasks/fan/travel-expense-reimbursement`

- 功能：
  - 读取 `groundtruth_workspace/expense_claims.json` 与 `policy_standards_en.json`
  - 按“目的地+级别”的上限检查每个报销单；逐条打印：
    - 合规/不合规、对应 PDF 路径
    - 不合规类别与明细（日期/金额/上限/超额）
  - 汇总输出：总单数、违规单数、按类别的违规统计

——

## TODOs（备选改进项）

- 生成器难度调节：
  - 调整各类别的超标比例与幅度（轻微/中度/严重），或只在单一类别制造轻微越界以增加判定难度。
- 政策范围扩展：
  - 补充更多目的地与员工级别，或严格对齐所参考的制度 PDF（条款编号、脚注规则等）。
- 规则深化：
  - 机票舱位合规（默认经济舱、审批例外的校验），按航段识别。
  - 发票阈值（>200 CNY 需发票）与“缺失/不合格票据”分类，联动材料完整性检查。
- 币种与汇率：
  - 支持目的地本币与汇率换算，统一以 CNY 判定上限。
- 评测产物：
  - 可输出 `audit.jsonl`（逐项违规的规则快照/上限/单位/幅度），便于审计回溯。
- E2E 扩展：
  - 集成“超标通知邮件”生成，与 Snowflake 入库记录的 flag 一致性核验。

——

## 全流程概览（Preprocess + Evaluation）

- 一键预处理（preprocess/main.py）
  - 基于 `groundtruth_workspace/policy_standards_en.json` 生成多人多单的 groundtruth：
    - 每位员工（EMP001–EMP004）1–2 份 claim，金额=收据=总计（表单正确的基础上）
    - 按政策自动混入“超标”场景（住宿/餐饮/本地交通/通讯/杂项），写入 `claim._policy_violations`
    - 将每条政策超标镜像到 `claim._errors`（type 同名，含 date/amount/cap/over_by）
    - 以固定比例注入“表单类错误”并记录到 `claim._errors`：
      - amount_mismatch（≈25%）：某行报销金额≠收据金额（记录 line_id/category/claimed_amount/receipt_amount）
      - missing_receipts（≈20%）：某行无收据（记录 line_id/category）
      - incomplete_receipts（≈15%）：从收据删除部分关键字段（记录 missing_fields）
      - total_mismatch（≈15%）：总额≠明细之和（记录 sum_line_items/total_claimed）
  - 产物：
    - JSON：
      - `groundtruth_workspace/expense_claims.json`（主数据）
      - `groundtruth_workspace/expense_claims_with_errors.json`（含 `_errors` 与 `_policy_violations`）
      - `groundtruth_workspace/manager_mapping.json`（员工↔主管映射与本地邮箱密码）
    - PDF：
      - `files/policy_en.pdf`（英文政策）
      - `files/expense_claim_*.pdf`（各报销单）
  - Snowflake 初始化：
    - 默认执行 `preprocess/create_snowflake_db.py`，创建并填充 `TRAVEL_EXPENSE_REIMBURSEMENT.PUBLIC.ENTERPRISE_CONTACTS`
  - 运行：
    - `uv run -m tasks.fan.travel-expense-reimbursement.preprocess.main --agent_workspace tasks/fan/travel-expense-reimbursement --launch_time <ISO8601>`

- 统一评测（evaluation/main.py）
  - 输入参数（推荐）：
    - `--agent_workspace`：通常为 `tasks/fan/travel-expense-reimbursement`
    - `--groundtruth_workspace`：通常为 `tasks/fan/travel-expense-reimbursement/groundtruth_workspace`
    - `--launch_time`：占位参数（与 preprocess 对齐），不影响评测
  - Step 1｜政策合规评测：
    - 读取 `policy_standards_en.json` 和 `expense_claims.json`
    - 按“目的地+级别”计算上限：
      - 住宿：每晚（accommodation_per_night）
      - 餐饮：每日（meals_per_day，客户招待可 1.5×）
      - 本地交通：每日合计（local_transport_per_day）
      - 通讯/杂项：每次出差合计（communication_per_trip/misc_per_trip）
    - 打印逐单违规明细与汇总分类统计
  - Step 2｜邮件检查：
    - 优先使用 `expense_claims_with_errors.json`（因带 `_errors` 明细）
    - 自动从 `manager_mapping.json.accounts` 与 `configs/users_data.json` 构建本地 IMAP 账户（无需手动传）
    - 针对每个不合规报销单，检查员工与对应主管收件箱是否收到：
      - 表单错误邮件：主题 `Expense Claim Review Required`，正文包含错误类型关键词（如 `amount mismatch`、`missing receipts`…）与对应 PDF 文件名（例如 `expense_claim_EXP2025001.pdf`）
      - 政策超标邮件：主题 `Expense Over-Cap Notice`，正文包含超标类别关键词（如 `Meals over cap`、`Communication over cap`…）与 PDF 文件名
  - Step 3｜DB 入库检查：
    - 仅“表单合规”的报销单应入库到 `TRAVEL_EXPENSE_REIMBURSEMENT.PUBLIC."2025Q3报销表"`
    - 若存在政策超标，入库记录应当 `FLAG=1`（否则 `FLAG=0`）
    - 评测通过 MCP Snowflake server 查询：
      - `SELECT COUNT(*)` 验证表行数可读
      - `SELECT COUNT(*) WHERE CLAIM_ID=...` 验证“应入库”的 claim 是否存在
      - `SELECT FLAG WHERE CLAIM_ID=...` 验证 flag 值是否与期望一致
  - 运行：
    - `uv run -m tasks.fan.travel-expense-reimbursement.evaluation.main --agent_workspace tasks/fan/travel-expense-reimbursement --groundtruth_workspace tasks/fan/travel-expense-reimbursement/groundtruth_workspace --launch_time <ISO8601>`

- 依赖假设
  - 本地 IMAP/SMTP（poste）服务可用，且 `manager_mapping.json`/`configs/users_data.json` 中的邮箱已在 poste 中创建
  - MCP Snowflake server 可用，允许访问数据库 `TRAVEL_EXPENSE_REIMBURSEMENT`

- 备注
  - “表单错误”与“政策超标”的差异：
    - 表单错误（_errors: amount_mismatch/missing_receipts/incomplete_receipts/total_mismatch）→ 发送主题 `Expense Claim Review Required` 的邮件，不入库
    - 政策超标（_errors 中的 ..._over_cap）→ 发送主题 `Expense Over-Cap Notice` 的邮件，仍可入库并标记 `FLAG=1`，建议在记录的 `flag_reasons_json` 中存储结构化超标原因（类型/金额/上限/单位/规则引用等）
