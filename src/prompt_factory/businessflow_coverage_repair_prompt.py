from __future__ import annotations


class BusinessFlowCoverageRepairPrompt:
    """
    Coverage Repair 阶段专用 prompt（在已有业务流基础上，对“未覆盖函数列表”做业务分组补全）。

    关键约束（由调用方保证传入的函数名来自 tree-sitter）：
    - 只能使用未覆盖函数列表中的函数名
    - 禁止外部接口/依赖、常量/typehash/事件名、裸函数名
    - 倾向更粗（少条长 flow）
    - 不允许修正旧 Fi（不输出 ~）
    """

    @staticmethod
    def p3_group_uncovered_to_new_flows(
        *,
        existing_overview: str,
        uncovered_functions_list: str,
        next_group_id: str,
        next_flow_id: str,
        target_new_flows: int = 3,
    ) -> str:
        return f"""
你是“业务流补全助手”。我们已经有一批业务流/业务流组（Gi/Fi），但仍有一批 tree-sitter 解析出的函数未被任何业务流覆盖。
你的任务：把这些“未覆盖函数”按业务语义进行分组，并产出**新增**的业务流组/业务流（Gi/Fi），用于继续 planning。

【硬约束（必须遵守）】
- 你只能使用我给出的“未覆盖函数列表”中的函数名（完全一致匹配）。
- 禁止输出任何未覆盖列表之外的函数（包括外部接口/外部依赖/库函数/系统合约等）。
- 禁止常量/状态变量/typehash/事件名；只允许函数。
- 禁止裸函数名，必须是 `ContractOrLibrary.func`（或带签名）形式。
- **不允许修正旧 Fi**：不要输出 ~ 行，只能输出新增的 `new_flows`。
- **尽量更粗**：请用更少的 flow 覆盖更多函数（少条长 flow），目标新增 flow 数约 {target_new_flows} 条（可少不可多）。

【agentic workflow 要求】
你可以在受控目录内使用只读命令（rg/grep/cat/ls）确认函数属于同一业务域，但最终 `function_refs` 仍必须严格来自未覆盖列表。

【已有 Gi/Fi 概览（仅供你避免重复命名/重复分组，不代表可引用函数）】
{existing_overview}

【未覆盖函数列表（你只能从这里挑选）】
{uncovered_functions_list}

【输出要求（只输出 JSON，不要任何额外文本）】
输出必须是单个 JSON 对象，严格遵循：
{{
  "schema_version": "business_flow_coverage_repair_v1",
  "new_groups": [
    {{"group_id": "{next_group_id}", "group_name": "string", "functions": ["Contract.func"]}}
  ],
  "new_flows": [
    {{
      "flow_id": "{next_flow_id}",
      "flow_name": "string",
      "group_ids": ["{next_group_id}"],
      "function_refs": ["Contract.func", "Contract.func"]
    }}
  ]
}}

额外规则：
- `new_flows` 必须非空。
- `new_groups` 可为空数组（如果你认为不需要新增组）。
- `function_refs` 中的每一项必须来自未覆盖列表；如果不确定，宁愿不输出该函数。
""".strip()




class BusinessFlowCoverageRepairPrompt:
    """
    Coverage Repair 阶段专用 prompt（在已有业务流基础上，对“未覆盖函数列表”做业务分组补全）。

    关键约束（由调用方保证传入的函数名来自 tree-sitter）：
    - 只能使用未覆盖函数列表中的函数名
    - 禁止外部接口/依赖、常量/typehash/事件名、裸函数名
    - 倾向更粗（少条长 flow）
    - 不允许修正旧 Fi（不输出 ~）
    """

    @staticmethod
    def p3_group_uncovered_to_new_flows(
        *,
        existing_overview: str,
        uncovered_functions_list: str,
        next_group_id: str,
        next_flow_id: str,
        target_new_flows: int = 3,
    ) -> str:
        return f"""
你是“业务流补全助手”。我们已经有一批业务流/业务流组（Gi/Fi），但仍有一批 tree-sitter 解析出的函数未被任何业务流覆盖。
你的任务：把这些“未覆盖函数”按业务语义进行分组，并产出**新增**的业务流组/业务流（Gi/Fi），用于继续 planning。

【硬约束（必须遵守）】
- 你只能使用我给出的“未覆盖函数列表”中的函数名（完全一致匹配）。
- 禁止输出任何未覆盖列表之外的函数（包括外部接口/外部依赖/库函数/系统合约等）。
- 禁止常量/状态变量/typehash/事件名；只允许函数。
- 禁止裸函数名，必须是 `ContractOrLibrary.func`（或带签名）形式。
- **不允许修正旧 Fi**：不要输出 ~ 行，只能输出新增的 `new_flows`。
- **尽量更粗**：请用更少的 flow 覆盖更多函数（少条长 flow），目标新增 flow 数约 {target_new_flows} 条（可少不可多）。

【agentic workflow 要求】
你可以在受控目录内使用只读命令（rg/grep/cat/ls）确认函数属于同一业务域，但最终 `function_refs` 仍必须严格来自未覆盖列表。

【已有 Gi/Fi 概览（仅供你避免重复命名/重复分组，不代表可引用函数）】
{existing_overview}

【未覆盖函数列表（你只能从这里挑选）】
{uncovered_functions_list}

【输出要求（只输出 JSON，不要任何额外文本）】
输出必须是单个 JSON 对象，严格遵循：
{{
  "schema_version": "business_flow_coverage_repair_v1",
  "new_groups": [
    {{"group_id": "{next_group_id}", "group_name": "string", "functions": ["Contract.func"]}}
  ],
  "new_flows": [
    {{
      "flow_id": "{next_flow_id}",
      "flow_name": "string",
      "group_ids": ["{next_group_id}"],
      "function_refs": ["Contract.func", "Contract.func"]
    }}
  ]
}}

额外规则：
- `new_flows` 必须非空。
- `new_groups` 可为空数组（如果你认为不需要新增组）。
- `function_refs` 中的每一项必须来自未覆盖列表；如果不确定，宁愿不输出该函数。
""".strip()


