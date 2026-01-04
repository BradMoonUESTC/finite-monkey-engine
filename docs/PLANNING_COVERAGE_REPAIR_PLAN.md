## Planning 覆盖率评估与兜底补全方案（仅方案，不改代码）

### 已确认口径（实现时严格按此执行）
- **覆盖率目标**：最终验收 **≥90%**（两步都完成后统一计算最终覆盖率；中途仅做可选进度统计）。
- **统计粒度**：按 **所有函数** 统计（不区分 external/internal/private）。
- **重复覆盖**：允许（第一步/第二步都可重复覆盖同一函数，不做去重，不影响落库）。
- **Ambiguous（同名多实现/重载）**：**不考虑**；对齐时不强制要求输出参数签名，也不做多实现消歧（实现可取任意一个匹配作为覆盖）。
- **Missing**：一律视为 **未覆盖**（仅用于覆盖率与诊断，不阻止临时保存/后续补全流程）。
- **补全策略**：只允许 **新增新的 Gi/Fi**，**不允许修正旧 Fi**（不输出/不接受 `~ Fi ...`）。
- **业务流粒度**：倾向 **更粗**（少条长 flow），允许一个 flow 覆盖较多函数。
- **staging 临时保存**：只在**内存变量**中保存 Gi/Fi 与 function_refs（不落文件、不落数据库）；但 **Codex 对话日志仍需要记录**。
- **rule_key 来源**：按“当前实现”口径，**沿用现有 prompt/checklist 体系提供的 rule_key 列表**（不引入新的分配/轮询策略）。

### 背景与目标
现有 planning 通过 Codex 抽取业务流/业务流组（Gi/Fi），并将每个 Fi 落库为 `project_task.business_flow_code`（后续扫描的主输入）。

但 **业务流集合可能无法覆盖整个 codebase**：tree-sitter 已解析出“全量函数清单”，我们也能从已落库任务中得到“已覆盖函数集合”。因此需要新增一个“覆盖率评估 + 兜底补全”的 planning 增量流程：

- **覆盖率评估**：给出项目函数覆盖率、未覆盖函数列表、未覆盖热点（按文件/合约/可见性统计）。
- **兜底补全**：把未覆盖函数作为输入再次让 Codex 分组（按业务逻辑归类），生成新增的业务流/业务流组，并继续落库。
- **迭代收敛**：重复“评估→补全→再评估”，直到达到覆盖率目标或未覆盖项可接受。

---

### 总体落地形态：两步制（先正向抽取，再覆盖率补全，最后统一落库）
从当前代码/流程的角度，planning 未来会被明确拆成两大阶段，并引入“临时保存（staging）→最终落库（finalize）”的概念：

#### 第一步：正向业务流/业务流组解析（P0/P1/P2）→ 匹配 → 临时保存
1) Tree-sitter 解析得到全量函数清单 \(F\)（`ContractOrLibrary.func`）。
2) Codex 进行正向抽取（P0/P1/P2），得到初始 Gi/Fi（JSON）。
3) 对初始 Fi 的 `function_refs` 做 tree-sitter 对齐（matched/missing/ambiguous），并计算初始覆盖集合 \(C_0\) 与未覆盖集合 \(U_0\)。
4) **临时保存（staging）**：
   - 保存初始的 Gi/Fi JSON（原始输出 + 解析结果 + 对齐日志 + 覆盖率报告）。
   - 保存每个 Fi 的“函数引用列表（function_refs）”作为后续补全的基线（不急着写成最终可扫描任务）。

> 这一阶段的产物重点是：得到“初始业务流集合 + 初始覆盖率画像”，并把它们稳定落到可追踪的临时状态里。

#### 第二步：覆盖率补全到 100%（或 90%+）→ 拆分/再分组 → 临时保存
1) 基于 \(U_0\)（未覆盖函数列表）触发 coverage repair（P3/P4/P5）：
   - 目标：覆盖率达到阈值（建议默认 90%+，最好 100%）。
