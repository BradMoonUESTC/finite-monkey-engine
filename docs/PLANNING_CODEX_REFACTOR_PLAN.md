# Planning 过程重构方案（Codex 业务流抽取版，仅方案，不改代码）

## 目标

- **删除 planning 阶段的 RAG/向量库/文档分块相关逻辑**（不再初始化 LanceDB，不做检索增强）。
- **删除调用关系解析相关逻辑**（不构建 call tree / call graph；不做 upstream/downstream）。
- **只保留 Tree-sitter 的解析结果**，并把它作为 Codex 业务流抽取的唯一结构化输入：
  - 函数身份标识以 **“文件/合约/类名.函数名(可带签名)”**为主（与 `businessflow_history_chat` 的命名规则对齐）。
- 使用 Codex CLI 的 **agentic workflow**（只读多步检索）在受控目录内提取：
  - **业务流组 Gi**
  - **业务流 Fi**
  - （可选）关系 Rk（相似/相反、分叉/汇聚）
- 将所有 Fi 作为后续扫描的 **`business_flow_code` 对象**集合（planning 的产物），供 reasoning 扫描使用。

> 本文只给出方案：不改代码、不落库、不实现。

---

## 工作目录/范围约束（硬约束）

planning 里 Codex 的 workspace root 必须严格限制在主扫描项目目录：

- `project_id` 来自 `src/main.py`
- `dataset_base = <repo>/src/dataset/agent-v1-c4`
- `datasets.json[project_id].path` 给出相对目录，例如 `dca5555 -> dca`
- **project_root = join(dataset_base, path)**，例如：`src/dataset/agent-v1-c4/dca`

Codex 执行时必须：
- `codex exec --cd <project_root>`（不 add-dir）
- `sandbox=read-only`
- `--ask-for-approval never`（避免批处理卡住）

---

## Tree-sitter 解析保留范围（planning 只用这些）

planning 阶段只保留并使用以下树解析结果：

- **函数清单**：形如 `合约/类名.函数名`（必要时带参数签名）
- **函数元信息（可选）**：
  - `visibility`（external/public/internal/private）
  - `file_path`（相对路径）
  - `line_number`（可选）

planning 阶段不再依赖：
- `chunks`（文档分块/RAG）
- `call_trees`
- `call_graphs`

> 规划输出的业务流仍然允许 Codex 在 workspace 内用 `rg/grep` 自行查证、补全跨合约函数；但系统自身不维护调用图结构。

---

## 业务流产物数据模型（planning 输出）

### 1) Business Flow Group（Gi）
- `group_id`: `"G1"`, `"G2"`, ...
- `group_name`: 业务域名称（如“交易与持仓”“治理与费用”“领取与铸造”）
- `functions`: `["合约.函数", "合约.函数", ...]`

### 2) Business Flow（Fi）→ 后续扫描的 `business_flow_code` 对象
对每个 Fi，planning 产出一个对象：

- `flow_id`: `"F1"`, `"F2"`, ...
- `flow_name`: 业务流名称
- `group_ids`: `["G1","G6"]`（允许多归属）
- `function_refs`: `["合约.函数", "合约.函数", ...]`（跨文件/跨合约可混排）
- `notes`（可选）：
  - `doc_refs`（若引用了 README/spec 注释）
  - `risk_gap_checklist`（自检中仍待补充项）

> 这里的 `business_flow_code` **不是“拼接的调用链代码”**，而是“可枚举的函数引用序列”。后续 reasoning 扫描若需要代码正文，可以在扫描阶段按 `function_refs` 回填函数 body（只取这些函数，不做调用扩展）。

---

## ProjectTask 存储策略调整（以业务流为中心）

### 变化点（从“按函数”到“按业务流”）
planning 阶段不再围绕 `functions_to_check` 的单函数迭代逐条落库，而是：
- 先用 Codex 产出一批 **Gi/Fi（业务流组/业务流）**
- 再把 **每个 Fi** 作为一条 `project_task`（后续扫描的基本单位）

