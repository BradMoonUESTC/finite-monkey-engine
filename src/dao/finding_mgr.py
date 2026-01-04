import sqlalchemy
from sqlalchemy.orm import sessionmaker

from dao.entity import Project_Finding


class ProjectFindingMgr(object):
    """
    Finding 管理器：管理 project_finding 表（单漏洞条目）。
    幂等写入采用方案 A：按 task_id 删除旧 findings，再插入本次全量 findings。
    """

    def __init__(self, project_id, engine) -> None:
        self.project_id = project_id
        self.engine = engine
        Project_Finding.__table__.create(engine, checkfirst=True)
        self.Session = sessionmaker(bind=engine)

    def _operate_in_session(self, func, *args, **kwargs):
        with self.Session() as session:
            return func(session, *args, **kwargs)

    def add_finding(self, finding: Project_Finding, commit=True):
        return self._operate_in_session(self._add_finding, finding, commit=commit)

    def _add_finding(self, session, finding: Project_Finding, commit=True):
        try:
            session.add(finding)
            if commit:
                session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()

    def add_findings(self, findings, commit=True):
        return self._operate_in_session(self._add_findings, findings, commit=commit)

    def _add_findings(self, session, findings, commit=True):
        try:
            session.add_all(findings)
            if commit:
                session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()

    def delete_findings_by_task_id(self, task_id: int):
        return self._operate_in_session(self._delete_findings_by_task_id, task_id)

    def _delete_findings_by_task_id(self, session, task_id: int):
        session.query(Project_Finding).filter_by(project_id=self.project_id, task_id=task_id).delete()
        session.commit()

    def query_findings_by_project_id(self, project_id: str):
        return self._operate_in_session(self._query_findings_by_project_id, project_id)

    def _query_findings_by_project_id(self, session, project_id: str):
        return session.query(Project_Finding).filter_by(project_id=project_id).all()

    def query_findings_by_task_id(self, task_id: int):
        return self._operate_in_session(self._query_findings_by_task_id, task_id)

    def _query_findings_by_task_id(self, session, task_id: int):
        return session.query(Project_Finding).filter_by(project_id=self.project_id, task_id=task_id).all()

    def update_dedup_status(self, finding_id: int, dedup_status: str):
        return self._operate_in_session(self._update_dedup_status, finding_id, dedup_status)

    def _update_dedup_status(self, session, finding_id: int, dedup_status: str):
        session.query(Project_Finding).filter_by(id=finding_id).update({Project_Finding.dedup_status: dedup_status})
        session.commit()

    def update_validation(self, finding_id: int, validation_status: str, validation_record: str = ''):
        return self._operate_in_session(self._update_validation, finding_id, validation_status, validation_record)

    def _update_validation(self, session, finding_id: int, validation_status: str, validation_record: str):
        session.query(Project_Finding).filter_by(id=finding_id).update({
            Project_Finding.validation_status: validation_status,
            Project_Finding.validation_record: validation_record
        })
        session.commit()

    def get_findings_for_dedup(self):
        """待去重：kept/pending 都可参与，这里只排除 delete。"""
        return self._operate_in_session(self._get_findings_for_dedup)

    def _get_findings_for_dedup(self, session):
        return session.query(Project_Finding).filter(
            Project_Finding.project_id == self.project_id,
            (Project_Finding.dedup_status.is_(None)) | (Project_Finding.dedup_status != 'delete')
        ).all()

    def get_findings_for_validation(self):
        """待验证：未被去重删除，且 validation_status 仍为 pending/空。"""
        return self._operate_in_session(self._get_findings_for_validation)

    def _get_findings_for_validation(self, session):
        return session.query(Project_Finding).filter(
            Project_Finding.project_id == self.project_id,
            (Project_Finding.dedup_status.is_(None)) | (Project_Finding.dedup_status != 'delete'),
            (Project_Finding.validation_status.is_(None)) | (Project_Finding.validation_status == '') | (Project_Finding.validation_status == 'pending')
        ).all()

    def get_findings_for_export(self):
        """导出：仅导出明确为漏洞的 finding（validation_status == 'vulnerability'）。"""
        return self._operate_in_session(self._get_findings_for_export)

    def _get_findings_for_export(self, session):
        return session.query(Project_Finding).filter(
            Project_Finding.project_id == self.project_id,
            (Project_Finding.dedup_status.is_(None)) | (Project_Finding.dedup_status != 'delete'),
            Project_Finding.validation_status == "vulnerability"
        ).all()