2) 将新增/修正后的业务流（新增 Gi/Fi 或对已有 Fi 的 ~ 修正）与第一步结果合并，得到最终函数覆盖集合 \(C_1\) 与未覆盖集合 \(U_1\)。
3) 将“剩余仍未覆盖的函数”继续分批喂给 Codex 进行下一轮补全，直到达标或进入人工确认名单。
4) **临时保存（staging）**：
   - 保存每轮补全的输入 batch、输出 delta、合并后的最终 JSON、以及每轮 coverage_report。
   - 保存拆分后的业务流（可能比第一步更多、更细粒度的 Fi）。

> 这一阶段的产物重点是：让业务流集合尽可能覆盖整个代码库，并把“补全后的业务流集合”稳定下来，等待最终落库。

#### Finalize：把“业务流函数 list + 每个函数体内容”组装成 business_flow_code，并按 **多 rule_key 复制落库**
在两步的 staging 都完成后，进行一次“最终落库（finalize）”：

1) 对每个最终 Fi：
   - 取其 `function_refs`（严格来自 tree-sitter 清单）。
   - 从 tree-sitter 解析结果中抓取每个函数的函数体内容（file+line range 或 content 字段），拼装为该 Fi 的 `business_flow_code`（可理解为该业务流的“主代码包”）。
2) **rule_key 复制策略（每个 Fi 绑定多个 rule_key）**：
   - 系统支持配置多个 rule_key（例如环境变量 `BUSINESS_FLOW_RULE_KEYS=PURE_SCAN,RK2,RK3,RK4,RK5`）。
   - **每个 Fi 必须对每个 rule_key 都生成一条任务**（即 “Fi × rule_keys” 的笛卡尔积）。
     - 示例：5 个 rule_key、6 条 business flow → 每个 flow 生成 5 条任务 → 总计 30 条落库记录。
   - 目的：让同一条业务流在后续扫描阶段能被不同 rule/prompt 体系分别跑一遍（并行或分批均可）。
3) 落库（最终态，复制写入）：
   - 对每个 Fi、对每个 rule_key，写入一条 `project_task`：
     - `business_flow_code`：该 Fi 拼好的代码正文（由函数体拼接）；不同 rule_key 版本内容相同，但 `rule_key` 不同。
     - `rule`：JSON meta（建议至少包含）：
       - `flow_id / flow_name / group_ids`
       - `function_refs`
       - `missing_function_refs / ambiguous_function_refs`（若存在）
       - `planning_stage="finalize"`
       - `rule_key`
     - `rule_key`：当前这一条任务对应的 rule_key
   - **命名/可追踪性建议**：
     - `name`：`Fi:<flow_id> <flow_name> [<rule_key>]`（避免同一 flow 的多条任务重名）
     - `group` 字段（如有）：仍建议保留 `<flow_id>`，便于按 flow 聚合多条 rule_key 任务
     - 运行日志/扫描结果应能按 `(project_id, flow_id, rule_key)` 三元组定位

> 核心要求：**最终写入 DB 的每条任务，必须已经是“可扫描”的 business_flow_code（含函数体内容）**；staging 阶段只存列表/日志/中间 JSON，不混淆最终任务。

### 硬约束（必须遵守）
- **工作目录约束**：Codex 执行必须 `codex exec --cd <project_root>`，`project_root` 严格由 `main.py -> dataset_base -> datasets.json[project_id].path` 决定（位于 `src/dataset/agent-v1-c4` 下）。
- **sandbox/审批**：建议 `sandbox=read-only`，`--ask-for-approval never`。
- **函数引用约束**：
  - `function_refs` **只能来自 tree-sitter 函数清单**（完全一致匹配）。
  - **禁止外部接口/外部依赖**（例如 IERC20/IVault/外部库等）出现在 `function_refs`。
  - **禁止常量/状态变量/typehash/事件名**出现在 `function_refs`。
  - **禁止裸函数名**（必须是 `ContractOrLibrary.func` 形式，必要时带签名）。

### 输入与输出（数据形态）
#### 输入
- **全量函数清单**：来自 tree-sitter 解析结果（每项至少包含 `name=Contract.func`、`relative_file_path`、`visibility`、`start_line/end_line`）。
- **已抽取的业务流结果**：
  - 来自 `project_task` 已落库的 `rule(JSON)` 与 `business_flow_code`：
    - `rule.function_refs`：该 flow 的函数引用序列
    - `rule.missing_function_refs`：允许 partial 落库时的缺失列表
  - 也可从 planning 日志目录中的 `tree_sitter_mapping.json` 汇总（若需要离线评估）。

