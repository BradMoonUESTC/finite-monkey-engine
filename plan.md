## 基于 Codex 的漏洞挖掘总体方案

### 背景与目标

这套流程的目标是把“漏洞挖掘”做成一个可重复、可追溯、可控成本的工程闭环：Planning 负责把代码库切成可扫描的业务流任务，Reasoning 负责在业务流上做中性审计式挖掘并产出单漏洞条目，Validation 负责对每条漏洞做只读证据核验并给出是否成立的最终结论。整个链路以数据库为主干，以日志目录为审计材料，尽量减少“猜测式输出”和“不可复现的结论”。

本方案默认使用 Codex CLI 的只读 agentic workflow（自动检索、交叉引用、基于证据下结论），并且把工作目录严格限定在数据集的单个项目目录内，避免越权读取与不可控的上下文污染。

### 总体数据流

Tree-sitter 解析产出“全量函数目录”和函数体边界，Planning 用它作为唯一结构化基准，驱动 Codex 抽取业务流并最终生成可扫描的 `project_task`。Reasoning 读取 `project_task.business_flow_code` 与该任务绑定的 checklist 规则，调用 LLM 输出固定 JSON，再将多漏洞结果拆成单漏洞 `project_finding`。Validation 只针对 `project_finding` 逐条调用 Codex 做证据核验，并把结论写回 `validation_status/validation_record`，后续去重与导出都以 finding 为中心处理。

### 统一约束（工程硬边界）

受控目录必须与主扫描一致：从 `src/dataset/agent-v1-c4/datasets.json` 按 `project_id` 取 `path`，最终以 `<repo>/src/dataset/agent-v1-c4/<path>` 作为工作区根目录。任何目录缺失、越界或校验失败时，流程要给出明确的错误记录并可继续处理其它条目。

Planning 与 Reasoning/Validation 的“可写权限”需要区分。Planning 阶段只做业务流抽取与对齐拼接，继续保持只读执行即可；Reasoning 与 Validation 在智能合约项目里不仅需要读代码，还需要通过 Foundry 自动生成与运行 PoC 来验证可利用性与影响，因此必须允许在受控项目目录内进行受限写入与测试执行，但仍要保持工作区边界不变，并要求所有生成物可追溯、可清理、可复跑。

### Planning（已在monkey中实现）

#### 目标与产物

Planning 的产物是“业务流任务集合”，即把项目代码按业务语义切分成一组 Fi，并为每个 Fi 生成可直接喂给 Reasoning 的主代码包。Planning 不做 RAG、不维护向量库、不构建调用图；它只依赖 tree-sitter 的函数清单与函数体内容，确保所有引用都能被定位与拼接。

最终落库产物是 `project_task`。每条任务的核心输入在 `business_flow_code`，它由 Fi 的 `function_refs` 对齐到 tree-sitter 的函数体后拼接得到。任务的 `rule_key` 与 `rule`（checklist 列表）在 Planning 阶段就绑定好，Reasoning 不再临时分配检查规则。

#### 核心流程

第一步是正向抽取：把 tree-sitter 函数目录作为“可用函数清单”写入 prompt，调用 Codex 依次完成 P0（初次抽取）、P1（增量补全）、P2（收敛为 JSON）。P2 的 JSON 必须是机器可解析的 `flows/groups` 结构，并且 `function_refs` 必须严格来自可用函数清单，避免出现外部接口、常量、事件名或裸函数名。

第二步是覆盖率补全：从首轮 flows 计算覆盖集合与未覆盖集合，若覆盖率未达到目标阈值，则把未覆盖函数列表按批输入 Codex 做分组补全，产出新增的 `new_flows`，并合并到当前 flows 中。补全阶段倾向“更粗的 flow”，用更少的新增 flow 覆盖更多函数，避免把任务切得过碎导致后续成本飙升。

第三步是 finalize：在 flows 收敛后统一落库。对每个 Fi，先用 tree-sitter 对齐并拼装 `business_flow_code`，再按 checklist 体系做笛卡尔积生成任务，即 “Fi × rule_keys” 每个组合落一条 `project_task`。这样同一条业务流会按不同检查维度分别跑一遍，便于覆盖不同类型漏洞而不额外做调用图扩展。

已有的覆盖率数据：1000行项目，正向抽取覆盖率98%

#### 关键工程点

Planning 必须把 Codex 的 prompt/stdout/stderr 与 tree-sitter 映射日志一并保存到 `logs/planning_<project_id>_<timestamp>/`，并且把规划元信息写入 `project_task.scan_record`，保证后续可以追溯“某条任务是怎么来的、覆盖率是多少、哪些函数没对齐”。对于无法对齐的引用，需要保留缺失清单用于后续诊断，但不阻塞其它任务的生成。

### Reasoning（已经按照人类流程做了测试）

