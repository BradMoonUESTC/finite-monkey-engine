import os
from dataclasses import dataclass
from typing import Optional

from codex_runner import CodexCliResult
from codex_runner import codex_exec


@dataclass(frozen=True)
class CodexSettings:
    """
    Codex 通用配置（建议在 main 入口处初始化一次，后续各阶段复用同一实例）。
    """

    model: str = "gpt-5.2"
    sandbox: str = "read-only"
    ask_for_approval: str = "never"
    timeout_sec: int = 1800

    @staticmethod
    def from_env() -> "CodexSettings":
        model = (os.getenv("CODEX_MODEL") or "gpt-5.2").strip()
        sandbox = (os.getenv("CODEX_SANDBOX") or "read-only").strip()
        ask_for_approval = (os.getenv("CODEX_ASK_FOR_APPROVAL") or "never").strip()
        timeout_sec_s = (os.getenv("CODEX_TIMEOUT_SEC") or os.getenv("CODEX_VALIDATION_TIMEOUT_SEC") or "1800").strip()
        try:
            timeout_sec = int(timeout_sec_s)
        except Exception:
            timeout_sec = 1800
        return CodexSettings(model=model, sandbox=sandbox, ask_for_approval=ask_for_approval, timeout_sec=timeout_sec)


class CodexClient:
    """
    Codex 调用统一入口：
    - 在 main.py 初始化一次
    - planning/reasoning/validation 统一复用
    """

    def __init__(self, settings: Optional[CodexSettings] = None):
        self.settings = settings or CodexSettings.from_env()

    def exec(self, *, workspace_root: str, prompt: str, timeout_sec: Optional[int] = None) -> CodexCliResult:
        return codex_exec(
            workspace_root=workspace_root,
            prompt=prompt,
            model=self.settings.model,
            sandbox=self.settings.sandbox,
            ask_for_approval=self.settings.ask_for_approval,
            timeout_sec=timeout_sec if timeout_sec is not None else self.settings.timeout_sec,
        )


