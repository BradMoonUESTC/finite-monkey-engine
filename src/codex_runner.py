import os
import subprocess
from dataclasses import dataclass
from typing import List
from typing import Optional


class CodexCliError(RuntimeError):
    pass


@dataclass(frozen=True)
class CodexCliResult:
    stdout: str
    stderr: str
    returncode: int


def _check_codex_available() -> None:
    try:
        r = subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=10)
    except Exception as e:
        raise CodexCliError(f"无法执行 codex：{e}") from e
    if r.returncode != 0:
        raise CodexCliError(f"codex 不可用（退出码 {r.returncode}）：{(r.stderr or r.stdout).strip()}")


def codex_exec(
    *,
    workspace_root: str,
    prompt: str,
    model: str = "gpt-5.2",
    sandbox: str = "read-only",
    ask_for_approval: str = "never",
    timeout_sec: int = 1800,
    extra_configs: Optional[List[str]] = None,
) -> CodexCliResult:
    """
    执行 `codex exec` 并返回 stdout/stderr。

    约束：
    - 通过 `--cd` 将 Codex 的可访问范围限制为 workspace_root
    - 默认 `--ask-for-approval never`，避免批处理卡住
    - 默认 `sandbox=read-only`，不允许写 workspace
    """
    workspace_root = os.path.abspath(os.path.expanduser(workspace_root))
    if not os.path.isdir(workspace_root):
        raise CodexCliError(f"workspace_root 不存在或不是目录：{workspace_root}")

    _check_codex_available()

    cmd: List[str] = [
        "codex",
        "--ask-for-approval",
        ask_for_approval,
        "exec",
        "-m",
        model,
        "-s",
        sandbox,
        "--skip-git-repo-check",
        "--cd",
        workspace_root,
    ]

    if extra_configs:
        for c in extra_configs:
            cmd.extend(["--config", c])

    cmd.append(prompt)

    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=workspace_root,
        timeout=timeout_sec,
    )
    return CodexCliResult(stdout=r.stdout or "", stderr=r.stderr or "", returncode=r.returncode)


