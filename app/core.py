from textual import work
from textual.app import App
from textual.widgets import Footer, Header
from models.schemas import LogCtxData
from ui.widgets import ThinSpinner, BilingualTable, TranslationToggle
import asyncio
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Input
import asyncio
import sys
import io
from textual import app, work
from textual.widgets import Input, RichLog
from textual.widgets import ProgressBar
from textual.reactive import reactive
#from rich.layout import VerticalScroll
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll, Horizontal


from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Switch, Static
from textual import work, on
from textual.reactive import var
from app.translation import TranslationService


class CoreApp(App):
    CSS = """
    #main-content {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        height: 1fr;
    }
    """
    translation_enabled = var(True)  # Enabled by default

    async def on_mount(self):
        self.main_loop = asyncio.get_running_loop()
        self.start_ipython()

    @work(thread=True, exclusive=True)
    def start_ipython(self):
        """Start IPython in background thread"""
        import sys
        from IPython import start_ipython
        
        class IPythonWrapper:
            def __init__(self, app):
                self.app = app
                
            def write(self, data):
                asyncio.run_coroutine_threadsafe(
                    self.app.post_output(data),
                    loop=self.app.main_loop
                )
            def flush(self):
                pass
                
            def isatty(self):
                return False  # Crucial fix for prompt_toolkit integration
                
            def fileno(self):
                return -1  # Indicate no real file descriptor

            
        sys.stdout = IPythonWrapper(self)
        start_ipython(argv=[], user_ns={
            "app": self,
            "toggle_translation": self.toggle_translation
        })

    async def post_output(self, data: str):
        """Handle output from IPython thread"""
        if self.translation_enabled:
            # Add translation logic here
            self.query_one(BilingualTable).add_row(data)
        else:
            self.query_one(BilingualTable).add_row(data)
        self.refresh()

    def action_quit(self):
        self.exit()

    def toggle_translation(self, enabled: bool):
        """Toggle translation mode from IPython"""
        self.translation_enabled = enabled
        self.notify(f"Translation {'enabled' if enabled else 'disabled'}")

    CSS = """
    #main-content {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        height: 1fr;
    }
    """
    translation_enabled = var(True)  # Enabled by default

    def compose(self):
        # Top controls
        yield Horizontal(
            ThinSpinner(),
            TranslationToggle(value=True),  # Toggle enabled by default
            id="spinner-container"
        )
        
        # Main content - side by side tables
        yield Horizontal(
            BilingualTable("English", lang="EN"),
            BilingualTable("中文", lang="CN"),
            id="main-content"
        )
        
        # Input at bottom
        yield Horizontal(
            Input(placeholder="Input text/commands >>> "),
            id="input-container"
        )

    async def process_output(self, data: str):
        """Process all output with bidirectional translation"""
        try:
            # Detect input language
            is_english = self._is_english(data)
            source_lang = "EN" if is_english else "CN"
            target_lang = "CN" if is_english else "EN"
            
            # Create translation context
            ctx = LogCtxData(
                txtENG=data if is_english else "",
                txtCN=data if not is_english else "",
                detail="Auto-translation"
            )
            
            # Always show original + translation when enabled
            if self.translation_enabled:
                translated = await self.translation.translate(ctx, target_lang)
                self._update_tables(
                    source_text=data,
                    translated_text=translated,
                    source_lang=source_lang
                )
            else:
                self._update_single_table(data, source_lang)
                
        except Exception as e:
            self.log_error(f"Translation error: {str(e)}")

    def _update_tables(self, source_text: str, translated_text: str, source_lang: str):
        """Update both tables with original and translation"""
        en_table = self.query_one("#english-table")
        zh_table = self.query_one("#chinese-table")
        
        if source_lang == "EN":
            en_table.add_row(source_text)
            zh_table.add_row(translated_text)
        else:
            zh_table.add_row(source_text)
            en_table.add_row(translated_text)

    def _update_single_table(self, text: str, source_lang: str):
        """Update only the relevant table when translation off"""
        table = self.query_one("#english-table" if source_lang == "EN" else "#chinese-table")
        table.add_row(text)

    @on(Input.Submitted)
    async def handle_input(self, event: Input.Submitted):
        """Handle user input with immediate translation"""
        input_text = event.value
        if input_text:
            await self.process_output(input_text)
            event.input.clear()