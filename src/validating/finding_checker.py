from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from typing import Any
from typing import Dict
from typing import Optional

from tqdm import tqdm

from codex_runner import CodexCliError
from codex_service import CodexClient
from dao.entity import Project_Finding
from dao.finding_mgr import ProjectFindingMgr
from prompt_factory.validation_codex_prompt import ValidationCodexPrompt


ALLOWED_VALIDATION_STATUS = {
    "pending",
    "intended_design",
    "false_positive",
    "vulnerability",
    "vuln_high_cost",
    "vuln_low_impact",
    "not_sure",
    "error",
}


def _dataset_base_abs() -> str:
    # src/validating -> src -> src/dataset/agent-v1-c4
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "dataset", "agent-v1-c4"))


def _ensure_under_base(path: str, base: str) -> bool:
    try:
        return os.path.commonpath([os.path.abspath(path), os.path.abspath(base)]) == os.path.abspath(base)
    except Exception:
        return False


def _extract_json_object(text: str) -> Optional[str]:
    """从文本中尽量提取一个 JSON object（用于模型偶发输出杂质时兜底）。"""
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


def _project_root_from_datasets_json(*, project_id: str, dataset_base: str) -> Optional[str]:
    """
    严格对齐主流程的 project_root 计算方式：
    - project_id 来自 main.py
    - datasets.json 中查该 project_id 对应的 path
    - project_root = <dataset_base>/<path>
    """
    try:
        datasets_json = os.path.join(dataset_base, "datasets.json")
        with open(datasets_json, "r", encoding="utf-8") as f:
            dj = json.load(f)
        info = dj.get(project_id) or {}
        rel = (info.get("path") or "").strip()
        if not rel:
            return None
        return os.path.abspath(os.path.join(dataset_base, rel))
    except Exception:
        return None


def _parse_validation_result(final_text: str) -> tuple[str, Optional[Dict[str, Any]], Optional[str]]:
    raw = (final_text or "").strip()
    if not raw:
        return "not_sure", None, "empty_output"

    candidate = _extract_json_object(raw)
    if not candidate:
        return "not_sure", None, "no_json_object_found"

    try:
        obj = json.loads(candidate)
    except Exception as e:
        return "not_sure", None, f"json_parse_error: {e}"

    status = (obj.get("status") or "").strip()
    if status not in ALLOWED_VALIDATION_STATUS:
        # 兼容：prompt 允许的 status 不含 error，但我们解析允许 error；若模型输出未知值，落 not_sure
        return "not_sure", obj, f"invalid_status: {status}"

    # 统一：将 error/status 以外的异常交由调用方处理；这里不抛异常
    return status, obj, None