### 字段使用约定（对齐你当前需求）
`project_task` 表中：
- **`business_flow_code`（关键字段）**：存放“待扫描主代码”的抽象表示（函数引用列表），用于后续扫描阶段再去补齐代码正文。
- **`content`（弱化）**：在业务流中心规划下，`content` 基本不再承载主输入；可以留空或只存简短备注/描述。
- 其它字段（建议）：
  - `name`：建议使用 `Fi:<flow_id> <flow_name>`，保证可追踪
  - `rule_key`：建议固定为 `"BUSINESS_FLOW_PLANNING"`（用于与传统漏洞扫描任务区分）
  - `rule`：可留空或存放规划策略版本

> 核心观点：后续 scanning 也将依赖 Codex，在“主业务流函数列表”不够时再补充；因此 planning 的“主资产”就是 `business_flow_code`。

---

## `business_flow_code` 输出必须 JSON 化（便于解析与稳定落库）

### 为什么必须 JSON
为了保证：
- 机器可解析（避免逗号分隔/换行的歧义）
- 可做字段校验（缺字段、空数组、重复等）
- 能与 tree-sitter 的解析结果做对齐校验（防止“合约名.函数名”写错导致后续取不到代码）

### 推荐 JSON Schema（planning 输出的 Fi 列表）
建议 P2（汇总输出）阶段让 Codex 输出 **单个 JSON**，例如：

- `schema_version`: `"business_flow_planning_v1"`
- `groups`: Gi 列表（可选：若只需要 Fi，也可以省略）
- `flows`: Fi 列表（必须）

Fi 对象最少字段：
- `flow_id`: `"F1"`
- `flow_name`: `"Cred单笔买卖流"`
- `group_ids`: `["G1","G6"]`
- `function_refs`: `["Cred.buyShareCred", "Cred._handleTrade", "BondingCurve.getPriceData"]`

> 这能直接映射到 `project_task.business_flow_code`（建议整段 JSON 原样落库，或取其中单个 Fi JSON 存入单条 task）。

---

## 与 Tree-sitter 解析结果对齐（必须做的校验/归一化）

### 对齐目标
planning 输出的每个 `function_ref`（合约/类名.函数名 或带签名）必须能在 tree-sitter 解析结果中被定位：
- 通过 `file_path + contract/class + function` 找到唯一函数定义
- 至少能定位到该函数所在文件，便于后续扫描阶段提取函数 body

### 建议的对齐策略（实现时遵循）
对每个 `function_ref`：
1. **归一化**：
   - 去除多余空格
   - 统一 constructor/receive/fallback 表达
   - 重载函数：若 tree-sitter 不提供参数签名，则先按 `合约.函数名` 进行匹配，再在同名函数多于 1 个时标记为 ambiguous
2. **tree-sitter 检索**：
   - 优先按 `contract/class + function_name` 精确匹配
   - 次级按 `file_path` 限定范围匹配（若 prompt 提供了 hint_file）
3. **对齐结果分三类**：
   - `matched`：唯一命中（可继续）
   - `ambiguous`：多命中（需要 Codex 在 P1/P2 修正或在扫描阶段补充签名）
   - `missing`：未命中（需要 Codex 修正引用或说明为 interface）

### 为什么这块“很重要”
因为 `business_flow_code` 后续要作为扫描主输入来源：
- 若 `function_refs` 与 tree-sitter 不对齐 → 扫描阶段无法提取函数 body → 任务失效
- 因此规划阶段必须确保输出“可解析、可定位、可落库”

## Codex 提示词策略：1 次主 prompt + 2 次副 prompt（增量修正）

本方案直接参考 `codex_example/businessflow_history_chat` 的三段交互结构：

### Prompt P0（主 prompt：首轮抽取）
目标：让 Codex 在受控 workspace 内，自行多步检索并输出：
- Gi（业务流组）
- Fi（业务流）
- Rk（相似/相反、分叉/汇聚）
- 完整性自检 checklist（标注需要二轮补充）

关键约束：
- **输出必须可迭代**：Gi/F i 使用稳定 ID（后续补充不能重排/复用已分配 ID）
- **函数命名规则**：合约/类名.函数名（重载带签名；constructor/receive/fallback 特殊格式）
- **agentic workflow**：要求其明确用 `rg/grep`、打开文件片段等方式完成交叉引用

> P0 原型可直接用 `businessflow_history_chat` 顶部那段（1-40 行）。

