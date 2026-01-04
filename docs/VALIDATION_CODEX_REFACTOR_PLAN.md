# Validation（漏洞误报确认）基于 Codex 的重构方案（仅方案，不改代码）

## 目标与范围

### 目标
- 在 **reasoning 产出漏洞（写入 `project_finding`）之后**，进行“漏洞是否真实存在 / 是否为误报”的确认（validation）。
- **大幅简化**现有 validation 流程：不再走复杂的上下文构造与多阶段处理器链路，而是 **直接把单条漏洞信息喂给 Codex**，让其在**受控工作目录**下做只读检索与判断。
- 将 Codex 的判断结果：
  - 保存到内存变量（`codex_result` / `final_text`）
  - 再写回数据库：`project_finding.validation_status` 与 `project_finding.validation_record`

### 本方案只覆盖（第一阶段）
- 仅重构 **validation**（确认/误报判断）这一段。
- 不涉及 planning/reasoning/dedup 的重构（后续再做）。

### 约束
- **工作目录必须限定**在“主扫描项目目录”，不能让 Codex 访问其它目录。
  - 主扫描项目目录由：
    - `src/main.py` 里的 `dataset_base = "./src/dataset/agent-v1-c4"`
    - `src/dataset/agent-v1-c4/datasets.json` 中指定的 `project.path`
    - `src/dataset_manager.py::Project.path = join(base_path, path)`
  - 因此最终受控目录形如：`<repo>/src/dataset/agent-v1-c4/<datasets.json:path>`
- Codex 采用 `read-only` sandbox；文件写入由 Python 落库，不让 Codex 写 workspace。

---

## 现状梳理（对齐当前代码）

### 数据表与落库字段
`project_finding`（见 `src/dao/entity.py`）关键字段：
- `finding_json`: 单漏洞 JSON（字符串）
- `validation_status`: 当前设计注释为 `pending / yes / no / not_sure`
- `validation_record`: 记录 validation 过程（字符串）

写回接口（见 `src/dao/finding_mgr.py`）：
- `ProjectFindingMgr.update_validation(finding_id, validation_status, validation_record)`
  - 更新列：`validation_status`、`validation_record`

### 现有 validation 调用入口
`src/main.py::check_function_vul(...)` 当前走：
- `from validating.finding_checker import FindingVulnerabilityChecker`
- `checker.check_findings()`

`FindingVulnerabilityChecker` 目前会把 finding 适配成 task-like，再走 `AnalysisProcessor.process_task_analysis(...)`，最后写回：
- `validation_status`（短结论）
- `validation_record`（过程记录）

> 你当前需求是：有了漏洞信息后，不需要复杂流程，直接把漏洞信息给 Codex 输入确认是否存在——因此后续要 **绕开/替换** `AnalysisProcessor` 这一套。

---

## 新的 Validation 总体流程（Codex 直连）

### 新流程概览
对每条待验证 finding（`validation_status in ["", "pending"]` 且未被 dedup delete）：
1. 计算 **受控工作目录**（仅该项目根目录）
2. 构造 **Codex Prompt**（输入：`finding_json` + 必要上下文）
3. 调用 `codex_example/src/codex_client.py::ask_codex(...)`
   - `sandbox="read-only"`
   - `--cd` 指向受控工作目录
4. 将 Codex 返回的 `final_text` 保存到变量 `codex_result_text`
5. 解析 `codex_result_text` 得到预定义枚举 `validation_status`
6. 写回数据库：
   - `project_finding.validation_status = <枚举值>`
   - `project_finding.validation_record = <结构化 JSON 或原文 + 元信息>`

### 为什么这样能满足“目录限定”
Codex CLI 调用会使用 `--cd <project_path>`（见 `codex_example/src/codex_client.py`）：
- Codex 的可访问范围默认就以 `--cd` 作为 workspace root
- 不传 `--add-dir`，即可避免扩权

---

## “主扫描项目目录”的确定（必须严格一致）

### 数据来源（必须与主扫描一致）
- `src/main.py`：`dataset_base = "./src/dataset/agent-v1-c4"`
- `datasets.json`：每个 `project_id` 有字段 `path`
- `src/dataset_manager.py::Project`：`Project.path = join(base_path, path)`

