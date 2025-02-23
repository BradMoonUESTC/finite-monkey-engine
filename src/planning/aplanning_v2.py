import asyncio
import json
import os
from typing import AsyncGenerator, Callable, Any

from dao.atask_mgr import AProjectTaskMgr

# Assume AProjectTaskMgr and other dependencies are imported

# class APlanningV2:
#     def __init__(self, project, mgr:AProjectTaskMgr ):
#         self.project = project
#         self.taskmgr = AProjectTaskMgr
#         self.scan_list_for_larget_context: list[Any] = []

#     async def do_planning(self) -> AsyncGenerator[Callable[[], Any], None]:
#         """
#         Asynchronously plan the business flows for each function.
#         Instead of returning a final result, yield a lambda that, when invoked,
#         returns a future (a coroutine) for each iteration of planning.
#         This allows an external agent to evaluate each stage as a future.
#         """
#         # For example, fetch tasks from the DB.
#         tasks = await self.taskmgr.get_task_list_by_id(self.project.project_id)
#         if tasks:
#             # If tasks already exist, we consider planning already done.
#             return

#         # Filter functions (example logic).
#         functions_to_check = [f for f in self.project.functions_to_check if "test" not in f['name']]
#         self.project.functions_to_check = functions_to_check

#         # If business code switching is enabled, get all business flows.
#         switch_business_code = eval(os.environ.get('SWITCH_BUSINESS_CODE', 'True'))
#         if switch_business_code:
#             all_business_flow, all_business_flow_line, all_business_flow_context = await self.get_all_business_flow(self.project.functions_to_check)
#         else:
#             all_business_flow = all_business_flow_line = all_business_flow_context = {}

#         # Iterate over each function to plan its business flow.
#         for function in self.project.functions_to_check:
#             name = function['name']
#             contract_name = function['contract_name']
#             # Log processing
#             print(f"Processing function: {name}")

#             # Use your existing search_business_flow to get the flow code.
#             business_flow_code, line_info_list, other_contract_context = await self.search_business_flow(
#                 all_business_flow, all_business_flow_line, all_business_flow_context,
#                 name.split(".")[1], contract_name
#             )
#             # Build a prompt for type checking.
#             type_check_prompt = (
#                 "分析以下智能合约代码，判断它属于哪些业务类型。可能的类型包括:\n"
#                 "chainlink, dao, inline assembly, lending, liquidation, liquidity manager, signature, "
#                 "slippage, univ3, other\n"
#                 "请以JSON格式返回结果，格式为: {\"business_types\": [\"type1\", \"type2\"]}\n\n"
#                 "代码:\n{0}"
#             )
#             formatted_prompt = type_check_prompt.format(business_flow_code + "\n" + other_contract_context + "\n" + function['content'])
            
#             # Instead of directly calling a REST method to get the answer, yield a lambda
#             # that returns a coroutine to be evaluated later by the caller.
#             yield lambda: self.common_ask_for_json(formatted_prompt)

#             # Optionally, you could also yield the current intermediate planning context.
#             # For example:
#             # yield lambda: asyncio.sleep(0, result={"function": name, "prompt": formatted_prompt})
    
#     async def common_ask_for_json(self, prompt: str) -> dict:
#         """
#         Simulate an asynchronous call to an LLM API that returns a JSON result.
#         In your production code, this would be replaced with a pydantic-ai Agent call.
#         """
#         # Simulated delay
#         await asyncio.sleep(0.5)
#         # For demonstration, return a dummy JSON response.
#         # In reality, your agent would process the prompt.
#         dummy_response = {"business_types": ["example_type1", "example_type2"]}
#         print(f"Processed prompt: {prompt[:60]}... -> {dummy_response}")
#         return dummy_response

#     # Placeholder methods for get_all_business_flow and search_business_flow
#     async def get_all_business_flow(self, functions_to_check):
#         # Simulated async processing.
#         await asyncio.sleep(0.5)
#         # Return dummy dictionaries.
#         return {}, {}, {}

#     async def search_business_flow(self, all_flow, all_flow_line, all_flow_context, function_name, contract_name):
#         # Simulated async search.
#         await asyncio.sleep(0.5)
#         # Return dummy business flow code and context.
#         return f"business flow code for {function_name}", [], f"context for {contract_name}"
import asyncio
import json
import os
import re
from typing import AsyncGenerator, Callable, Any, List, Tuple