#### 输出
1) **覆盖率评估报告**（建议 JSON + 人类可读摘要）
- `total_functions`
- `covered_functions`
- `coverage_ratio`
- `uncovered_functions`（列表：`Contract.func`）
- `uncovered_breakdown`（按 file/contract/visibility 统计）

2) **兜底补全的新增 Gi/Fi**
- 新增/修正形式（增量）或最终 JSON（同 `business_flow_planning_v1`）
- 落库方式：继续生成新的 `project_task`（追加，不覆盖旧任务），或对现有任务做 `~` 修正（可选策略，见下文）。

---

### 覆盖率评估逻辑（定义与算法）
#### 1) “覆盖”的定义（建议）
给定 tree-sitter 的全量函数集合 \(F\)，以及 planning 已生成的任务集合 \(T\)：

- 对每条任务 \(t \in T\)，取其 `rule.function_refs` 中 **能在 tree-sitter 清单中匹配到的**函数集合 \(M_t\)。
  - 若当前允许 partial 落库，则 `missing_function_refs` 不计入覆盖。
- 全局覆盖集合：\(C = \bigcup_{t \in T} M_t\)。
- 未覆盖集合：\(U = F \setminus C\)。
- 覆盖率：\(\text{coverage} = |C| / |F|\)。

#### 2) 需要额外记录的诊断指标（建议）
- **未覆盖热点**：
  - 按 `relative_file_path` 统计 `U` 中的数量（TopN）。
  - 按 `ContractOrLibrary`（`name` 的前缀）统计（TopN）。
  - 按 `visibility` 统计（external/public/internal/private）。
- **重复覆盖（允许，不需要去重）**：
  - 仅用于统计与可观测性：哪些函数被多个 flow 覆盖、覆盖次数分布等。
  - 重复覆盖不影响流程：第一步/第二步都允许多个业务流引用同一函数。

#### 3) 评估输出的落盘与可追踪性
- 每次评估生成一个 `coverage_report.json`，写到 `logs/planning_<project_id>_<ts>/` 下（与 codex artifacts 同目录）。
- 报告里记录：
  - `planning_run_id`（时间戳/哈希）
  - `project_id`
  - `task_ids_used`（参与评估的 project_task id 列表，或筛选条件）
  - `function_catalog_hash`（tree-sitter 清单的 hash）

---

### 兜底补全（Coverage Repair）流程设计
#### 总体策略
对未覆盖函数集合 \(U\) 做增量规划：

1) 将 \(U\) 作为“待分组对象集”输入给 Codex。
2) 让 Codex **只基于这些函数**，按业务语义进行分组，并产出新增的 Gi/Fi（增量形式）。
3) 将新增 Fi 临时保存（staging，保存新增 Gi/Fi 与对齐结果）。
   - 覆盖率在此阶段仅做“进度统计”（可选），不作为最终验收口径。
   - **最终覆盖率统一在两步都完成、产出最终 Gi/Fi 集合后计算**（见“覆盖率评估逻辑”与“验收标准”）。

#### 兜底补全的 ID 稳定性要求
为保证 Gi/Fi ID 全局稳定：
- 读取现有 planning 结果中最大的 `Gx/Fx` 序号（例如已有 `G1..G8`、`F1..F11`）。
- 兜底补全阶段新增的 ID 必须从 **下一个序号**开始（例如 `G9`、`F12`…）。
- 后续多轮补全也遵循“只新增/修正，不重排已存在 ID”。

#### 分批策略（避免一次喂给 Codex 太大）
未覆盖函数可能很多，建议分批输入：
- **Batch by file/contract**：按 `relative_file_path` 或合约/库名前缀聚类，优先处理未覆盖热点文件。
- **Batch size**：每批控制在 150~400 个函数引用（根据模型上下文与成本调整）。
- **重叠控制**：每个函数只属于一个 batch；若 Codex 判断应跨批归并，则在“修正轮”里允许把函数移动到其它 Gi/Fi（以 `~` 行输出）。

