# 多漏洞 Reasoning Prompt/Planning/Validation 改造方案（v1）

> 目标：让 **Reasoning 阶段使用 `gpt-5.2` 作为主模型**，用“中性、基于 checklist 的正经审计式提示词”输出 **固定 JSON**，并支持 **一次扫描产出多个确定漏洞**；当出现多个漏洞时，将结果 **拆分为多条 finding（单漏洞条目）写入新表 `project_finding`**，从而减少重复扫描次数；同时保证 **validation / 去重 / 输出全部只针对 finding 表**，task 表保持兼容并支持断点续跑。

---

### 1. 背景与现状（基于当前代码）

#### 1.1 Reasoning 当前实现

- **Reasoning 扫描入口**：`src/reasoning/scanner.py` 的 `VulnerabilityScanner._execute_vulnerability_scan()`
- **Prompt 组装点**：`src/reasoning/scanner.py` 的 `VulnerabilityScanner._assemble_prompt_with_specific_rule()`
- **当前“诱导式/欺骗式”上下文来源**：`src/prompt_factory/core_prompt.py` 的 `CorePrompt.core_prompt_assembled()`，其关键内容是：
  - “We have already confirmed … contains only one exploitable … vulnerability …”
- **LLM 调用**：`src/openai_api/openai.py` 的 `detect_vulnerabilities(prompt)`  
  - 当前模型由 `model_config.json` 的 `vulnerability_detection` 决定（默认兜底是 `gpt-4o-mini`）
- **Reasoning 结果落库**：`task_manager.update_result(task.id, result)`（写入 `Project_Task.result`）

#### 1.2 Validation 当前实现（与本方案的交互点）

- **Validation 入口**：`src/validating/checker.py` → `ConfirmationProcessor.execute_vulnerability_confirmation()`
- **任务过滤规则（现状）**：只过滤 `short_result == 'delete'`（逻辑删除）
  - 见 `src/validating/processors/confirmation_processor.py`
- **是否已处理判断**：`short_result` 非空即视为已处理（会跳过）
  - 见 `src/validating/utils/check_utils.py`

#### 1.3 Reasoning 后去重与导出（关键交互点）

- Reasoning 后去重在 `src/main.py` 中调用：`ResProcessor.perform_post_reasoning_deduplication()`
- 去重数据来源：`entity.result`（现状只要 `result` 非空且有 `business_flow_code` 就收集）
  - 见 `src/res_processor/res_processor.py` 的 `perform_post_reasoning_deduplication()`
- Excel 导出：`ResProcessor.generate_excel()`  
  - 仅导出 `short_result` 包含 `"yes"` 的记录，并跳过 `short_result == 'delete'`

---

### 2. 目标与非目标

#### 2.1 目标（结合你最新口径：新增 finding 表，不再复制 task）

- **主模型统一**：Reasoning 漏洞扫描主模型固定为 **`gpt-5.2`**
- **新 Prompt（中性审计式）**：不再用“已确认存在漏洞”的诱导方式，而是基于 checklist 做审计式分析
- **多漏洞输出**：同一个扫描任务允许返回多个“最确定、非 intended design、非误报、会造成危害”的纯漏洞
- **固定 JSON 输出**：Reasoning 输出必须为固定 schema 的 JSON，便于稳定解析与拆分
- **多漏洞拆分入库（新表）**：当 JSON 中包含多个漏洞时：
  - `project_task.result` 保存 **多漏洞聚合 JSON**（用于留档/回溯/兼容旧流程）
  - 将每个漏洞拆成 1 条 **finding（单漏洞条目）**写入新表 `project_finding`
  - **去重/validation/导出只处理 finding 表，不再对 task 表做这些动作**

#### 2.2 非目标（本阶段不做或不强制）

- 不在本次方案里强制改变 planning 的“1 checklist → 1 任务”的生成方式（可以后续做优化）
- 不在本次方案里重做 `ResProcessor` 的 AI 去重策略（只保证它的数据源从 finding 表读取，并且每条 finding 的 JSON 语义适中：每个漏洞 100-200 词量级信息）

---

### 3. 固定 JSON 协议（Reasoning 输出协议）

#### 3.1 Schema（建议 v1，兼顾去重质量）