class FindingVulnerabilityChecker:
    """
    新版 Validation：只对 project_finding 进行验证。
    """

    def __init__(self, project_audit, db_engine, codex_client: Optional[CodexClient] = None):
        self.project_audit = project_audit
        self.db_engine = db_engine
        self.codex_client = codex_client or CodexClient()

    def check_findings(self):
        project_id = self.project_audit.project_id
        finding_mgr = ProjectFindingMgr(project_id, self.db_engine)
        findings = finding_mgr.get_findings_for_validation()

        # 过滤掉已逻辑删除的 finding
        findings = [f for f in findings if (getattr(f, 'dedup_status', '') or '') != 'delete']

        print(f"📊 Finding验证统计: project={project_id}, 待验证数量={len(findings)}")
        if not findings:
            return []

        # 测试/灰度开关：限制本次最多验证多少条 finding（默认不限制）
        max_findings_env = (os.getenv("CODEX_VALIDATION_MAX_FINDINGS") or "").strip()
        if max_findings_env:
            try:
                max_n = int(max_findings_env)
                if max_n > 0:
                    findings = findings[:max_n]
            except Exception:
                pass

        max_threads = int(os.getenv("MAX_THREADS_OF_CONFIRMATION", 3))
        timeout_sec = int(os.getenv("CODEX_VALIDATION_TIMEOUT_SEC", "1800"))

        # 受控目录：必须限定在主扫描目录（agent-v1-c4 下的具体项目目录）
        dataset_base = _dataset_base_abs()
        project_root = _project_root_from_datasets_json(project_id=project_id, dataset_base=dataset_base)

        # fallback：若 datasets.json 缺失/不包含该 project_id，则回退到 project_audit.project_path（但仍需在 base 下）
        if not project_root:
            project_root = os.path.abspath(os.path.expanduser(getattr(self.project_audit, "project_path", "") or ""))

        if not project_root or not os.path.isdir(project_root):
            # 无法确定项目根目录：直接将所有 finding 标记 error，避免卡死
            err = f"invalid project_root: {project_root}"
            for f in findings:
                finding_mgr.update_validation(f.id, "error", json.dumps({"schema_version": "validation_codex_v1", "error": err}, ensure_ascii=False))
            return findings

        if not _ensure_under_base(project_root, dataset_base):
            err = f"project_root not under dataset_base. project_root={project_root}, dataset_base={dataset_base}"
            for f in findings:
                finding_mgr.update_validation(f.id, "error", json.dumps({"schema_version": "validation_codex_v1", "error": err}, ensure_ascii=False))
            return findings

        def process_one(finding: Project_Finding):
            status = (finding.validation_status or '').strip()
            if status not in ("", "pending"):
                return

            started = time.time()
            hint_file = (finding.task_relative_file_path or "").strip()
            hint_function = (finding.task_name or "").strip()
            rule_key = (finding.rule_key or "").strip()
            finding_json = (finding.finding_json or "").strip()

            prompt = ValidationCodexPrompt.build_validation_prompt(
                finding_json=finding_json, rule_key=rule_key, hint_file=hint_file, hint_function=hint_function
            )
            prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

            record: Dict[str, Any] = {
                "schema_version": "validation_codex_v1",
                "codex_model": self.codex_client.settings.model,
                "sandbox": self.codex_client.settings.sandbox,
                "workspace_root": project_root,
                "prompt_hash": prompt_hash,
                "started_at": started,
            }

            try:
                res = self.codex_client.exec(workspace_root=project_root, prompt=prompt, timeout_sec=timeout_sec)
                record["returncode"] = res.returncode
                record["stdout"] = res.stdout
                record["stderr"] = res.stderr

                if res.returncode != 0:
                    record["error"] = "codex_returncode_nonzero"
                    record["finished_at"] = time.time()
                    record["duration_ms"] = int((record["finished_at"] - started) * 1000)
                    finding_mgr.update_validation(finding.id, "error", json.dumps(record, ensure_ascii=False))
                    return

                parsed_status, parsed_obj, parse_error = _parse_validation_result(res.stdout)
                record["parsed"] = parsed_obj
                record["parse_error"] = parse_error

                record["finished_at"] = time.time()
                record["duration_ms"] = int((record["finished_at"] - started) * 1000)
                finding_mgr.update_validation(finding.id, parsed_status, json.dumps(record, ensure_ascii=False))

            except subprocess.TimeoutExpired as e:
                record["error"] = f"timeout: {e}"
                record["finished_at"] = time.time()
                record["duration_ms"] = int((record["finished_at"] - started) * 1000)
                finding_mgr.update_validation(finding.id, "error", json.dumps(record, ensure_ascii=False))
            except CodexCliError as e:
                record["error"] = f"codex_cli_error: {e}"
                record["finished_at"] = time.time()
                record["duration_ms"] = int((record["finished_at"] - started) * 1000)
                finding_mgr.update_validation(finding.id, "error", json.dumps(record, ensure_ascii=False))
            except Exception as e:
                record["error"] = f"unexpected_error: {e}"
                record["finished_at"] = time.time()
                record["duration_ms"] = int((record["finished_at"] - started) * 1000)
                finding_mgr.update_validation(finding.id, "error", json.dumps(record, ensure_ascii=False))

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(process_one, f) for f in findings]
            with tqdm(total=len(futures), desc="Validating findings") as pbar:
                for fut in as_completed(futures):
                    fut.result()
                    pbar.update(1)

        return findings