---

### Coverage Repair 的 Prompt 设计（建议新增 P3/P4/P5）
> 说明：下面是“覆盖率兜底补全”专用对话结构，思路与现有 P0/P1/P2 一致：主 prompt + 2 轮增量修正 + 最终 JSON 收敛。

#### P3（主 prompt：对未覆盖函数进行业务分组与新增业务流）
输入包含三部分：
- 现有 Gi/Fi 概览（只要 ID 与组名/流名，不需要完整函数列表，避免太长）
- 未覆盖函数列表（必须来自 catalog，完全一致）
- 约束（禁止外部依赖/常量/裸函数名）

**P3 期望输出（增量形式）**：
- `+ Gi ...`：新增业务流组（可选；若只新增 Fi 也可以）
- `+ Fi ...`：新增业务流（核心）
- `~ Fi ...`：若发现某些未覆盖函数实际上应补进已存在 flow，也允许修正（可选策略；若不希望修改旧 flow，可禁用 `~`）
- checklist（仅列未覆盖风险类别，不展开解释）

#### P4（修正 prompt：针对“仍未覆盖/分组不合理/疑似遗漏”做增量补全）
输入：
- P3 输出
- 剩余未覆盖函数列表（即 \(U\) 减去 P3 新覆盖的部分）

输出仅允许：
- `+ Gi` / `+ Fi` / `~ Fi`

#### P5（收敛 prompt：输出最终 JSON）

输出必须是单个 JSON 对象（只包含新增/修正后的最终全量 Fi，便于程序解析）：
- `schema_version`: `"business_flow_planning_v1"`
- `groups`: 可选（如果 Gi 也要维护）
- `flows`: 必须（全量 Fi；ID 不重排）

---

### Coverage Repair Prompt 模板（可直接复制使用）
> 注意：本补全流程 **完全禁止 external/interface/依赖函数** 出现在 `function_refs`；凡是不在 catalog 的函数，必须直接丢弃，不允许用 `(interface)` 占位。

#### P3 主 Prompt（未覆盖函数分组）
你是“业务流补全助手”。现在我们已经有一批业务流/业务流组（Gi/Fi），但仍有一批 tree-sitter 解析出的函数未被任何业务流覆盖。请你把这些“未覆盖函数”按业务语义进行分组，并产出新增的业务流组/业务流（Gi/Fi），用于继续 planning 落库。

【硬约束】
- 你只能使用我给出的“未覆盖函数列表”中的函数名（完全一致匹配）。
- 禁止输出任何未覆盖列表之外的函数（包括外部接口/外部依赖/库函数/系统合约等）。
- 禁止常量/状态变量/typehash/事件名；只允许函数。
- 禁止裸函数名，必须是 `ContractOrLibrary.func`（或带签名）形式。

【已有 Gi/Fi 概览（仅供你避免重复命名/重复分组，不代表可引用函数）】
{EXISTING_GI_FI_OVERVIEW}

【未覆盖函数列表（你只能从这里挑选）】
{UNCOVERED_FUNCTIONS_LIST}

【输出要求（增量形式，只输出新增/修正行，不要解释）】
1) 新增业务流组（可选）：
- + Gi 组名: Contract.func, Contract.func ...

2) 新增业务流（必须）：
- + Fi 业务流名 (归属: Gx,...): Contract.func, Contract.func ...

3) 若你认为“未覆盖函数应该并入现有某个 Fi”，允许用 ~ 修正（可选）：
- ~ Fi 业务流名 (归属: Gx,...): Contract.func, Contract.func ...

4) 最后输出 checklist（只列类别名称，标注仍待补充/确认，不展开代码）。

#### P4 修正 Prompt（对剩余未覆盖做增量补全）
基于你上一轮输出的 `+/~` 行，我们仍然有一些未覆盖函数。请继续增量补全：只输出新增/修正行，不要重复已覆盖的行。

【硬约束同上】
- 只能使用“剩余未覆盖函数列表”中的函数名（完全一致匹配）。
- 禁止任何未在列表中的函数；禁止外部依赖/接口；禁止常量/typehash/事件；禁止裸函数名。

