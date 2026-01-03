import csv

import sqlalchemy
from dao.entity import Project_Task
from sqlalchemy.orm import sessionmaker
import tqdm

class ProjectTaskMgr(object):

    def __init__(self, project_id, engine) -> None:
        self.project_id = project_id
        self.engine = engine
        Project_Task.__table__.create(engine, checkfirst = True)
        self.Session = sessionmaker(bind=engine)

    def _operate_in_session(self, func, *args, **kwargs):
        with self.Session() as session:
            return func(session, *args, **kwargs)

    def add_tasks(self, tasks):
        for task in tasks:
            self._operate_in_session(self._add_task, task)
    def add_task_in_one(self, task):
        self._operate_in_session(self._add_task, task)
    def query_task_by_project_id(self, id):
        return self._operate_in_session(self._query_task_by_project_id, id)
    def _query_task_by_project_id(self, session, id):
        return session.query(Project_Task).filter_by(project_id=id).all()
    
    def query_tasks_by_group(self, group_uuid):
        """按group UUID查询任务"""
        return self._operate_in_session(self._query_tasks_by_group, group_uuid)
    def _query_tasks_by_group(self, session, group_uuid):
        return session.query(Project_Task).filter_by(project_id=self.project_id, group=group_uuid).all()
    
    def query_tasks_with_results_by_group(self, group_uuid):
        """查询同组中已有结果的任务"""
        return self._operate_in_session(self._query_tasks_with_results_by_group, group_uuid)
    def _query_tasks_with_results_by_group(self, session, group_uuid):
        """查询同组中已有result且不为空的任务"""
        return session.query(Project_Task).filter(
            Project_Task.project_id == self.project_id,
            Project_Task.group == group_uuid,
            Project_Task.result.isnot(None),
            Project_Task.result != ''
        ).all()
    # update_score方法已删除，因为score字段不再存在
    # update_business_flow_context方法已删除，因为business_flow_context字段不再存在
    def save_task(self, task: Project_Task, **kwargs):
        """保存Project_Task实例到数据库"""
        self._operate_in_session(self._add_task, task, **kwargs)
    
    def add_task(self, name, content, rule, rule_key='', result='', contract_code='', start_line='', end_line='', relative_file_path='', absolute_file_path='', recommendation='', business_flow_code='', scan_record='', short_result='', group='', **kwargs):
        """使用V3版本的参数创建任务"""
        task = Project_Task(self.project_id, name, content, rule, rule_key, result, contract_code, start_line, end_line, relative_file_path, absolute_file_path, recommendation, business_flow_code, scan_record, short_result, group)
        self._operate_in_session(self._add_task, task, **kwargs)

    def _add_task(self, session, task, commit=True):
        try:
            key = task.get_key()
            # ts = session.query(Project_Task).filter_by(project_id=self.project_id, key=key).all()
            # if len(ts) == 0:
            session.add(task)
            if commit:
                res=session.commit()
        except sqlalchemy.exc.IntegrityError as e:
            # 如果违反唯一性约束，则回滚事务
            session.rollback()

    def get_task_list(self):
        return self._operate_in_session(self._get_task_list)

    def _get_task_list(self, session):
        return list(session.query(Project_Task).filter_by(project_id=self.project_id).all())
    def get_task_list_by_id(self, id):
        return self._operate_in_session(self._get_task_list_by_id, id)
    def _get_task_list_by_id(self, session, id):
        return list(session.query(Project_Task).filter_by(project_id=id).all())
    def update_result(self, id, result):
        self._operate_in_session(self._update_result, id, result)

    def _update_result(self, session, id, result):
        session.query(Project_Task).filter_by(id=id).update({Project_Task.result: result})
        session.commit()
    # update_similarity_generated_referenced_score方法已删除，因为similarity_with_rule字段不再存在
    # update_category方法已删除，因为category字段不再存在
    # update_description方法已删除，因为description字段不再存在

    def update_recommendation(self, id, recommendation):
        self._operate_in_session(self._update_recommendation, id, recommendation)
    def _update_recommendation(self, session, id, recommendation):
        session.query(Project_Task).filter_by(id=id).update({Project_Task.recommendation: recommendation})
        session.commit()
    
    def update_rule_key(self, id, rule_key):
        """更新任务的rule_key"""
        self._operate_in_session(self._update_rule_key, id, rule_key)
    def _update_rule_key(self, session, id, rule_key):
        session.query(Project_Task).filter_by(id=id).update({Project_Task.rule_key: rule_key})
        session.commit()
    
    def update_scan_record(self, id, scan_record):
        """更新任务的scan_record"""
        self._operate_in_session(self._update_scan_record, id, scan_record)
    def _update_scan_record(self, session, id, scan_record):
        session.query(Project_Task).filter_by(id=id).update({Project_Task.scan_record: scan_record})
        session.commit()
    
    def update_short_result(self, id, short_result):
        """更新任务的short_result"""
        self._operate_in_session(self._update_short_result, id, short_result)
    def _update_short_result(self, session, id, short_result):
        session.query(Project_Task).filter_by(id=id).update({Project_Task.short_result: short_result})
        session.commit()
    
    def delete_task_by_id(self, id):
        """根据ID删除任务记录"""
        return self._operate_in_session(self._delete_task_by_id, id)
    def _delete_task_by_id(self, session, id):
        """执行删除操作的内部方法"""
        try:
            # 查找要删除的记录
            task = session.query(Project_Task).filter_by(id=id).first()
            if task:
                session.delete(task)
                session.commit()
                return True
            else:
                return False
        except Exception as e:
            session.rollback()
            raise e
    # update_title方法已删除，因为title字段不再存在
        
    def import_file(self, filename):
        reader = csv.DictReader(open(filename, 'r', encoding='utf-8'))

        processed = 0
        for row in tqdm.tqdm(list(reader), "import tasks"):
            self.add_task(**row, commit=False)
            processed += 1
            if processed % 10 == 0:
                self._operate_in_session(lambda s: s.commit())
        self._operate_in_session(lambda s: s.commit())

    
    def dump_file(self, filename):
        writer = self.get_writer(filename)

        def write_rows(session):
            ts = session.query(Project_Task).filter_by(project_id=self.project_id).all()
            for row in ts:
                writer.writerow(row.as_dict())

        self._operate_in_session(write_rows)
        del writer
    def get_writer(self, filename):
        file = open(filename, 'w', newline='', encoding='utf-8')
        writer = csv.DictWriter(file, fieldnames=Project_Task.fieldNames)
        writer.writeheader()  # write header
        return writer

    def merge_results(self, function_rules):
        # merge_results方法需要根据新的字段结构调整
        rule_map = {}
        for rule in function_rules:
            keys = [rule.get('name', ''), rule.get('content', ''), rule.get('rule_key', '')]
            key = "/".join(keys)
            rule_map[key] = rule

        return rule_map.values() 

