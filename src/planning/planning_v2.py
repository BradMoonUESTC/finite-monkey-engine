# planning.py
import random
import os
from tqdm import tqdm
from dao.entity import Project_Task
from prompt_factory.prompt_assembler import PromptAssembler

class PlanningV2(object):
    def __init__(self, project, taskmgr) -> None:
        self.project = project
        self.taskmgr = taskmgr

    def do_planning(self):
        print("Begin do planning...")
        tasks = self.taskmgr.get_task_list_by_id(self.project.project_id)
        if len(tasks) > 0:
            return

        # Group functions by contract
        contracts = {}
        for function in self.project.functions_to_check:
            contract_name = function['contract_name']
            if contract_name not in contracts:
                contracts[contract_name] = {
                    'contract_code': function['contract_code'],
                    'relative_file_path': function['relative_file_path'],
                    'absolute_file_path': function['absolute_file_path']
                }

        # Create tasks for each contract and prompt
        for contract_name, contract_info in tqdm(contracts.items(), desc="Creating tasks for contracts"):
            prompts = PromptAssembler.assemble_prompt(contract_info['contract_code'])
            
            # Create a task for each prompt
            for i, prompt_data in enumerate(prompts):
                task = Project_Task(
                    project_id=self.project.project_id,
                    name=contract_name,
                    content=prompt_data["prompt"],  # Use the prompt as content
                    keyword=str(random.random()),
                    business_type='',
                    sub_business_type='',
                    function_type='',
                    rule='',
                    result='',
                    result_gpt4='',
                    score='',
                    category='',
                    contract_code=contract_info['contract_code'],
                    risklevel='',
                    similarity_with_rule='',
                    description='',
                    start_line=0,
                    end_line=0,
                    relative_file_path=contract_info['relative_file_path'],
                    absolute_file_path=contract_info['absolute_file_path'],
                    recommendation='',
                    title=prompt_data["title"],  # Use the title from prompt data
                    business_flow_code='',
                    business_flow_lines='',
                    business_flow_context='',
                    if_business_flow_scan=0
                )
                self.taskmgr.add_task_in_one(task)