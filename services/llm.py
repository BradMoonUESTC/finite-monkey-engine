from httpx import AsyncClient
from openai import AsyncOpenAI
from models.schemas import LogCtxData

from openai import AsyncOpenAI
from httpx import AsyncClient
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.agent import Agent
from pydantic_ai.result import RunResult
from typing import Optional
from rich.console import Console
class LLMClientv1:
    def __init__(self):
        self.http_client = AsyncClient()
        self.client = AsyncOpenAI(
            base_url="http://127.0.0.1:11434/v1",
            api_key="k",
            http_client=self.http_client
        )
    
    async def translate(self, text: str, direction: str) -> str:
        prompt = f"Translate this text to {direction}: {text}"
        response = await self.client.chat.completions.create(
            model="towerinstruct",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content


class OpenAIModel:
    """Wrapper for OpenAI client with custom config"""
    def __init__(self, model: str, api_key: str, base_url: str, http_client: AsyncClient):
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            http_client=http_client
        )
        self.model = model

class LLMClient:
    def __init__(self):
        self.http = AsyncClient()
        self.ingress = OpenAIModel(
            "hf.co/mradermacher/TowerInstruct-WMT24-Chat-7B-i1-GGUF:Q4_K_M",
            api_key="k",
            base_url="http://127.0.0.1:11434/v1",
            http_client=self.http
        )
        self.egress = OpenAIModel(
            "hf.co/mradermacher/TowerInstruct-WMT24-Chat-7B-i1-GGUF:Q4_K_M",
            api_key="k",
            base_url="http://127.0.0.1:11434/v1",
            http_client=self.http
        )