### 最终目录计算（建议绝对路径）
- `dataset_base_abs = abspath(<repo>/src/dataset/agent-v1-c4)`
- `project_rel = datasets[project_id]["path"]`
- **受控工作目录**：`project_root = abspath(join(dataset_base_abs, project_rel))`

### 校验与失败策略
在调用 Codex 前必须校验：
- `project_root` 必须存在且为目录
- 不允许 `..` 等路径穿越（建议在 join 后再做 `commonpath` 校验，确保仍在 `dataset_base_abs` 下）
失败时：
- `validation_status = "error"`（或 `not_sure`，但推荐显式 error）
- `validation_record` 写入错误原因

---

## 预定义 Validation 结果枚举（核心需求）

你希望可能出现的确认结果包括：
- intended design
- 漏洞
- 误报
- 漏洞但利用成本高
- 漏洞但影响低

### 建议的枚举值（写入 `project_finding.validation_status`）
为避免后续统计/导出混乱，建议使用 **固定英文枚举**（稳定、可检索）：
- `pending`：待处理（保留）
- `intended_design`：符合设计/预期行为（非漏洞）
- `false_positive`：误报（非漏洞）
- `vulnerability`：确认存在漏洞（可利用且影响显著）
- `vuln_high_cost`：存在漏洞，但利用成本高/前置条件苛刻（保守标记）
- `vuln_low_impact`：存在漏洞，但影响较低/边界场景（保守标记）
- `not_sure`：无法确认（信息不足/代码复杂/证据不充分）
- `error`：系统或调用失败（codex 不可用/超时/目录不存在等）

> 注意：现有注释是 `pending/yes/no/not_sure`，后续代码需要同步适配（本阶段仅方案，不改代码）。  
> 特别是导出逻辑目前硬编码 `validation_status == 'yes'`（见 `ProjectFindingMgr.get_findings_for_export`），未来需要调整为“哪些状态算可导出漏洞”。

### “可导出漏洞”的建议规则（后续改代码时实现）
推荐把以下视为“确认漏洞”：
- `vulnerability`
- `vuln_high_cost`
- `vuln_low_impact`

把以下视为“非漏洞”：
- `intended_design`
- `false_positive`

保留：
- `not_sure`、`error`（不导出或单独导出到“待人工复核/系统错误”）

---

## Codex 输出格式（强烈建议结构化）

为保证后续能稳定解析并写回枚举，建议要求 Codex **严格输出 JSON**（不是事件流，而是正文 JSON）：

### 利用 Codex CLI 的 agentic workflow（多步代理式检索）做“可追溯验证”
Codex CLI 的核心能力之一是 **agentic workflow**：你给目标，它会自动规划步骤，并在需要时主动执行只读的终端命令完成检索/交叉引用（常见是 `rg/grep/sed -n/cat/ls` 等）。

这对 validation 非常关键：我们不希望它“凭经验判断”，而是希望它 **先在受控目录内检索证据 → 再基于证据给结论**。因此建议在 validation prompt 中明确要求：
- **必须执行检索**：至少运行 2~5 次只读检索命令（例如先定位关键函数/变量，再沿调用链或关键条件追踪）。
- **必须报告证据来源**：在 `evidence` 里给出文件路径、关键片段或定位方式。

> 在 `sandbox=read-only` 下，这些命令依然可以执行（不会写文件）；同时你通常能在 Codex 输出中看到它执行过的命令记录（经常表现为类似 `exec ... bash -lc "rg ..."` 的日志片段），这非常适合做审计追溯。

### 审批模式（避免 agentic workflow 卡住）
如果 Codex CLI 的审批模式不是 `never`，它可能会在执行某些命令前暂停等待确认，导致 validation 批处理卡住。  
因此在 validation 阶段建议强制：
- `ask_for_approval="never"`（对应 CLI：`codex --ask-for-approval never exec ...`）

> `codex_example/src/codex_client.py::ask_codex(...)` 已支持该参数，本项目后续实现 validation 时应固定开启。

### 建议输出 JSON Schema（最小集合）
- `status`: 上述枚举之一
- `confidence`: `high|medium|low`
- `reason`: 1-3 句话概述判断逻辑
- `evidence`: 数组，包含：
  - `file`: 相对路径（相对于受控项目根）
  - `lines`: 可选（行号范围或关键片段定位方式）
  - `snippet`: 可选（简短代码片段，避免超长）
  - `why`: 该证据支持什么结论
