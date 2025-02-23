from dataclasses import dataclass
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from trace import logging
@dataclass
class RunContext:
    console: Console
    live: Live

    def update_markdown(self, text: str):
        # Update the live display with new Markdown content
        self.live.update(Markdown(text))
        logging.log("[RunContext] Updated Markdown output.")
