import csv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from tqdm.asyncio import tqdm as tqdm_asyncio
from dao.aentity import AProject_Task
Base = declarative_base()

class AProjectTaskMgr:
    def __init__(self, project_id, engine_url):
        self.project_id = project_id
        # Create async engine
        self.engine: AsyncEngine = create_async_engine(engine_url)
        # Ensure table is created
        Base.metadata.create_all(self.engine)
        # Configure sessionmaker to use AsyncSession
        self.Session = sessionmaker(bind=self.engine, class_=AsyncSession)

    async def _operate_in_session(self, func, *args, **kwargs):
        """Generic function to handle operations within an async session."""
        async with self.Session() as session:
            return await func(session, *args, **kwargs)

    async def add_tasks(self, tasks):
        for task in tasks:
            await self._operate_in_session(self._add_task, task)
    
    async def _add_task(self, session, task, commit=True):
        try:
            key = task.get_key()
            # Uncomment if you need to check uniqueness
            # ts = (await session.execute(select(Project_Task).filter_by(project_id=self.project_id, key=key))).scalars().all()
            # if not ts:  # Assuming get_key returns a unique identifier
            session.add(task)
            if commit:
                await session.commit()
        except IntegrityError as e:
            await session.rollback()

    async def query_task_by_project_id(self, id):
        return await self._operate_in_session(self._query_task_by_project_id, id)

    async def _query_task_by_project_id(self, session, id):
        result = (await session.execute(select(AProject_Task).filter_by(project_id=id))).scalars().all()
        return list(result)
    
    async def update_score(self, id, score):
        await self._operate_in_session(self._update_score, id, score)

    async def _update_score(self, session, id, score):
        await session.execute(
            select(AProject_Task).filter_by(id=id).values(score=score)
        )
        await session.commit()

    async def update_business_flow_context(self, id, context):
        await self._operate_in_session(self._update_business_flow_context, id, context)

    async def _update_business_flow_context(self, session, id, context):
        await session.execute(
            select(AProject_Task).filter_by(id=id).values(business_flow_context=context)
        )
        await session.commit()

    async def add_task(
        self,
        name,
        content,
        keyword,
        business_type,
        sub_business_type,
        function_type,
        rule,
        result='',
        result_gpt4='',
        score='0.00',
        category='',
        contract_code='',
        risklevel='',
        similarity_with_rule='',
        description='',
        start_line='',
        end_line='',
        relative_file_path='',
        absolute_file_path='',
        recommendation='',
        title='',
        business_flow_code='',
        business_flow_lines='',
        business_flow_context='',
        if_business_flow_scan='',
        **kwargs
    ):
        task = AProject_Task(
            self.project_id, name, content, keyword, business_type, sub_business_type,
            function_type, rule, result, result_gpt4, score, category, contract_code,
            risklevel, similarity_with_rule, description, start_line, end_line,
            relative_file_path, absolute_file_path, recommendation, title,
            business_flow_code, business_flow_lines, business_flow_context,
            if_business_flow_scan
        )
        await self._operate_in_session(self._add_task, task)

    async def get_task_list(self):
        return await self._operate_in_session(self._get_task_list)

    async def _get_task_list(self, session):
        result = (await session.execute(select(AProject_Task).filter_by(project_id=self.project_id))).scalars().all()
        return list(result)

    async def get_task_list_by_id(self, id):
        return await self._operate_in_session(self._get_task_list_by_id, id)

    async def _get_task_list_by_id(self, session, id):
        result = (await session.execute(select(AProject_Task).filter_by(project_id=id))).scalars().all()
        return list(result)

    async def update_result(self, id, result, result_gpt4, result_assumation):
        await self._operate_in_session(self._update_result, id, result, result_gpt4, result_assumation)

    async def _update_result(self, session, id, result, result_gpt4, result_assumation):
        await session.execute(
            select(AProject_Task).filter_by(id=id).values(
                result=result,
                result_gpt4=result_gpt4,
                category=result_assumation
            )
        )
        await session.commit()

    async def update_similarity_generated_referenced_score(self, id, similarity_with_rule):
        await self._operate_in_session(self._update_similarity_generated_referenced_score, id, similarity_with_rule)

    async def _update_similarity_generated_referenced_score(self, session, id, similarity_with_rule):
        await session.execute(
            select(AProject_Task).filter_by(id=id).values(similarity_with_rule=similarity_with_rule)
        )
        await session.commit()

    async def update_description(self, id, description):
        await self._operate_in_session(self._update_description, id, description)

    async def _update_description(self, session, id, description):
        await session.execute(
            select(AProject_Task).filter_by(id=id).values(description=description)
        )
        await session.commit()

    async def update_recommendation(self, id, recommendation):
        await self._operate_in_session(self._update_recommendation, id, recommendation)

    async def _update_recommendation(self, session, id, recommendation):
        await session.execute(
            select(AProject_Task).filter_by(id=id).values(recommendation=recommendation)
        )
        await session.commit()

    async def update_title(self, id, title):
        await self._operate_in_session(self._update_title, id, title)

    async def _update_title(self, session, id, title):
        await session.execute(
            select(AProject_Task).filter_by(id=id).values(title=title)
        )
        await session.commit()

    async def import_file(self, filename):
        reader = csv.DictReader(open(filename, 'r', encoding='utf-8'))

        processed = 0
        for row in tqdm_asyncio(list(reader), "import tasks"):
            await self.add_task(**row)
            processed += 1
            if processed % 10 == 0:
                await self._operate_in_session(lambda s: s.commit())
        await self._operate_in_session(lambda s: s.commit())

    def dump_file(self, filename):
        writer = self.get_writer(filename)

        async def write_rows():
            ts = await self._operate_in_session(self._get_task_list)
            for row in ts:
                writer.writerow(row.as_dict())
        
        # Run the asynchronous task within an event loop
        import asyncio
        asyncio.run(write_rows())

        del writer

    def get_writer(self, filename):
        file = open(filename, 'w', newline='', encoding='utf-8')
        writer = csv.DictWriter(file, fieldnames=AProject_Task.fieldNames)
        writer.writeheader()  # write header
        return writer

    def merge_results(self, function_rules):
        rule_map = {}
        for rule in function_rules:
            keys = [
                rule['name'],
                rule['content'],
                rule['BusinessType'],
                rule['Sub-BusinessType'],
                rule['FunctionType'],
                rule['KeySentence']
            ]
            key = "/".join(keys)
            rule_map[key] = rule

        return rule_map.values()