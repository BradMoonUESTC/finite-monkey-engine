# forward 分支 vs main 分支：思路差异说明 + 建表 SQL

本文档说明 `forward` 分支相对 `main` 的核心设计思路变化，并给出 `project_task` 与 `project_finding` 两张表的 PostgreSQL 建表 SQL（从当前代码的 SQLAlchemy 实体编译导出）。

---

## 1) 核心思路差异（一句话版）

- **main**：以 `project_task` 为中心，任务表既承载“扫描任务”也承载“扫描结果/验证结果/去重状态”，导致多漏洞时需要复制 task 或在多处做复杂过滤。
- **forward**：以“任务(task) / 发现(finding)”分离为核心，`project_task` 只保存任务和聚合结果（多漏洞 JSON），新增 `project_finding` 专门保存**单漏洞条目**，后续去重/验证/输出全部基于 finding。

---

## 2) 数据流差异（按阶段）

### 2.1 Planning（任务生成）

- **main**：生成 `project_task` 列表（同一个扫描单元会受 `BUSINESS_FLOW_COUNT` 影响生成多条 task），每条 task 绑定 `rule_key + rule + business_flow_code`。
- **forward**：保持 planning 不变，仍然生成 `project_task`（兼容旧逻辑）。

### 2.2 Reasoning（扫描）

- **main**：
  - prompt 里存在“诱导式上下文”（例如“已确认存在漏洞/只有一个漏洞”）
  - reasoning 结果写回 `project_task.result`
  - 多漏洞承接困难：需要多轮/多次扫描或复制 task

- **forward**：
  - reasoning 主模型切到 `gpt-5.2`（并强制 `response_format=json_object`）
  - 使用中性审计式 JSON prompt，允许返回多个漏洞（`vulnerabilities[]`）
  - **聚合多漏洞 JSON** 仍然写入 `project_task.result`
  - 若 `task.short_result != split_done`，则把聚合 JSON 拆分为多条 `project_finding`（幂等方案 A：按 `task_id` 删除旧 findings 再重建），然后写 `task.short_result=split_done`
  - 断点续跑：  
    - `result` 非空且 `short_result==split_done` → 跳过  
    - `result` 非空且 `short_result!=split_done` → 只补拆分写 finding  
    - `result` 为空 → 执行扫描 + 拆分写 finding

### 2.3 去重（Reasoning 后 Dedup）

- **main**：从 `project_task.result` 汇总候选项，并通过 `short_result='delete'` 标记逻辑删除。
- **forward**：只对 `project_finding` 做去重，写回 `project_finding.dedup_status='delete'`。

### 2.4 Validation（验证）

- **main**：对 `project_task` 做验证，多轮 agent 逻辑把 yes/no 写回 `project_task.short_result`，并把日志写入 `scan_record`。
- **forward**：对 `project_finding` 做验证：
  - 只验证 `dedup_status != delete` 且 `validation_status` 为 `pending/空` 的 finding
  - 验证结论写回 `project_finding.validation_status`，验证过程写回 `project_finding.validation_record`
  - `project_task.short_result` 不再承载 yes/no，只承载“是否已拆分”的状态（`split_done/split_failed`）

### 2.5 输出/导出

- **main**：导出主要依赖 `project_task.short_result` 包含 yes 的记录。
- **forward**：导出只读取 `project_finding`：
  - `dedup_status != delete`
  - `validation_status == yes`
  - finding 表已冗余复制了 task 的代码相关字段（name/content/business_flow_code/路径/行号/rule/group 等），导出基本不需要 join task。

---

## 3) 关键字段语义变化

### 3.1 `project_task.short_result`

- **main**：主要承载 validation 结论（yes/no）以及部分流程标记（delete 等）。
- **forward**：只承载“是否已拆分写入 finding”的状态：
  - `""`：未拆分
  - `split_done`：已拆分
  - `split_failed`：拆分失败（可重试）

### 3.2 `project_task.result`

- **main**：reasoning 的自然语言结果/混合结果。
- **forward**：reasoning 的**多漏洞聚合 JSON**（供留档/追溯/同组 summary 使用）。

### 3.3 `project_finding.*`

`project_finding` 是 forward 的核心：每行代表一个“单漏洞条目”，并携带去重/验证状态与验证记录，同时尽量自包含 task 的代码上下文。

---

## 4) PostgreSQL 建表 SQL（从代码编译导出）

> 说明：以下 DDL 来自 `sqlalchemy.schema.CreateTable(...).compile(dialect=postgresql)` 的输出，字段类型与索引（例如 `index=True`）在实际数据库中会对应到额外的 `CREATE INDEX`；这里先给出 `CREATE TABLE` 主体结构。

### 4.1 `project_task`

```sql
CREATE TABLE project_task (
        id SERIAL NOT NULL, 
        uuid VARCHAR, 
        project_id VARCHAR, 
        name VARCHAR, 
        content VARCHAR, 
        rule VARCHAR, 
        rule_key VARCHAR, 
        result VARCHAR, 
        contract_code VARCHAR, 
        start_line VARCHAR, 
        end_line VARCHAR, 
        relative_file_path VARCHAR, 
        absolute_file_path VARCHAR, 
        recommendation VARCHAR, 
        business_flow_code VARCHAR, 
        scan_record VARCHAR, 
        short_result VARCHAR, 
        "group" VARCHAR, 
        PRIMARY KEY (id)
);
```

### 4.2 `project_finding`

```sql
CREATE TABLE project_finding (
        id SERIAL NOT NULL, 
        uuid VARCHAR, 
        project_id VARCHAR, 
        task_id INTEGER, 
        task_uuid VARCHAR, 
        rule_key VARCHAR, 
        finding_json VARCHAR, 
        task_name VARCHAR, 
        task_content VARCHAR, 
        task_business_flow_code VARCHAR, 
        task_contract_code VARCHAR, 
        task_start_line VARCHAR, 
        task_end_line VARCHAR, 
        task_relative_file_path VARCHAR, 
        task_absolute_file_path VARCHAR, 
        task_rule VARCHAR, 
        task_group VARCHAR, 
        dedup_status VARCHAR, 
        validation_status VARCHAR, 
        validation_record VARCHAR, 
        PRIMARY KEY (id)
);
```


