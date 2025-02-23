from textual import work
from app import translation
from app.core import App
import asyncio 
from rich.table import Table
zh_table = Table("Translation")
en_table = Table("Source")

class IPythonConsole(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    """

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

def some_function():
    source = "Default Source"
    style_class = "default"  # Define a default style class
    en_table.add_row(f"[{style_class}]{source}")
    zh_table.add_row(f"[{style_class}]{translation}")