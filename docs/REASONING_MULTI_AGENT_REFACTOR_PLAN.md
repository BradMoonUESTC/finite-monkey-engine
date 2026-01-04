## Reasoning 过程重构方案：Reasoner + Watcher + Ideator（三代理协作）（仅方案，不改代码）

### 目标（两件事）
- **P0：尽可能全面地产出漏洞**（coverage of issues）
- **P0：尽可能降低误报**（false-positive control）

其中：
- 降低误报主要依赖 **Codex 的 agentic workflow**（自动只读检索：rg/grep/cat/ls，交叉引用文档/实现），prompt 里强调“必须基于证据、必须能指向具体函数/代码片段”即可显著减少“明显误报”。
- 提升“全面性”需要新增一个“围绕单个 task 的持续挖掘编排层”，即：**Watcher + Ideator** 与现有的“漏洞挖掘者 Reasoner”协同。

---

### 当前输入（planning 之后你已经拥有的东西）
对每个 `project_task`（数据库一行）：
- **business_flow_code**：待扫描主代码（已经拼好函数体，来自业务流函数列表）
- **rule_key**：细粒度检查类别 key（来自 `src/prompt_factory/vul_prompt_common.py` 的 checklist keys）
- **rule（rule list）**：该 rule_key 对应的 checklist 条目列表（后续会拼进 prompt）

Reasoning 阶段将基于上述三者进行多轮漏洞挖掘与收敛。

---

### 新的三代理角色定义

#### 1) Reasoner（漏洞挖掘者 / 挖掘执行器）
定位：对某一条 task 的 `business_flow_code + rule_list` 做“漏洞发现/证据收集/修复建议”。

能力要求：
- 使用 Codex 的 agentic workflow 做上下文搜索（只读命令），例如：
  - `rg` 找调用点/状态变量读写
  - `cat/sed` 查看关键函数与结构体
  - 优先读项目文档（README/spec）与注释（用于“是否 intended design”判断）

输出（建议强制 JSON）：
- `findings`: [ ... ]（可以是 0..N 个）
  - `title`
  - `severity`（或 impact/likelihood）
  - `confidence`
  - `evidence`: 具体到函数名/文件/代码片段引用（必须）
  - `attack_path` / `exploit_scenario`
  - `false_positive_checks`: “为何不是误报”的核验点
  - `next_steps`: 若不确定，给出下一轮需要验证的点（这将驱动下一轮）
- `next_actions`: 明确下一轮要做什么（例如“搜索 X 是否可被外部调用”“检查 Y 的写入是否在 Z 条件下发生”）
- `stop_signal`: `continue | stop`（Reasoner 自己的建议，Watcher 最终裁决）

> 备注：Reasoner 不负责“何时停止”与“是否陷入死胡同”的最终判断，只给建议。

#### 2) Watcher（过程监督者 / 记忆体 / 终止器）
定位：围绕“单个 task 的多轮挖掘过程”进行编排，核心目的 3 个：
1) **将每一次的思考结果保存下来，作为项目知识**
2) **根据 Reasoner 每次输出决定是否继续挖掘**（通常下一轮思路由 Reasoner 给出）
3) **避免 Reasoner 过度思考陷入死胡同**（及时终止或改换方向）

Watcher 输入：
- task 的静态信息：`task_id / rule_key / rule_list / business_flow_code`
- 运行状态：历史轮次记录、已发现 findings、未解决疑点列表、消耗（轮次/时间/成本）
- 来自 Ideator 的“新角度假设/新检查维度”

Watcher 输出（建议强制 JSON）：
- `decision`: `continue | stop | pivot`
- `reason`: 为什么继续/停止/转向（简短）
- `budget`: 下一轮允许的资源（`max_more_rounds`, `time_limit_sec` 等）
- `instruction_to_reasoner`: 下一轮的具体指令（可以引用 Reasoner 的 next_actions，也可结合 Ideator 的想法合并）
- `record_to_persist`: 本轮要落库的“过程记录/知识片段”

**停止条件（建议明确化）**：
- 达到硬预算：`max_rounds` / `max_time` / `max_no_progress_rounds`
- 连续 N 轮没有新增高置信 findings（或仅新增低价值/重复点）
- Reasoner 多次给出相同 next_actions（陷入循环）
- Ideator 给出的替代方向也验证失败（无新信息增益）

> 关键：Watcher 是“流程控制器”，不是漏洞发现者本体。

#### 3) Ideator（发散者 / 新想法引擎）
定位：专门负责提出“Reasoner 可能遗漏的角度”，提升全面性，避免被某个 checklist 视角束缚。

输入：
- 当前 task 的业务流与关键资产/权限/资金流摘要（可由 Watcher 汇总）
- 当前已发现的 findings（用于避免重复）
- 当前未解决疑点（open questions）
- **Watcher 对 Reasoner 的动作上下文**（必须可见）：
  - Watcher 的最近决策：`continue | stop | pivot`
  - 本轮/下一轮预算：`max_more_rounds / time_limit_sec / no_progress_rounds` 等
  - Watcher 给 Reasoner 的指令（instruction_to_reasoner）与 pivot 目标
  - Watcher 认为“已验证/已否定/已收敛”的点（避免 Ideator 再提同样方向）

