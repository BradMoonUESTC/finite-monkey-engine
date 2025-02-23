import asyncio
import sys
import io
from typing import Any
from textual import app, work
from textual.widgets import Input, RichLog
from textual.widgets import ProgressBar
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll, Horizontal, Container
from textual.widgets import DataTable, Switch, Static
from models.schemas import LogCtxData
from src.agents.md_output import LogView, ingress_txt
from pydantic_ai import Agent

           
from textual.widgets import Button, Sparkline
from datetime import datetime
import shelve


class TranslationFilter:
    """Translation engine integration"""
    def __init__(self):
        self.enabled = False
        self.log_ctx = LogView()
        
    async def process_line(self, text: str) -> str | tuple[str, float]:
        """Apply translation if enabled"""
        if not self.enabled:
            return text
            
        lang = await self.log_ctx.detect_language(text)
        ctx = LogCtxData(txtENG=text, txtCN=text)
        
        try:
            trans = await ingress_txt.run(
                f"{lang}",
                deps=ctx.dict()
            )
            return f"{text} → {trans.data}"
        except Exception as e:
            return f"{text} [Translation Error: {str(e)}]"

class TranslationUI(Container):
    """Bilingual output interface"""
    def compose(self) -> ComposeResult:
        # yield Horizontal(
        en_table: DataTable = DataTable()
        zh_table: DataTable = DataTable()

        yield Horizontal(
            Vertical(en_table),
            Vertical(zh_table)
        )

        # Add rows to the tables
        style_class = "quality-poor"
        source = "Hello, World!"
        translation = "你好，世界！"

        en_table.add_row(f"[{style_class}]{source}")
        zh_table.add_row(f"[{style_class}]{translation}")
        DataTable(id="output-english", zebra_stripes=True),
        DataTable(id="output-chinese", zebra_stripes=True),
        classes="translation-columns"
        # )
        
    def add_line(self, en: str, zh: str):
        self.query_one("#output-english", DataTable).add_row(en)
        self.query_one("#output-chinese", DataTable).add_row(zh)
            
class BaseWindow(app.App):
    """Main application window with composed layout"""
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1;
        grid-rows: 1fr 8fr 1fr;
    }
    
    #spinner-container {
        height: 1;
        background: $surface;
    }
    
    #main-content {
        height: 100%;
        overflow: hidden;
    }
    
    #ipython-container {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        """Declarative layout composition"""
        yield Vertical(
            Horizontal(
                ThinSpinner(show_eta=False, id="spinner"),
                id="spinner-container"
            ),
            Vertical(
                CustomRichUI(),
                id="custom-ui"
            ),
            VerticalScroll(
                RichLog(id="output-view"),
                Input(placeholder=">>> "),
                id="ipython-container"
            )
        )

class EnhancedIPythonConsole(BaseWindow):
    """IPython console with translation capabilities"""
    CSS = """
    .translation-columns {
        width: 100%;
        height: 1fr;
        grid-size: 2;
    }
    
    #translation-toggle {
        dock: top;
        height: 1;
        background: $surface;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.translation_filter = TranslationFilter()
        self.translation_ui = TranslationUI()
        self.output_queue = asyncio.Queue()

    def compose(self) -> ComposeResult:
        yield Vertical(
            Horizontal(
                Switch(id="translation-toggle"),
                Static("实时翻译", classes="toggle-label"),
                id="translation-control"
            ),
            self.translation_ui
        )
        yield from super().compose()

    async def process_output(self) -> None:
        """Handle output with translation support"""
        while not self.output_queue.empty():
            data = await self.output_queue.get()
            
            if self.translation_filter.enabled:
                translated = await self.translation_filter.process_line(data)
                en, zh = self.parse_translation(translated)
                self.translation_ui.add_line(en, zh)
            else:
                self.query_one("#output-view", RichLog).write(data)
                self.query_one("#output-view", RichLog).scroll_end(animate=False)

    def parse_translation(self, text: str) -> tuple[str, str]:
        """Split translated text into EN/CN components"""
        if "→" in text:
            parts = text.split("→", 1)
            return parts[0].strip(), parts[1].strip()
        return text, text

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle translation toggle"""
        self.translation_filter.enabled = event.value
        self.translation_ui.display = event.value
        self.refresh_layout()

    def refresh_layout(self):
        """Adjust layout based on translation state"""
        if self.translation_filter.enabled:
            self.query_one("RichLog").display = False
            self.translation_ui.display = True
        else:
            self.query_one("RichLog").display = True
            self.translation_ui.display = False
 
