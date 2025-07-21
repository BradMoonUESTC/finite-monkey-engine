import csv
from .project_parser import parse_project, BaseProjectFilter
import re
import os
from library.sgp.utilities.contract_extractor import extract_state_variables_from_code, extract_state_variables_from_code_move
from concurrent.futures import ThreadPoolExecutor, as_completed
from context.call_tree_builder import CallTreeBuilder

class ProjectAudit(object):
    def __init__(self, project_id, project_path, db_engine):
        self.project_id = project_id
        self.project_path = project_path
        self.functions = []
        self.functions_to_check = []
        self.tasks = []
        self.taskkeys = set()
        self.call_tree_builder = CallTreeBuilder()

    def print_call_tree(self, node, level=0, prefix=''):
        """打印调用树（代理到CallTreeBuilder）"""
        self.call_tree_builder.print_call_tree(node, level, prefix)

    def parse(self, white_files, white_functions):
        parser_filter = BaseProjectFilter(white_files, white_functions)
        functions, functions_to_check = parse_project(self.project_path, parser_filter)
        self.functions = functions
        self.functions_to_check = functions_to_check
        
        # 🆕 检查 huge_project 开关，如果为 true 则跳过 call tree 构建
        huge_project = eval(os.environ.get('HUGE_PROJECT', 'False'))
        if huge_project:
            print("🚀 检测到 HUGE_PROJECT=True，跳过 call tree 构建")
            self.call_trees = []  # 设置为空列表，避免后续访问出错
        else:
            # 使用CallTreeBuilder构建调用树
            self.call_trees = self.call_tree_builder.build_call_trees(functions_to_check, max_workers=1)

    def get_function_names(self):
        return set([function['name'] for function in self.functions])