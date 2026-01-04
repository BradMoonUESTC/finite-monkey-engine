class ValidationCodexPrompt:
    @staticmethod
    def build_validation_prompt(*, finding_json: str, rule_key: str, hint_file: str, hint_function: str) -> str:
        """
        Codex CLI validation 专用 prompt：
        - 强制 agentic workflow（多步只读检索）
        - 文档优先（README/docs/spec/NatSpec 等）
        - 严格 JSON-only 输出，便于落库到 validation_status/validation_record
        """
        return f"""
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
{{
  "schema_version": "validation_codex_v1",
  "status": "pending|intended_design|false_positive|vulnerability|vuln_high_cost|vuln_low_impact|not_sure",
  "confidence": "high|medium|low",
  "exists": true/false,
  "classification": "vulnerability|non_vulnerability|uncertain",
  "impact": "high|medium|low|unknown",
  "exploit_difficulty": "easy|medium|hard|unknown",
  "reason": "用 2-5 句话说明你为何得出该结论（必须引用证据要点）",
  "evidence": [
    {{
      "file": "相对路径（相对 workspace root）",
      "locator": "函数名/变量名/关键片段定位方式（可写行号范围或 grep 命中关键词）",
      "snippet": "<= 30 行的关键片段（可选，但强烈建议）",
      "why": "这段证据如何支持你的判断"
    }}
  ],
  "doc_references": [
    {{
      "file": "相对路径",
      "locator": "章节标题/关键词",
      "excerpt": "相关原文摘录（可选）",
      "why": "它如何表明 intended design 或影响评估"
    }}
  ],
  "attack_preconditions": ["若为漏洞，列出成立前置条件；不确定可为空数组"],
  "attack_path": "若为漏洞，简述可利用路径/触发方式；非漏洞可为空字符串",
  "mitigation": "若为漏洞，给出 1-3 条修复建议；非漏洞可为空字符串",
  "unknowns": ["如果 not_sure，请列出缺失信息/无法确认的点，并说明需要看什么才能确认"]
}}

【判定口径（避免误报）】
- intended_design：行为有文档/注释/显式逻辑支持“这是预期行为”，且不存在可被滥用造成真实损害的路径。
- false_positive：finding 描述/推断与代码事实不符（例如关键条件不存在、权限不可获得、入口不可达、变量不可控、逻辑相反等）。
- vulnerability：存在现实可利用路径，并可能造成明确损害（资金损失/权限提升/资产锁死/DoS 等）。
- vuln_high_cost：漏洞成立但利用门槛很高（需高权限、苛刻链上条件、复杂多交易/时间窗口、经济成本过高等）。
- vuln_low_impact：漏洞成立但影响面小（仅边缘用户、可控损失极小、需要用户自损或极端条件）。
- not_sure：在受控目录内已尽力检索仍不足以确认（必须在 unknowns 中写清楚缺什么）。

【输入：候选漏洞 finding_json】
{finding_json}

【辅助信息（可能为空）】
rule_key: {rule_key}
hint_file: {hint_file}
hint_function: {hint_function}
""".strip()