输出：
- `new_hypotheses`: 新的攻击/失败模式假设（多条）
- `suggested_probes`: 建议 Reasoner 下一轮做的验证动作（rg/grep 关键词、要看的文件、要找的状态变量）
- `coverage_gaps`: 认为还没覆盖到的业务环节（例如“撤销/退款/暂停/升级/权限变更/边界条件”）

> Ideator 不做最终判断，只提供“可执行的探索方向”。

---

### 三代理如何交互（单 task 的执行循环）
对每个 `project_task`，运行一个多轮 loop：

1) **Watcher 初始化**
   - 建立 task 的运行上下文：`round=0`，预算（默认如 3~6 轮，可配置），并生成首轮给 Reasoner 的指令。
   - 生成“task 摘要”（业务流入口、资产、权限点、关键状态变量/事件）供 Ideator 使用。

2) **Reasoner 第 1 轮**
   - 输入：business_flow_code + rule_list + Watcher 指令
   - 输出：findings + next_actions + stop_signal

3) **Watcher 记录与裁决**
   - 把本轮“思考结果（结构化）”写入 `record_to_persist`
   - 判断：是否继续？若继续，明确下一轮 budget 与 instruction_to_reasoner

4) **Ideator 发散补充（可与 2/3 并行或插入）**
   - Ideator 基于当前状态输出新 hypotheses/probes
   - Watcher 合并 Ideator 的 probes 到下一轮指令（或触发 pivot）

5) **循环 2~4 直到 Watcher stop**

6) **最终收敛输出**
   - Watcher 汇总所有 findings（去重、合并证据、标注置信度）
   - 写入数据库（见下节）

---

### “思考过程/项目知识”如何保存（落库口径）
你希望 “每一次思考结果保存下来，作为项目知识”。建议分两层：

#### A) per-task 的过程记录（强相关）
落到 `project_task.scan_record`（或新增专用列/表，但此方案先按现有字段复用）：
- `schema_version`: `reasoning_trace_v1`
- `task_id / task_uuid / project_id / flow_id / rule_key`
- `rounds`: [
  - `{round, agent, started_at, finished_at, input_hash, output_json, codex_stdout_path, codex_stderr_path, decision}` …
]
- `final_summary`: 本 task 的最终结论（含 0..N findings）

#### B) per-project 的“可复用知识”（弱相关，但可积累）
（可选，后续实现时再决定落库位置）
- “跨 task 复用”的知识片段，例如：
  - 项目关键角色/权限模型（owner/admin/guardian）
  - 关键资产与资金流（vault/token/feeTo）
  - 关键不变量（balance/totalSupply/order lifecycle）
  - 已确认的 intended design（避免后续反复误报）
- 形式建议：`knowledge_items: [{tag, content, evidence_refs, created_from_task_ids}]`

> 注意：你当前强调“降低明显误报”主要靠 Codex 搜索能力和 prompt 约束；这个 per-project 知识层更多用于“跨任务记忆”和“减少重复探索”。

---

### 误报控制（prompt 约束建议）
为了让 Reasoner 在 Codex 的自动检索能力加持下减少明显误报，建议在 prompt 强制：
- 必须给出“可定位证据”：至少 1 个函数名 + 关键代码片段/条件分支说明
- 必须显式写出“为什么不是 intended design / 为什么不是受权限保护”
- 对任何“外部调用可达性”的结论必须通过搜索确认（例如 `rg "function X"` + 检查可见性/调用路径）

---

### 全面性增强（Watcher/Ideator 的检查维度）
即使 rule_key 已细粒度拆分（来自 `vul_prompt_common.py`），仍建议 Ideator 定期注入以下“通用漏检面”：
- 权限/治理变更、暂停/恢复、升级/初始化
- 资金流：withdraw/refund/fee 去向、边界金额、重入点
- 状态机：订单/申诉/取消/超时等生命周期边界
- 观察性：事件遗漏导致不可追踪、前端依赖读接口
- 经济性：极值参数/精度/溢出与舍入误差累积

---

### 资源与并发建议（避免死胡同 + 提升吞吐）
- task 粒度并行：不同 task 可并行（小并发）
- 单 task 内：Reasoner 串行多轮；Ideator 可并行生成新想法；Watcher 最终裁决
- 预算控制：`max_rounds_per_task`、`max_time_per_task`、`max_no_progress_rounds`

---

### 与现有数据表的衔接（输出写入）
最终漏洞结果仍按现有设计写入 `project_finding`：
- Reasoner/Watcher 汇总出的每个 finding 拆分成一条 `project_finding`
- `validation_status/validation_record` 仍由后续 validation 阶段（Codex confirm）负责

本方案在 reasoning 阶段额外强调：
- **过程轨迹**：写入 `project_task.scan_record`（每轮输出/决策/证据）
- **最终结论**：写入 `project_task.result`（或沿用现有拆分逻辑直接写 finding）

---

### 验收标准（DoD）
- 每条 task 都能看到完整的“多轮挖掘轨迹”（Watcher 记录）
- 误报明显下降：所有 finding 都有可定位证据与反证检查点
- 全面性提升：Ideator 能持续提供新角度，Watcher 能控制深度与收敛