- `repro_or_attack_path`: 可选（若是漏洞，给出可利用路径/前置条件）
- `mitigation`: 可选（修复建议）

### 解析策略
后续实现时建议：
- 优先 `json.loads(final_text)` 解析
- 解析失败则降级：
  - `status = "not_sure"`
  - `validation_record` 保存原文 + “解析失败”原因

---

## Prompt 设计（输入：finding_json，输出：JSON）

### 输入应包含哪些信息

建议把“单漏洞 JSON + 与之绑定的 task 上下文”一起提供给 Codex，保证其能定位到具体代码位置并复核：
- `finding_json`（必填）：来自 `Project_Finding.finding_json`
- `rule_key`（建议）：来自 `Project_Finding.rule_key`
- `task_relative_file_path` / `task_absolute_file_path`（若存在，建议）：帮助快速定位
- `task_name`（建议）：函数名/合约名/入口提示
- `task_content` 或 `task_business_flow_code`（可选，体积较大时可不传）：给 Codex 初始上下文；但注意 token 成本

> 实施时可以采用“轻量输入优先”：先只给 `finding_json + (file/func hint)`，让 Codex 自己在受控目录里 `rg/grep` 查证据；必要时再追加上下文（第二轮）。

### Prompt 关键约束（必须写进 prompt）
- **目录约束**：明确告诉 Codex “只能基于当前工作目录下的文件判断”，不得引用外部项目、不得假设缺失代码存在。
- **输出约束**：必须输出 **单个 JSON**，不允许 Markdown 包裹、不允许额外解释文本（否则解析不稳）。
- **枚举约束**：`status` 必须为预定义枚举之一。
- **agentic workflow 约束**：必须先做“多步只读检索/交叉引用”再下结论；`evidence` 必须来自这些检索的结果。

### Prompt 模板（建议）
（后续实现时由 Python 拼接，变量用占位符表示）

```text
你是安全审计验证器。你只能读取当前工作目录(workspace root)下的文件进行验证，不能假设目录外存在任何代码或配置。

现在给你一条“候选漏洞（单条 finding）”，请你验证它是否真实存在、是否可能只是误报或设计使然。

【输出要求（非常重要）】
1) 你必须只输出一个 JSON（不要输出 Markdown、不要输出额外文本）。
2) JSON 必须包含字段：status, confidence, reason, evidence。
3) status 只能取以下之一：
   pending | intended_design | false_positive | vulnerability | vuln_high_cost | vuln_low_impact | not_sure
4) evidence 至少给出 1 条（如果 not_sure，也要说明你检查过哪些文件/关键字）。
5) 你必须先执行多步只读检索（agentic workflow）再给结论：请至少进行 2~5 次检索/交叉引用（例如 rg/grep 定位关键点，再打开相关文件片段核对调用路径和条件）。

【输入：候选漏洞 finding_json】
{FINDING_JSON}

【辅助信息（可能为空）】
rule_key: {RULE_KEY}
hint_file: {RELATIVE_FILE_PATH}
hint_function: {TASK_NAME}

请在当前目录内检索并核对证据（可使用只读命令如 rg/grep/cat/sed -n），最后给出 JSON 结论。
```

### Validation Prompt（推荐版本：更严格、覆盖“误报/设计使然/影响/难度/文档参考”）
下面是一份更适合本项目“Codex 直连 validation”的 prompt 模板（建议直接使用这一份替换上一份基础模板）。它融合了仓库现有 prompt 的关键约束风格（JSON-only、先分析后结论、证据要求、信息不足要保守），并且把你提供的中文指令原句纳入要求。

