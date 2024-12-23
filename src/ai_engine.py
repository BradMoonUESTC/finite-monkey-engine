from concurrent.futures import ThreadPoolExecutor
import json
import re
import threading
import time
from typing import List
import requests
import tqdm
from sklearn.metrics.pairwise import cosine_similarity
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import warnings
import urllib3

from dao.task_mgr import ProjectTaskMgr
warnings.filterwarnings('ignore', category=urllib3.exceptions.NotOpenSSLWarning)
from dao.entity import Project_Task
from prompt_factory.prompt_assembler import PromptAssembler
from prompt_factory.core_prompt import CorePrompt
from openai_api.openai import *
class AiEngine(object):

    def __init__(self, planning, taskmgr:ProjectTaskMgr):
        # Step 1: 获取results
        self.planning = planning
        self.project_taskmgr = taskmgr
    def do_planning(self):
        self.planning.do_planning()
    def process_task_do_scan(self,task:Project_Task, filter_func = None, is_gpt4 = False):
        
        response_final = ""
        response_vul = ""
        result = task.get_result(is_gpt4)
        prompt=task.content
        title=task.title
        if result is not None and len(result) > 0:
            print("\t skipped (scanned)")
        else:
            print("\t to scan")
            response_vul=ask_claude(prompt)
            print(response_vul)
            response_vul = response_vul if response_vul is not None else ""
            breif_prompt=f"基于扫描结果，对这个结果进行一个单词的总结，判断一下这个结果的结论是否存在{title}风险，输出为json形式，如果结果为有此{title}风险，则输出为{{'risk':true}}，否则输出为{{'risk':false}}"             
            response_breif=common_ask_for_json(response_vul+breif_prompt)
            print(response_breif)
            self.project_taskmgr.update_result(task.id, response_vul, response_breif,"")
    def do_scan(self, is_gpt4=False, filter_func=None):
        # self.llm.init_conversation()

        tasks = self.project_taskmgr.get_task_list()
        if len(tasks) == 0:
            return

        # 定义线程池中的线程数量
        max_threads = 5

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(self.process_task_do_scan, task, filter_func, is_gpt4) for task in tasks]
            
            with tqdm(total=len(tasks), desc="Processing tasks") as pbar:
                for future in as_completed(futures):
                    future.result()  # 等待每个任务完成
                    pbar.update(1)  # 更新进度条

        return tasks

if __name__ == "__main__":
    pass