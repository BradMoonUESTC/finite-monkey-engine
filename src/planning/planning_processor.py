import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from dao.entity import Project_Task
from dao.task_mgr import ProjectTaskMgr
from codex_runner import CodexCliError
from codex_service import CodexClient
from logging_config import get_logger
from prompt_factory.businessflow_planning_prompt import BusinessFlowPlanningPrompt
from prompt_factory.businessflow_coverage_repair_prompt import BusinessFlowCoverageRepairPrompt
from prompt_factory.vul_prompt_common import VulPromptCommon


class PlanningProcessor:
    """
    新版 Planning（业务流中心）：
    - 不使用 RAG / chunks / LanceDB
    - 不解析调用关系（不构建 call tree / call graph）
    - 仅使用 tree-sitter 的函数清单（合约/类名.函数名）作为对齐基准
    - 使用 Codex（P0/P1/P2）产出业务流 JSON
    - 将每个 Fi 落库为一条 Project_Task，核心字段为 business_flow_code（拼接后的主代码）
    """

    def __init__(self, project_audit, taskmgr: ProjectTaskMgr, codex_client: Optional[CodexClient] = None):
        self.project_audit = project_audit
        self.taskmgr = taskmgr
        self.codex_client = codex_client or CodexClient()
        self.logger = get_logger("PlanningProcessor")

        self.functions: List[Dict[str, Any]] = getattr(project_audit, "functions", []) or []
        self.project_root: str = getattr(project_audit, "project_path", "") or ""

        # name -> [func...]
        self._func_map: Dict[str, List[Dict[str, Any]]] = {}
        for f in self.functions:
            nm = (f.get("name") or "").strip()
            if not nm:
                continue
            self._func_map.setdefault(nm, []).append(f)

    @staticmethod
    def _extract_json_object(text: str) -> Optional[str]:
        s = (text or "").strip()
        if not s:
            return None
        if s.startswith("{") and s.endswith("}"):
            return s
        l = s.find("{")
        r = s.rfind("}")
        if l != -1 and r != -1 and r > l:
            return s[l : r + 1]
        return None

    def _resolve_function_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        ref = (ref or "").strip()
        if not ref:
            return None
        # 去掉 interface 标记（interface 本身不在 tree-sitter 函数清单里）
        if ref.endswith("(interface)"):
            ref = ref[: -len("(interface)")].strip()
        # 直接匹配
        if ref in self._func_map:
            return self._func_map[ref][0]
        # 处理带签名的情况：Foo.bar(uint256) -> Foo.bar
        if "(" in ref and ref.endswith(")"):
            base = ref.split("(", 1)[0].strip()
            if base in self._func_map:
                return self._func_map[base][0]
        return None

    def _build_business_flow_code(self, function_refs: List[str]) -> tuple[str, List[str], List[str]]:
        missing: List[str] = []
        interface_refs: List[str] = []
        blocks: List[str] = []
        for ref in function_refs:
            if ref.endswith("(interface)"):
                interface_refs.append(ref)
                continue
            func = self._resolve_function_ref(ref)
            if not func:
                missing.append(ref)
                continue
            rel = func.get("relative_file_path", "") or func.get("file_path", "")
            start = func.get("start_line", "")
            end = func.get("end_line", "")
            header = f"===== {func.get('name','')} ({rel}:{start}-{end}) ====="
            blocks.append(header)
            blocks.append(func.get("content", "") or "")
            blocks.append("")  # spacer
        return "\n".join(blocks).strip() + "\n", missing, interface_refs

    def _build_function_catalog(self, limit: int = 800) -> str:
        """
        给 Codex 的“可用函数清单”，用于约束其输出必须与 tree-sitter 对齐。
        """
        lines: List[str] = []
        for name, funcs in sorted(self._func_map.items()):
            f0 = funcs[0]
            rel = f0.get("relative_file_path", "") or ""
            lines.append(f"- {name} ({rel})")
            if len(lines) >= limit:
                break
        return "\n".join(lines)

    @staticmethod
    def _safe_int_env(name: str, default: int) -> int:
        v = (os.getenv(name) or "").strip()
        if not v:
            return default
        try:
            return int(v)
        except Exception:
            return default

    def _get_checklist_rule_keys(self) -> List[Tuple[str, List[str]]]:
        """
        rule_key 来源：沿用现有 checklist 体系（VulPromptCommon.vul_prompt_common_new）。

        返回：[(rule_key, rule_list), ...]，按 dict 原始顺序稳定输出。
        """
        # 对齐当前系统“细粒度 checklist 模式”的口径：
        # - checklist 定义在 src/prompt_factory/vul_prompt_common.py
        # - scan_mode == COMMON_PROJECT_FINE_GRAINED 时，按 checklist keys 进行细粒度扫描
        scan_mode = (os.getenv("SCAN_MODE") or "").strip()
        if scan_mode and scan_mode != "COMMON_PROJECT_FINE_GRAINED":
            # 允许在 planning_only 下仍然生成 checklist 任务（便于调试），但给出提示
            self.logger.warning(
                f"[planning] SCAN_MODE={scan_mode} (expected COMMON_PROJECT_FINE_GRAINED for checklist mode); "
                "still using VulPromptCommon checklists as rule_keys"
            )

        all_checklists = VulPromptCommon.vul_prompt_common_new(prompt_index=None) or {}
        pairs: List[Tuple[str, List[str]]] = []
        for k, v in all_checklists.items():
            if isinstance(v, list):
                pairs.append((str(k), [str(x) for x in v]))

        limit = self._safe_int_env("PLANNING_RULE_KEY_LIMIT", 0)
        if limit and limit > 0:
            pairs = pairs[:limit]
        return pairs

    def _coverage_sets_from_flows(self, flows: List[Dict[str, Any]]) -> Tuple[set, set]:
        """
        覆盖率按“所有函数”计算（不区分 external/internal/private）。
        - covered: 业务流里能 resolve 到 tree-sitter 的函数名集合（canonical=func['name']）
        - uncovered: F - covered
        """
        all_funcs = set(self._func_map.keys())
        covered: set = set()

        for flow in flows or []:
            refs = flow.get("function_refs") or []
            if not isinstance(refs, list):
                continue
            for r in refs:
                ref = str(r).strip()
                if not ref:
                    continue
                func = self._resolve_function_ref(ref)
                if func and func.get("name"):
                    covered.add(str(func["name"]).strip())

        uncovered = all_funcs - covered
        return covered, uncovered

    @staticmethod
    def _flow_overview_text(flows: List[Dict[str, Any]], max_lines: int = 200) -> str:
        """
        给 coverage repair 的“已有 Fi 概览”：仅包含 ID 与名称，避免 prompt 过长。
        """
        lines: List[str] = []
        for f in flows or []:
            fid = (f.get("flow_id") or "").strip()
            nm = (f.get("flow_name") or "").strip()
            if not fid:
                continue
            lines.append(f"- {fid}: {nm}".strip())
            if len(lines) >= max_lines:
                break
        return "\n".join(lines).strip()

    @staticmethod
    def _next_id(prefix: str, existing_ids: List[str], start_at: int = 1) -> str:
        mx = 0
        for s in existing_ids:
            if not isinstance(s, str):
                continue
            s = s.strip()
            if not s.startswith(prefix):
                continue
            num = s[len(prefix) :]
            try:
                mx = max(mx, int(num))
            except Exception:
                continue
        nxt = max(mx + 1, start_at)
        return f"{prefix}{nxt}"

    def _run_codex_coverage_repair(
        self,
        *,
        log_dir: Path,
        flows: List[Dict[str, Any]],
        uncovered_batch: List[str],
        next_group_id: str,
        next_flow_id: str,
        target_new_flows: int,
    ) -> Dict[str, Any]:
        """
        Coverage repair：对“未覆盖函数列表”进行分组补全，返回 new_flows/new_groups（JSON）。
        """
        existing_overview = self._flow_overview_text(flows)
        uncovered_text = "\n".join([f"- {x}" for x in uncovered_batch])

        p3 = BusinessFlowCoverageRepairPrompt.p3_group_uncovered_to_new_flows(
            existing_overview=existing_overview,
            uncovered_functions_list=uncovered_text,
            next_group_id=next_group_id,
            next_flow_id=next_flow_id,
            target_new_flows=target_new_flows,
        )

        self.logger.info(f"[planning] codex P3(coverage_repair) start, uncovered_batch={len(uncovered_batch)}")
        r3 = self.codex_client.exec(workspace_root=self.project_root, prompt=p3)
        if r3.returncode != 0:
            raise CodexCliError(f"codex p3 failed: {r3.stderr.strip()}")

        # dump artifacts
        def _dump(name: str, content: str) -> str:
            p = log_dir / name
            with open(p, "w", encoding="utf-8") as f:
                f.write(content or "")
            return str(p)

        p3_prompt_path = _dump(f"p3_prompt_{next_flow_id}.txt", p3)
        p3_stdout_path = _dump(f"p3_stdout_{next_flow_id}.txt", r3.stdout)
        p3_stderr_path = _dump(f"p3_stderr_{next_flow_id}.txt", r3.stderr)

        raw_json = self._extract_json_object(r3.stdout)
        if not raw_json:
            raise RuntimeError("codex p3 output has no json object")
        obj = json.loads(raw_json)

        return {
            "schema_version": "coverage_repair_codex_v1",
            "workspace_root": self.project_root,
            "p3": {
                "prompt_path": p3_prompt_path,
                "stdout_path": p3_stdout_path,
                "stderr_path": p3_stderr_path,
                "returncode": r3.returncode,
            },
            "parsed": obj,
        }

    def _run_codex_planning(self) -> Dict[str, Any]:
        if not self.project_root or not os.path.isdir(self.project_root):
            raise RuntimeError(f"invalid project_root: {self.project_root}")

        project_id = getattr(self.project_audit, "project_id", "") or self.taskmgr.project_id
        ts = time.strftime("%Y%m%d_%H%M%S")
        log_dir = Path("logs") / f"planning_{project_id}_{ts}"
        log_dir.mkdir(parents=True, exist_ok=True)

        # dump tree-sitter function index for debugging (name -> file/lines)
        fn_index_path = log_dir / "tree_sitter_functions.jsonl"
        try:
            with open(fn_index_path, "w", encoding="utf-8") as f:
                for func in self.functions:
                    rec = {
                        "name": func.get("name", ""),
                        "relative_file_path": func.get("relative_file_path", ""),
                        "start_line": func.get("start_line", ""),
                        "end_line": func.get("end_line", ""),
                        "visibility": func.get("visibility", ""),
                    }
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.logger.info(f"[planning] tree-sitter functions index dumped: {fn_index_path}")
        except Exception as e:
            self.logger.warning(f"[planning] dump tree-sitter functions index failed: {e}")

        started = time.time()
        function_catalog = self._build_function_catalog()
        p0 = BusinessFlowPlanningPrompt.p0_initial(function_catalog=function_catalog)
        self.logger.info(f"[planning] codex P0 start, workspace_root={self.project_root}")
        r0 = self.codex_client.exec(workspace_root=self.project_root, prompt=p0)
        if r0.returncode != 0:
            raise CodexCliError(f"codex p0 failed: {r0.stderr.strip()}")

        p1 = BusinessFlowPlanningPrompt.p1_incremental(r0.stdout)
        self.logger.info("[planning] codex P1 start (incremental)")
        r1 = self.codex_client.exec(workspace_root=self.project_root, prompt=p1)
        if r1.returncode != 0:
            raise CodexCliError(f"codex p1 failed: {r1.stderr.strip()}")

        p2 = BusinessFlowPlanningPrompt.p2_final_json(r0.stdout, r1.stdout)
        self.logger.info("[planning] codex P2 start (final json)")
        r2 = self.codex_client.exec(workspace_root=self.project_root, prompt=p2)
        if r2.returncode != 0:
            raise CodexCliError(f"codex p2 failed: {r2.stderr.strip()}")

        # persist codex conversation artifacts (prompt/stdout/stderr)
        def _dump(name: str, content: str) -> str:
            p = log_dir / name
            with open(p, "w", encoding="utf-8") as f:
                f.write(content or "")
            return str(p)

        p0_prompt_path = _dump("p0_prompt.txt", p0)
        p0_stdout_path = _dump("p0_stdout.txt", r0.stdout)
        p0_stderr_path = _dump("p0_stderr.txt", r0.stderr)
        p1_prompt_path = _dump("p1_prompt.txt", p1)
        p1_stdout_path = _dump("p1_stdout.txt", r1.stdout)
        p1_stderr_path = _dump("p1_stderr.txt", r1.stderr)
        p2_prompt_path = _dump("p2_prompt.txt", p2)
        p2_stdout_path = _dump("p2_stdout.txt", r2.stdout)
        p2_stderr_path = _dump("p2_stderr.txt", r2.stderr)

        self.logger.info(f"[planning] codex artifacts saved under: {log_dir}")
        self.logger.info(f"[planning] P0 stdout: {p0_stdout_path}")
        self.logger.info(f"[planning] P1 stdout: {p1_stdout_path}")
        self.logger.info(f"[planning] P2 stdout: {p2_stdout_path}")

        raw_json = self._extract_json_object(r2.stdout)
        if not raw_json:
            raise RuntimeError("codex p2 output has no json object")
        obj = json.loads(raw_json)

        return {
            "schema_version": "planning_codex_v1",
            "codex_model": self.codex_client.settings.model,
            "sandbox": self.codex_client.settings.sandbox,
            "workspace_root": self.project_root,
            "log_dir": str(log_dir),
            "prompt_hash": hashlib.sha256((p0 + "\n\n" + p1 + "\n\n" + p2).encode("utf-8")).hexdigest(),
            "started_at": started,
            "finished_at": time.time(),
            "p0": {"returncode": r0.returncode, "stdout_path": p0_stdout_path, "stderr_path": p0_stderr_path, "prompt_path": p0_prompt_path},
            "p1": {"returncode": r1.returncode, "stdout_path": p1_stdout_path, "stderr_path": p1_stderr_path, "prompt_path": p1_prompt_path},
            "p2": {"returncode": r2.returncode, "stdout_path": p2_stdout_path, "stderr_path": p2_stderr_path, "prompt_path": p2_prompt_path},
            "parsed": obj,
        }

    def process_for_common_project_mode(self, max_depth: int = 5) -> Dict[str, Any]:
        # 兼容旧接口：忽略 max_depth
        return self.do_planning()

    def do_planning(self) -> Dict[str, Any]:
        project_id = getattr(self.project_audit, "project_id", "") or self.taskmgr.project_id

        # 两步制：stage1 正向抽取 (P0/P1/P2)；stage2 coverage repair；finalize 再统一落库（Fi×rule_keys）
        planning_record = self._run_codex_planning()
        parsed = planning_record.get("parsed") or {}
        flows: List[Dict[str, Any]] = parsed.get("flows") or []

        # 可选：限制首轮 flow 数（调试用）
        max_flows_env = (os.getenv("PLANNING_MAX_FLOWS") or "").strip()
        if max_flows_env:
            try:
                n = int(max_flows_env)
                if n > 0:
                    flows = flows[:n]
            except Exception:
                pass

        # stage2: coverage repair（内存保存 function list；不落库）
        target_coverage = float(os.getenv("PLANNING_TARGET_COVERAGE", "0.90") or "0.90")
        max_rounds = self._safe_int_env("PLANNING_COVERAGE_MAX_ROUNDS", 6)
        batch_size = self._safe_int_env("PLANNING_COVERAGE_BATCH_SIZE", 200)
        target_new_flows = self._safe_int_env("PLANNING_COVERAGE_TARGET_NEW_FLOWS", 3)

        log_dir = Path(planning_record.get("log_dir") or "logs")

        covered, uncovered = self._coverage_sets_from_flows(flows)
        coverage = (len(covered) / max(len(self._func_map.keys()), 1)) if self._func_map else 1.0
        self.logger.info(f"[planning] stage1 coverage={coverage:.4f}, covered={len(covered)}, uncovered={len(uncovered)}")

        rounds = 0
        repair_records: List[Dict[str, Any]] = []
        while coverage < target_coverage and uncovered and rounds < max_rounds:
            rounds += 1
            # 更粗：每轮只做 1 个 batch，目标产出少量长 flow
            batch = sorted(list(uncovered))[:batch_size]
            existing_flow_ids = [str(f.get("flow_id") or "").strip() for f in flows]
            existing_group_ids = [str(g.get("group_id") or "").strip() for g in (parsed.get("groups") or [])]
            next_flow_id = self._next_id("F", existing_flow_ids, start_at=1)
            next_group_id = self._next_id("G", existing_group_ids, start_at=1)

            rec = self._run_codex_coverage_repair(
                log_dir=log_dir,
                flows=flows,
                uncovered_batch=batch,
                next_group_id=next_group_id,
                next_flow_id=next_flow_id,
                target_new_flows=target_new_flows,
            )
            repair_records.append(rec)
            obj = rec.get("parsed") or {}
            new_flows = obj.get("new_flows") or []
            if not isinstance(new_flows, list) or not new_flows:
                self.logger.warning("[planning] coverage repair produced no new_flows; stop")
                break

            # 合并：只新增，不修正旧 flow
            for nf in new_flows:
                if not isinstance(nf, dict):
                    continue
                fid = (nf.get("flow_id") or "").strip()
                fnm = (nf.get("flow_name") or "").strip()
                refs = nf.get("function_refs") or []
                if not fid or not isinstance(refs, list) or not refs:
                    continue
                flows.append(
                    {
                        "flow_id": fid,
                        "flow_name": fnm,
                        "group_ids": nf.get("group_ids") or [],
                        "function_refs": [str(x).strip() for x in refs if str(x).strip()],
                    }
                )

            covered, uncovered = self._coverage_sets_from_flows(flows)
            coverage = (len(covered) / max(len(self._func_map.keys()), 1)) if self._func_map else 1.0
            self.logger.info(f"[planning] stage2 round={rounds}, coverage={coverage:.4f}, covered={len(covered)}, uncovered={len(uncovered)}")

        # finalize: 统一落库（Fi×rule_keys）
        if os.getenv("PLANNING_CLEAR_EXISTING", "true").lower() == "true":
            self.taskmgr.delete_tasks_by_project_id(project_id)

        checklist_pairs = self._get_checklist_rule_keys()
        if not checklist_pairs:
            raise RuntimeError("no checklist rule_keys found from VulPromptCommon")

        created = 0
        skipped = 0

        mapping_log: List[Dict[str, Any]] = []
        for flow in flows:
            flow_id = (flow.get("flow_id") or "").strip()
            flow_name = (flow.get("flow_name") or "").strip()
            function_refs = flow.get("function_refs") or []
            if not flow_id or not isinstance(function_refs, list) or not function_refs:
                skipped += 1
                continue

            cleaned_refs = [str(x).strip() for x in function_refs if str(x).strip()]
            code, missing, interface_refs = self._build_business_flow_code(cleaned_refs)

            if not code.strip():
                skipped += 1
                mapping_log.append(
                    {
                        "flow_id": flow_id,
                        "flow_name": flow_name,
                        "status": "skipped_no_match",
                        "missing": missing,
                        "interface_refs": interface_refs,
                        "function_refs": cleaned_refs,
                    }
                )
                continue

            mapping_log.append(
                {
                    "flow_id": flow_id,
                    "flow_name": flow_name,
                    "status": "partial_missing" if missing else "ok",
                    "missing": missing,
                    "interface_refs": interface_refs,
                    "function_refs": cleaned_refs,
                }
            )

            # 每个 Fi 对每个 rule_key 生成一条任务（Fi × rule_keys）
            for rule_key, rule_list in checklist_pairs:
                meta = {
                    "schema_version": "business_flow_code_v1",
                    "project_id": project_id,
                    "flow_id": flow_id,
                    "flow_name": flow_name,
                    "group_ids": flow.get("group_ids") or [],
                    "function_refs": cleaned_refs,
                    "missing_function_refs": missing,
                    "interface_refs": interface_refs,
                    "planning_source": "planning_codex_v2_two_step",
                    "planning_record": {
                        "planning": planning_record,
                        "coverage_target": target_coverage,
                        "coverage_final": coverage,
                        "repair_rounds": rounds,
                        "repair_records": repair_records,
                    },
                    "rule_key": rule_key,
                }

                project_task = Project_Task(
                    project_id=project_id,
                    name=f"Fi:{flow_id} {flow_name} [{rule_key}]".strip(),
                    content="",
                    rule=json.dumps(rule_list, ensure_ascii=False),
                    rule_key=rule_key,
                    result="",
                    contract_code="",
                    start_line="",
                    end_line="",
                    relative_file_path="",
                    absolute_file_path="",
                    recommendation="",
                    business_flow_code=code,
                    scan_record=json.dumps(meta, ensure_ascii=False),
                    short_result="",
                    group=flow_id,
                )
                self.taskmgr.save_task(project_task)
                created += 1

        # dump mapping log（用于排查对齐问题）
        try:
            if log_dir:
                p = Path(log_dir) / "tree_sitter_mapping.json"
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(mapping_log, f, ensure_ascii=False, indent=2)
                self.logger.info(f"[planning] tree-sitter mapping log saved: {p}")
        except Exception as e:
            self.logger.warning(f"[planning] dump mapping log failed: {e}")

        return {
            "success": True,
            "project_id": project_id,
            "flows_total": len(flows),
            "rule_keys_total": len(checklist_pairs),
            "tasks_created": created,
            "tasks_skipped": skipped,
            "coverage_target": target_coverage,
            "coverage_final": coverage,
            "repair_rounds": rounds,
        }
    