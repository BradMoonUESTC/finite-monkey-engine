import argparse
import ast
import os
import time
import audit_config
from ai_engine import *
from project import ProjectAudit
from library.dataset_utils import load_dataset, Project
from planning import PlanningV2
from prompts import prompts
from sqlalchemy import create_engine
from dao import CacheManager, ProjectTaskMgr
import os
import pandas as pd
from openpyxl import Workbook,load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from codebaseQA.rag_processor import RAGProcessor
from res_processor.res_processor import ResProcessor

import dotenv
dotenv.load_dotenv()

def scan_project(project, db_engine):
    project_audit = ProjectAudit(project.id, project.path, db_engine)
    project_audit.parse(project.white_files, project.white_functions)
    
    project_taskmgr = ProjectTaskMgr(project.id, db_engine) 
    
    planning = PlanningV2(project_audit, project_taskmgr)
    engine = AiEngine(planning, project_taskmgr)
    engine.do_planning()
    engine.do_scan()

def check_function_vul(engine,lancedb,lance_table_name,project_audit):
    project_taskmgr = ProjectTaskMgr(project.id, engine)
    engine = AiEngine(None, project_taskmgr,lancedb,lance_table_name,project_audit)
    engine.check_function_vul()
    # print(result)
# main.py
def generate_excel(output_path, project_id):
    project_taskmgr = ProjectTaskMgr(project_id, engine)
    entities = project_taskmgr.query_task_by_project_id(project.id)
    
    data = []
    for entity in entities:
        data.append({
            '扫描结果': entity.result,         # 原始英文扫描结果
            '漏洞分类': entity.title,          # 漏洞分类
            '合约名称': entity.name,  # 合约名称
            '项目ID': entity.project_id,       # 项目ID
            '任务ID': entity.id               # 任务ID
        })
    
    if not data:
        print("没有数据需要处理")
        return
        
    df = pd.DataFrame(data)
    
    try:
        res_processor = ResProcessor(df)
        processed_df = res_processor.process()
        
        # Save to Excel
        processed_df.to_excel(output_path, index=False)
        print(f"Excel文件已保存至: {output_path}")
    except Exception as e:
        print(f"保存Excel文件时发生错误: {e}")
if __name__ == '__main__':

    switch_production_or_test = 'test' # prod / test

    if switch_production_or_test == 'test':
        start_time=time.time()
        db_url_from = os.environ.get("DATABASE_URL")
        engine = create_engine(db_url_from)
        
        dataset_base = "./src/dataset/agent-v1-c4"
        projects = load_dataset(dataset_base)

        project_id = 'redpacket'
        project_path = ''
        project = Project(project_id, projects[project_id])
        
        cmd = 'detect_vul'
        if cmd == 'detect_vul':
            scan_project(project, engine) # scan
        # elif cmd == 'check_vul_if_positive':
        #     check_function_vul(engine) # confirm

        end_time=time.time()
        print("Total time:",end_time-start_time)
        generate_excel("./output.xlsx",project_id)
        
        
    if switch_production_or_test == 'prod':
        # Set up command line argument parsing
        parser = argparse.ArgumentParser(description='Process input parameters for vulnerability scanning.')
        parser.add_argument('-fpath', type=str, required=True, help='Combined base path for the dataset and folder')
        parser.add_argument('-id', type=str, required=True, help='Project ID')
        # parser.add_argument('-cmd', type=str, choices=['detect', 'confirm','all'], required=True, help='Command to execute')
        parser.add_argument('-o', type=str, required=True, help='Output file path')
        # usage:
        # python main.py 
        # --fpath ../../dataset/agent-v1-c4/Archive 
        # --id Archive_aaa 
        # --cmd detect

        # Parse arguments
        args = parser.parse_args()
        print("fpath:",args.fpath)
        print("id:",args.id)
        print("cmd:",args.cmd)
        print("o:",args.o)
        # Split dataset_folder into dataset and folder
        dataset_base, folder_name = os.path.split(args.fpath)
        print("dataset_base:",dataset_base)
        print("folder_name:",folder_name)
        # Start time
        start_time = time.time()

        # Database setup
        db_url_from = os.environ.get("DATABASE_URL")
        engine = create_engine(db_url_from)

        # Load projects
        projects = load_dataset(dataset_base, args.id, folder_name)
        project = Project(args.id, projects[args.id])

        # Execute command
        # if args.cmd == 'detect':
        #     scan_project(project, engine)  # scan            
        # elif args.cmd == 'confirm':
        #     check_function_vul(engine)  # confirm
        # elif args.cmd == 'all':
        lancedb=scan_project(project, engine)  # scan
        check_function_vul(engine,lancedb)  # confirm

        end_time = time.time()
        print("Total time:", end_time -start_time)
        generate_excel(args.o,args.id)




