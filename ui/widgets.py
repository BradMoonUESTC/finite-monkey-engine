from typing import Any, Union
from rich.text import Text
from textual.widgets import ProgressBar, DataTable, Switch
from textual.reactive import reactive

# class BilingualTable(DataTable):
#     def __init__(self, title: str):
#         super().__init__(zebra_stripes=True)
#         self.border_title = title
#         self.add_column("Content")
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
        # border: solid yellow;
    }
    """

    def on_mount(self) -> None:
        # Start animation with slight delay to ensure CSS loads
        self.call_later(lambda: self.animate("_animation_progress", 1.0, duration=1.5, on_complete=self.on_mount))
        self.set_interval(0.05, self.update)

    def updte_animation_progress(self, progress: float)  -> None:
        self.progress = int(progress * 100)
# python
# python
class TranslationToggle(Switch):
    def __init__(self, value: bool = False):
        super().__init__(value)
        self.label = "🌐 TRANSLATE ON" if value else "🌐 TRANSLATE OFF"
    
    def on_change(self, event: Switch.Changed):
        self.label = "🌐 TRANSLATE ON" if event.value else "🌐 TRANSLATE OFF"
        
        
        

# class TranslationToggle(Switch):
#     def __init__(self):
#         super().__init__("🌐 TRANSLATE OFF")
        
#     def on_change(self, event: Switch.Changed):
#         self.label = "🌐 TRANSLATE ON" if event.value else "🌐 TRANSLATE OFF"
    
class BilingualTable(DataTable):
    STYLES = {
        "EN": ("bold #1F618D", "▷"),
        "CN": ("bold #C0392B", "◁")
    }

    def __init__(self, title: str, lang: str):
        super().__init__(zebra_stripes=True, cursor_type="row")
        self.border_title = f"{self.STYLES[lang][1]} {title}"
        self.lang = lang
        self.add_columns("Content")
    def add_row(self, *cells: Any, height: int = 1, key: str = "", label: Union[str, Text] = "") -> Any:
    #def add_row(self, *cells: Any, height: int = 1, key: str = "", label: str = "") -> Any:
        return super().add_row(*cells, height=height, key=key, label=label)
        #color, _ = self.STYLES[self.lang]
        #styled = f"[{color}]{text}[/]"
        #super().add_row(styled)