class BusinessFlowPlanningPrompt:
    """
    Planning 阶段：业务流/业务流组抽取 prompt（参考 codex_example/businessflow_history_chat）。
    """

    @staticmethod
    def p0_initial(function_catalog: str = "") -> str:
        # 首轮：Gi/Fi/Rk + checklist（可迭代 ID）
        catalog_block = ""
        if function_catalog.strip():
            catalog_block = f"""

【可用函数清单（必须严格使用这些名称）】
下面是本项目通过 tree-sitter 解析得到的“可用函数全量清单”。你在输出 Gi/Fi/Rk 时：
- **必须优先从清单中选择函数名**（完全一致的字符串匹配）
- **禁止**输出任何不在清单中的函数（包括外部接口/外部依赖/库函数/系统合约等）。
- **禁止**把常量/状态变量/typehash/事件名当成函数写进列表。
- **禁止**输出裸函数名（例如 `create` / `fill` / `orderConfig`），必须使用清单中的完整形式（如 `LibP2POrderManager.create`）。

{function_catalog}
""".rstrip()

        return ("""
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
""".strip() + catalog_block)

    @staticmethod
    def p1_incremental(previous_output: str) -> str:
        # 第二轮：只输出增量 +/~ 行 + checklist
        return f"""
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

====================
【上一轮输出（供你增量补全）】
{previous_output}
""".strip()

    @staticmethod
    def p2_final_json(p0_output: str, p1_delta_output: str) -> str:
        # 第三轮：收敛成 JSON，便于程序解析落库
        return f"""
你现在需要输出“最终版”的业务流（Fi）全量列表，并且必须以 JSON 输出，方便机器解析与落库。

【输入】
1) 首轮输出（P0）
{p0_output}

2) 增量补全输出（P1，仅包含 +/~ 行）
{p1_delta_output}

【输出要求（只输出 JSON，不要任何额外文本）】
输出必须是单个 JSON 对象，严格遵循：
{{
  "schema_version": "business_flow_planning_v1",
  "groups": [{{"group_id":"G1","group_name":"string","functions":["Contract.func"]}}],
  "flows": [
    {{
      "flow_id": "F1",
      "flow_name": "string",
      "group_ids": ["G1"],
      "function_refs": ["Contract.func", "Contract._internalFunc", "OtherContract.dep"]
    }}
  ]
}}

约束：
- flows 必须包含所有 Fi（全量），且 flow_id 必须稳定，不要重排。
- function_refs 必须是“合约/类名.函数名”列表（按业务流执行顺序排列）。
- function_refs 中 **禁止**出现外部接口/依赖（例如 IERC20/IVault 等）、禁止出现常量/typehash/事件名、禁止出现裸函数名。
""".strip()



    Planning 阶段：业务流/业务流组抽取 prompt（参考 codex_example/businessflow_history_chat）。
    """

    @staticmethod
    def p0_initial(function_catalog: str = "") -> str:
        # 首轮：Gi/Fi/Rk + checklist（可迭代 ID）
        catalog_block = ""
        if function_catalog.strip():
            catalog_block = f"""

【可用函数清单（必须严格使用这些名称）】
下面是本项目通过 tree-sitter 解析得到的“可用函数全量清单”。你在输出 Gi/Fi/Rk 时：
- **必须优先从清单中选择函数名**（完全一致的字符串匹配）
- **禁止**输出任何不在清单中的函数（包括外部接口/外部依赖/库函数/系统合约等）。
- **禁止**把常量/状态变量/typehash/事件名当成函数写进列表。
- **禁止**输出裸函数名（例如 `create` / `fill` / `orderConfig`），必须使用清单中的完整形式（如 `LibP2POrderManager.create`）。

{function_catalog}
""".rstrip()

        return ("""
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
""".strip() + catalog_block)

    @staticmethod
    def p1_incremental(previous_output: str) -> str:
        # 第二轮：只输出增量 +/~ 行 + checklist
        return f"""
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

====================
【上一轮输出（供你增量补全）】
{previous_output}
""".strip()

    @staticmethod
    def p2_final_json(p0_output: str, p1_delta_output: str) -> str:
        # 第三轮：收敛成 JSON，便于程序解析落库
        return f"""
你现在需要输出“最终版”的业务流（Fi）全量列表，并且必须以 JSON 输出，方便机器解析与落库。

【输入】
1) 首轮输出（P0）
{p0_output}

2) 增量补全输出（P1，仅包含 +/~ 行）
{p1_delta_output}

【输出要求（只输出 JSON，不要任何额外文本）】
输出必须是单个 JSON 对象，严格遵循：
{{
  "schema_version": "business_flow_planning_v1",
  "groups": [{{"group_id":"G1","group_name":"string","functions":["Contract.func"]}}],
  "flows": [
    {{
      "flow_id": "F1",
      "flow_name": "string",
      "group_ids": ["G1"],
      "function_refs": ["Contract.func", "Contract._internalFunc", "OtherContract.dep"]
    }}
  ]
}}

约束：
- flows 必须包含所有 Fi（全量），且 flow_id 必须稳定，不要重排。
- function_refs 必须是“合约/类名.函数名”列表（按业务流执行顺序排列）。
- function_refs 中 **禁止**出现外部接口/依赖（例如 IERC20/IVault 等）、禁止出现常量/typehash/事件名、禁止出现裸函数名。
""".strip()


