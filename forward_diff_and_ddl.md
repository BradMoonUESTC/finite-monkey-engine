# `main` vs `forward`：设计思路差异 & 建表 SQL（PostgreSQL）

> 这份文档用于在 `main` 分支中说明：为何我们引入 `forward` 分支，以及两者在“任务/结果存储与流程组织”上的核心差异。  
> 注：这里的 `project_finding` 是 **forward 分支**的新表设计；`main` 分支默认仍以 `project_task` 为中心。

---

## 1) 一句话差异

- **`main`**：以 `project_task` 为中心，任务表同时承载“任务 + 扫描结果 + 去重/验证状态”，多漏洞承接会变复杂（容易引入大量过滤/状态分支）。
- **`forward`**：把“任务(task)”与“漏洞条目(finding)”解耦：`project_task` 只保留任务与聚合结果（多漏洞 JSON），新增 `project_finding` 专门存 **单漏洞条目**，后续去重/验证/输出全部基于 finding 表。

---

## 2) 数据流对比（重点）

### 2.1 Reasoning（扫描阶段）

- **main**
  - 结果写回 `project_task.result`
  - 需要通过重复扫描/多轮迭代来覆盖多个漏洞，或者在任务层做复制/过滤

- **forward**
  - `project_task.result` 保存 **多漏洞聚合 JSON**（用于留档与同组摘要）
  - 将聚合 JSON 拆分成 N 条 **单漏洞**记录写入 `project_finding`
  - `project_task.short_result` 只做“是否已拆分”的断点标记（例如 `split_done`）

### 2.2 Dedup（去重）

- **main**：对 `project_task` 做去重并标记逻辑删除（通常复用 `short_result`）
- **forward**：只对 `project_finding` 做去重，写回 `project_finding.dedup_status`

### 2.3 Validation（验证）

- **main**：验证任务来自 `project_task`
- **forward**：只验证 `project_finding`（未去重删除、且状态为 pending 的 finding）

### 2.4 输出/导出

- **main**：输出主要依赖 `project_task.short_result`（yes/no）等字段
- **forward**：输出只依赖 `project_finding`（`validation_status=yes` 且 `dedup_status!=delete`），finding 表尽量冗余 task 的代码上下文字段，减少 join

---

## 3) PostgreSQL 建表 SQL（摘录）

> 说明：这是 **DDL 主体结构**（`CREATE TABLE`）。索引/唯一约束可按需要补充（在 SQLAlchemy 里通过 `index=True/unique=True` 会生成额外的 `CREATE INDEX`）。

### 3.1 `project_task`（main/forward 都存在）

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

### 3.2 `project_finding`（forward 新增）

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


