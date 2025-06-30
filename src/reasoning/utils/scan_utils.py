import os
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from prompt_factory.prompt_assembler import PromptAssembler
from prompt_factory.vul_prompt_common import VulPromptCommon
from openai_api.openai import ask_vul, ask_deepseek, ask_claude, cut_reasoning_content


class ScanUtils:
    """扫描相关的工具函数类"""
    
    @staticmethod
    def get_scan_prompt(code_to_be_tested: str, task, current_index: int = None) -> str:
        """根据扫描模式获取相应的提示词"""
        scan_mode = os.getenv("SCAN_MODE", "COMMON_VUL")
        
        if scan_mode == "OPTIMIZE":
            return PromptAssembler.assemble_optimize_prompt(code_to_be_tested)
        elif scan_mode == "CHECKLIST":
            print("📋Generating checklist...")
            prompt = PromptAssembler.assemble_checklists_prompt(code_to_be_tested)
            response_checklist = cut_reasoning_content(ask_deepseek(prompt))
            print("[DEBUG🐞]📋response_checklist length: ", len(response_checklist))
            print(f"[DEBUG🐞]📋response_checklist: {response_checklist[:50]}...")
            return PromptAssembler.assemble_checklists_prompt_for_scan(code_to_be_tested, response_checklist)
        elif scan_mode == "CHECKLIST_PIPELINE":
            checklist = task.description
            print(f"[DEBUG🐞]📋Using checklist from task description: {checklist[:50]}...")
            return PromptAssembler.assemble_prompt_for_checklist_pipeline(code_to_be_tested, checklist)
        elif scan_mode == "COMMON_PROJECT":
            return PromptAssembler.assemble_prompt_common(code_to_be_tested)
        elif scan_mode == "COMMON_PROJECT_FINE_GRAINED":
            # 在COMMON_PROJECT_FINE_GRAINED模式下，直接使用task.recommendation中的checklist类型
            if hasattr(task, 'recommendation') and task.recommendation:
                print(f"[DEBUG🐞]📋Using pre-set checklist type from recommendation: {task.recommendation}")
                # 根据checklist类型名称获取对应的索引
                all_checklists = VulPromptCommon.vul_prompt_common_new()
                checklist_keys = list(all_checklists.keys())
                if task.recommendation in checklist_keys:
                    checklist_index = checklist_keys.index(task.recommendation)
                    return PromptAssembler.assemble_prompt_common_fine_grained(code_to_be_tested, checklist_index)
                else:
                    print(f"[WARNING] Checklist type '{task.recommendation}' not found, using index 0")
                    return PromptAssembler.assemble_prompt_common_fine_grained(code_to_be_tested, 0)
            elif current_index is not None:
                print(f"[DEBUG🐞]📋Using prompt index {current_index} for fine-grained scan (fallback)")
                return PromptAssembler.assemble_prompt_common_fine_grained(code_to_be_tested, current_index)
            else:
                raise ValueError("Neither task.recommendation nor current_index is available for COMMON_PROJECT_FINE_GRAINED mode")
        elif scan_mode == "JUST_ASK":
            # 在JUST_ASK模式下，使用solidity_audit_agent_prompt
            if hasattr(task, 'recommendation') and task.recommendation:
                print(f"[DEBUG🐞]📋Using pre-set checklist type from recommendation for JUST_ASK: {task.recommendation}")
                # 根据checklist类型名称获取对应的checklist内容
                all_checklists = VulPromptCommon.vul_prompt_common_new()
                if task.recommendation in all_checklists:
                    checklist_content = "\n".join(all_checklists[task.recommendation])
                    return PromptAssembler.solidity_audit_agent_prompt(code_to_be_tested, checklist_content)
                else:
                    print(f"[WARNING] Checklist type '{task.recommendation}' not found for JUST_ASK mode")
                    # 使用第一个checklist作为fallback
                    first_checklist = list(all_checklists.values())[0]
                    checklist_content = "\n".join(first_checklist)
                    return PromptAssembler.solidity_audit_agent_prompt(code_to_be_tested, checklist_content)
            elif current_index is not None:
                print(f"[DEBUG🐞]📋Using prompt index {current_index} for JUST_ASK scan (fallback)")
                checklist_dict = VulPromptCommon.vul_prompt_common_new(current_index)
                if checklist_dict:
                    checklist_content = "\n".join(list(checklist_dict.values())[0])
                    return PromptAssembler.solidity_audit_agent_prompt(code_to_be_tested, checklist_content)
                else:
                    raise ValueError(f"Unable to get checklist for index {current_index} in JUST_ASK mode")
            else:
                raise ValueError("Neither task.recommendation nor current_index is available for JUST_ASK mode")
        elif scan_mode == "PURE_SCAN":
            return PromptAssembler.assemble_prompt_pure(code_to_be_tested)
        elif scan_mode == "SPECIFIC_PROJECT":
            business_type = task.recommendation
            business_type_list = business_type.split(',')
            return PromptAssembler.assemble_prompt_for_specific_project(code_to_be_tested, business_type_list)
        else:
            # 默认使用 COMMON_PROJECT
            return PromptAssembler.assemble_prompt_common(code_to_be_tested)
    
    @staticmethod
    def update_recommendation_for_fine_grained(task_manager, task_id: int, current_index: int):
        """为细粒度扫描更新推荐信息"""
        # 在新的实现中，recommendation已经在planning阶段设置好了，这里不需要再更新
        # 但为了兼容性，保留这个方法，只是不执行实际操作
        print(f"[DEBUG🐞]📋Skipping recommendation update - using pre-set recommendation from planning phase")
        pass
    
    @staticmethod
    def is_task_already_scanned(task) -> bool:
        """检查任务是否已经扫描过"""
        result = task.get_result(False)
        return result is not None and len(result) > 0 and str(result).strip() != "NOT A VUL IN RES no"
    
    @staticmethod
    def should_scan_task(task, filter_func) -> bool:
        """判断是否应该扫描该任务"""
        return filter_func is None or filter_func(task)
    
    @staticmethod
    def get_code_to_test(task):
        """获取要测试的代码"""
        business_flow_code = task.business_flow_code
        if_business_flow_scan = task.if_business_flow_scan
        function_code = task.content
        
        return business_flow_code if if_business_flow_scan == "1" else function_code
    
    @staticmethod
    def process_scan_response(response_vul: str) -> str:
        """处理扫描响应"""
        return response_vul if response_vul is not None else "no"
    
    @staticmethod
    def execute_parallel_scan(tasks: List, process_func, max_threads: int = 5):
        """执行并行扫描"""
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(process_func, task) for task in tasks]
            
            with tqdm(total=len(tasks), desc="Processing tasks") as pbar:
                for future in as_completed(futures):
                    future.result()
                    pbar.update(1)
    
    @staticmethod
    def group_tasks_by_name(tasks: List) -> Dict[str, List]:
        """按任务名称分组任务"""
        task_groups = {}
        for task in tasks:
            task_groups.setdefault(task.name, []).append(task)
        return task_groups
    
    @staticmethod
    def add_dialogue_history_to_prompt(prompt: str, dialogue_history: List[str]) -> str:
        """将对话历史添加到提示词中"""
        if dialogue_history:
            history_text = "\n\nPreviously Found Vulnerabilities:\n" + "\n".join(dialogue_history)
            prompt += history_text + "\n\nExcluding these vulnerabilities, please continue searching for other potential vulnerabilities."
        return prompt 