# Simulated pydantic model for LLM responses (for illustration)
from pydantic import BaseModel

class TranslationResult(BaseModel):
    english: str
    chinese: str

# Dummy implementations for demonstration.
# In production, replace these with real pydantic‑ai Agent calls.

class APlanningV2:
    def __init__(self, project, tm):
        self.project = project
        self.taskmgr = tm # Assume this is defined elsewhere
        self.scan_list_for_larget_context = []

    async def ask_openai_for_business_flow(self, function_name: str, contract_code_without_comment: str) -> List[str]:
        """
        Asynchronously call the LLM to get business flows starting with function_name.
        Returns a list of function names (strings).
        """
        prompt = f"""
        Based on the code below, analyze the business flows starting with the function {function_name}.
        Only output a JSON list of function names that are part of the business flow.
        Code:
        {contract_code_without_comment}
        """
        # Simulate API latency.
        await asyncio.sleep(0.5)
        # For demonstration, return dummy function names.
        return [function_name, function_name + "_helper", function_name + "_final"]

    async def extract_filtered_functions(self, business_flow_list: List[str]) -> List[str]:
        """
        Process the list of function names from the LLM output.
        For demonstration, simply remove duplicates.
        """
        await asyncio.sleep(0.1)
        return list(set(business_flow_list))

    async def extract_and_concatenate_functions_content(self, function_lists: List[str], contract_info: dict) -> str:
        """
        Given a list of function names and contract info, concatenate their contents.
        For demonstration, we simulate by returning dummy content for each function.
        """
        await asyncio.sleep(0.1)
        contents = [f"Content for {fn}" for fn in function_lists]
        return "\n".join(contents)

    async def extract_results(self, text: str) -> List[dict]:
        """
        Extract results from a text output (dummy implementation).
        """
        await asyncio.sleep(0.2)
        # For demonstration, return a dummy list.
        return [{"result": "yes"}]

    async def merge_and_sort_rulesets(self, high: List[dict], medium: List[dict]) -> List[dict]:
        """
        Merge two rulesets and sort by sim_score.
        """
        combined = high + medium
        combined.sort(key=lambda x: x.get("sim_score", 0), reverse=True)
        return combined

    async def decode_business_flow_list_from_response(self, response: str) -> List[str]:
        """
        Decode a JSON-formatted business flow list from a response.
        """
        pattern = r'({\s*\"[a-zA-Z0-9_]+\"\s*:\s*\[[^\]]*\]\s*})'
        matches = re.findall(pattern, response)
        functions = set()
        for match in matches:
            try:
                data = json.loads(match)
                for key, value in data.items():
                    functions.add(key)
                    functions.update(value)
            except Exception:
                continue
        return list(functions)

    async def identify_contexts(self, functions_to_check: List[dict]) -> dict:
        """
        For each function in functions_to_check, identify its sub_calls and parent_calls.
        Returns a dictionary mapping function names to context information.
        """
        await asyncio.sleep(0.2)
        contexts = {}
        for function in functions_to_check:
            name = function.get("name", "unknown")
            contexts[name] = {
                "sub_calls": [{"name": name + "_sub", "content": "dummy sub-call content"}],
                "parent_calls": [{"name": name + "_parent", "content": "dummy parent-call content"}]
            }
        return contexts

    async def search_business_flow(self,
                                   all_business_flow: dict,
                                   all_business_flow_line: dict,
                                   all_business_flow_context: dict,
                                   function_name: str,
                                   contract_name: str) -> Tuple[str, List[Tuple[int, int]], str]:
        """
        Search for business flow information given a function name and contract name.
        Returns a tuple of:
         - business_flow_code (str)
         - line_info_list (list of tuples)
         - context_info (str)
        """
        await asyncio.sleep(0.3)
        business_flow_code = f"Business flow code for {function_name} in contract {contract_name}"
        line_info_list = [(1, 10)]
        context_info = f"Extended context for {contract_name}"
        return business_flow_code, line_info_list, context_info

    async def common_ask_for_json(self, prompt: str) -> dict:
        """
        Simulate an asynchronous call to an LLM API that returns a JSON result.
        """
        await asyncio.sleep(0.5)
        dummy_response = {"business_types": ["type1", "type2"]}
        print(f"[LLM] Processed prompt (first 60 chars): {prompt[:60]}... -> {dummy_response}")
        return dummy_response

    async def do_planning(self) -> AsyncGenerator[Callable[[], Any], None]:
        """
        Asynchronously process planning for each function.
        Yield a lambda that returns a future (coroutine) for each planning iteration.
        """
        # Simulate fetching tasks – if tasks already exist, planning may be skipped.
        tasks = await self.taskmgr.get_task_list_by_id(self.project.project_id)
        if tasks:
            return  # Planning already done.

        # Filter functions to check.
        functions_to_check = [f for f in self.project.functions_to_check if "test" not in f.get('name', "")]
        self.project.functions_to_check = functions_to_check

        # Optionally, if business code switching is enabled, get all business flows.
        switch_business_code = eval(os.environ.get('SWITCH_BUSINESS_CODE', 'True'))
        if switch_business_code:
            all_business_flow, all_business_flow_line, all_business_flow_context = await self.get_all_business_flow(self.project.functions_to_check)
        else:
            all_business_flow = all_business_flow_line = all_business_flow_context = {}

        # Process each function.
        for function in self.project.functions_to_check:
            name = function.get('name', "unknown")
            contract_name = function.get('contract_name', "default")
            print(f"Processing function: {name}")

            # Retrieve business flow code and context.
            business_flow_code, line_info_list, other_contract_context = await self.search_business_flow(
                all_business_flow, all_business_flow_line, all_business_flow_context,
                name.split(".")[1] if "." in name else name, contract_name
            )
            # Build a prompt.
            type_check_prompt = (
                "分析以下智能合约代码，判断它属于哪些业务类型。可能的类型包括：\n"
                "chainlink, dao, inline assembly, lending, liquidation, liquidity manager, signature, "
                "slippage, univ3, other\n"
                "请以JSON格式返回结果，格式为: {\"business_types\": [\"type1\", \"type2\"]}\n\n"
                "代码：\n{0}"
            )
            formatted_prompt = type_check_prompt.format(business_flow_code + "\n" + other_contract_context + "\n" + function.get('content', ""))
            
            # Yield a lambda that, when called, returns the coroutine to get the JSON response.
            yield lambda: self.common_ask_for_json(formatted_prompt)
            
            # Optionally, you might also yield additional intermediate context.
            # For example:
            # yield lambda: asyncio.sleep(0, result={"function": name, "prompt": formatted_prompt})

    # Dummy implementation of get_all_business_flow for completeness.
    async def get_all_business_flow(self, functions_to_check: List[dict]) -> Tuple[dict, dict, dict]:
        await asyncio.sleep(0.5)
        # Return dummy dictionaries.
        return {}, {}, {}

    # Dummy implementations for task manager and project for testing purposes.
    class AProjectTaskMgr:
        async def get_task_list_by_id(self, project_id: int) -> List[Any]:
            await asyncio.sleep(0.1)
            return []  # Simulate no tasks yet.

    class DummyProject:
        project_id = 1
        functions_to_check = [
            {"name": "ContractA.transfer", "content": "function transfer(...) {}", "contract_name": "ContractA"},
            {"name": "ContractA.approve", "content": "function approve(...) {}", "contract_name": "ContractA"}
        ]

    # ---------------------------
    # Example Orchestrator: Consume the Async Generator
    # ---------------------------
    # async def process_planning():
    #     project = DummyProject()
    #     planning = APlanningV2(project)
    #     # Iterate over each planning stage.
    #     async for stage_callable in planning.do_planning():
    #         # Call the lambda to get the coroutine and await its result.
    #         result = await stage_callable()
    #         print("Orchestrator received planning stage result:", result)

    # if __name__ == "__main__":
    #     asyncio.run(process_planning())

# ---------------------------
# Example Usage: An Orchestrator Evaluating the Generator
# ---------------------------
async def process_planning():
    # Assume we have a dummy project object with required attributes.
    class DummyProject:
        project_id = 1
        functions_to_check = [
            {"name": "ContractA.transfer", "content": "function transfer...", "contract_name": "ContractA"},
            {"name": "ContractA.approve", "content": "function approve...", "contract_name": "ContractA"}
        ]
    project = DummyProject()
    planning = APlanningV2(project)
    
    async for stage_callable in planning.do_planning():
        # stage_callable is a lambda that returns a coroutine (future).
        result = await stage_callable()
        print("Agent processed planning stage with result:", result)

if __name__ == "__main__":
    asyncio.run(process_planning())