#### 目标与产物

Reasoning 的目标是“在给定业务流与给定 checklist 下，产出尽可能确定的漏洞条目，并把误报风险压到最低”。它不做诱导式“必有漏洞”提示词，而是以中性审计式提示词驱动模型；允许输出零漏洞，但一旦输出则要求证据可定位、描述可用于去重与复核。

Reasoning 的直接产物是每条 `project_task.result` 的多漏洞 JSON（固定 schema），以及拆分后的 `project_finding` 单漏洞记录。后续 Validation、去重、导出都围绕 finding 表，不再以 task 表作为漏洞载体。（这个是基于monkey的修改所确定的，在其他项目上有所出入）

#### 实践经验与本次核心目标（更可落地的定义）

Watcher、Reasoner、Ideator 这三种角色已经在两次真实 audit 中验证过有效：当时由人类承担 Watcher 与 Ideator，Codex 承担 Reasoner。这说明“把单次扫描变成可编排的多轮过程”，比单轮一次性输出更稳，且更接近真实审计工作方式。

本次要把三者落到系统里，必须做到两件事：

1) **职责清晰**：每个角色都有可执行的输入/输出格式（最好是 JSON），执行器无需“理解人话”也能跑。
2) **预算可控**：Watcher 有明确的停止条件与转向规则，避免 Reasoner 反复钻同一个点。

#### 三个角色的“专门职责”（必须可执行）

##### 1) Reasoner（挖掘执行器：负责产出漏洞候选）
**输入**（本轮固定输入，不得随意扩展）：
- `business_flow_code`：该 task 的主代码包
- `rule_key` + `rule_list`：该维度的 checklist
- `watcher_instruction`：Watcher 给出的本轮目标（要验证什么、要找什么证据）
- `constraints`：必须 JSON 输出、必须给证据、不得输出 intended design/纯建议

**输出**（固定 JSON，便于机器处理；保持现有多漏洞 schema 不变）：
- `{"schema_version":"1.0","vulnerabilities":[{"description":"..."}]}`（0..N 条）
- 同时在 `description` 内必须包含：
  - 触发条件与影响
  - 证据定位（至少函数名/文件名/关键语句）
  - “为什么不是误报”的反证点（例如权限/前置条件/不可达性已排除）

> 说明：Reasoner 不负责决定“是否继续”，只负责给出“本轮结果 + 下一步建议”（下一步建议写进 watcher_record 即可）。

##### 2) Watcher（流程控制器：负责继续/转向/停止 + 轨迹记录）
**职责 1：记录**（把挖掘过程变成可回放的回合制）：
- 每一轮都记录：输入摘要、Reasoner 结果摘要、已确认/已否定/未决列表、消耗与预算。

**职责 2：裁决**（继续/转向/停止）：
- `continue`：Reasoner 给出明确的下一步可验证动作，且预计有信息增益
- `pivot`：连续若干轮无增益/陷入循环/证据不足，转向 Ideator 的新探针
- `stop`：达到预算上限或已无高价值未决点

**职责 3：给出“可执行指令”**：
- 输出下一轮 `watcher_instruction`（必须是可执行的：要检索的关键词/文件/变量/分支）
- 给出下一轮预算：`max_more_rounds / time_limit_sec / no_progress_rounds`

##### 3) Ideator（发散引擎：负责提供“可验证的新角度”）
**核心职责**：在预算内给出少量“可检索、可验证”的新方向，避免泛泛建议。

**输入必须包含 Watcher 的动作上下文**（你刚刚确认的点）：
- Watcher 的决策（continue/stop/pivot）
- Watcher 的预算与限制
- Watcher 给 Reasoner 的指令（以及已否定/已收敛清单）

**输出必须可执行**：
- `new_hypotheses`：2~5 个假设（每个假设要能被验证）
- `suggested_probes`：每个假设对应的检索探针（rg 关键词/要看的文件/要找的状态变量）
- `expected_evidence`：若假设成立，应当看到什么证据（用于 Watcher 判断是否有增益）

#### 回合制闭环（落地流程，按 task 执行）

对每条 `project_task`（一行）：
1) **Watcher 初始化**：读取 task 输入（business_flow_code/rule_key/rule_list），设置预算（如 3~6 轮），生成首轮 watcher_instruction。
2) **Reasoner 执行**：基于 watcher_instruction 输出多漏洞 JSON（可为 0）。
3) **拆分入库（保持现有逻辑）**：把 `project_task.result` 拆分成 `project_finding`（幂等：按 task_id 先删后建）。
4) **Watcher 评估**：对比本轮前后状态，决定 `continue/pivot/stop`，并记录本轮轨迹。
5) **Ideator（仅在需要时）**：当 Watcher 判定 `pivot` 或“本轮无增益”时触发，产出新的 probes，供下一轮 watcher_instruction 使用。
6) 重复 2~5 直到 stop。

