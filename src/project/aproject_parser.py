import os
from typing import Any, Dict, Tuple, Union, List, Set
from os import path
import asyncio

async def parse_project_async(project_path: str, project_filter=None):
    if project_filter is None:
        project_filter = ABaseProjectFilter([], [])

    ignore_folders = set()
    if os.environ.get('IGNORE_FOLDERS'):
        ignore_folders = set(os.environ.get('IGNORE_FOLDERS').split(','))
    ignore_folders.add('.git')
    all_results = []
    
    async def walk_and_parse(dirpath: str, dirs: List[str], files: List[str]):
        dirs[:] = [d for d in dirs if d not in ignore_folders]
        for file in files:
            to_scan = not await project_filter.filter_file_async(dirpath, file)
            sol_file = os.path.join(dirpath, file)  # relative path
            absolute_path = os.path.abspath(sol_file)  # absolute path
            print("parsing file: ", sol_file, " " if to_scan else "[skipped]")
            
            if to_scan:
                results = await get_antlr_parsing_async(sol_file)
                for result in results:
                    result['relative_file_path'] = sol_file
                    result['absolute_file_path'] = absolute_path
                all_results.extend(results)

    tasks = []
    for dirpath, dirs, files in os.walk(project_path):
        tasks.append(walk_and_parse(dirpath, dirs, files))
    
    await asyncio.gather(*tasks)

    functions = [result for result in all_results if result['type'] == 'FunctionDefinition']
    # fix func name 
    fs = []
    for func in functions:
        if func['name'][8:] != "tor":
            name = func['name'][8:]  # remove SPECIAL_ Prefix, I forgot the specific reason, it seems to be to consider a specific function name
        else:
            name = "constructor"
        func['name'] = "%s.%s" % (func['contract_name'], name)
        fs.append(func)

    fs_filtered = fs[:]
    # 2. filter contract 
    fs_filtered = [func for func in fs_filtered if not await project_filter.filter_contract_async(func)]

    # 3. filter functions 
    fs_filtered = [func for func in fs_filtered if not await project_filter.filter_functions_async(func)]

    return fs, fs_filtered 

class ABaseProjectFilter(object):
    def __init__(self, white_files=[], white_functions=[]):
        self.white_files = white_files
        self.white_functions = white_functions

    async def filter_file_async(self, path: str, filename: str) -> bool:
        # 检查文件后缀
        valid_extensions = ('.sol', '.rs', '.py', '.move', '.cairo', '.tact', '.fc', '.fr', '.java')
        if not any(filename.endswith(ext) for ext in valid_extensions) or filename.endswith('.t.sol'):
            return True

        # 如果白名单不为空，检查文件是否在白名单中
        if len(self.white_files) > 0:
            return not any(os.path.basename(filename) in white_file for white_file in self.white_files)

        return False

    async def filter_contract_async(self, function: Dict[str, Any]) -> bool:
        # rust情况下，不进行筛选
        if '_rust' in function["name"]:
            return False
        if '_python' in function["name"]:
            return False
        if '_move' in function["name"]:
            return False
        if '_cairo' in function["name"]:
            return False
        if '_tact' in function["name"]:
            return False
        if '_func' in function["name"]:
            return False
        if '_fa' in function["name"]:
            return False

        # solidity情况下，进行筛选
        if str(function["contract_name"]).startswith("I") and function["contract_name"][1].isupper():
            print("function ", function['name'], " skipped for interface contract")
            return True
        if "test" in str(function["name"]).lower():
            print("function ", function['name'], " skipped for test function")
            return True

        if "function init" in str(function["content"]).lower() or "function initialize" in str(function["content"]).lower() or "constructor(" in str(function["content"]).lower() or "receive()" in str(function["content"]).lower() or "fallback()" in str(function["content"]).lower():
            print("function ", function['name'], " skipped for constructor")
            return True

        return False

    async def filter_functions_async(self, function: Dict[str, Any]) -> bool:
        # Step 3: function 筛选 ( 白名单检查 )
        if len(self.white_functions) == 0:
            return False
        return function['name'] not in self.white_functions

async def get_antlr_parsing_async(sol_file: str) -> List[Dict[str, Any]]:
    # Simulate asynchronous parsing process
    await asyncio.sleep(1)  # Placeholder for actual async operation
    return [{"type": "FunctionDefinition", "contract_name": "example", "name": "exampleFunc"}]  # TODO!!

async def main():
    from library.dataset_utils import load_dataset_async
    dataset_base = "../../dataset/agent-v1-c4"
    projects = await load_dataset_async(dataset_base)
    project = projects['whalefall']

    project_path = os.path.join(project['base_path'], project['path'])
    white_files, white_functions = project.get('files', []), project.get('functions', [])

    parser_filter = ABaseProjectFilter(white_files, white_functions)
    functions, functions_to_check = await parse_project_async(project_path, parser_filter)

    print(functions_to_check)

if __name__ == '__main__':
    asyncio.run(main())