```text
你是一个专业的智能合约/区块链安全审计验证专家（Validation）。你的任务是对“候选漏洞 finding”进行复核确认。

【工作区约束（必须遵守）】
- 你只能读取当前工作目录(workspace root)下的文件来判断，不得引用或假设目录外的任何代码/配置/部署细节。
- 允许使用只读命令进行检索与交叉引用（例如 rg/grep/ls/find/cat/sed -n），不得尝试写文件。

【必须使用 agentic workflow（多步检索）】
- 在给出最终结论前，你必须执行多步只读检索/交叉引用（至少 3 次，最多 10 次）：
  1) 根据 finding 的关键词/函数名/文件提示定位相关代码位置
  2) 沿调用链或关键条件分支追踪（查调用者/被调函数/关键状态变量）
  3) 验证漏洞成立条件（权限、可控输入、外部调用点、状态更新顺序、边界条件）
  4) 如存在文档/规范/README/注释，必须优先检索并参考（见下方“文档要求”）

【文档要求（必须做）】
如果项目内存在任何文档/规范/注释可以解释“这是设计如此还是漏洞”，你必须优先参考它们再下结论。检索建议：
- README/README_CN、docs/、spec/、design/、whitepaper、audit 相关 md
- 合约头部注释、NatSpec（@notice/@dev）、关键常量/参数说明

【你要完成的验证问题（必须覆盖，含原句）】
“检查一下这个漏洞是否存在，是否是误报，是否是intend design，影响程度如何，利用难度如何，如果有文档的话要参考文档”

【输出要求（非常重要：只输出 JSON）】
你必须只输出一个 JSON（不要 Markdown、不要额外解释文本），并严格匹配以下 schema：
{
  "schema_version": "validation_codex_v1",
  "status": "pending|intended_design|false_positive|vulnerability|vuln_high_cost|vuln_low_impact|not_sure",
  "confidence": "high|medium|low",
  "exists": true/false,
  "classification": "vulnerability|non_vulnerability|uncertain",
  "impact": "high|medium|low|unknown",
  "exploit_difficulty": "easy|medium|hard|unknown",
  "reason": "用 2-5 句话说明你为何得出该结论（必须引用证据要点）",
  "evidence": [
    {
      "file": "相对路径（相对 workspace root）",
      "locator": "函数名/变量名/关键片段定位方式（可写行号范围或 grep 命中关键词）",
      "snippet": "<= 30 行的关键片段（可选，但强烈建议）",
      "why": "这段证据如何支持你的判断"
    }
  ],
  "doc_references": [
    {
      "file": "相对路径",
      "locator": "章节标题/关键词",
      "excerpt": "相关原文摘录（可选）",
      "why": "它如何表明 intended design 或影响评估"
    }
  ],
  "attack_preconditions": ["若为漏洞，列出成立前置条件；不确定可为空数组"],
  "attack_path": "若为漏洞，简述可利用路径/触发方式；非漏洞可为空字符串",
  "mitigation": "若为漏洞，给出 1-3 条修复建议；非漏洞可为空字符串",
  "unknowns": ["如果 not_sure，请列出缺失信息/无法确认的点，并说明需要看什么才能确认"]
}

【判定口径（避免误报）】
- intended_design：行为有文档/注释/显式逻辑支持“这是预期行为”，且不存在可被滥用造成真实损害的路径。
- false_positive：finding 描述/推断与代码事实不符（例如关键条件不存在、权限不可获得、入口不可达、变量不可控、逻辑相反等）。
- vulnerability：存在现实可利用路径，并可能造成明确损害（资金损失/权限提升/资产锁死/DoS 等）。
- vuln_high_cost：漏洞成立但利用门槛很高（需高权限、苛刻链上条件、复杂多交易/时间窗口、经济成本过高等）。
- vuln_low_impact：漏洞成立但影响面小（仅边缘用户、可控损失极小、需要用户自损或极端条件）。
- not_sure：在受控目录内已尽力检索仍不足以确认（必须在 unknowns 中写清楚缺什么）。

【输入：候选漏洞 finding_json】
{FINDING_JSON}

【辅助信息（可能为空）】
rule_key: {RULE_KEY}
hint_file: {RELATIVE_FILE_PATH}
hint_function: {TASK_NAME}
```


---

## `validation_record` 的存储建议（写回数据库）

### 为什么要结构化
`validation_status` 只放枚举值，信息不足；为了可追溯、可复现、可二次分析，建议把更完整的信息放入 `validation_record`。

### 推荐写入格式（JSON 字符串）
建议 `validation_record` 写成 JSON 字符串（而不是纯文本），至少包含：
- `schema_version`: 例如 `"validation_codex_v1"`
- `codex_model`: 例如 `"gpt-5.2"`
- `sandbox`: `"read-only"`
- `workspace_root`: 受控目录绝对路径（或相对路径）
- `prompt_hash`: prompt 的 hash（便于审计与去重）
- `started_at` / `finished_at` / `duration_ms`
- `raw_final_text`: Codex 的原始输出（即 `codex_result_text`）
- `parsed`: 解析后的对象（成功时）
- `parse_error`: 解析失败原因（失败时）