> 约束：**永远返回同样字段结构**。无漏洞时 `has_vulnerabilities=false` 且 `vulnerabilities=[]`。

> 为了避免 reasoning 后去重质量下降：要求每个漏洞条目在 JSON 内提供**适中语义密度**（建议每个漏洞 100-200 个英文单词量级，或等价信息量），不要过短（像标签），也不要过长（像整篇报告）。

```json
{
  "schema_version": "1.0",
  "engine_stage": "reasoning",
  "task": {
    "project_id": "string",
    "task_uuid": "string",
    "rule_key": "string",
    "function_name": "string",
    "relative_file_path": "string",
    "start_line": "string",
    "end_line": "string"
  },
  "has_vulnerabilities": true,
  "vulnerabilities": [
    {
      "title": "string",
      "severity": "critical|high|medium|low",
      "confidence": "high|medium|low",
      "summary": "string",
      "checklist_key": "string",
      "checklist_item": "string",
      "impact": "string",
      "attack_scenario": "string",
      "evidence": [
        {
          "file": "string",
          "start_line": 1,
          "end_line": 2,
          "code_excerpt": "string"
        }
      ],
      "recommendation": "string"
    }
  ],
  "notes": "string"
}
```

#### 3.2 多漏洞拆分规则（JSON 层 & 存储层约定：task 存聚合，finding 存单条）

- **task（原任务）**：
  - `project_task.result`：保存**多漏洞完整 JSON**（`vulnerabilities` 可能 > 1）
  - `project_task.short_result`：保存“是否已拆分写入 finding”的状态标记（见 5.2）
- **finding（新表单漏洞条目）**：
  - 每条 finding 保存 **单漏洞 JSON**（同 schema，但 `vulnerabilities` 必须长度为 1）
  - finding 承载：去重状态、validation 状态、导出所需信息

---

### 4. 新 Prompt 设计（Reasoning 用）

#### 4.1 Prompt 目标

- **审计式**：基于 checklist 逐项检查
- **中性**：不预设“肯定有漏洞”，允许输出 0 漏洞
- **高精度**：只输出“最确定、会造成危害”的纯漏洞
- **结构化**：必须输出符合 schema 的 JSON

#### 4.2 Prompt 组成（建议）

- **Role/Context**：智能合约/区块链安全审计专家
- **Inputs**：
  - 代码（优先 `business_flow_code`）
  - checklist（来自任务 rule/rule_list）
  - 可选：设计文档上下文（现有机制 `design_doc_content`）
  - 可选：同组 summary（现有机制 `SUMMARY_IN_REASONING`）
- **Hard rules**：
  - 不输出 intended design
  - 不输出“需要更多信息但猜测有漏洞”的内容
  - 证据必须来自给定代码（至少给出代码片段/行号范围）
  - 输出严格 JSON（不包含额外解释文字）

> 落地方式：新增一个 prompt 工厂文件（例如 `src/prompt_factory/vul_reasoning_json_prompt.py`），由 `scanner.py` 调用。并且在 `scanner.py` 中不再拼接 `CorePrompt.core_prompt_assembled()`。

---

### 5. 多漏洞拆分与任务落库（DB 方案：新增 `project_finding`）

#### 5.1 DB 结构现状与可用字段（保持兼容）

`Project_Task`（`src/dao/entity.py`）关键字段：

- `id`：自增主键
- `uuid`：唯一（在 `Project_Task.__init__` 内自动生成 `uuid4()`）
- `result`：reasoning 原始输出（目前是字符串）
- `scan_record`：可存放额外过程信息（JSON 字符串）
- `short_result`：目前用于 validation yes/no 与逻辑删除（`delete`）

#### 5.2 新增约定：task 的“已拆分”标记（断点续跑）

为满足“同一个 task 在中断后可跳过重复拆分写入 finding”，task 表使用 `short_result` 记录拆分状态（注意：这会与旧流程的 yes/no 含义共存，但新流程不再用 task.short_result 做 validation/export 判断）。

- 建议取值：
  - `short_result = ""`：未拆分/未写入 finding
  - `short_result = "split_done"`：已将多漏洞 JSON 拆分写入 `project_finding`
  - `short_result = "split_failed"`：拆分失败（可重试）

约束（新流程）：

