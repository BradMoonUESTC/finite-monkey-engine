import argparse
import ast
import os
import sys
import time
from ai_engine import *
from tree_sitter_parsing import TreeSitterProjectAudit as ProjectAudit
from dataset_manager import load_dataset, Project
from planning.planning import Planning
from sqlalchemy import create_engine
from dao import CacheManager, ProjectTaskMgr
import os
import pandas as pd
from openpyxl import Workbook,load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from res_processor.res_processor import ResProcessor

import dotenv
# 优先加载默认 .env（如果存在），并额外加载 src/.env（你提供的环境文件位置）
dotenv.load_dotenv()
dotenv.load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=False)

# 添加日志系统
from logging_config import setup_logging, get_logger, log_section_start, log_section_end, log_step, log_error, log_warning, log_success, log_data_info



def scan_project(project, db_engine):
    logger = get_logger("scan_project")
    scan_start_time = time.time()
    
    log_section_start(logger, "项目扫描", f"项目ID: {project.id}, 路径: {project.path}")
    
    # 1. parsing projects  
    log_step(logger, "Tree-sitter解析项目", f"项目路径: {project.path}")
    parsing_start = time.time()
    
    project_audit = ProjectAudit(project.id, project.path, db_engine)
    project_audit.parse()
    
    parsing_duration = time.time() - parsing_start
    log_success(logger, "项目解析完成", f"耗时: {parsing_duration:.2f}秒")
    log_data_info(logger, "解析的函数", len(project_audit.functions_to_check))
    # 新版 planning 不再需要调用树/调用图
    
    # 新版 planning：删除 RAG 相关逻辑（不再初始化向量库/文档分块）
    

    
    # 2. planning & scanning - 直接使用project_audit
    log_step(logger, "创建任务管理器")
    project_taskmgr = ProjectTaskMgr(project.id, db_engine) 
    log_success(logger, "任务管理器创建完成")
    
    # Codex 通用对象：建议在入口创建一次并向下传递（planning/reasoning/validation 可复用同一配置）
    from codex_service import CodexClient
    codex_client = CodexClient()

    # 创建规划处理器，直接传递project_audit
    log_step(logger, "创建规划处理器")
    planning = Planning(project_audit, project_taskmgr, codex_client=codex_client)
    log_success(logger, "规划处理器创建完成")
    
    # 新版 planning：无 RAG 初始化
    
    # 创建AI引擎
    log_step(logger, "创建AI引擎")
    lancedb_table = None
    lancedb_table_name = ""
    engine = AiEngine(planning, project_taskmgr, lancedb_table, lancedb_table_name, project_audit, codex_client=codex_client)
    log_success(logger, "AI引擎创建完成")
    
    # 执行规划和扫描
    log_step(logger, "执行项目规划")
    planning_start = time.time()
    planning_res = engine.do_planning()
    planning_duration = time.time() - planning_start
    log_success(logger, "项目规划完成", f"耗时: {planning_duration:.2f}秒")
    if isinstance(planning_res, dict):
        cov = planning_res.get("coverage_final")
        flows_total = planning_res.get("flows_total")
        rule_keys_total = planning_res.get("rule_keys_total")
        tasks_created = planning_res.get("tasks_created")
        logger.info(f"[planning_result] coverage_final={cov}, flows_total={flows_total}, rule_keys_total={rule_keys_total}, tasks_created={tasks_created}")

    # 运行到 planning 后提前停止（用于“正经 main.py 流程”调试）
    if os.getenv("STOP_AFTER_PLANNING", "false").lower() == "true":
        log_warning(logger, "STOP_AFTER_PLANNING=true，已完成 planning，将在 reasoning 前停止")
        total_scan_duration = time.time() - scan_start_time
        log_section_end(logger, "项目扫描", total_scan_duration)
        return lancedb_table, lancedb_table_name, project_audit
    
    log_step(logger, "执行漏洞扫描(Reasoning)")
    scan_start = time.time()
    engine.do_scan()
    scan_duration = time.time() - scan_start
    log_success(logger, "漏洞扫描(Reasoning)完成", f"耗时: {scan_duration:.2f}秒")
    
    # 在reasoning完成后，validation开始前进行去重
    log_step(logger, "Reasoning后去重处理")
    dedup_start = time.time()
    ResProcessor.perform_post_reasoning_deduplication(project.id, db_engine, logger)
    dedup_duration = time.time() - dedup_start
    log_success(logger, "Reasoning后去重处理完成", f"耗时: {dedup_duration:.2f}秒")
    
    total_scan_duration = time.time() - scan_start_time
    log_section_end(logger, "项目扫描", total_scan_duration)

    return lancedb_table, lancedb_table_name, project_audit


