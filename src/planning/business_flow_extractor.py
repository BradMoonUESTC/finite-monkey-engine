import json
import re
from typing import Any, Dict, Tuple, List, Optional
from collections import defaultdict
import logging

# Local module imports
from dao.entity import Project_Task  # Ensure usage or remove if unnecessary
from library.parsing import CallGraph  # Replace with actual import path
from library.sgp.utilities.contract_extractor import (
    group_functions_by_contract,
    check_function_if_public_or_external,
    check_function_if_view_or_pure
)

# Configure logger (if not already configured elsewhere)
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logger.setLevel(logging.INFO)  # Adjust as needed
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class BusinessFlowExtractor:
    # Centralized language patterns to avoid redundancy
    LANGUAGE_PATTERNS = {
        '.rust': lambda f: True,  # No visibility filter for Rust
        '.python': lambda f: True,  # No visibility filter for Python
        '.move': lambda f: f.get('visibility') == 'public',
        '.fr': lambda f: f.get('visibility') == 'public',
        '.java': lambda f: f.get('visibility') in ['public', 'protected'],
        '.cairo': lambda f: f.get('visibility') == 'public',
        '.tact': lambda f: f.get('visibility') == 'public',
        '.func': lambda f: f.get('visibility') == 'public'
    }

    def __init__(self, call_graph: CallGraph) -> None:
        """
        Initialize the BusinessFlowExtractor with an instance of CallGraph.

        :param call_graph: An instance of the CallGraph class.
        """
        self.call_graph = call_graph

    def get_all_business_flow(
        self, 
        functions_to_check: List[str]
    ) -> Tuple[
        Dict[str, Dict[str, Any]], 
        Dict[str, Dict[str, List[Tuple[int, int]]]], 
        Dict[str, Dict[str, str]]
    ]:
        """
        Extracts all business flows for a list of functions.

        :param functions_to_check: A list of function names to extract business flows for.
        :return: 
            - all_business_flow: Dict[contract_name, Dict[function_name, business_flow_code]]
            - all_business_flow_line: Dict[contract_name, Dict[function_name, List[Tuple[start_line, end_line]]]]
            - all_business_flow_context: Dict[contract_name, Dict[function_name, extended_flow_code]]
        """
        if not functions_to_check:
            logger.warning("No functions provided for business flow extraction.")
            return {}, {}, {}

        # Group functions by their respective contracts
        grouped_functions = group_functions_by_contract(functions_to_check)
        # Identify contexts for the functions
        contexts = self.call_graph.identify_contexts(functions_to_check)

        # Initialize dictionaries to store business flows
        all_business_flow: Dict[str, Dict[str, Any]] = defaultdict(dict)
        all_business_flow_line: Dict[str, Dict[str, List[Tuple[int, int]]]] = defaultdict(dict)
        all_business_flow_context: Dict[str, Dict[str, str]] = defaultdict(dict)

        logger.info(f"Grouped contract count: {len(grouped_functions)}")

        for contract_info in grouped_functions:
            contract_name = contract_info.get('contract_name')
            functions = contract_info.get('functions', [])
            contract_code_without_comments = contract_info.get('contract_code_without_comment', '')
            file_path = contract_info.get('file_path')  # Assuming 'file_path' key exists

            if not contract_name:
                logger.warning("Contract info missing 'contract_name'. Skipping.")
                continue

            logger.info(f"Processing contract: {contract_name}")

            # Determine file extension and corresponding visibility filter
            file_ext = self._get_file_extension(functions)
            visibility_filter = self._get_visibility_filter(file_ext)

            # Filter public/external functions based on visibility
            all_public_external_function_names = [
                self._extract_function_name(function.get('name', '')) 
                for function in functions 
                if visibility_filter(function)
            ]

            logger.info(f"Public/External functions count in {contract_name}: {len(all_public_external_function_names)}")

            for function_name in all_public_external_function_names:
                if not function_name:
                    logger.warning(f"Encountered empty function name in contract '{contract_name}'. Skipping.")
                    continue

                logger.debug(f"Processing function: {function_name}")

                # Special handling for Python contracts with a single public/external function
                if "_python" in contract_name.lower() and len(all_public_external_function_names) == 1:
                    # Assuming downstream methods expect a dictionary, not a JSON string
                    business_flow_list = {
                        function_name: all_public_external_function_names
                    }
                else:
                    try:
                        business_flow_list = self.ask_openai_for_business_flow(function_name, contract_code_without_comments)
                    except Exception as e:
                        logger.error(f"Error fetching business flow for {function_name}: {e}")
                        business_flow_list = {}

                if not business_flow_list:
                    logger.warning(f"No business flow data for function: {function_name}")
                    continue

                # Extract function lists from business_flow_list
                try:
                    function_lists = business_flow_list.get("BusinessFlow", {}).get("flow", [])
                    function_lists = [fn for fn in function_lists if fn != function_name]
                except AttributeError as e:
                    logger.error(f"Error processing business_flow_list for {function_name}: {e}")
                    continue

                logger.debug(f"Business flow list for {function_name}: {function_lists}")

                # Retrieve line information for each function in the flow
                line_info_list = []
                for fn in function_lists:
                    if isinstance(fn, str) and fn != "-1":
                        func_struct = self.call_graph.get_function_detail(file=file_path, contract=contract_name, function=fn)
                        if func_struct:
                            line_info = (func_struct.get('start_line'), func_struct.get('end_line'))
                            line_info_list.append(line_info)

                # Extract and concatenate function contents
                business_flow_code = self.extract_and_concatenate_functions_content(function_lists, contract_info)

                # Build extended flow code from contexts
                extended_flow_code = self._build_extended_flow_code(contract_name, function_lists, contexts)

                # Assign to respective dictionaries
                all_business_flow[contract_name][function_name] = business_flow_code
                all_business_flow_line[contract_name][function_name] = line_info_list
                all_business_flow_context[contract_name][function_name] = extended_flow_code.strip()

        return all_business_flow, all_business_flow_line, all_business_flow_context

    def _get_file_extension(self, functions: List[Dict[str, Any]]) -> Optional[str]:
        """
        Determine the file extension based on the functions' relative file paths.

        :param functions: List of function dictionaries.
        :return: File extension if found, else None.
        """
        for func in functions:
            file_path = func.get('relative_file_path', '')
            for ext, filter_func in self.LANGUAGE_PATTERNS.items():
                if file_path.endswith(ext) and filter_func(func):
                    return ext
        return None

    def _get_visibility_filter(self, file_ext: Optional[str]):
        """
        Retrieve the visibility filter lambda based on the file extension.

        :param file_ext: File extension.
        :return: A lambda function for visibility filtering.
        """
        return self.LANGUAGE_PATTERNS.get(file_ext, lambda f: True)

    def _extract_function_name(self, full_name: str) -> str:
        """
        Extract the function name from its full name.

        :param full_name: Full function name (e.g., "Contract.Function").
        :return: Function name (e.g., "Function").
        """
        if "." in full_name:
            return full_name.split(".")[-1]
        else:
            logger.warning(f"Function name '{full_name}' does not contain a period. Returning as is.")
            return full_name

    def _build_extended_flow_code(
        self, 
        contract_name: str, 
        function_lists: List[str], 
        contexts: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Build the extended flow code by aggregating context content.

        :param contract_name: Name of the contract.
        :param function_lists: List of function names involved in the business flow.
        :param contexts: Contexts dictionary containing sub_calls and parent_calls.
        :return: Concatenated extended flow code.
        """
        extended_flow_parts = []
        for func in function_lists:
            key = f"{contract_name}.{func}"
            context = contexts.get(key, {})
            sub_calls = context.get("sub_calls", [])
            parent_calls = context.get("parent_calls", [])
            
            combined_calls = sub_calls + parent_calls
            if not combined_calls:
                logger.debug(f"No sub_calls or parent_calls found for key '{key}'.")
                continue
            
            context_content = "\n".join(call.get("content", "") for call in combined_calls if call.get("content"))
            if context_content:
                extended_flow_parts.append(context_content)
            else:
                logger.debug(f"No content found in sub_calls or parent_calls for key '{key}'.")
        
        extended_flow_code = "\n".join(extended_flow_parts)
        return extended_flow_code.strip()

    def ask_openai_for_business_flow(self, function_name: str, contract_code: str) -> Dict[str, Any]:
        """
        Interface with OpenAI to retrieve business flow for a given function.

        :param function_name: Name of the function.
        :param contract_code: Source code of the contract.
        :return: Parsed JSON response from OpenAI.
        """
        prompt = f"""
        Analyze the business flow for the function '{function_name}' in the following contract code. Identify all functions that are called by '{function_name}' and the sequence of these calls. Provide the output in the following JSON format:

        {{
            "BusinessFlow": {{
                "flow": ["{function_name}", "FunctionA", "FunctionB", "..."]
            }}
        }}
        """

        try:
            logger.info(f"Asking OpenAI for business flow of function '{function_name}'.")
            response = openai.Completion.create(
                engine="text-davinci-003",  # Replace with the desired engine
                prompt=prompt,
                max_tokens=500,
                n=1,
                stop=None,
                temperature=0.5
            )
            response_text = response.choices[0].text.strip()
            business_flow = json.loads(response_text)
            logger.debug(f"Received business flow from OpenAI for function '{function_name}': {business_flow}")
            return business_flow
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error while fetching business flow for '{function_name}': {e}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error for function '{function_name}': {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error while fetching business flow for '{function_name}': {e}")
            return {}

    def extract_and_concatenate_functions_content(
        self, 
        function_names: List[str], 
        contract_info: Dict[str, Any]
    ) -> str:
        """
        Extracts the content of functions based on a given function list and contract info,
        and concatenates them into a single string.

        :param function_names: List of function names to extract.
        :param contract_info: Information about the contract containing the functions.
        :return: Concatenated source code of the specified functions.
        """
        file_path = contract_info.get('file_path')
        contract_name = contract_info.get('contract_name')
        if not file_path or not contract_name:
            logger.error("Contract information missing 'file_path' or 'contract_name'.")
            return ""

        functions = contract_info.get('functions', [])
        concatenated_code_parts = []

        for func_name in function_names:
            if not func_name:
                logger.warning(f"Encountered empty function name in contract '{contract_name}'. Skipping.")
                continue

            func_detail = self.call_graph.get_function_detail(file=file_path, contract=contract_name, function=func_name)
            if func_detail:
                func_src = self.call_graph.get_function_src(file=file_path, func=func_detail)
                if func_src:
                    concatenated_code_parts.append(func_src)
                else:
                    logger.warning(f"Source code for function '{func_name}' in contract '{contract_name}' is empty.")
            else:
                logger.warning(f"Function '{func_name}' not found in contract '{contract_name}'.")

        concatenated_code = "\n".join(concatenated_code_parts)
        return concatenated_code.strip()

    def merge_and_sort_rulesets(
        self, 
        high: List[Dict[str, Any]], 
        medium: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge two rulesets based on sim_score and sort them in descending order.

        :param high: List of high-priority rules.
        :param medium: List of medium-priority rules.
        :return: Sorted combined ruleset.
        """
        combined_ruleset = high + medium
        sorted_ruleset = sorted(combined_ruleset, key=lambda x: x.get('sim_score', 0), reverse=True)
        logger.debug(f"Merged and sorted ruleset with {len(sorted_ruleset)} rules.")
        return sorted_ruleset

    def decode_business_flow_list_from_response(self, response: str) -> List[str]:
        """
        Extracts unique function names from a JSON response.

        :param response: JSON string containing business flow information.
        :return: A list of unique function names.
        """
        unique_functions = set()
        try:
            json_obj = json.loads(response)
            business_flow = json_obj.get("BusinessFlow", {}).get("flow", [])
            for func in business_flow:
                if isinstance(func, str):
                    func_name = func.split(".")[-1] if "." in func else func
                    unique_functions.add(func_name)
                else:
                    logger.warning(f"Unexpected function format in business flow: {func}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during business flow decoding: {e}")
        return sorted(unique_functions)

    def search_business_flow(
        self,
        all_business_flow: Dict[str, Dict[str, Any]],
        all_business_flow_line: Dict[str, Dict[str, Any]],
        all_business_flow_context: Dict[str, Dict[str, Any]],
        function_name: str,
        contract_name: str
    ) -> 'BusinessFlowResult':
        """
        Search for the business flow code based on a function name and contract name.

        :param all_business_flow: The dictionary containing all business flows.
        :param all_business_flow_line: The dictionary containing business flow lines.
        :param all_business_flow_context: The dictionary containing business flow contexts.
        :param function_name: The name of the function to search for.
        :param contract_name: The name of the contract where the function is located.
        :return: BusinessFlowResult containing (business_flow_code, business_flow_line, business_flow_context) 
                 if found, otherwise (None, [], None).
        """
        contract_flows = all_business_flow.get(contract_name)
        contract_flows_line = all_business_flow_line.get(contract_name, {})
        contract_flows_context = all_business_flow_context.get(contract_name, {})

        if not contract_flows:
            logger.warning(f"Contract '{contract_name}' not found in all_business_flow.")
            return BusinessFlowResult(None, [], None)

        business_flow_code = contract_flows.get(function_name)
        if business_flow_code is None:
            logger.warning(f"Function '{function_name}' not found in contract '{contract_name}'.")
            return BusinessFlowResult(None, [], None)

        business_flow_line = contract_flows_line.get(function_name, [])
        business_flow_context = contract_flows_context.get(function_name, "")

        return BusinessFlowResult(business_flow_code, business_flow_line, business_flow_context)


from typing import NamedTuple

class BusinessFlowResult(NamedTuple):
    business_flow_code: Optional[str]
    business_flow_line: List[Tuple[int, int]]
    business_flow_context: Optional[str]
