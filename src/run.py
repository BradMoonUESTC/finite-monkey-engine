import asyncio
from functools import partial
from getpass import getpass
import os
from contextlib import redirect_stdout, redirect_stderr
from typing import Optional
from httpx import AsyncClient
from openai import AsyncOpenAI
from rich.console import Console
from rich.live import Live
from pydantic_ai import Agent, RunContext
from nodes_config import nodes_config, Settings
from main_pipeline import DynamicGovernor, governed_task, main_pipeline

from tracing import logger as logging  # Import the logger from the logView module
from agents.md_output import LogToMarkdown, logView
from dataclasses import dataclass
from sqlalchemy.ext.asyncio.engine import create_async_engine, AsyncEngine
from dao.atask_mgr import AProjectTaskMgr
from codebaseQA.arag_processor import ARAGProcessor
from res_processor.ares_processor import AResProcessor
from project.aproject_audit import AProjectAudit
from planning.aplanning_v2 import APlanningV2
from ai_engine import AiEngine

import asyncio


logger = logging.opt(colors=True)

# Global configurations
cfg = nodes_config()

console = Console()



class Project:
    def __init__(self, config: nodes_config) -> None:
        self.id = config.id
        self.output = config.output
        self.path = config.base_dir
        self.project = self.start_project(dataset_path=config.base_dir, code_path=config.src_dir)
        self.functions: list[str] = []
        self.white_files = self.project["files"]
        self.white_functions = self.project.get("functions", [])
        self.files = self.project["files"]

    def __repr__(self) -> str:
        return f"Project(id={self.id}, path={self.path})"

    def start_project(self, dataset_path:str, code_path:str):
        self.AllFiles = False
        self.AllMySource = True
        srcs: str = f"{dataset_path}/{code_path}"
        return {
            "path": code_path,
            "files": [
                os.path.relpath(os.path.join(root, file), dataset_path)
                for root, _, files in os.walk(srcs)
                for file in files
                if file.endswith(".sol")
            ],
            "functions": [],
            "base_path": dataset_path,
            "AllFiles": False,
            "AllMySource": True,
        }


@dataclass
class Context:
    def __init__(self, config: nodes_config, db_engine: AsyncEngine) -> None:
        self.config: nodes_config = config
        self.project: Project = Project(config)
        self.id: str = config.id
        self.path: str = self.project.path
        self.db_engine: AsyncEngine = db_engine
        self.all_files: bool = self.project.AllFiles
        self.statefile: str = f"{config.id}-funcs.json"
        self.output: str = config.output
        self.tags: list[str] = [""]
        logger.log(31, "Context: CallGraph")
        # self.call_graph = CallGraph(root=self.path)
        logger.log(31, "Context: ProjectAudit")
        self.project_audit = AProjectAudit(config)
        self.aproject_audit = AProjectAudit(config)

        logger.log(31, "Contex: RAGProcesssor")
        self.rag_processor = ARAGProcessor(config.id, audit=self.project_audit)

        self.project_taskmgr = AProjectTaskMgr(self.id, self.db_engine)
        self.planning = APlanningV2(
            self.project_audit,
            self.project_taskmgr
        )
        self.ai_engine: AiEngine = AiEngine(self.planning, self.project_taskmgr, self.rag_processor.db, "lancedb_" + config.id, self.project_audit)

    # classes with complicated startups need to be in a secondary init routine since init is sync
    # and these have nothing todo with the pipeline
    async def startup(self):
        logger.log(31, "Contex: RAGProcesssor")
        self.rag_processor = ARAGProcessor(self.config.id, audit=self.project_audit)
        if await self.rag_processor.table_exists() and await self.rag_processor.acheck_data_count(len(self.project_audit.functions_to_check)):
            print(f"Table {self.rag_processor.table_name} already exists with correct data count. Skipping processing.")
        else:
            self.rag_processor._create_database(self.project_audit.functions_to_check)

        self.project_taskmgr = AProjectTaskMgr(self.id, self.db_engine)
        self.planning = APlanningV2(
            self.project_audit,
            self.project_taskmgr
        )
        self.ai_engine: AiEngine = AiEngine(self.planning, self.project_taskmgr, self.rag_processor.db, "lancedb_" + self.config.id, self.project_audit)


hx = AsyncClient(base_url="http://127.0.0.1:11434/api")
client = AsyncOpenAI(http_client=hx)

async def integrated_pipeline():
    await logView.logdata("test startup logging")

    config = nodes_config()
    engine: AsyncEngine = create_async_engine(config.settings.ASYNC_DB_URL, echo=True)
    context = Context(config, engine)

    with Live("", console=console, vertical_overflow="visible") as live:
        await asyncio.to_thread(context.project_audit.parse, context.project.white_files, context.project.white_functions)
        async for stage_callable in context.planning.do_planning():
            result = await stage_callable()
            print("Orchestrator received planning stage result:", result)

    while True:
        await logView.logdata("The pipeline has completed execution.")
        await asyncio.sleep(-1)


async def integrated_pipeline():
    await logView.logdata("test startup logging")

    config = nodes_config()
    engine: AsyncEngine = create_async_engine(config.ASYNC_DB_URL, echo=True)
    context = Context(config, engine)

    with Live("", console=console, vertical_overflow="visible") as live:
        await asyncio.to_thread(context.project_audit.parse, context.project.white_files, context.project.white_functions)
        async for stage_callable in context.planning.do_planning():
            result = await stage_callable()
            print("Orchestrator received planning stage result:", result)

    while True:
        await logView.logdata("What time is it???")
        await asyncio.sleep(1)

async def gather_tasks():
    governor = DynamicGovernor(initial_limit=5, window_size=10)
    ...
    # Simulate a list of tasks with varying delays
    # tasks = [governed_task(simulated_task, governor, i, delay)
            #  for i, delay in enumerate([0.5, 0.7, 1.2, 0.9, 0.6, 0.8, 1.5, 0.4, 0.3, 1.0, 0.5, 0.9])]
    
    # results = await asyncio.gather(*tasks)
    # print("Results:", results)


async def async_input(prompt: str, /, *, hide: Optional[bool] = None) -> str:
    """Asynchronous equivalent of `input()` function.
    Arguments:
        prompt (`str`): A prompt message to be displayed.
    Keyword Arguments:
        hide (`bool`, optional): If `True`, the input text will be hidden.
    Returns:
        `str`: The input text.
    """
    #with ThreadPoolExecutor(1) as executor:
    #wrapped_input = partial(getpass if hide else input, prompt)
    #    with ThreadPoolExecutor(1) as executor:
    wrapped_input = partial(getpass if hide else input, prompt)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, wrapped_input)

async def setup_live_console(logView):
    await logView.logdata("Setting up live console...")
    md_logger = LogToMarkdown('output.md')
    with redirect_stdout(md_logger), redirect_stderr(md_logger):
        await integrated_pipeline()

async def main():
    await setup_live_console(logView=logView)

    

# async def main():
#     # Set up the Markdown logger
#     md_logger = LogToMarkdown('output.md')
    
#     with redirect_stdout(md_logger), redirect_stderr(md_logger):
#         setup_logging()  # Ensure logging is set up before running the pipeline
#         await integrated_pipeline()


async def main():
    await setup_live_console(logView=logView)
     # Set up the Markdown logger
#    await integrated_pipeline()

if __name__ == "__main__":
    logView.setup_logging()
    asyncio.run(main())