def plan_project(project, db_engine):
    """
    仅执行 planning（用于调试 business flow planning，避免跑 reasoning/validation）。
    """
    logger = get_logger("plan_project")
    start_time = time.time()
    log_section_start(logger, "仅Planning", f"项目ID: {project.id}, 路径: {project.path}")

    log_step(logger, "Tree-sitter解析项目", f"项目路径: {project.path}")
    project_audit = ProjectAudit(project.id, project.path, db_engine)
    project_audit.parse()
    log_success(logger, "项目解析完成", f"待检查函数数: {len(project_audit.functions_to_check)}")

    log_step(logger, "创建任务管理器")
    project_taskmgr = ProjectTaskMgr(project.id, db_engine)

    # Codex 通用对象：入口处统一创建一次并向下传递
    from codex_service import CodexClient
    codex_client = CodexClient()

    log_step(logger, "执行Planning（Codex业务流抽取）")
    planning = Planning(project_audit, project_taskmgr, codex_client=codex_client)
    res = planning.do_planning()
    log_success(logger, "Planning完成", f"result={res}")

    log_section_end(logger, "仅Planning", time.time() - start_time)
    return res

def check_function_vul(engine, lancedb, lance_table_name, project_audit):
    """执行漏洞检查（新版：只验证 project_finding 表），直接使用project_audit数据"""
    logger = get_logger("check_function_vul")
    check_start_time = time.time()
    
    log_section_start(logger, "漏洞验证", f"项目ID: {project_audit.project_id}")
    
    log_step(logger, "创建项目任务管理器")
    project_taskmgr = ProjectTaskMgr(project_audit.project_id, engine)
    log_success(logger, "项目任务管理器创建完成")
    
    # 新版：只对 finding 表执行验证
    log_step(logger, "初始化Finding漏洞检查器")
    from validating.finding_checker import FindingVulnerabilityChecker
    # Codex 通用对象：入口处统一配置一次，后续各阶段复用同一套设置
    from codex_service import CodexClient
    codex_client = CodexClient()
    checker = FindingVulnerabilityChecker(project_audit, engine, codex_client=codex_client)
    log_success(logger, "Finding漏洞检查器初始化完成")
    
    # 执行漏洞检查
    log_step(logger, "执行漏洞验证")
    validation_start = time.time()
    checker.check_findings()
    validation_duration = time.time() - validation_start
    log_success(logger, "漏洞验证完成", f"耗时: {validation_duration:.2f}秒")
    
    total_check_duration = time.time() - check_start_time
    log_section_end(logger, "漏洞验证", total_check_duration)


