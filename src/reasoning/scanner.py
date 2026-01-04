import os
import re
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from .utils.scan_utils import ScanUtils
from prompt_factory.vul_prompt_common import VulPromptCommon
from prompt_factory.periphery_prompt import PeripheryPrompt
from prompt_factory.core_prompt import CorePrompt
from prompt_factory.assumption_validation_prompt import AssumptionValidationPrompt
from prompt_factory.vul_reasoning_json_prompt import VulReasoningJsonPrompt
from prompt_factory.prompt_assembler import PromptAssembler
from openai_api.openai import analyze_code_assumptions
from logging_config import get_logger
import json
from dao.entity import Project_Finding
from dao.finding_mgr import ProjectFindingMgr
from codex_service import CodexClient
from codex_runner import CodexCliError


class VulnerabilityScanner:
    """漏洞扫描器，负责智能合约代码的漏洞扫描"""
    
    def __init__(self, project_audit, codex_client: Optional[CodexClient] = None):
        self.project_audit = project_audit
        self.logger = get_logger(f"VulnerabilityScanner[{project_audit.project_id}]")
        self.codex_client = codex_client or CodexClient()
        
        # 🎯 读取项目设计文档（如果启用）
        self.design_doc_content = self._load_design_document()
        
        # 🎯 读取固定不变量列表（如果启用）
        self.fixed_invariants = self._load_fixed_invariants()
    
    def _load_design_document(self) -> str:
        """加载项目设计文档内容"""
        # 检查是否启用设计文档上下文
        enable_design_doc = os.getenv("ENABLE_DESIGN_DOC_CONTEXT", "False").lower() == "true"
        
        if not enable_design_doc:
            return ""
        
        # 获取设计文档路径（相对于项目根目录）
        doc_path = os.getenv("PROJECT_DESIGN_DOC_PATH", "project_design.md")
        
        # 尝试读取文档
        try:
            # 获取项目根目录（假设scanner.py在src/reasoning/下）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
            full_path = os.path.join(project_root, doc_path)
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        self.logger.info(f"✅ 成功加载项目设计文档: {doc_path} ({len(content)} 字符)")
                        return content
                    else:
                        self.logger.warning(f"⚠️ 设计文档为空: {doc_path}")
                        return ""
            else:
                self.logger.warning(f"⚠️ 设计文档不存在: {full_path}")
                return ""
                
        except Exception as e:
            self.logger.error(f"❌ 读取设计文档失败: {e}")
            return ""
    
    def _load_fixed_invariants(self) -> list:
        """加载固定不变量列表"""
        # 检查是否启用固定不变量
        enable_fixed_invariants = os.getenv("ENABLE_FIXED_INVARIANTS", "False").lower() == "true"
        
        if not enable_fixed_invariants:
            return []
        
        # 获取固定不变量文件路径（相对于项目根目录）
        invariants_path = os.getenv("FIXED_INVARIANTS_PATH", "fixed_invariants.md")
        
        # 尝试读取文件
        try:
            # 获取项目根目录（假设scanner.py在src/reasoning/下）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
            full_path = os.path.join(project_root, invariants_path)
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        # 使用<|INVARIANT_SPLIT|>分割符解析固定不变量
                        invariants_raw = content.split("<|INVARIANT_SPLIT|>")
                        invariants_list = []
                        for inv in invariants_raw:
                            cleaned_inv = inv.strip()
                            # 过滤掉空字符串和只包含标题/注释的部分
                            if cleaned_inv and not cleaned_inv.startswith('#') and len(cleaned_inv) > 50:
                                invariants_list.append(cleaned_inv)
                        
                        if invariants_list:
                            self.logger.info(f"✅ 成功加载固定不变量: {invariants_path} ({len(invariants_list)} 个不变量)")
                            return invariants_list
                        else:
                            self.logger.warning(f"⚠️ 固定不变量文件中没有有效的不变量: {invariants_path}")
                            return []
                    else:
                        self.logger.warning(f"⚠️ 固定不变量文件为空: {invariants_path}")
                        return []
            else:
                self.logger.warning(f"⚠️ 固定不变量文件不存在: {full_path}")
                return []
                
        except Exception as e:
            self.logger.error(f"❌ 读取固定不变量失败: {e}")
            return []

    def do_scan(self, task_manager, is_gpt4=False, filter_func=None):
        """执行漏洞扫描"""
        # 获取任务列表
        tasks = task_manager.get_task_list()
        if len(tasks) == 0:
            return []

        print("🔄 标准模式运行中")
        return self._scan_standard_mode(tasks, task_manager, filter_func, is_gpt4)

    def _scan_standard_mode(self, tasks, task_manager, filter_func, is_gpt4):
        """标准模式扫描
        
        执行策略：
        1. 按 group 分组任务
        2. 同一个 group 内的任务串行执行（保证同组总结的顺序性）
        3. 不同 group 之间并行执行（提升整体效率）
        """
        max_threads = int(os.getenv("MAX_THREADS_OF_SCAN", 5))
        
        # 按 group 分组任务
        group_dict = {}
        for task in tasks:
            group_uuid = getattr(task, 'group', '') or 'no_group'
            if group_uuid not in group_dict:
                group_dict[group_uuid] = []
            group_dict[group_uuid].append(task)
        
        # 为每个 group 定义处理函数（串行处理 group 内的任务）
        def process_group(group_tasks):
            for task in group_tasks:
                self._process_single_task_standard(task, task_manager, filter_func, is_gpt4)
        
        # 并行处理不同的 group
        group_list = list(group_dict.values())
        ScanUtils.execute_parallel_scan(group_list, process_group, max_threads)
        return tasks

    def _execute_vulnerability_scan(self, task, task_manager, is_gpt4: bool) -> str:
        """执行漏洞扫描（使用任务中已确定的rule）
        
        注意：现在统一使用vulnerability_detection配置(claude4sonnet)，is_gpt4参数已不再使用但保留以兼容
        """
        try:
            # 获取任务的business_flow_code作为代码部分
            business_flow_code = getattr(task, 'business_flow_code', task.content)
            
            # 从任务中获取已经确定的rule（Planning阶段已经分配好的checklist）
            task_rule = getattr(task, 'rule', '')
            rule_key = getattr(task, 'rule_key', '')
            
            # 解析rule
            rule_list = []
            if task_rule:
                # 🎯 assumption_violation类型的任务，rule是列表格式（分组的assumption/invariant）
                if rule_key == "assumption_violation":
                    rule_list = task_rule  # 直接使用列表
                else:
                    # 其他类型任务，尝试解析JSON格式
                    try:
                        rule_list = json.loads(task_rule)
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"任务 {task.name} 的rule解析失败: {e}")
                        rule_list = []
            
            # 🎯 将固定不变量添加到检查列表中（仅对assumption_violation类型的任务）
            if rule_key == "assumption_violation" and self.fixed_invariants:
                if isinstance(rule_list, list):
                    # 将固定不变量添加到现有列表中
                    original_count = len(rule_list)
                    rule_list = rule_list + self.fixed_invariants
                    self.logger.debug(f"任务 {task.name} 添加了 {len(self.fixed_invariants)} 个固定不变量 (原有: {original_count}, 总计: {len(rule_list)})")
                elif isinstance(rule_list, str):
                    # 如果rule_list是字符串，转换为列表后添加
                    rule_list = [rule_list] + self.fixed_invariants
                    self.logger.debug(f"任务 {task.name} 添加了 {len(self.fixed_invariants)} 个固定不变量")
                else:
                    # 如果rule_list为空或其他类型，直接使用固定不变量
                    rule_list = self.fixed_invariants
                    self.logger.debug(f"任务 {task.name} 使用 {len(self.fixed_invariants)} 个固定不变量")
            
            # 🎯 新增：基于group查询同组已有结果并生成总结（根据环境变量开关控制）
            # 你最新口径：不需要在意历史数据，默认关闭同组总结（如需开启可设 SUMMARY_IN_REASONING=True）
            summary_in_reasoning = os.getenv("SUMMARY_IN_REASONING", "False").lower() == "true"
            group_summary = ""
            if summary_in_reasoning:
                group_summary = self._get_group_results_summary(task, task_manager)
            
            # 手动组装prompt（使用任务的具体rule而不是索引）
            assembled_prompt = self._assemble_prompt_with_specific_rule(
                business_flow_code, 
                rule_list, 
                rule_key
            )
            
            # 🎯 如果启用了项目设计文档，将其添加到prompt最前面
            if self.design_doc_content:
                design_doc_prefix = f"""# PROJECT DESIGN CONTEXT

The following is the project's design document, which provides important context about the system's architecture, business logic, and security model. Use this information to better understand the developer's intentions and identify potential vulnerabilities.

{self.design_doc_content}

{"=" * 80}

"""
                assembled_prompt = design_doc_prefix + assembled_prompt
            
            # 🎯 如果启用了同组总结且有总结内容，将其添加到prompt前面（在设计文档之后）
            # 默认关闭：SUMMARY_IN_REASONING=False
            if summary_in_reasoning and group_summary:
                from prompt_factory.group_summary_prompt import GroupSummaryPrompt
                enhanced_prefix = GroupSummaryPrompt.get_enhanced_reasoning_prompt_prefix()
                assembled_prompt = enhanced_prefix + group_summary + "\n\n" + "=" * 80 + "\n\n" + assembled_prompt
            
            # 🎯 reasoning阶段：改为 Codex 执行（agentic workflow + 只读检索）
            project_root = getattr(self.project_audit, "project_path", "") or ""
            if not project_root:
                raise RuntimeError("project_audit.project_path is empty; cannot set codex --cd workspace")

            codex_res = self.codex_client.exec(workspace_root=project_root, prompt=assembled_prompt)
            if codex_res.returncode != 0:
                raise CodexCliError(f"codex reasoning failed: {codex_res.stderr.strip()}")

            result = self._extract_json_object_or_raise(codex_res.stdout)
            
            # 保存结果
            if hasattr(task, 'id') and task.id:
                task_manager.update_result(task.id, result)
            else:
                self.logger.warning(f"任务 {task.name} 没有ID，无法保存结果")

            # 🎯 新增：将多漏洞 JSON 拆分写入 project_finding（幂等：按 task_id 删除旧 findings 再重建）
            self._split_and_persist_findings(task, task_manager, result)
            
            print(f"✅ 任务 {task.name} 扫描完成，使用rule: {rule_key} ({len(rule_list)}个检查项)")
            return result
        except Exception as e:
            print(f"❌ 漏洞扫描执行失败: {e}")
            return ""

    @staticmethod
    def _extract_json_object_or_raise(text: str) -> str:
        """
        Codex stdout 可能包含 agentic workflow 的“Explored/exec ...”等非 JSON 文本。
        这里做稳健提取：优先取 ```json ...```，否则尝试从文本中解析第一个 JSON 对象。
        返回：可被 json.loads 解析且为 dict 的 JSON 字符串。
        """
        s = (text or "").strip()
        if not s:
            raise ValueError("empty codex output")

        # fenced json
        m = re.search(r"```json\\s*([\\s\\S]*?)\\s*```", s, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            obj = json.loads(candidate)
            if not isinstance(obj, dict):
                raise ValueError("codex fenced json is not an object")
            return candidate

        # raw decode: find first JSON object
        dec = json.JSONDecoder()
        for i, ch in enumerate(s):
            if ch != "{":
                continue
            try:
                obj, end = dec.raw_decode(s[i:])
                if isinstance(obj, dict):
                    return s[i : i + end]
            except Exception:
                continue

        # fallback: first '{' last '}' slice
        l = s.find("{")
        r = s.rfind("}")
        if l != -1 and r != -1 and r > l:
            candidate = s[l : r + 1]
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return candidate

        raise ValueError("no json object found in codex output")

    def _process_single_task_standard(self, task, task_manager, filter_func, is_gpt4):
        """标准模式处理单个任务"""
        # 新版断点续跑逻辑：
        # - result 非空 & short_result == split_done: 跳过扫描与拆分
        # - result 非空 & short_result != split_done: 跳过扫描，但需要补拆分写入 finding
        # - result 为空: 需要扫描（scan 时会自动拆分）
        short_result = getattr(task, 'short_result', '') or ''
        has_result = bool(getattr(task, 'result', '') or '')

        if has_result and short_result == "split_done":
            self.logger.info(f"任务 {task.name} 已扫描且已拆分(split_done)，跳过")
            return

        if has_result and short_result != "split_done":
            self.logger.info(f"任务 {task.name} 已扫描但未拆分，执行补拆分写入 finding")
            self._split_and_persist_findings(task, task_manager, task.result)
            return
        
        # 检查是否应该扫描此任务
        if not ScanUtils.should_scan_task(task, filter_func):
            self.logger.info(f"任务 {task.name} 不满足扫描条件，跳过")
            return
        
        # 执行漏洞扫描
        self._execute_vulnerability_scan(task, task_manager, is_gpt4)

    def _split_and_persist_findings(self, task, task_manager, result_json_text: str):
        """将 task.result(多漏洞 JSON) 拆分写入 project_finding，并将 task.short_result 标记为 split_done（幂等方案 A）。"""
        try:
            if not getattr(task, 'id', None):
                return

            # 如果已经标记 split_done，则跳过
            if (getattr(task, 'short_result', '') or '') == "split_done":
                return

            # 解析 JSON
            data = json.loads(result_json_text) if result_json_text else {}
            vulns = data.get("vulnerabilities", []) if isinstance(data, dict) else []

            # 无漏洞也视为拆分完成（避免反复重试）
            engine = getattr(task_manager, 'engine', None) or getattr(getattr(task_manager, 'Session', None), 'kw', {}).get('bind', None)
            if engine is None:
                self.logger.warning("无法获取 DB engine，跳过 findings 写入")
                return
            finding_mgr = ProjectFindingMgr(task_manager.project_id, engine)

            # 幂等：先删后建
            finding_mgr.delete_findings_by_task_id(task.id)

            findings = []
            for vuln in (vulns or []):
                # 兼容两种形式：
                # 1) vuln 是字符串 -> 转成 {"description": "..."}
                # 2) vuln 是对象 -> 若无 description 则兜底塞入字符串化内容
                if isinstance(vuln, str):
                    vuln_obj = {"description": vuln}
                elif isinstance(vuln, dict):
                    if "description" not in vuln:
                        vuln_obj = {"description": json.dumps(vuln, ensure_ascii=False)}
                    else:
                        vuln_obj = vuln
                else:
                    vuln_obj = {"description": str(vuln)}

                single_json = {
                    "schema_version": data.get("schema_version", "1.0") if isinstance(data, dict) else "1.0",
                    "vulnerabilities": [vuln_obj],
                }
                findings.append(
                    Project_Finding(
                        project_id=task_manager.project_id,
                        task_id=task.id,
                        task_uuid=getattr(task, 'uuid', ''),
                        rule_key=getattr(task, 'rule_key', ''),
                        finding_json=json.dumps(single_json, ensure_ascii=False),
                        task_name=getattr(task, 'name', ''),
                        task_content=getattr(task, 'content', ''),
                        task_business_flow_code=getattr(task, 'business_flow_code', ''),
                        task_contract_code=getattr(task, 'contract_code', ''),
                        task_start_line=getattr(task, 'start_line', ''),
                        task_end_line=getattr(task, 'end_line', ''),
                        task_relative_file_path=getattr(task, 'relative_file_path', ''),
                        task_absolute_file_path=getattr(task, 'absolute_file_path', ''),
                        task_rule=getattr(task, 'rule', ''),
                        task_group=getattr(task, 'group', ''),
                        dedup_status='kept',
                        validation_status='pending',
                        validation_record='',
                    )
                )

            if findings:
                finding_mgr.add_findings(findings, commit=True)

            # 标记拆分完成
            task_manager.update_short_result(task.id, "split_done")
        except Exception as e:
            self.logger.warning(f"拆分写入 finding 失败: {e}")
            try:
                if getattr(task, 'id', None):
                    task_manager.update_short_result(task.id, "split_failed")
            except Exception:
                pass
    
    def _get_group_results_summary(self, task, task_manager) -> str:
        """获取同组任务的结果总结"""
        try:
            # 获取任务的group UUID
            group_uuid = getattr(task, 'group', None)
            if not group_uuid or group_uuid.strip() == "":
                return ""
            
            # 查询同组中已有结果的任务
            tasks_with_results = task_manager.query_tasks_with_results_by_group(group_uuid)
            if not tasks_with_results:
                return ""
            
            # 排除当前任务自己
            current_task_uuid = getattr(task, 'uuid', None)
            if current_task_uuid:
                tasks_with_results = [t for t in tasks_with_results if t.uuid != current_task_uuid]
            
            if not tasks_with_results:
                return ""
            
            # 使用结果总结器生成总结
            from .utils.group_result_summarizer import GroupResultSummarizer
            summary = GroupResultSummarizer.summarize_group_results(tasks_with_results)
            
            if summary:
                print(f"🔍 为任务 {task.name} 找到 {len(tasks_with_results)} 个同组已完成任务的结果总结")
            
            return summary or ""
        except Exception as e:
            self.logger.warning(f"获取同组结果总结失败: {e}")
            return ""

    def _assemble_prompt_with_specific_rule(self, code: str, rule_list: list, rule_key: str) -> str:
        """使用具体的rule列表组装prompt"""
        
        # 🎯 专门处理assumption_violation类型的任务
        if rule_key == "assumption_violation":
            # 对于assumption验证，rule_list是列表格式（一组assumption/invariant，最多3个）
            # 直接使用专门的assumption验证prompt
            return AssumptionValidationPrompt.get_assumption_validation_prompt(
                code, rule_list
            )
        
        # 🎯 专门处理PURE_SCAN类型的任务
        if rule_key == "PURE_SCAN":
            # 使用pure scan的prompt组装器
            return PromptAssembler.assemble_prompt_pure(code)
        
        # 原有的漏洞扫描逻辑（非assumption类型）
        else:
            # 关键：不要再拼接 PeripheryPrompt.guidelines/jailbreak_prompt
            # 这些通用尾巴会引入非 JSON 的输出格式要求，导致模型倾向只输出 1 条甚至输出异常。
            return (
                VulReasoningJsonPrompt.build_prompt(
                code=code,
                rule_key=rule_key,
                rule_list=rule_list,
                group_summary="",  # 当前默认不使用历史
                )
                + "\n"
                + PeripheryPrompt.guidelines_json_only()
            )