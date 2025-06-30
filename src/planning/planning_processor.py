import json
import random
import csv
import sys
import os.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import List, Dict
from tqdm import tqdm
from dao.entity import Project_Task
from openai_api.openai import common_ask_for_json
from prompt_factory.core_prompt import CorePrompt
from prompt_factory.vul_prompt_common import VulPromptCommon
from .business_flow_utils import BusinessFlowUtils
from .config_utils import ConfigUtils
from .business_flow_processor import BusinessFlowProcessor


class PlanningProcessor:
    """规划处理器，负责处理规划相关的复杂逻辑"""
    
    def __init__(self, project, taskmgr, checklist_generator=None):
        self.project = project
        self.taskmgr = taskmgr
        self.checklist_generator = checklist_generator
        self.business_flow_processor = BusinessFlowProcessor(project)
        # 为COMMON_PROJECT_FINE_GRAINED模式添加计数器
        self.fine_grained_counter = 0
    
    def do_planning(self):
        """执行规划的核心逻辑"""
        print("Begin do planning...")
        
        # 准备规划工作
        config = self._prepare_planning()
        if config is None:
            return  # 已有任务，直接返回
        
        # 获取所有业务流
        all_business_flow_data = self._get_business_flows_if_needed(config)
        
        # 处理每个函数
        self._process_all_functions(config, all_business_flow_data)
    
    def _prepare_planning(self) -> Dict:
        """准备规划工作"""
        # 获取扫描配置
        config = ConfigUtils.get_scan_configuration()
        
        # 检查现有任务
        tasks = self.taskmgr.get_task_list_by_id(self.project.project_id)
        if len(tasks) > 0:
            return None
        
        # 过滤测试函数
        self._filter_test_functions()
        
        return config
    
    def _filter_test_functions(self):
        """过滤掉测试函数"""
        functions_to_remove = []
        for function in self.project.functions_to_check:
            name = function['name']
            if "test" in name:
                functions_to_remove.append(function)
        
        for function in functions_to_remove:
            self.project.functions_to_check.remove(function)
    
    def _get_business_flows_if_needed(self, config: Dict) -> Dict:
        """如果需要的话获取所有业务流"""
        if config['switch_business_code']:
            all_business_flow, all_business_flow_line, all_business_flow_context = self.business_flow_processor.get_all_business_flow(
                self.project.functions_to_check
            )
            return {
                'all_business_flow': all_business_flow,
                'all_business_flow_line': all_business_flow_line,
                'all_business_flow_context': all_business_flow_context
            }
        return {}
    
    def _process_all_functions(self, config: Dict, all_business_flow_data: Dict):
        """处理所有函数"""
        for function in tqdm(self.project.functions_to_check, desc="Finding project rules"):
            self._process_single_function(function, config, all_business_flow_data)
    
    def _process_single_function(self, function: Dict, config: Dict, all_business_flow_data: Dict):
        """处理单个函数"""
        name = function['name']
        content = function['content']
        contract_code = function['contract_code']
        
        # 检查函数长度
        if len(content) < config['threshold']:
            print(f"Function code for {name} is too short for <{config['threshold']}, skipping...")
            return
        
        # 检查是否应该排除
        if ConfigUtils.should_exclude_in_planning(self.project, function['relative_file_path']):
            print(f"Excluding function {name} in planning process based on configuration")
            return
        
        contract_name = function['contract_name']
        print(f"————————Processing function: {name}————————")
        
        # 处理业务流代码
        if config['switch_business_code']:
            self._handle_business_flow_planning(
                function, config, all_business_flow_data
            )
        
        # 处理函数代码
        if config['switch_function_code']:
            self._handle_function_code_planning(function, config)
    
    def _handle_business_flow_planning(self, function: Dict, config: Dict, all_business_flow_data: Dict):
        """处理业务流规划"""
        name = function['name']
        content = function['content']
        contract_name = function['contract_name']
        
        # 获取业务流代码
        business_flow_code, line_info_list = BusinessFlowUtils.search_business_flow(
            all_business_flow_data.get('all_business_flow', {}),
            all_business_flow_data.get('all_business_flow_line', {}),
            all_business_flow_data.get('all_business_flow_context', {}),
            name.split(".")[1],
            contract_name
        )
        
        print(f"[DEBUG] 获取到的业务流代码长度: {len(business_flow_code) if business_flow_code else 0}")
        
        if business_flow_code == "not found":
            return
        
        # 生成检查清单和业务类型分析
        checklist, business_type_str = self._generate_checklist_and_analysis(
            business_flow_code, content, contract_name, is_business_flow=True
        )
        
        # 创建任务
        for i in range(config['actual_iteration_count']):
            self._create_planning_task(
                function, checklist, business_type_str, 
                str(business_flow_code), line_info_list, 
                if_business_flow_scan=1, config=config
            )
    
    def _handle_function_code_planning(self, function: Dict, config: Dict):
        """处理函数代码规划"""
        content = function['content']
        contract_name = function['contract_name']
        
        # 生成检查清单
        checklist, _ = self._generate_checklist_and_analysis(
            "", content, contract_name, is_business_flow=False
        )
        
        # 创建任务
        for i in range(config['actual_iteration_count']):
            self._create_planning_task(
                function, checklist, "", 
                "", "", 
                if_business_flow_scan=0, config=config
            )
    
    def _generate_checklist_and_analysis(
        self, 
        business_flow_code: str, 
        content: str, 
        contract_name: str, 
        is_business_flow: bool
    ) -> tuple[str, str]:
        """生成检查清单和业务类型分析"""
        checklist = ""
        business_type_str = ""
        
        if self.checklist_generator:
            print(f"\n📋 为{'业务流程' if is_business_flow else '函数代码'}生成检查清单...")
            
            # 准备代码用于检查清单生成
            code_for_checklist = f"{business_flow_code}\n{content}" if is_business_flow else content
            business_description, checklist = self.checklist_generator.generate_checklist(code_for_checklist)
            
            # 写入CSV文件
            csv_file_name = "checklist_business_code.csv" if is_business_flow else "checklist_function_code.csv"
            self._write_checklist_to_csv(
                csv_file_name, contract_name, 
                business_flow_code if is_business_flow else "", 
                content, business_description, checklist
            )
            
            print(f"✅ Checklist written to {csv_file_name}")
            print("✅ 检查清单生成完成")
            
            # 如果是业务流，进行业务类型分析
            if is_business_flow:
                business_type_str = self._analyze_business_type(business_flow_code, content)
        
        return checklist, business_type_str
    
    def _write_checklist_to_csv(
        self, 
        csv_file_path: str, 
        contract_name: str, 
        business_flow_code: str, 
        content: str, 
        business_description: str, 
        checklist: str
    ):
        """将检查清单写入CSV文件"""
        with open(csv_file_path, mode='a', newline='', encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file)
            if csv_file.tell() == 0:
                csv_writer.writerow(["contract_name", "business_flow_code", "content", "business_description", "checklist"])
            csv_writer.writerow([contract_name, business_flow_code, content, business_description, checklist])
    
    def _analyze_business_type(self, business_flow_code: str, content: str) -> str:
        """分析业务类型"""
        try:
            core_prompt = CorePrompt()
            type_check_prompt = core_prompt.type_check_prompt()
            
            formatted_prompt = type_check_prompt.format(business_flow_code + "\n" + content)
            type_response = common_ask_for_json(formatted_prompt)
            print(f"[DEBUG] Claude返回的响应: {type_response}")
            
            cleaned_response = type_response
            print(f"[DEBUG] 清理后的响应: {cleaned_response}")
            
            type_data = json.loads(cleaned_response)
            business_type = type_data.get('business_types', ['other'])
            print(f"[DEBUG] 解析出的业务类型: {business_type}")
            
            # 防御性逻辑：确保business_type是列表类型
            if not isinstance(business_type, list):
                business_type = [str(business_type)]
            
            # 处理 other 的情况
            if 'other' in business_type and len(business_type) > 1:
                business_type.remove('other')
            
            # 确保列表不为空
            if not business_type:
                business_type = ['other']
            
            business_type_str = ','.join(str(bt) for bt in business_type)
            print(f"[DEBUG] 最终的业务类型字符串: {business_type_str}")
            
            return business_type_str
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON解析失败: {str(e)}")
            return 'other'
        except Exception as e:
            print(f"[ERROR] 处理业务类型时发生错误: {str(e)}")
            return 'other'
    
    def _create_planning_task(
        self, 
        function: Dict, 
        checklist: str, 
        business_type_str: str, 
        business_flow_code: str, 
        business_flow_lines, 
        if_business_flow_scan: int,
        config: Dict = None
    ):
        """创建规划任务"""
        # 处理recommendation字段
        recommendation = business_type_str
        
        # 如果是COMMON_PROJECT_FINE_GRAINED模式，设置checklist类型到recommendation
        if config and config['scan_mode'] in ["COMMON_PROJECT_FINE_GRAINED", "JUST_ASK"]:
            # 获取当前checklist类型
            checklist_dict = VulPromptCommon.vul_prompt_common_new(self.fine_grained_counter % config['total_checklist_count'])
            if checklist_dict:
                checklist_key = list(checklist_dict.keys())[0]
                recommendation = checklist_key
                print(f"[DEBUG🐞]📋Setting recommendation to checklist key: {checklist_key} (index: {self.fine_grained_counter % config['total_checklist_count']})")
            self.fine_grained_counter += 1
        
        task = Project_Task(
            project_id=self.project.project_id,
            name=function['name'],
            content=function['content'],
            keyword=str(random.random()),
            business_type='',
            sub_business_type='',
            function_type='',
            rule='',
            result='',
            result_gpt4='',
            score='',
            category='',
            contract_code=function['contract_code'],
            risklevel='',
            similarity_with_rule='',
            description=checklist,
            start_line=function['start_line'],
            end_line=function['end_line'],
            relative_file_path=function['relative_file_path'],
            absolute_file_path=function['absolute_file_path'],
            recommendation=recommendation,
            title='',
            business_flow_code=business_flow_code,
            business_flow_lines=business_flow_lines,
            business_flow_context='',
            if_business_flow_scan=if_business_flow_scan
        )
        self.taskmgr.add_task_in_one(task) 