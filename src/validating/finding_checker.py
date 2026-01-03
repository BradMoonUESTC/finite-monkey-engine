from typing import Any, Dict
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from dao.finding_mgr import ProjectFindingMgr
from dao.entity import Project_Finding
from .processors.analysis_processor import AnalysisProcessor


class _FindingTaskAdapter:
    """
    让现有 AnalysisProcessor 复用在 finding 上的适配器。
    AnalysisProcessor 期望的关键字段/方法：
    - task.id
    - task.result
    - task.business_flow_code
    - task.rule_key
    - task.name
    - task.content
    - task.scan_record (str)
    - task.set_short_result(str)
    - task.get_short_result()
    """

    def __init__(self, finding: Project_Finding):
        self.id = finding.id
        self.result = finding.finding_json  # 单漏洞 JSON 作为“漏洞描述”
        self.business_flow_code = finding.task_business_flow_code or ""
        self.rule_key = finding.rule_key or ""
        self.name = finding.task_name or ""
        self.content = finding.task_content or ""

        # 复用字段名：scan_record 保存 validation 过程
        self.scan_record = finding.validation_record or ""

        # 复用字段名：short_result 保存 validation 结论（yes/no/not_sure）
        self.short_result = finding.validation_status or ""

    def set_short_result(self, short_result: str):
        self.short_result = short_result

    def get_short_result(self):
        return None if self.short_result == '' else self.short_result


class _FindingManagerAdapter:
    """给 AnalysisProcessor 提供 save_task 接口，将结果写回 finding 表。"""

    def __init__(self, finding_mgr: ProjectFindingMgr):
        self.finding_mgr = finding_mgr

    def save_task(self, task_like: _FindingTaskAdapter, **kwargs):
        # AnalysisProcessor 在失败路径可能不设置 short_result，这里将其收敛为 not_sure，避免无限重复验证
        status = (getattr(task_like, 'short_result', '') or '').strip()
        if status == "":
            status = "not_sure"

        record = getattr(task_like, 'scan_record', '') or ''
        self.finding_mgr.update_validation(task_like.id, status, record)


class FindingVulnerabilityChecker:
    """
    新版 Validation：只对 project_finding 进行验证。
    """

    def __init__(self, project_audit, db_engine):
        self.project_audit = project_audit
        self.db_engine = db_engine

        self.context_data: Dict[str, Any] = {
            'functions': project_audit.functions,
            'functions_to_check': project_audit.functions_to_check,
            'call_trees': project_audit.call_trees,
            'project_id': project_audit.project_id,
            'project_path': project_audit.project_path,
            'project_audit': project_audit,
        }

        self.analysis_processor = AnalysisProcessor(self.context_data)

    def check_findings(self):
        project_id = self.project_audit.project_id
        finding_mgr = ProjectFindingMgr(project_id, self.db_engine)
        findings = finding_mgr.get_findings_for_validation()

        # 过滤掉已逻辑删除的 finding
        findings = [f for f in findings if (getattr(f, 'dedup_status', '') or '') != 'delete']

        print(f"📊 Finding验证统计: project={project_id}, 待验证数量={len(findings)}")
        if not findings:
            return []

        max_threads = int(os.getenv("MAX_THREADS_OF_CONFIRMATION", 5))
        mgr_adapter = _FindingManagerAdapter(finding_mgr)

        def process_one(finding: Project_Finding):
            adapter = _FindingTaskAdapter(finding)
            # 若已经有非 pending 的状态则跳过
            status = (finding.validation_status or '').strip()
            if status not in ("", "pending"):
                return
            self.analysis_processor.process_task_analysis(adapter, mgr_adapter)

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(process_one, f) for f in findings]
            with tqdm(total=len(futures), desc="Validating findings") as pbar:
                for fut in as_completed(futures):
                    fut.result()
                    pbar.update(1)

        return findings