- **Validation / 去重 / 输出**：只看 `project_finding`，不再依赖 task.short_result 的 yes/no 语义
- **Reasoning**：若 `task.short_result == "split_done"`，则跳过“拆分写入 finding”的步骤（但是否跳过 LLM 扫描可由 `result` 是否为空决定）

#### 5.3 Reasoning → 拆分写入 finding 流程（按你最新口径）

当 reasoning 得到 `result_json`：

1. **将多漏洞聚合 JSON 保存到 task 表**：
   - `project_task.result = 多漏洞 JSON（字符串）`
2. **若 `task.short_result != "split_done"`，执行拆分写入 finding**：
   - 解析 `result_json.vulnerabilities`
   - 对每个漏洞生成 1 条 `project_finding` 记录（单漏洞 JSON，`vulnerabilities=[one]`）
   - 写入完成后：`project_task.short_result = "split_done"`
3. **断点续跑**：
   - 若程序中断，重跑时看到 `split_done` 则跳过重复写 finding（避免重复插入）

> 说明：此方案不再需要“复制 task 生成子任务”，因此也不再需要“子任务 result 置空来避免重扫”的绕路。

#### 5.4 新增表：`project_finding`（只保存单漏洞条目，但尽量自包含）

表名：`project_finding`（你指定）

建议字段（自包含版本：尽可能复制 task 的代码相关字段，减少 join）：

- `id`：自增主键
- `uuid`：唯一 UUID
- `project_id`：项目 ID（冗余便于查询）
- `task_id`：关联 `project_task.id`
- `task_uuid`：冗余，便于追踪
- `rule_key`：冗余，便于筛选
- `finding_json`：单漏洞 JSON（同 schema，`vulnerabilities` 长度为 1）

从 `project_task` 复制过来的“代码/上下文相关字段”（你要求尽可能有用都复制过去）：

- `task_name`：对应 `project_task.name`
- `task_content`：对应 `project_task.content`（root function 内容）
- `task_business_flow_code`：对应 `project_task.business_flow_code`（业务流程代码）
- `task_contract_code`：对应 `project_task.contract_code`
- `task_start_line`：对应 `project_task.start_line`
- `task_end_line`：对应 `project_task.end_line`
- `task_relative_file_path`：对应 `project_task.relative_file_path`
- `task_absolute_file_path`：对应 `project_task.absolute_file_path`
- `task_rule`：对应 `project_task.rule`（完整 checklist 原文/JSON，便于验证阶段引用）
- `task_group`：对应 `project_task.group`（可选但推荐，便于追溯与调试）

- `dedup_status`：`kept | delete`（或 bool）
- `validation_status`：`pending | yes | no | not_sure`
- `validation_record`：可选（存 validation 过程日志/结构化结果）

幂等写入（不使用 fingerprint 的前提下，避免“中断重跑导致同一 task 重复插入 findings”）：

- 方案 A（推荐）：写入前按 `task_id` 删除旧 findings，然后再插入本次解析出的全量 findings
- 方案 B：为 finding 增加 `task_id + local_index`（本次解析的序号）并加唯一约束，重跑时 upsert/忽略重复

---

### 6. 与 Validation / 去重 / 导出的交互改动点（需要改代码的位置清单）

> 本节只列出将来要改的点，当前阶段不动代码。

#### 6.1 Validation：从 task 表迁移到 finding 表

目标行为（新口径）：

- validation 只针对 `project_finding` 表进行
- 选择条件：
  - `dedup_status != 'delete'`
  - `validation_status == 'pending'`
- 不再对 `project_task` 做 validation

#### 6.2 Reasoning 后去重：从 task 表迁移到 finding 表

目标行为（新口径）：

- 去重只针对 `project_finding` 表进行（输入：finding_json）
- 去重结果写回 `project_finding.dedup_status`
- 不再对 `project_task` 做 delete 标记

#### 6.3 Excel/输出：从 task 表迁移到 finding 表

目标行为（新口径）：

- 导出只读取 `project_finding`：
  - `dedup_status != 'delete'`
  - `validation_status == 'yes'`
- 因为 finding 已复制了绝大多数 task 的代码字段，导出可不依赖 join（仅在需要核对时 join）

#### 6.4 Reasoning 同组总结（SUMMARY_IN_REASONING=True）：仍按 task.group 做“运行时临时总结”

你提到的 `group` 目的解释如下（也回答你“不理解 group 干嘛用”）：

