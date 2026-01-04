#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from dao.task_mgr import ProjectTaskMgr
from .planning_processor import PlanningProcessor
from codex_service import CodexClient


class Planning:
    """规划处理器，负责协调各个规划组件"""
    
    def __init__(self, project_audit, taskmgr: ProjectTaskMgr, codex_client=None):
        """
        初始化规划处理器
        
        Args:
            project_audit: TreeSitterProjectAudit实例，包含解析后的项目数据
            taskmgr: 项目任务管理器
            codex_client: CodexClient（统一配置对象，planning/reasoning/validation 可复用）
        """
        self.project_audit = project_audit
        self.taskmgr = taskmgr
        
        # 初始化规划处理器，直接传递project_audit
        self.planning_processor = PlanningProcessor(project_audit, taskmgr, codex_client=codex_client or CodexClient())
        
    def do_planning(self):
        """执行规划处理"""
        return self.planning_processor.do_planning()    
    def process_for_common_project_mode(self, max_depth: int = 5):
        """处理通用项目模式"""
        return self.planning_processor.process_for_common_project_mode(max_depth)
