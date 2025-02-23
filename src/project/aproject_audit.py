import csv
from typing import Any, Dict, Optional, Tuple, Union, List, Set
from os import path
import asyncio
from nodes_config import nodes_config
from library.parsing.callgraph import CallGraph
from .aproject_parser import parse_project_async,ABaseProjectFilter
import re
from library.sgp.utilities.contract_extractor import extract_state_variables_from_code, extract_state_variables_from_code_move

__all__ = ('ProjectAudit')

class AProjectAudit(object):
    def __init__(self, config: nodes_config) -> None:
        self.config: nodes_config = config
        self.project_id: str = config.id
        self.project_path: str = config.base_dir
        self.cg = CallGraph(root=path.join(config.base_dir, config.src_dir))
        
        self.functions_to_check: list = []
        self.functions: list = []
        self.tasks: list = []
        self.taskkeys: set = set()

    async def analyze_function_relationships(self, functions_to_check: List[Dict]) -> Tuple[Dict[str, Dict[str, Set]], Dict[str, Dict]]:
        # Construct a mapping and calling relationship dictionary from function name to function information
        func_map = {}
        relationships = {'upstream': {}, 'downstream': {}}
        for idx, func in enumerate(functions_to_check):
            func_name = func['name'].split('.')[-1]
            func['func_name'] = func_name
            func_map[func_name] = {
                'index': idx,
                'data': func
            }
        
        # Analyze the calling relationship of each function
        for idx, func in enumerate(functions_to_check):
            func_name = func['name'].split('.')[-1]
            content = func['content'].lower()
            
            if func_name not in relationships['upstream']:
                relationships['upstream'][func_name] = set()
            if func_name not in relationships['downstream']:
                relationships['downstream'][func_name] = set()
            
            # Check whether other functions call the current function
            for other_func in functions_to_check:
                if other_func == func:
                    continue
                other_name = other_func['name'].split('.')[-1]
                other_content = other_func['content'].lower()
                
                # If other functions call the current function
                if re.search(r'\b' + re.escape(func_name.lower()) + r'\b', other_content):
                    relationships['upstream'][func_name].add(other_name)
                    if other_name not in relationships['downstream']:
                        relationships['downstream'][other_name] = set()
                    relationships['downstream'][other_name].add(func_name)
                
                # If the current function calls other functions
                if re.search(r'\b' + re.escape(other_name.lower()) + r'\b', content):
                    relationships['downstream'][func_name].add(other_name)
                    if other_name not in relationships['upstream']:
                        relationships['upstream'][other_name] = set()
                    relationships['upstream'][other_name].add(func_name)
        
        return relationships, func_map

    async def build_call_tree(self, func_name: str, relationships: Dict[str, Dict[str, Set]], direction: str, func_map: Dict[str, Dict], visited: Optional[Set[str]] = None) -> Optional[Dict[str, Any]]:
        if visited is None:
            visited = set()
        
        if func_name in visited:
            return None
        
        visited.add(func_name)
        
        # 获取函数完整信息
        func_info = func_map.get(func_name, {'index': -1, 'data': None})
        node = {
            'name': func_name,
            'index': func_info['index'],
            'function_data': func_info['data'],  # 包含完整的函数信息
            'children': []
        }
        
        # 获取该方向上的所有直接调用
        related_funcs = relationships[direction].get(func_name, set())
        
        # 递归构建每个相关函数的调用树
        for related_func in related_funcs:
            child_tree: Optional[Dict[str, Any]] = await self.build_call_tree(related_func, relationships, direction, func_map, visited.copy())
            if child_tree:
                node['children'].append(child_tree)
        
        return node

    def print_call_tree(self, node: Dict[str, Any], level: int = 0, prefix: str = ''):
        if not node:
            return
        
        # 打印当前节点的基本信息
        func_data = node['function_data']
        if func_data:
            print(f"{prefix}{'└─' if level > 0 else ''}{node['name']} (index: {node['index']}, "
                  f"lines: {func_data['start_line']}-{func_data['end_line']})")
        else:
            print(f"{prefix}{'└─' if level > 0 else ''}{node['name']} (index: {node['index']})")
        
        # 打印子节点
        for i, child in enumerate(node['children']):
            is_last = i == len(node['children']) - 1
            new_prefix = prefix + (' ' if level == 0 else '│ ' if not is_last else ' ')
            self.print_call_tree(child, level + 1, new_prefix + ('└─' if is_last else '├─'))

    async def parse(self, white_files: List[str], white_functions: List[str]) -> None:
        parser_filter = ABaseProjectFilter(white_files, white_functions)
        functions, functions_to_check = await parse_project_async(self.project_path, parser_filter)
        self.functions = functions
        self.functions_to_check = functions_to_check
        
        relationships: Dict[str, Dict]
        func_map: Dict
        
        # 分析函数关系
        relationships, func_map = await self.analyze_function_relationships(functions_to_check)
        
        # 为每个函数构建并打印调用树
        call_trees: List[Dict] = []
        for func in functions_to_check:
            func_name = func['name'].split('.')[-1]
            
            upstream_tree = await self.build_call_tree(func_name, relationships, 'upstream', func_map)
            downstream_tree = await self.build_call_tree(func_name, relationships, 'downstream', func_map)
            
            state_variables: List[str] = []
            if func['relative_file_path'].endswith('.move'):
                state_variables = extract_state_variables_from_code_move(func['contract_code'], func['relative_file_path'])
            if func['relative_file_path'].endswith('.sol') or func['relative_file_path'].endswith('.fr'):
                state_variables = extract_state_variables_from_code(func['contract_code'])
            
            state_variables_text = '\n'.join(state_variables) if state_variables else ''
            call_trees.append({
                'function': func_name,
                'upstream_tree': upstream_tree,
                'downstream_tree': downstream_tree,
                'state_variables': state_variables_text
            })
        
        self.call_trees: List[Dict] = call_trees

    def get_function_names(self) -> Set[str]:
        return set([function['name'] for function in self.functions])