class EnhancedTranslationFilter(TranslationFilter):
    """Translation engine with caching and quality metrics"""
    def __init__(self):
        super().__init__()
        self.cache = shelve.open("translation_cache")
        self.quality_metrics = {}
        
    async def process_line(self, text: str) -> tuple[str, float]:
        """Return translated text with quality score (0-1)"""
        cache_key = f"{hash(text)}-{self.target_lang}"
        
        # Check cache first
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            self.quality_metrics[cache_key] = cached['quality']
            return cached['text'], cached['quality']
            
        # New translation
        start_time = datetime.now()
        try:
            ctx = LogCtxData(txtENG=text, txtCN=text)
            user_prompt = await self.log_ctx.detect_language(text)
            trans = await ingress_txt.run(user_prompt, deps=ctx.dict())
            translation = trans.data
            quality = self._calculate_quality(text, translation, start_time)
            
            # Cache results
            self.cache[cache_key] = {
                'text': translation,
                'quality': quality,
                'timestamp': datetime.now().isoformat()
            }
            return translation, quality
        except Exception as e:
            return f"[Error: {str(e)}]", 0.0

    def _calculate_quality(self, source: str, translation: str, start: datetime) -> float:
        """Calculate translation quality score (mock implementation)"""
        time_diff = (datetime.now() - start).total_seconds()
        length_factor = min(len(source) / 100, 1.0)
        return max(0.0, min(1.0 - (time_diff * 0.1), 0.9)) * length_factor

class QualityIndicator(Sparkline):
    """Visual quality indicator sparkline"""
    def __init__(self):
        super().__init__([], summary_function="max")
        self.border_title = "Quality"
        
    def update_quality(self, score: float):
        new_values = list(self.data[-9:]) + [score * 100]
        self.data = new_values[-10:]

class TranslationToggle(Button):
    """Custom toggle button with status indicators"""
    def __init__(self):
        super().__init__("🌐 TRANSLATE", id="translation-toggle")
        self.quality_indicator = QualityIndicator()
        
    def compose(self) -> ComposeResult:
        yield self.quality_indicator
        yield from super().compose()

class EnhancedTranslationUI(Container):
    """Enhanced UI with quality visualization"""
    CSS = """
    #quality-header {
        height: 3;
        border-bottom: heavy $accent;
    }
    .quality-good { color: green; }
    .quality-medium { color: yellow; }
    .quality-poor { color: red; }
    """
    
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Static("[b]English", id="en-header"),
                DataTable(id="output-english"),
                classes="column"
            ),
            Vertical(
                Static("[b]中文", id="zh-header"),
                DataTable(id="output-chinese"),
                classes="column"
            ),
            Vertical(
                Static("Quality Metrics", id="quality-header"),
                QualityIndicator(),
                classes="quality-panel"
            ),
            classes="translation-grid"
        )

    def add_translation(self, source: str, translation: str, quality: float):
        # Add to tables with quality coloring
        en_table = self.query_one("#output-english", DataTable)
        zh_table = self.query_one("#output-chinese", DataTable)
        
        style_class = (
            "quality-good" if quality > 0.7 else
            "quality-medium" if quality > 0.4 else
            "quality-poor"
        )
        en_table.add_row(f"[{style_class}]{source}")
        zh_table.add_row(f"[{style_class}]{translation}")      
        # en_table.add_row(f"[{style_class}]{source}")
        # zh_table.add_row(f"[{style_class}]{translation}")
        
        # Update quality sparkline
        self.query_one(QualityIndicator).update_quality(quality)

# class EnhancedIPythonConsole(BaseWindow):
#     """Final integrated console with all features"""
#     def compose(self) -> ComposeResult:
#         yield Horizontal(
#             TranslationToggle(),
#             Static("|"),
#             Button("Clear Cache", id="clear-cache"),
#             id="control-bar"
#         )
#         yield EnhancedTranslationUI()
#         yield super().compose()

#     async def on_button_pressed(self, event: Button.Pressed):
#         if event.button.id == "translation-toggle":
#             self.translation_filter.enabled = not self.translation_filter.enabled
#             event.button.label = "🌐 TRANSLATING" if self.translation_filter.enabled else "🌐 TRANSLATE"
#             self.refresh_layout()
#         elif event.button.id == "clear-cache":
#             self.translation_filter.cache.clear()
#             self.notify("Translation cache cleared!", severity="information")

#     async def process_output(self) -> None:
#         while not self.output_queue.empty():
#             data = await self.output_queue.get()
            
#             if self.translation_filter.enabled:
#                 translated, quality = await self.translation_filter.process_line(data)
#                 self.translation_ui.add_translation(data, translated, quality)
#             else:
#                 self.rich_log.write(data)
                
#             self.refresh_quality_display()

#     def refresh_quality_display(self):
#         """Update quality indicators based on recent metrics"""
#         if self.translation_filter.quality_metrics:
#             avg_quality = sum(self.translation_filter.quality_metrics.values()) / len(self.translation_filter.quality_metrics)
#             self.query_one(QualityIndicator).update_quality(avg_quality)

