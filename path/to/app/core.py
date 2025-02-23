# app/core.py
from textual import work

from services.translation import TranslationProcessor


class CoreApp:
    def __init__(self):
        self.translation_enabled = False
        self.main_loop = None
        self.translation = TranslationProcessor()  # Ensure this attribute exists

    @work(thread=True, exclusive=True)
    async def start_ipython(self):
        # Existing code remains the same
        pass

    async def _update_tables(self, ctx, target_lang):
        if self.translation_enabled:
            translated = await self.translation.translate(ctx, target_lang)
            self._update_tables()  # Ensure this method exists and is correctly named