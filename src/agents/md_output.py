import asyncio
import threading
from typing import Any, TextIO

from httpx import AsyncClient
from rich.console import Console, ConsoleOptions, RenderResult,Group
from rich.live import Live
from rich.markdown import CodeBlock, Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.columns import Columns

from pydantic_ai.models import KnownModelName
from rich.panel import Panel
from pydantic_ai.agent import Agent, RunContext
from pydantic.dataclasses import dataclass
from pydantic_ai.models.openai import OpenAIModel
from rich.logging import RichHandler


console = Console()

    
from loguru import logger as logging
def logdata(message):
    logging.info(message)
    
class LogToMarkdown:
    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename, 'a+')

    def write(self, message):
        # Translate and log the message to Markdown
        translated_message = self.translate_to_markdown(message)
        self.file.write(translated_message)

    def flush(self):
        self.file.flush()

    @staticmethod
    def translate_to_markdown(text):
        # Simple translation logic (you can customize this part as needed)
        return text.replace('\n', '  \n') + '\n'

    def close(self):
        self.file.close()
   

@dataclass
class LogCtxData:
    txtENG: str = ""
    txtCN: str = ""
    detail: str = ""


h = AsyncClient()
oai = OpenAIModel(
    "hf.co/mradermacher/TowerInstruct-WMT24-Chat-7B-i1-GGUF:Q4_K_M",
    api_key="k",
    base_url="http://127.0.0.1:11434/v1",
    http_client=h,
)
sys_prompt = """You are a very concise and capable translation helper.
You are very good at making clear and accurate translations for technical phrases and slang into a familure and understandable phrase of the language indicated by the user.
You adapt technical jargon as best as possible and maintain clear translations.
After commencing through a translation, you do not add any exantemperanious information, only the text being evaluated is to be reflected in you're output as that is needed."""
egress_txt = Agent(
    oai,
    deps_type=LogCtxData,
    system_prompt=sys_prompt
)

ingress_txt = Agent(
    oai,
    deps_type=LogCtxData,
    system_prompt=sys_prompt
)


class LogView:
    def __init__(self):
        self.scroll_offset = 0
        self.content1 = ""
        self.content2 = ""
        self.minimized_column = None
    
    def setup_logging(self):
        ...
        # logging.basicConfig(
        #     level=logging.DEBUG,
        #     format="%(message)s",
        #     datefmt="[%X]",
        #     handlers=[RichHandler(rich_tracebacks=True)])  
            
    async def logdata(self, info: str, details: str = ""):
        lang = await self.detect_language(info)
        eng = zh = ""

        ctx = LogCtxData(txtENG=info, txtCN=info, detail=details)
        try:
            trans = await ingress_txt.run(
                deps=ctx,
                user_prompt=f"{lang}"
            )
            if lang.startswith("CN->EN"):
                eng = info
                zh = trans.data
            else:
                eng = trans.data
                zh = info
        except Exception as e:
            console.print(f"Error during translation: {e}")
            return

        self.content1 += f"{eng}\n"
        self.content2 += f"{zh}\n"

    async def detect_language(self, text: str) -> str:
        # Return EN for chinese and ZH for english as we want to know what language to translate into
        return "CN->EN: Translate the text following this sentence from Chinese (zh) to English (en) ### " if any("\u4e00" <= ch <= "\u9fff" for ch in text) else "EN->CN: Translate the text following this sentence from English (en) to Chinese (zh) ### "


    async def render(self):
        if self.minimized_column == 1:
            left_panel = Panel(Markdown(self.content1[self.scroll_offset:]), title="Chinese")
            right_panel = ""
        elif self.minimized_column == 2:
            left_panel = ""
            right_panel = Panel(Markdown(self.content2[self.scroll_offset:]), title="English")
        else:
            left_panel = Panel(Markdown(self.content1[self.scroll_offset:]), title="Chinese")
            right_panel = Panel(Markdown(self.content2[self.scroll_offset:]), title="English")
            spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            # Reconfigure logging to write debug logs to "debug.log" instead of the UI console.
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
            file_handler = logging.FileHandler("debug.log")
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            logging.getLogger().addHandler(file_handler)
            spinner = spinner_frames[int(asyncio.get_event_loop().time() * 10) % len(spinner_frames)]
            status_bar = Panel(Markdown(f"{spinner} UI Active"), style="bold green", height=1)
            renderable = Group(Columns([left_panel, right_panel]), status_bar)
            console.clear()  # Clear previous output
            console.print(renderable)
        #     return

        # columns_txt = Columns([left_panel, right_panel])
        
        
logView = LogView()

async def setup_live_console():
    prettier_code_blocks()
    console = Console()
    with Live('', console=console, vertical_overflow='visible') as live:
        async for message in egress_txt.stream():
            live.update(Markdown(message))
def prettier_code_blocks():
    class SimpleCodeBlock(CodeBlock):
        def __rich_console__(
            self, console: Console, options: ConsoleOptions
        ) -> RenderResult:
            code = str(self.text).rstrip()
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
        
def start_event_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Create a new event loop for the group of coroutines.
new_loop = asyncio.new_event_loop()

# Start the new event loop in a dedicated thread.
t = threading.Thread(target=start_event_loop, args=(new_loop,))
t.start()

# Now, schedule your coroutines on the new loop:
async def run_console_output(name):
    await setup_live_console()
    print(f"Task {name} done in isolated loop")


if __name__ == '__main__':
    asyncio.run(run_console_output("logging"))
    
    

# # Create a new event loop for the group of coroutines.
# new_loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
# # Start the new event loop in a dedicated thread.
# t = threading.Thread(target=start_event_loop, args=(new_loop,))
# t.start()

# # Now, schedule your coroutines on the new loop:
# async def run_console_output(name):
#     await setup_live_console(logView)
#     print(f"Task {name} done in isolated loop")
