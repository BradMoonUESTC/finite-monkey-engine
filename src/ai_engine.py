import os
from typing import List

from planning.planning import Planning
from reasoning import VulnerabilityScanner
from validating.finding_checker import FindingVulnerabilityChecker
from codex_service import CodexClient


class AiEngine(object):
    """
    重构后的AI引擎，整合漏洞扫描和漏洞检查功能
    
    主要功能：
    - 漏洞扫描：通过 VulnerabilityScanner 执行
    - 漏洞检查：通过 VulnerabilityChecker 执行
    - 计划处理：执行项目分析计划
    """

    def __init__(self, planning: Planning, taskmgr, lancedb, lance_table_name, project_audit, codex_client=None):
        """
        初始化AI引擎
        
        Args:
            planning: 计划处理器
            taskmgr: 任务管理器
            lancedb: 向量数据库
            lance_table_name: 数据库表名
            project_audit: 项目审计信息
        """
        self.planning = planning
        self.project_taskmgr = taskmgr
        self.lancedb = lancedb
        self.lance_table_name = lance_table_name
        self.project_audit = project_audit
        
        # CodexClient：统一配置对象（planning/reasoning/validation 可复用）
        self.codex_client = codex_client or CodexClient()

        # 初始化扫描和检查模块
        self.vulnerability_scanner = VulnerabilityScanner(project_audit, codex_client=self.codex_client)
        # 新版：验证只针对 project_finding
        self.finding_checker = FindingVulnerabilityChecker(project_audit, getattr(taskmgr, 'engine', None), codex_client=self.codex_client)

    def do_planning(self):
        """执行项目分析计划"""
        return self.planning.do_planning()
    
    def do_scan(self, is_gpt4=False, filter_func=None):
        """执行漏洞扫描"""
        return self.vulnerability_scanner.do_scan(self.project_taskmgr, is_gpt4, filter_func)

    def check_function_vul(self):
        """执行漏洞检查"""
        return self.finding_checker.check_findings()


if __name__ == "__main__":
    pass 


if __name__ == "__main__":
    pass 