#### “过程记录”怎么写进系统（必须可追溯）

建议把每个 task 的全过程写入 `project_task.scan_record`（JSON 字符串），结构建议：
- `schema_version: reasoning_trace_v1`
- `task_id / task_uuid / project_id / rule_key`
- `rounds: [{round, watcher_instruction, reasoner_stdout_path, parsed_result_summary, watcher_decision, ideator_output_summary, budget_snapshot}]`
- `final: {vuln_count, stop_reason, key_evidence_refs}`

> Codex 的 stdout/stderr 仍然写到 `logs/reasoning_<project_id>/<task_id>/<round>/`，scan_record 里只保存路径与摘要，避免数据库膨胀。

#### Foundry PoC（可选增强：让 finding 更硬）

当项目允许在受控目录内做受限写入/测试执行时，可把 Foundry 加入 Reasoner 的“验证动作”集合：
- Watcher 允许的情况下（预算内），Reasoner 生成最小化测试并运行 `forge test`，把失败栈/日志/复现步骤写入 evidence。
- Ideator 提供“可验证假设 + 预期现象”，Watcher 用来判断是否继续或转向。

> 如果当前阶段只做只读扫描，也可以先不启用 Foundry：但三角色协作与回合制闭环仍成立。

#### 核心流程

Reasoning 读取任务的 `business_flow_code` 作为主代码输入，并读取 `rule_key` 与 `rule`（JSON 列表）作为检查清单。模型调用强制 `response_format=json_object`，输出 JSON 中的 `vulnerabilities` 必须是数组，数组元素以 `description` 承载单漏洞文本，单条描述控制在适合去重与复核的长度范围。

Reasoning 执行完成后，会将多漏洞 JSON 拆分写入 `project_finding`。拆分采用幂等策略：以 `task_id` 为粒度先删除旧 findings 再重建，避免中断重跑导致重复插入。为了支持断点续跑，task 侧使用 `short_result` 标记拆分是否完成；当 `result` 已存在但未拆分时，仅补拆分而不再重复调用模型。

#### 任务编排与可追踪性

Reasoning 的并行策略以业务流为单位：任务会按 `group` 分组，同组（同一 Fi）串行，不同组并行，便于未来在同一业务流内引入“同组总结”以减少重复发现。即使默认不开启历史总结，也应保留组维度，保证可控的执行顺序与回溯路径。

### Validation（已在monkey中实现）

#### 目标与产物

Validation 的目标是把 Reasoning 产出的“候选漏洞”变成“可站得住的结论”。它只对 `project_finding` 表中的单漏洞条目做核验，利用 Codex 在受控目录内执行多步只读检索与交叉引用，判断漏洞是否真实存在、是否只是误报或设计使然，并给出影响程度与利用难度的结论。

Validation 的产物写回 finding 表：`validation_status` 存放稳定枚举值，`validation_record` 存放可追溯的 JSON 记录（包含模型、沙盒设置、workspace_root、prompt_hash、原始输出、解析结果与耗时等）。

#### 核心流程

Validation 只拉取“未被去重删除且仍为 pending/空”的 findings，逐条构造严格 JSON-only 的 Codex prompt，并强制要求先检索后下结论，同时要求优先参考项目文档与 NatSpec 注释。Codex 的工作目录通过 `datasets.json` 严格计算，并校验必须位于数据集基路径之下，确保不会访问到项目目录之外的文件。

Codex 返回后，系统解析其 JSON 输出并写回枚举状态；任何解析失败、超时或非零返回码，都要落为明确的 `error` 或保守的 `not_sure`，并把原始 stdout/stderr 与错误原因完整写入 `validation_record`，保证后续可以复盘与灰度改进 prompt。

#### 用 Foundry 做实证确认：把“可能成立”变成“可复现成立”

当 Reasoning 已经产出 PoC 或测试线索时，Validation 不应仅做文本层面的复核，而应把“复现与确认”变成第一等公民：在受控项目目录内，优先复跑对应的 `forge test`，确认漏洞触发条件、影响与可利用路径确实成立，并把复现结果写入 `validation_record` 作为最终裁决的依据。对于 Reasoning 未能稳定复现但怀疑度较高的 finding，Validation 可以在预算内补全最小 PoC 来验证关键前置条件；若仍无法复现或证据不足，则应保守落为 `not_sure`，并在记录中明确缺失点与下一步需要的外部信息。

#### 状态口径与下游对齐

Validation 的状态枚举需要稳定、可统计、可导出。导出规则应以 finding 为中心，只导出明确为漏洞的状态集合；误报与设计使然应明确可区分；不确定与系统错误应单独留档以便人工复核或重跑。这样可以把“发现、确认、导出”三件事解耦，减少流程互相污染，也便于逐步提升自动化比例。


