from dataclasses import dataclass
from typing import Protocol, Any

class TranslationClient(Protocol):
    async def translate(self, text: str, direction: str) -> str: ...

@dataclass
class TranslationProcessor:
    client: TranslationClient
    cache: Any
    
    async def process(self, text: str) -> tuple[str, str]:
        # Implementation using injected dependencies
        if cached := self.cache.get(text):
            return cached
        
        direction = await self.detect_language(text)
        result = await self.client.translate(text, direction)
        self.cache.set(text, result)
        return (text, result) if direction == "EN->CN" else (result, text)
    
    async def detect_language(self, text: str) -> str:
        return "EN->CN" if any(ord(c) > 127 for c in text) else "CN->EN"