### Prompt P1（副 prompt #1：增量补全/修正）
目标：基于 P0 的 Gi/Fi/Rk 输出结果，**只输出新增或修正行**（用 `+`/`~` 标记），不重复完整覆盖内容。

策略：
- 先列“遗漏风险最高类别”（权限/治理、签名/merkle、时间窗、索引分页、资金流、事件、升级、跨链/环境假设）
- 允许你在 prompt 末尾追加少量“你怀疑遗漏的函数线索”（例如 `Foo.pause, Foo.unpause`）

> P1 原型可直接用 `businessflow_history_chat` 中的“增量补全”那段（约 130-173 行）。

### Prompt P2（副 prompt #2：汇总输出所有 Fi）
目标：在应用 P1 的增量修正后，让 Codex 输出“最终的 Fi 全量列表”，用于直接生成 planning 的 `business_flow_code` 对象集合。

输出格式建议：
- 仅输出 Fi 行（每行 `Fi 名称 (归属: Gx,...): 合约.函数, ...`）
- 不输出 Gi/Rk（避免噪声）
- 不输出解释文本（便于解析落库/生成任务）

> `businessflow_history_chat` 里有一句类似“现在输出刚才所有的业务流”，可作为 P2 的核心指令。

---

## Prompt 模板（可直接复制使用）

> 说明：以下 P0/P1 为你提供的版本，已整理为可直接复用的“备用 prompt”。  
> 建议在实际调用时，把 workspace root 严格限定为 `<project_root>`（`codex exec --cd <project_root>`），并保持 `sandbox=read-only`、`--ask-for-approval never`。

### P0 主 Prompt（首轮提取；输出为 合约名.函数名 列表）

你是“业务流/业务流组抽取助手”。请基于我提供的代码仓库内容，提取该项目的业务流与业务流组，并输出为“合约名.函数名”逗号分隔列表（例如：Cred.buyShareCred, BondingCurve.getPriceData）。不同业务流模块可以出现在同一个文件里；同一函数也可能属于多个业务流组。

【输出必须可迭代】
- 给每个业务流组稳定 ID：G1, G2...
- 给每个业务流稳定 ID：F1, F2...
- 后续补充必须引用这些 ID；不要重排已有 ID。

【函数命名规则】
- Solidity/面向对象：用 合约/类名.函数名
- 重载函数必须带参数类型签名：合约名.函数名(type1,type2,...)
- constructor/receive/fallback 统一写：合约名.constructor / 合约名.receive / 合约名.fallback
- 若只看到接口调用、无法定位实现：接口名.函数名 并在末尾加 (interface)

若信息不足/仓库太大，先问我最多 3 个澄清问题（例如：重点合约/模块、核心角色、范围目录），再开始。

【首轮输出内容】
1) 概括业务流组（按能力域分组）
- 对每个 Gi 输出一行：
  Gi 组名: 合约A.函数1, 合约A.函数2, 合约B.函数3 ...
- 该列表必须包含：对外入口（external/public）+ 关键共享内部管线函数（如 _handleTrade/_processClaim 这类）+ 关键跨合约依赖点（被调用的核心函数）。

2) 业务流（组内拆分成更细的 Fi）
- 对每个 Fi 输出一行：
  Fi 业务流名 (归属: Gx,...): 合约A.函数1, 合约B.函数2 ...
- 若一个业务流横跨多个合约/模块，必须把跨合约函数都列进同一行列表。

3) 一对一相似/相反关系组（只输出函数列表）
- 每个关系一行（左右两侧都是“合约.函数”列表）：
  Rk 类型(相似/相反): [合约.函数, 合约.函数] <-> [合约.函数, 合约.函数]

4) 一对多/多对一（分叉/汇聚）关系组（只输出函数列表）
- 分叉示例（入口/分支都用列表）：
  Rk 分叉: Entry[...函数列表...] -> BranchA[...], BranchB[...]
- 汇聚示例：
  Rk 汇聚: Inputs[...函数列表...] -> Core[...函数列表...]

5) 完整性自检（只列“可能遗漏类型”清单，不展开代码）
- 输出一个 checklist：创建/更新、启停、单/批量、入账/出账、校验(签名/merkle/权限)、时间窗、上限下限、索引/分页、事件、升级/初始化、跨链/环境假设。
- 对每个未覆盖项，标注“需要二轮补充”。