> 这能保证：即使未来枚举体系扩展/导出规则变化，也能回溯当时证据与判断。

---

## 并发、限流与可靠性（后续实现建议）

### 并发策略
现有 finding validation 采用线程池（`MAX_THREADS_OF_CONFIRMATION`）。Codex 直连后建议：
- 默认小并发（例如 2~5），防止本机 `codex` 进程过多 + API 速率限制
- 可复用现有环境变量 `MAX_THREADS_OF_CONFIRMATION`

### 子进程生命周期管理（重要：拿到结果要实时关闭老进程）
Codex CLI 调用本质是启动一个本机子进程。为避免小并发场景下仍然出现“进程堆积/残留”，实现时必须做到：
- **每条 finding 独立启动一次 `codex exec`**，拿到结果（成功/失败/超时）后立刻回收，不要复用长驻进程。
- **优先使用非 streaming 模式**（`stream_output=False`）：
  - `subprocess.run(..., timeout=...)` 在返回时子进程已退出，更容易保证“实时关闭”。
  - 如需保留 agentic workflow 的命令记录，可直接把 `stdout`/`stderr` 作为 `validation_record.raw_*` 落库（不依赖 streaming）。
- 若必须使用 streaming（`subprocess.Popen`）：
  - 在 `finally` 中确保：
    - `proc.poll()` 仍未退出则 `proc.terminate()`，短暂等待后 `proc.kill()`
    - 关闭 `proc.stdout/proc.stderr`（避免 pipe 资源泄露）
    - join 读取线程（stdout/stderr worker）防止线程泄露
  - 超时路径必须执行 kill，避免线程池挂起或出现僵尸进程。

> 目标是：线程池里的每个 worker 结束时，系统里不应该残留对应的 `codex` 进程；`validation_record` 中要能看到该条任务是 “ok/timeout/error” 哪种退出方式。

### 超时与重试
`ask_codex(...)` 本身支持 `timeout_sec`，建议：
- 单条 finding 超时：例如 10~20 分钟（视项目大小）
- 超时后写 `status="error"` 或 `not_sure`，并记录 timeout
- 需要重试时，最多 1 次（避免无限循环消耗）

### 避免交互卡住
`codex_example/src/codex_client.py` 已支持 `ask_for_approval`（对应 CLI `--ask-for-approval`）。验证阶段建议强制：
- `ask_for_approval="never"`

---

## 与现有导出/下游兼容的改动点（第二阶段要做）

### 1) 导出规则
目前 `ProjectFindingMgr.get_findings_for_export` 只导出 `validation_status == 'yes'`。  
引入新枚举后，需要改成导出：
- `validation_status in ('vulnerability','vuln_high_cost','vuln_low_impact')`

### 2) UI/报表/Excel
若 Excel/前端/报告中显示 “yes/no”，需要同步展示新的枚举（或映射为中文标签）。

### 3) 数据迁移（可选）
历史数据里已存在 `yes/no/not_sure` 时，建议映射：
- `yes` -> `vulnerability`（或 `vulnerability` + `confidence=medium`）
- `no` -> `false_positive`（或 `intended_design` 需要再细分）
- `not_sure` 保留

---

## 实施步骤（建议按 commit 拆分）

### Phase A：最小可用（MVP）
- 新增一个 “CodexFindingValidator/Processor”（替换或旁路 `AnalysisProcessor`）
- 对每个 finding：
  - 计算受控目录
  - ask_codex
  - 解析 JSON -> 枚举
  - update_validation 写回

### Phase B：对齐下游
- 修改导出逻辑与报告展示
- 增加历史数据映射（可选）

---

## 验收标准（Definition of Done）
- Codex 验证时，工作目录被严格限定在目标项目根目录（`--cd project_root`），且不会读取其它目录文件。
- `project_finding.validation_status` 能稳定写入预定义枚举之一。
- `project_finding.validation_record` 能保存可追溯的 raw 输出与解析结果。
- 对解析失败/超时/目录缺失等异常路径，能写入 `status=error/not_sure` 且不会阻塞全流程。


