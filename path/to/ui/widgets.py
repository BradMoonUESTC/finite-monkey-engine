# ui/widgets.py
from textual.widgets import Switch
class TranslationToggle(Switch):
    def __init__(self, title: str = "🌐 TRANSLATE OFF"):
        super().__init__(title)
        self.border_title = title
        self.add_column("Content")  # Fixed method name

    def add_row(self, text: str):
        super().addRow(text)  # Ensure the method name matches if necessary

    def on_change(self, value: bool):
        self.label = "🌐 TRANSLATE ON" if value else "🌐 TRANSLATE OFF"