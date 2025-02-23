# app/ipython.py
import asyncio
import sys
from typing import Callable, Optional
from textual.widgets import Input
from textual.app import App
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
class IPythonConsole(App):
# class IPythonConsole(BaseWindow):
    """IPython-integrated console inheriting from base window"""
    def on_mount(self) -> None:
        # Initialize IPython components
        self.main_loop = asyncio.get_running_loop()
        self.start_ipython()
        self.set_interval(0.05, self.process_output)

    # Keep previous IPython integration methods
    @work(thread=True)
    def start_ipython(self) -> None:
        # Same thread setup as before
        ...

    def process_output(self) -> None:
        # Same output handling
        ...

    # Rest of your IPython methods
# class IPythonConsole(app.App):
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
     
# class IPythonConsole(app.App):
    """Textual app hosting an IPython REPL with async integration"""
    CSS = """
    RichLog {
        height: 1fr;
        overflow-y: auto;
    }
    Input {
        dock: bottom;
    }
    """

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

    def run_in_main_loop(self, coro) -> any:
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


# class IPythonIO:
#     """Thread-safe I/O redirection with proper event loop handling"""
#     def __init__(self, callback: Callable, main_loop: asyncio.AbstractEventLoop):
#         self.callback = callback
#         self.main_loop = main_loop
        
#     def write(self, data: str):
#         if data.strip():
#             # Use the main thread's event loop
#             asyncio.run_coroutine_threadsafe(
#                 self.callback(data),
#                 loop=self.main_loop
#             )
    
#     def flush(self):
#         pass

# class IPythonHost:
#     """Managed IPython integration with lifecycle control"""
#     def __init__(self, translation_callback: Callable):
#         self.translation_callback = translation_callback
#         self.main_loop: Optional[asyncio.AbstractEventLoop] = None
        
#     def start(self, main_loop: asyncio.AbstractEventLoop):
#         """Start IPython with proper loop reference"""
#         self.main_loop = main_loop
#         sys.stdout = IPythonIO(self.handle_output, main_loop)
        
#         from IPython import start_ipython
#         start_ipython(argv=[], user_ns={
#             "app": self,
#             "translate": self.translation_callback
#         })

#     async def handle_output(self, data: str):
#         """Process output through translation pipeline"""
#         try:
#             if self.main_loop and self.main_loop.is_running():
#                 await self.translation_callback(data)
#         except Exception as e:
#             print(f"Output handling error: {e}")
