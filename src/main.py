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
    log_data_info(logger, "调用树", len(project_audit.call_trees))
    log_data_info(logger, "调用图", len(project_audit.call_graphs))
    
    # 1.5 初始化RAG处理器（可选）
    log_step(logger, "初始化RAG处理器")
    rag_processor = None
    try:
        from context.rag_processor import RAGProcessor
        rag_start = time.time()
        
        # 传递project_audit对象，包含functions, functions_to_check, chunks
        rag_processor = RAGProcessor(
            project_audit, 
            "./src/codebaseQA/lancedb", 
            project.id
        )
        
        rag_duration = time.time() - rag_start
        log_success(logger, "RAG处理器初始化完成", f"耗时: {rag_duration:.2f}秒")
        log_data_info(logger, "基于tree-sitter解析的函数构建RAG", len(project_audit.functions_to_check))
        log_data_info(logger, "基于文档分块构建RAG", len(project_audit.chunks))
        log_data_info(logger, "使用调用树构建关系型RAG", len(project_audit.call_trees))
        log_data_info(logger, "集成调用图(Call Graph)", len(project_audit.call_graphs))
        
        # 显示 call graph 统计信息
        if project_audit.call_graphs:
            call_graph_stats = project_audit.get_call_graph_statistics()
            log_data_info(logger, "Call Graph统计", call_graph_stats)
        
    except ImportError as e:
        log_warning(logger, "RAG处理器不可用，将使用简化功能")
        print(e)
        logger.debug(f"ImportError详情: {e}")
    except Exception as e:
        log_error(logger, "RAG处理器初始化失败", e)
        rag_processor = None
    

    
    # 2. planning & scanning - 直接使用project_audit
    log_step(logger, "创建任务管理器")
    project_taskmgr = ProjectTaskMgr(project.id, db_engine) 
    log_success(logger, "任务管理器创建完成")
    
    # 创建规划处理器，直接传递project_audit
    log_step(logger, "创建规划处理器")
    planning = Planning(project_audit, project_taskmgr)
    log_success(logger, "规划处理器创建完成")
    
    # 如果有RAG处理器，初始化planning的RAG功能
    if rag_processor:
        log_step(logger, "初始化规划器的RAG功能")
        planning.initialize_rag_processor("./src/codebaseQA/lancedb", project.id)
        log_success(logger, "规划器RAG功能初始化完成")
    
    # 创建AI引擎
    log_step(logger, "创建AI引擎")
    lancedb_table = rag_processor.db if rag_processor else None
    lancedb_table_name = rag_processor.table_name if rag_processor else f"lancedb_{project.id}"
    logger.info(f"LanceDB表名: {lancedb_table_name}")
    
    engine = AiEngine(planning, project_taskmgr, lancedb_table, lancedb_table_name, project_audit)
    log_success(logger, "AI引擎创建完成")
    
    # 执行规划和扫描
    log_step(logger, "执行项目规划")
    planning_start = time.time()
    engine.do_planning()
    planning_duration = time.time() - planning_start
    log_success(logger, "项目规划完成", f"耗时: {planning_duration:.2f}秒")
    
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
    checker = FindingVulnerabilityChecker(project_audit, engine)
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
        project_id = 'dca5555'  # 使用存在的项目ID
        project_path = ''
        main_logger.info(f"目标项目ID: {project_id}")
        project = Project(project_id, projects[project_id])
        log_success(main_logger, "项目对象创建完成")
        
        # 检查扫描模式
        scan_mode = os.getenv("SCAN_MODE","SPECIFIC_PROJECT")
        main_logger.info(f"扫描模式: {scan_mode}")
        
        cmd = 'detect_vul'
        main_logger.info(f"执行命令: {cmd}")
        
        if cmd == 'detect_vul':
            # 执行项目扫描
            lancedb,lance_table_name,project_audit=scan_project(project, engine) # scan
            
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