- `project_task.group` 是 planning 在创建任务时打的“任务组 UUID”（见 `planning_processor.py`）
- reasoning 的标准模式会 **group 内串行**、group 间并行（保证同组顺序性）
- reasoning 侧的“同组总结”会用 `group` 去查“同组已完成任务的结果”，把它作为上下文前缀，减少重复发现

你最新口径里“同组总结是临时数据，执行时才出现”——这与当前实现吻合：总结文本不需要落库，只要在执行时从同组历史 `task.result` 里生成即可。  
因此：finding 表 **不需要存 group**；同组总结仍然只依赖 task 表的 `group + result`。

结合你的最新口径补充（这就是你说的“group 的真实目的”）：

- `BUSINESS_FLOW_COUNT` 控制同一个“扫描单元”（同 rule_key + 同 code 段）要创建几条 task（通常 2~3 条）
- 这些 task 使用同一个 `group`，每条 task 在 `result` 里保存一份“本轮多漏洞 JSON 聚合结果”（历史留档）
- 执行后续轮次时，summary 从同 group 的历史 `project_task.result` 汇总“已发现漏洞”，prompt 明确要求只输出新增不重复漏洞

---

### 7. Reasoning 主模型固定为 `gpt-5.2` 的落地方式

#### 7.1 推荐方式（更硬、更可控）

- 在 `src/openai_api/openai.py` 增加一个新的调用函数（示例）：
  - `detect_vulnerabilities_json(prompt, model="gpt-5.2")`
  - 使用 `response_format: { "type": "json_object" }` 强制返回 JSON（类似 `ask_openai_for_json` 的做法）
- 在 `scanner.py` 里调用这个新函数，避免“普通 chat”输出不稳定 JSON。

#### 7.2 备选方式（仅改配置）

- 在 `model_config.json` 中将 `vulnerability_detection` 映射到 `gpt-5.2`
- 但仍建议配合 `response_format`，否则 JSON 可靠性不足

---

### 8. 与 Planning 的关系（你第 3 点的效果如何体现）

#### 8.1 不改变 planning 结构

- 维持现有 planning：一条任务绑定一个 `rule_key + rule_list + code(business_flow_code)`
- 由 reasoning “一次输出多漏洞 + DB 拆分复制”来实现“扫描后扩充为多条漏洞条目”

#### 8.2 未来可选优化

- 如果拆分后效果良好，可降低 `BUSINESS_FLOW_COUNT` 或减少重复迭代次数，降低成本

---

### 9. 风险与兼容策略

#### 9.1 JSON 不可解析的情况

- 若 reasoning 输出不是合法 JSON：
  - 不进行拆分复制
  - 原样写入 `task.result`（保留排查材料）
  - 可选：走一次 `extract_structured_json()` 做二次结构化提取（但这会增加一次模型调用成本）

#### 9.2 Validation Prompt 接收 JSON 的兼容（新结构）

validation 侧输入应从 `project_finding.finding_json` 获取，并把其作为 `vulnerability_result`（或提取其中的 summary/title/evidence 组合成更适配的验证 prompt）。  
task.result 仍保留（多漏洞聚合 JSON）用于留档与同组总结，但不再直接作为 validation 输入。

---

### 10. 需要你确认的关键问题（不确认会影响最终落地细节）

1. **`gpt-5.2` 的具体模型名/路由**：你希望在 `model_config.json` 里写成 `"gpt-5.2"`，还是你们网关实际需要 `"gpt-5.2-xxx"`（例如带日期后缀）？
2. **多漏洞输出上限**：每个 task 最多允许输出多少个漏洞？（建议设一个上限，例如 5 或 8，避免长尾导致 token 爆炸）
3. **子任务的 `group` 是否沿用原任务的 `group`**：
   - 沿用：便于同组汇总/上下文，但可能让 group 变得更大
   - 新 group：更清晰，但可能影响现有 `SUMMARY_IN_REASONING` 的“同组总结”逻辑
4. **task.short_result 的状态值命名**：你希望用 `split_done/split_failed` 还是更偏好的字符串？
5. **finding 幂等写入策略**：你更偏好“写入前按 task_id 删除旧 findings 再重建”（方案 A）还是“task_id+local_index 唯一约束”（方案 B）？