### P1 配套补充 Prompt（第二/多轮：只增量补全，仍是列表输出）

基于你上一轮已经输出的 Gi/Fi/Rk，请做“增量补全”：只输出新增或修正的行，不要重复已完整覆盖的行。要求：

1) 先列出你认为遗漏风险最高的类别（优先补）：
- 权限/治理(set*/role/upgrade)、白名单
- 签名/merkle 数据管理与校验分支
- 时间窗/锁定/额度上限
- 索引/分页/查询流（容易漏但被分发/前端依赖）
- 资金流：退款/费用去向/提现
- 事件与可观测性
- 跨链/环境假设

2) 输出格式（必须引用已有 ID；新增用 +；修正用 ~）
- + Gi 组名: 合约.函数, 合约.函数 ...
- ~ Fi 业务流名 (归属: Gx,...): 合约.函数, 合约.函数 ...
- + Rk 类型: [..] <-> [..]  或  + Rk 分叉/汇聚: ...

3) 若发现“某函数应归属多个 Gi/Fi”，用 ~ 修正对应 Gi/Fi 的函数列表（只改动那一行）。

4) 最后再给一次 checklist，对仍未覆盖项标注“仍待补充/确认”。

### P2 汇总 Prompt（输出所有业务流 Fi，全量，用于生成 business_flow_code）

建议固定一个“收敛输出”prompt，避免模型跑偏输出其它内容：

- 现在输出“最终版”的所有业务流（Fi）全量列表。
- 只输出 Fi 行，不要输出 Gi/Rk/checklist，不要输出额外解释文本。
- 每行格式必须严格为：
  Fi 业务流名 (归属: Gx,...): 合约A.函数1, 合约B.函数2 ...

---

## Planning 实施后的流水线形态（高层）

planning 新流程（简化版）：

1. Tree-sitter parse：
   - 得到 `functions_to_check`（合约.函数 列表 + file/visibility 元信息）
2. Codex business flow extraction：
   - P0：主 prompt 抽取 Gi/Fi/Rk + checklist
   - P1：增量补全（只输出 +/~ 行）
   - P2：输出最终 Fi 全量
3. 规划产物输出：
   - 解析 P2 得到 `business_flow_code` 对象集合（每个 Fi 一个对象）
4. 下游扫描（reasoning）：
   - 遍历 `business_flow_code` 对象，按 `function_refs` 获取对应函数体内容作为扫描输入（不做调用扩展）

---

## 结果落库/任务生成（建议，后续再实现）

为尽量复用现有表结构（如 `project_task`），建议规划阶段把每个 Fi 映射成一个任务：

- `Project_Task.name`：`"<Fi> <flow_name>"` 或 `"Fi:<flow_id>"`
- `Project_Task.rule_key`：规划阶段专用标识（例如 `"BUSINESS_FLOW_PLANNING"`）
- `Project_Task.business_flow_code`：存放 **function_refs 的序列化文本或 JSON**（推荐 JSON）
- `Project_Task.content`：可存放 Fi 的“自然语言描述/备注”

> 重点：这里的 business_flow_code 作为“待扫描对象”，不再依赖 call tree 拼接。

---

## 解析与稳定性注意事项

- **防止“跑偏输出”**：P2 只允许输出 Fi 列表，避免出现聊天式内容（`businessflow_history_chat` 中曾出现过与项目无关的 F1..F17 示例，说明必须强约束输出格式）。
- **ID 稳定性**：P0 生成的 Fi/Gi ID 在 P1/P2 中必须保持稳定，避免规划产物不可追踪。
- **体量控制**：如果项目函数过多，允许先按模块目录分段运行（例如先提取核心合约，再补全外围），但仍要求 ID 不重排。

---

## 验收标准（DoD）

- planning 阶段完全不依赖 RAG、chunks、LanceDB。
- planning 阶段不构建 call tree/call graph，也不依赖调用关系结构。
- Codex 在 `--cd project_root` 受控目录内完成业务流抽取，输出 Gi/Fi，并通过 2 轮副 prompt 完成增量修正与最终汇总。
- 最终产物能提供可枚举的 `business_flow_code` 对象集合（Fi），可直接驱动后续扫描。


