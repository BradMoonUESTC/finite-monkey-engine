import asyncio
import os
from sqlalchemy import create_engine,Engine
from rich.console import Console, ConsoleOptions, RenderResult
from rich.live import Live
from rich.markdown import CodeBlock, Markdown
from rich.syntax import Syntax
from rich.text import Text
import logging

from pydantic_ai import Agent
from pydantic_ai.models import KnownModelName
from pydantic_ai.models.openai import OpenAIModel

from nodes_config import nodes_config

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logger.setLevel(logging.WARN)  # Adjust as needed
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')   # Adjust as needed
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    from dataclasses import dataclass

from dao.task_mgr import ProjectTaskMgr
from codebaseQA.rag_processor import RAGProcessor
from res_processor.res_processor import ResProcessor
from project.project_audit import ProjectAudit
from planning.planning_v2 import PlanningV2
from ai_engine import AiEngine


class Project(object):
    def __init__(self, config:nodes_config) -> None:
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

    def start_project(self, dataset_path, code_path):
        self.AllFiles = False
        self.AllMySource = True
        srcs = f"{dataset_path}/{code_path}"
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
    def __init__(self, config:nodes_config, db_engine:Engine) -> None:
        self.config:nodes_config= config
        self.project:Project = Project(config)
        self.id:str = config.id
        self.path:str = self.project.path
        self.db_engine:Engine = db_engine
        self.all_files:bool = self.project.AllFiles
        self.statefile:str = f"{config.id}-funcs.json"
        self.output:str = config.output
        self.tags:list[str] = [""]
        logger.log(31,"Coontext: CallGraph")
        #self.call_graph = CallGraph(root=self.path)
        logger.log(31,"Context: ProjectAudit")
        self.project_audit = ProjectAudit(config)
        logger.log(31,"Contex: RAGProcesssor")
        self.rag_processor = RAGProcessor(config.id,audit=self.project_audit)

        self.project_taskmgr = ProjectTaskMgr(project_id=self.id, engine=self.db_engine)
        self.planning = PlanningV2(
            project=self.project_audit,
            taskmgr=self.project_taskmgr)
        self.ai_engine:AiEngine = AiEngine(self.planning, self.project_taskmgr,self.rag_processor.db,"lancedb_"+config.id,self.project_audit)



async def main():
    prettier_code_blocks()
    console = Console()
    prompt = ''
    console.log(f'Asking: {prompt}...', style='cyan')
    agent = Agent(OpenAIModel(model_name='dolphin3:8b-llama3.1-q8_0',base_url='http://127.0.0.1:11434/v1'))

    with Live('', console=console, vertical_overflow='visible') as live:
        async with agent.run_stream(prompt) as result:
            async for message in result.stream():
                live.update(Markdown(message))
    console.log(result.usage())


def prettier_code_blocks():
    """Make rich code blocks prettier and easier to copy.
    From https://github.com/samuelcolvin/aicli/blob/v0.8.0/samuelcolvin_aicli.py#L22
    """

    class SimpleCodeBlock(CodeBlock):
        def __rich_console__(
            self, console: Console, options: ConsoleOptions
        ) -> RenderResult:
            code:str = str(self.text).rstrip()
            yield Text(self.lexer_name, style='dim')
            yield Syntax(
                code,
                self.lexer_name,
                theme=self.theme,
                background_color='default',
                word_wrap=True,
            )
            yield Text(f'/{self.lexer_name}', style='dim')

    Markdown.elements['fence'] = SimpleCodeBlock


if __name__ == '__main__':
    config = nodes_config()
    config.model_dump()
    logger.log(31, "Main: Project")
    logger.log(31, "Main: create_engine")
    engine = create_engine(config.DATABASE_URL, echo=True)
    context = Context(config, engine)
    
    logger.log(31,"starting project load/parse")
    context.project_audit.parse(context.project.white_files, context.project.white_functions)
    logger.log(31,f"saving state to {context.statefile}")
    context.planning.do_planning()
    context.ai_engine.do_scan()
    context.ai_engine.check_function_vul()
    asyncio.run(main())