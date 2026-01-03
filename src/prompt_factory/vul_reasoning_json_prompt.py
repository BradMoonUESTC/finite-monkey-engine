from typing import List


class VulReasoningJsonPrompt:
    """
    Reasoning 阶段漏洞挖掘提示词（中性审计式，基于 checklist，多漏洞，固定 JSON）。
    目标：只输出最确定、非 intended design、非误报、会造成危害的纯漏洞；允许输出 0 个漏洞。
    """

    @staticmethod
    def build_prompt(
        code: str,
        rule_key: str,
        rule_list: List[str],
        group_summary: str = "",
    ) -> str:
        checklist_lines = "\n".join([f"{i+1}. {item}" for i, item in enumerate(rule_list or [])])

        # 你最新口径：不需要在意历史数据，因此这里不强制加入“避免重复”的历史摘要。
        # 仍保留参数以便未来需要时打开（但默认不使用）。
        summary_section = ""

        return f"""
# Role
You are a senior smart contract / blockchain security auditor.

# Task
Perform a careful vulnerability assessment of the provided code using the checklist below.
Be neutral: vulnerabilities may or may not exist.

{summary_section}

# Checklist ({rule_key})
{checklist_lines}

# Hard Requirements
- Only report vulnerabilities that are **high confidence** and would cause real harm.
- Do NOT report intended design, best-practice suggestions, or hypothetical risks without exploitability.
- Evidence MUST come from the provided code (include file/line range and a short excerpt).
- Output MUST be a single JSON object matching the schema below. Output JSON only.
- If you find multiple distinct high-confidence vulnerabilities, you MUST include ALL of them as separate items in the array (up to 5).
- Do NOT stop after the first vulnerability.

# Output JSON Schema (MUST match exactly)
{{
  "schema_version": "1.0",
  "vulnerabilities": [{{"description": "string"}}]
}}

# Description length constraint
For each vulnerability, keep "description" around 100-200 English words (not shorter than ~80 words; not longer than ~250 words).

# Notes
- "vulnerabilities" MUST be an array.
- It MAY be an empty array [] if no high-confidence vulnerabilities exist.
- If there are N vulnerabilities (2 <= N <= 5), return N items. If more than 5, return the 5 most harmful & certain.

# Example (for structure only; do not copy text)
{{
  "schema_version": "1.0",
  "vulnerabilities": [
    {{"description": "Vuln 1 ..."}},
    {{"description": "Vuln 2 ..."}}
  ]
}}

# Code
{code}
""".strip()