【上一轮增量输出】
{P3_OUTPUT}

【剩余未覆盖函数列表】
{REMAINING_UNCOVERED_FUNCTIONS_LIST}

【输出格式】
- + Gi ...
- + Fi ...
- ~ Fi ...

最后给一次 checklist（只列类别，标注仍待补充/确认）。

#### P5 收敛 Prompt（最终 JSON）
你现在需要输出“最终版”的业务流（Fi）全量列表，并且必须以 JSON 输出，方便机器解析与落库。

【输入】
1) 现有全量业务流 JSON（上一阶段 planning 的最终 JSON，或当前数据库中汇总后的等价结果）：
{EXISTING_FINAL_JSON}

2) 本次 coverage repair 的增量输出（P3/P4 的 +/~ 行）：
{P3_P4_DELTA}

【输出要求（只输出 JSON，不要任何额外文本）】
输出必须是单个 JSON 对象，严格遵循：
{
  "schema_version": "business_flow_planning_v1",
  "groups": [{"group_id":"G1","group_name":"string","functions":["Contract.func"]}],
  "flows": [
    {
      "flow_id": "F1",
      "flow_name": "string",
      "group_ids": ["G1"],
      "function_refs": ["Contract.func", "Contract._internalFunc"]
    }
  ]
}

约束：
- flows 必须包含所有 Fi（全量），且 flow_id 必须稳定，不要重排。
- function_refs 必须全部来自 tree-sitter 函数清单（完全一致），且不得包含外部依赖/接口/常量/typehash/事件/裸函数名。

---

### 落库策略（建议）
#### 1) 追加式落库（推荐）
coverage repair 产生的新 Fi 作为新增 `project_task` 写入（不删除旧任务）：
- `name`: `Fi:<flow_id> <flow_name>`
- `rule(JSON)` 增加字段：
  - `planning_stage`: `"coverage_repair"`
  - `coverage_batch_id`: `"B1"|"B2"|...`（分批补全时）
  - `uncovered_seed_count`: 本批未覆盖输入数量
  - `covered_new_count`: 本批新增覆盖数量
- `business_flow_code`: 仍为拼接后的代码正文（或 function_refs JSON，取决于你当前实现策略）

#### 2) 修正式落库（可选）
允许 P3/P4 输出 `~ Fi ...` 来修改已有 flow 的函数列表：
- 优点：更贴近“最终正确的业务流集合”
- 风险：修改历史任务可能影响可追溯性
- 折中：对被修正的旧 task 做“逻辑废弃标记”，再写入新版本 task（保持不可变历史）

---

### 对齐与质量门槛（建议）
每轮补全都需要做对齐校验与质量门槛判断：
- **对齐**：新增的 `function_refs` 必须能在 tree-sitter 清单中匹配（否则直接剔除/退回重试）。
- **最小有效任务**：一个 Fi 至少包含 N 个函数（建议 N≥2），否则容易产生“碎片任务”。
- **重复覆盖无需处理**：不对 Fi 做“相似度去重/合并/跳过”，允许多个 Fi 高度重叠或共享关键管线函数。

---

### 运行与日志（建议）
每次 coverage repair 运行都记录完整日志（与现有 planning 日志同标准）：
- `coverage_report.json`：评估报告（含 uncovered 列表/统计）
- `uncovered_batch_Bk.txt/json`：每批输入给 Codex 的未覆盖函数列表
- `p3/p4/p5` 的 prompt/stdout/stderr 全部落盘
- `mapping_repair.json`：新增 Fi 的对齐结果（matched/missing）

---

### 验收标准（DoD）
- 能输出清晰的覆盖率报告：覆盖率、未覆盖列表、热点统计。
- 能对未覆盖函数进行分批兜底补全，并生成新增的业务流/业务流组（Gi/Fi）。
- 新增 Fi 能通过 tree-sitter 对齐校验，并落库为 `project_task`，可继续驱动后续扫描。
- 全流程严格遵守 `--cd project_root` 工作目录约束与“禁止外部依赖/接口/常量/裸函数名”的输出约束。