class CustomRichUI(RichLog):
    """Placeholder for custom rich UI widget"""
    pass

class ThinSpinner(ProgressBar):
    """Animated thin progress bar spinner"""
    _animation_progress = reactive(0.0)
    
    CSS = """
    ThinSpinner {
        height: 1;
        width: 100%;
        background: $surface;
        color: red;
        border: none;
        margin: 0;
    }
    
    ThinSpinner > .progress--bar {
        background: red;
        min-height: 1;
        width: 100%;
        background: $surface;
        margin: 0;
        color: red;
        border: solid yellow;
    }
    """

    def on_mount(self) -> None:
        # Start animation with slight delay to ensure CSS loads
        self.call_later(lambda: self.animate("_animation_progress", 1.0, duration=1.5, on_complete=self.on_mount))
        self.set_interval(0.05, self.update)

    def updte_animation_progress(self, progress: float)  -> None:
        self.progress = int(progress * 100)
        
   # Rest of your mount logic
class IPythonIO(io.TextIOBase):
    """Thread-safe I/O redirection for IPython"""
    def __init__(self, queue: asyncio.Queue, main_loop: asyncio.AbstractEventLoop):
        self.queue = queue
        self.main_loop = main_loop
        
    def write(self, data: str) -> int:
        asyncio.run_coroutine_threadsafe(
            self.queue.put(data),
            loop=self.main_loop
        )
        return len(data)
    
    def flush(self) -> None:
        pass

# class IPythonConsole(BaseWindow):
#     """IPython-integrated console inheriting from base window"""
#     def on_mount(self) -> None:
#         # Initialize IPython components
#         self.main_loop = asyncio.get_running_loop()
#         self.start_ipython()
#         self.set_interval(0.05, self.process_output)

#     # Keep previous IPython integration methods
#     @work(thread=True)
#     # def start_ipython(self) -> None:
    #     # Same thread setup as before
    #     ...

    # def process_output(self) -> None:
    #     # Same output handling
    #     ...

    # Rest of your IPython methods
class IPythonConsole(app.App):
    CSS = """
    Screen {
        layout: vertical;
    }
    
    Vertical {
        height: auto;
    }
    
    ThinSpinner {
        height: 1;
        margin: 0;
    }
    
    /* Rest of your CSS */
    """
    
    async def on_mount(self) -> None:
        # Mount spinner first in the layout
        await self.mount(
            ThinSpinner(show_eta=False, total=100, show_bar=True ),  # Explicit init
            CustomRichUI(),
            VerticalScroll(
                RichLog(id="output-view"),
                Input(placeholder=">>> ")
            )
        )
     

    def __init__(self):
        super().__init__()
        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        self.main_loop = None

    async def on_mount(self) -> None:
        """Initialize application components"""
        self.main_loop = asyncio.get_running_loop()
        self.rich_log = RichLog()
        self.input_widget = Input(placeholder=">>> ")
        await self.mount(self.rich_log, self.input_widget)
        self.start_ipython()
        self.set_interval(0.05, self.process_output)

    @work(thread=True)
    def start_ipython(self) -> None:
        """Launch IPython in a background thread"""
        ipy_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(ipy_loop)
        
        sys.stdin = self
        sys.stdout = IPythonIO(self.output_queue, self.main_loop)
        sys.stderr = IPythonIO(self.output_queue, self.main_loop)

        from IPython import start_ipython
        try:
            start_ipython(
                argv=[],
                user_ns=self.get_ipython_namespace(),
                display_banner=False
            )
        finally:
            sys.stdin = sys.__stdin__
            sys.stdout = sys.__stdout__

    def get_ipython_namespace(self) -> dict:
        """Provide objects accessible in IPython REPL"""
        return {
            "app": self,
            "run_async": self.run_in_main_loop,
            "fetch_data": self.sample_async_method
        }

    def run_in_main_loop(self, coro) -> Any:
        """Execute async code in main thread's event loop"""
        return asyncio.run_coroutine_threadsafe(
            coro,
            loop=self.main_loop
        ).result()

    async def sample_async_method(self) -> str:
        """Example async method callable from IPython"""
        await asyncio.sleep(1)
        return "Data fetched successfully!"

    async def process_output(self) -> None:
        """Update UI with output from IPython"""
        while not self.output_queue.empty():
            data = await self.output_queue.get()
            self.rich_log.write(data)
            self.rich_log.scroll_end(animate=False)

    def readline(self, size: int = -1) -> str:
        """Get input from queue (blocking in IPython thread)"""
        return asyncio.run_coroutine_threadsafe(
            self.input_queue.get(),
            loop=self.main_loop
        ).result()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submissions"""
        await self.input_queue.put(event.value + "\n")
        self.input_widget.clear()

if __name__ == "__main__":
    IPythonConsole().run()