if __name__ == '__main__':
    # 初始化日志系统
    log_file_path = setup_logging()
    main_logger = get_logger("main")
    main_start_time = time.time()
    
    main_logger.info("🎯 程序启动参数:")
    main_logger.info(f"   Python版本: {sys.version}")
    main_logger.info(f"   工作目录: {os.getcwd()}")
    main_logger.info(f"   环境变量已加载")

    switch_production_or_test = 'test' # test / direct_excel
    main_logger.info(f"运行模式: {switch_production_or_test}")

    if switch_production_or_test == 'direct_excel':
        log_section_start(main_logger, "直接Excel生成模式")
        
        start_time = time.time()
        
        # 初始化数据库
        log_step(main_logger, "初始化数据库连接")
        db_url_from = os.environ.get("DATABASE_URL") or "postgresql://postgres:1234@127.0.0.1:5432/postgres"
        main_logger.info(f"数据库URL: {db_url_from}")
        engine = create_engine(db_url_from)
        log_success(main_logger, "数据库连接创建完成")
        
        # 设置项目参数
        project_id = 'token0902'  # 使用存在的项目ID
        main_logger.info(f"目标项目ID: {project_id}")
        
        # 直接生成Excel报告
        log_step(main_logger, "直接使用ResProcessor生成Excel报告")
        excel_start = time.time()
        ResProcessor.generate_excel("./output_direct.xlsx", project_id, engine)
        excel_duration = time.time() - excel_start
        log_success(main_logger, "Excel报告生成完成", f"耗时: {excel_duration:.2f}秒, 文件: ./output_direct.xlsx")
        
        total_duration = time.time() - start_time
        log_section_end(main_logger, "直接Excel生成模式", total_duration)
        
    elif switch_production_or_test == 'test':
        log_section_start(main_logger, "测试模式执行")
        
        start_time=time.time()
        
        # 初始化数据库
        log_step(main_logger, "初始化数据库连接")
        db_url_from = os.environ.get("DATABASE_URL") or "postgresql://postgres:1234@127.0.0.1:5432/postgres"
        main_logger.info(f"数据库URL: {db_url_from}")
        engine = create_engine(db_url_from)
        log_success(main_logger, "数据库连接创建完成")
        
        # 加载数据集
        log_step(main_logger, "加载数据集")
        dataset_base = "./src/dataset/agent-v1-c4"
        main_logger.info(f"数据集路径: {dataset_base}")
        projects = load_dataset(dataset_base)
        log_success(main_logger, "数据集加载完成", f"找到 {len(projects)} 个项目")
 
        # 设置项目参数
        project_id = 'debox6666'  # 使用存在的项目ID
        project_path = ''
        main_logger.info(f"目标项目ID: {project_id}")
        project = Project(project_id, projects[project_id])
        log_success(main_logger, "项目对象创建完成")
        
        # 检查扫描模式
        scan_mode = os.getenv("SCAN_MODE","SPECIFIC_PROJECT")
        main_logger.info(f"扫描模式: {scan_mode}")
        
        cmd = os.getenv("CMD", "detect_vul")
        main_logger.info(f"执行命令: {cmd}")
        
        if cmd == 'planning_only':
            plan_project(project, engine)
        elif cmd == 'detect_vul':
            # 执行项目扫描
            lancedb,lance_table_name,project_audit=scan_project(project, engine) # scan

            # 如果只需要跑到 planning（reasoning 前停止），此处直接退出整个 main 流程
            if os.getenv("STOP_AFTER_PLANNING", "false").lower() == "true":
                main_logger.info("STOP_AFTER_PLANNING=true：已完成 planning，跳过 reasoning/validation/导出并退出")
                sys.exit(0)
            
            # 根据扫描模式决定是否执行漏洞验证
            if scan_mode in ["COMMON_PROJECT", "PURE_SCAN", "CHECKLIST", "COMMON_PROJECT_FINE_GRAINED"]:
                main_logger.info(f"扫描模式 '{scan_mode}' 需要执行漏洞验证")
                check_function_vul(engine,lancedb,lance_table_name,project_audit) # confirm
            else:
                main_logger.info(f"扫描模式 '{scan_mode}' 跳过漏洞验证步骤")

        # 统计总执行时间
        end_time=time.time()
        total_duration = end_time-start_time
        log_success(main_logger, "所有扫描任务完成", f"总耗时: {total_duration:.2f}秒")
        
        # 生成Excel报告
        log_step(main_logger, "生成Excel报告")
        excel_start = time.time()
        ResProcessor.generate_excel("./output.xlsx", project_id, engine)
        excel_duration = time.time() - excel_start
        log_success(main_logger, "Excel报告生成完成", f"耗时: {excel_duration:.2f}秒, 文件: ./output.xlsx")
        
        log_section_end(main_logger, "测试模式执行", time.time() - main_start_time)