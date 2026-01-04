import os

from sqlalchemy import create_engine

from codex_service import CodexClient
from validating.finding_checker import FindingVulnerabilityChecker


class _MinimalProjectAudit:
    def __init__(self, project_id: str, project_path: str):
        self.project_id = project_id
        self.project_path = project_path


def main() -> int:
    # 与 src/main.py 保持一致的 DB 取值逻辑
    db_url_from = os.environ.get("DATABASE_URL") or "postgresql://postgres:1234@127.0.0.1:5432/postgres"
    engine = create_engine(db_url_from)

    # 你指定的测试目标
    project_id = os.getenv("TEST_PROJECT_ID", "dca5555")

    # 主扫描目录（严格对齐主流程）：project_id -> datasets.json[path] -> dataset_base/path
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_base = os.path.abspath(os.path.join(repo_root, "src", "dataset", "agent-v1-c4"))
    datasets_json = os.path.join(dataset_base, "datasets.json")
    with open(datasets_json, "r", encoding="utf-8") as f:
        dj = __import__("json").load(f)
    rel = (dj.get(project_id) or {}).get("path") or ""
    project_root = os.path.abspath(os.path.join(dataset_base, rel))

    audit = _MinimalProjectAudit(project_id=project_id, project_path=project_root)

    codex_client = CodexClient()
    checker = FindingVulnerabilityChecker(audit, engine, codex_client=codex_client)
    checker.check_findings()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


