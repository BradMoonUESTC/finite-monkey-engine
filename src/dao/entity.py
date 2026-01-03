import random
import uuid as uuid_module
import sqlalchemy
from sqlalchemy import create_engine, select, Column, String, Integer, MetaData, Table, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .utils import str_hash

Base = declarative_base()

class CacheEntry(Base):
    __tablename__ = 'prompt_cache2'
    index = Column(String, primary_key=True)
    key = Column(String)
    value = Column(String)

class Project_Task(Base):
    __tablename__ = 'project_task'
    id = Column(Integer, autoincrement=True, primary_key=True)
    uuid = Column(String, unique=True, index=True)  # UUID列
    project_id = Column(String, index=True)
    name = Column(String)  # root_function的name（合约名+函数名用点连接）
    content = Column(String)  # root function的内容
    rule = Column(String)  # all_checklists定义的每一个rule，原始的list
    rule_key = Column(String)  # 规则key，用于标识不同类型的检查规则
    result = Column(String)
    contract_code = Column(String)
    start_line = Column(String)
    end_line = Column(String)
    relative_file_path = Column(String)
    absolute_file_path = Column(String)
    recommendation = Column(String)
    business_flow_code = Column(String)  # root func的内容加上所有downstream的内容
    scan_record = Column(String)  # 扫描记录
    short_result = Column(String)  # 简短结果，保存yes/no
    group = Column(String, index=True)  # 任务组UUID，用于标识同一组的任务

    fieldNames = ['id', 'uuid', 'project_id', 'name', 'content', 'rule', 'rule_key', 'result', 'contract_code', 'start_line', 'end_line', 'relative_file_path', 'absolute_file_path', 'recommendation', 'business_flow_code', 'scan_record', 'short_result', 'group']

    def __init__(self, project_id, name, content, rule, rule_key='', result='', contract_code='', start_line='', end_line='', relative_file_path='', absolute_file_path='', recommendation='', business_flow_code='', scan_record='', short_result='', group=''):
        self.uuid = str(uuid_module.uuid4())  # 生成UUID
        self.project_id = project_id
        self.name = name  # root_function的name（合约名+函数名用点连接）
        self.content = content  # root function的内容
        self.rule = rule  # all_checklists定义的每一个rule
        self.rule_key = rule_key  # 规则key
        self.result = result
        self.contract_code = contract_code
        self.start_line = start_line
        self.end_line = end_line
        self.relative_file_path = relative_file_path
        self.absolute_file_path = absolute_file_path
        self.recommendation = recommendation
        self.business_flow_code = business_flow_code  # root func的内容加上所有downstream的内容
        self.scan_record = scan_record  # 扫描记录
        self.short_result = short_result  # 简短结果，保存yes/no
        self.group = group  # 任务组UUID



    def as_dict(self):
        return {
            'id': getattr(self, 'id', None),
            'uuid': self.uuid,
            'project_id': self.project_id,
            'name': self.name,
            'content': self.content,
            'rule': self.rule,
            'rule_key': self.rule_key,
            'result': self.result,
            'contract_code': self.contract_code,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'relative_file_path': self.relative_file_path,
            'absolute_file_path': self.absolute_file_path,
            'recommendation': self.recommendation,
            'business_flow_code': self.business_flow_code,
            'scan_record': self.scan_record,
            'short_result': self.short_result,
            'group': self.group
        }
    
    def set_result(self, result):
        self.result = result

    def get_result(self):
        result = self.result
        return None if result == '' else result
    
    def set_short_result(self, short_result):
        self.short_result = short_result
    
    def get_short_result(self):
        short_result = self.short_result
        return None if short_result == '' else short_result
    
    def get_key(self):
        # 使用UUID作为key
        return self.uuid


class Project_Finding(Base):
    """
    单漏洞条目表：用于承接 reasoning 产出的多漏洞 JSON 拆分结果。
    设计目标：尽量自包含（复制 task 的代码/上下文字段），便于后续去重/validation/导出仅基于 finding 表完成。
    """
    __tablename__ = 'project_finding'

    id = Column(Integer, autoincrement=True, primary_key=True)
    uuid = Column(String, unique=True, index=True)

    project_id = Column(String, index=True)

    # 关联 task
    task_id = Column(Integer, index=True)
    task_uuid = Column(String, index=True)
    rule_key = Column(String, index=True)

    # 单漏洞 JSON（字符串）
    finding_json = Column(String)

    # 复制 task 的关键上下文字段（尽量自包含）
    task_name = Column(String)
    task_content = Column(String)
    task_business_flow_code = Column(String)
    task_contract_code = Column(String)
    task_start_line = Column(String)
    task_end_line = Column(String)
    task_relative_file_path = Column(String)
    task_absolute_file_path = Column(String)
    task_rule = Column(String)
    task_group = Column(String, index=True)

    # 去重与验证状态
    dedup_status = Column(String, index=True)  # kept / delete
    validation_status = Column(String, index=True)  # pending / yes / no / not_sure
    validation_record = Column(String)  # 可选：保存验证日志/结构化结果

    fieldNames = [
        'id', 'uuid', 'project_id',
        'task_id', 'task_uuid', 'rule_key',
        'finding_json',
        'task_name', 'task_content', 'task_business_flow_code',
        'task_contract_code', 'task_start_line', 'task_end_line',
        'task_relative_file_path', 'task_absolute_file_path',
        'task_rule', 'task_group',
        'dedup_status', 'validation_status', 'validation_record'
    ]

    def __init__(
        self,
        project_id: str,
        task_id: int,
        task_uuid: str,
        rule_key: str,
        finding_json: str,
        task_name: str = '',
        task_content: str = '',
        task_business_flow_code: str = '',
        task_contract_code: str = '',
        task_start_line: str = '',
        task_end_line: str = '',
        task_relative_file_path: str = '',
        task_absolute_file_path: str = '',
        task_rule: str = '',
        task_group: str = '',
        dedup_status: str = 'kept',
        validation_status: str = 'pending',
        validation_record: str = '',
    ):
        self.uuid = str(uuid_module.uuid4())

        self.project_id = project_id
        self.task_id = task_id
        self.task_uuid = task_uuid
        self.rule_key = rule_key
        self.finding_json = finding_json

        self.task_name = task_name
        self.task_content = task_content
        self.task_business_flow_code = task_business_flow_code
        self.task_contract_code = task_contract_code
        self.task_start_line = task_start_line
        self.task_end_line = task_end_line
        self.task_relative_file_path = task_relative_file_path
        self.task_absolute_file_path = task_absolute_file_path
        self.task_rule = task_rule
        self.task_group = task_group

        self.dedup_status = dedup_status
        self.validation_status = validation_status
        self.validation_record = validation_record

    def as_dict(self):
        return {name: getattr(self, name, None) for name in self.fieldNames}


