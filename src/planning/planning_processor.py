import json
import random
import csv
import sys
import os
import os.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import List, Dict
from tqdm import tqdm
from dao.entity import Project_Task
from openai_api.openai import common_ask_for_json
from prompt_factory.core_prompt import CorePrompt
from prompt_factory.vul_prompt_common import VulPromptCommon
from .business_flow_utils import BusinessFlowUtils
from .config_utils import ConfigUtils
from context import ContextFactory


class PlanningProcessor:
    """规划处理器，负责处理规划相关的复杂逻辑"""
    
    def __init__(self, project, taskmgr, checklist_generator=None):
        self.project = project
        self.taskmgr = taskmgr
        self.checklist_generator = checklist_generator
        self.context_factory = ContextFactory(project)
        # 为COMMON_PROJECT_FINE_GRAINED模式添加计数器
        self.fine_grained_counter = 0
    
    def do_planning(self):
        """执行规划的核心逻辑"""
        print("Begin do planning...")
        
        # 准备规划工作
        config = self._prepare_planning()
        if config is None:
            return  # 已有任务，直接返回
        
        # 获取所有业务流
        all_business_flow_data = self._get_business_flows_if_needed(config)
        
        # 处理每个函数
        self._process_all_functions(config, all_business_flow_data)
    
    def _prepare_planning(self) -> Dict:
        """准备规划工作"""
        # 获取扫描配置
        config = ConfigUtils.get_scan_configuration()
        
        # 检查现有任务
        tasks = self.taskmgr.get_task_list_by_id(self.project.project_id)
        if len(tasks) > 0:
            return None
        
        # 过滤测试函数
        self._filter_test_functions()
        
        return config
    
    def _filter_test_functions(self):
        """过滤掉测试函数"""
        functions_to_remove = []
        for function in self.project.functions_to_check:
            name = function['name']
            if "test" in name:
                functions_to_remove.append(function)
        
        for function in functions_to_remove:
            self.project.functions_to_check.remove(function)
    
    def _get_business_flows_if_needed(self, config: Dict) -> Dict:
        """如果需要的话获取所有业务流"""
        # 如果开启了文件级别扫描，则不需要业务流数据
        if config['switch_file_code']:
            print("🔄 文件级别扫描模式：跳过业务流数据获取")
            return {}
        
        # 只有在非文件级别扫描且开启业务流扫描时才获取业务流数据
        if config['switch_business_code']:
            try:
                # 🆕 新功能：尝试从mermaid文件中提取业务流
                if hasattr(self.project, 'mermaid_output_dir') and self.project.mermaid_output_dir:
                    # 检查是否使用已存在的mmd文件
                    if hasattr(self.project, 'mermaid_result') and self.project.mermaid_result is None:
                        print("🎯 检测到使用已存在的Mermaid文件，从现有文件中提取业务流...")
                    else:
                        print("🎨 尝试从新生成的Mermaid文件中提取业务流...")
                    
                    mermaid_business_flows = self._extract_business_flows_from_mermaid()
                    
                    if mermaid_business_flows:
                        print("✅ 成功从Mermaid文件提取业务流，使用基于mermaid的业务流")
                        return {
                            'use_mermaid_flows': True,
                            'mermaid_business_flows': mermaid_business_flows,
                            'all_business_flow': {},
                            'all_business_flow_line': {},
                            'all_business_flow_context': {}
                        }
                    else:
                        print("⚠️ 从Mermaid文件提取业务流失败，回退到传统方式")
                
                # 传统方式：从context_factory获取业务流
                print("🔄 使用传统方式获取业务流...")
                all_business_flow, all_business_flow_line, all_business_flow_context = self.context_factory.get_business_flow_context(
                    self.project.functions_to_check
                )
                return {
                    'use_mermaid_flows': False,
                    'mermaid_business_flows': {},
                    'all_business_flow': all_business_flow,
                    'all_business_flow_line': all_business_flow_line,
                    'all_business_flow_context': all_business_flow_context
                }
            except Exception as e:
                print(f"获取业务流时出错: {str(e)}")
                return {}
        return {}
    
    def _extract_business_flows_from_mermaid(self) -> Dict[str, List[Dict]]:
        """从mermaid文件中提取业务流，并将步骤匹配到实际函数
        
        Returns:
            Dict[str, List[Dict]]: 业务流名称到实际函数对象列表的映射
        """
        try:
            # 1. 从所有mermaid文件中提取原始业务流JSON
            raw_business_flows = BusinessFlowUtils.extract_all_business_flows_from_mermaid_files(
                self.project.mermaid_output_dir, 
                self.project.project_id
            )
            
            if not raw_business_flows:
                print("❌ 未从Mermaid文件中提取到任何业务流")
                return {}
            
            print(f"\n🎯 从Mermaid文件提取的原始业务流详情：")
            print("="*80)
            for i, flow in enumerate(raw_business_flows, 1):
                flow_name = flow.get('name', f'未命名业务流{i}')
                steps = flow.get('steps', [])
                print(f"\n📋 业务流 #{i}: {flow_name}")
                print(f"   步骤数量: {len(steps)}")
                print(f"   步骤详情:")
                for j, step in enumerate(steps, 1):
                    print(f"     {j}. {step}")
            print("="*80)
            
            # 2. 🆕 关键逻辑：根据业务流步骤在functions_to_check中查找实际函数
            matched_flows = self._match_business_flow_steps_to_functions(raw_business_flows)
            
            if matched_flows:
                print(f"\n🎉 业务流步骤匹配结果详情：")
                print("="*80)
                
                total_flows = len(matched_flows)
                total_functions = sum(len(functions) for functions in matched_flows.values())
                
                print(f"✅ 成功匹配 {total_flows} 个业务流，共 {total_functions} 个函数")
                
                # 详细打印每个匹配的业务流
                for flow_name, functions in matched_flows.items():
                    print(f"\n📊 业务流: '{flow_name}'")
                    print(f"   匹配函数数: {len(functions)}")
                    print(f"   函数详情:")
                    
                    for i, func in enumerate(functions, 1):
                        print(f"     {i}. {func['name']}")
                        print(f"        📁 文件: {func['relative_file_path']}")
                        print(f"        📍 行号: {func['start_line']}-{func['end_line']}")
                        print(f"        🏢 合约: {func['contract_name']}")
                        # 显示函数内容的前50字符
                        content_preview = func.get('content', '')[:50].replace('\n', ' ')
                        print(f"        📝 内容预览: {content_preview}{'...' if len(func.get('content', '')) > 50 else ''}")
                
                print("="*80)
                
                return matched_flows
            else:
                print("❌ 业务流步骤匹配失败，未找到对应的函数")
                return {}
                
        except Exception as e:
            print(f"❌ 从Mermaid提取业务流时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _match_business_flow_steps_to_functions(self, raw_business_flows: List[Dict]) -> Dict[str, List[Dict]]:
        """根据业务流步骤在functions_to_check中查找实际函数对象
        
        Args:
            raw_business_flows: 从mermaid提取的原始业务流
            格式: [{"name": "flow1", "steps": ["Token.transfer", "DEX.swap"]}, ...]
            
        Returns:
            Dict[str, List[Dict]]: 业务流名称到实际函数对象列表的映射
        """
        print(f"\n🔍 开始匹配业务流步骤到实际函数...")
        
        # 创建函数查找索引，便于快速查找
        function_lookup = self._build_function_lookup_index()
        
        matched_flows = {}
        
        for flow in raw_business_flows:
            flow_name = flow.get('name', 'Unknown Flow')
            steps = flow.get('steps', [])
            
            print(f"\n🔄 处理业务流: '{flow_name}' ({len(steps)} 个步骤)")
            
            matched_functions = []
            for step_index, step in enumerate(steps, 1):
                print(f"   步骤 {step_index}: {step}")
                
                # 在functions_to_check中查找匹配的函数
                matched_func = self._find_function_by_step(step, function_lookup)
                
                if matched_func:
                    matched_functions.append(matched_func)
                    print(f"     ✅ 匹配到: {matched_func['name']} ({matched_func['relative_file_path']})")
                else:
                    print(f"     ❌ 未找到匹配的函数")
            
            if matched_functions:
                matched_flows[flow_name] = matched_functions
                print(f"   ✅ 业务流 '{flow_name}' 成功匹配 {len(matched_functions)} 个函数")
            else:
                print(f"   ⚠️ 业务流 '{flow_name}' 未匹配到任何函数")
        
        return matched_flows
    
    def _build_function_lookup_index(self) -> Dict[str, List[Dict]]:
        """构建函数查找索引
        
        Returns:
            Dict: 多种查找方式的索引
            {
                'by_name': {function_name: [function_objects]},
                'by_contract_function': {contract.function: [function_objects]},
                'by_file_function': {file.function: [function_objects]}
            }
        """
        function_lookup = {
            'by_name': {},           # transfer -> [所有transfer函数]
            'by_contract_function': {},  # Token.transfer -> [Token合约的transfer函数]
            'by_file_function': {}   # Token.sol.transfer -> [Token.sol文件的transfer函数]
        }
        
        for func in self.project.functions_to_check:
            func_name = func['name']
            
            # 提取纯函数名（去掉合约前缀）
            if '.' in func_name:
                contract_name, pure_func_name = func_name.split('.', 1)
                
                # 按纯函数名索引
                if pure_func_name not in function_lookup['by_name']:
                    function_lookup['by_name'][pure_func_name] = []
                function_lookup['by_name'][pure_func_name].append(func)
                
                # 按合约.函数名索引
                contract_func_key = f"{contract_name}.{pure_func_name}"
                if contract_func_key not in function_lookup['by_contract_function']:
                    function_lookup['by_contract_function'][contract_func_key] = []
                function_lookup['by_contract_function'][contract_func_key].append(func)
                
                # 按文件.函数名索引
                file_name = os.path.basename(func['relative_file_path']).replace('.sol', '').replace('.py', '').replace('.js', '').replace('.ts', '')
                file_func_key = f"{file_name}.{pure_func_name}"
                if file_func_key not in function_lookup['by_file_function']:
                    function_lookup['by_file_function'][file_func_key] = []
                function_lookup['by_file_function'][file_func_key].append(func)
        
        return function_lookup
    
    def _find_function_by_step(self, step: str, function_lookup: Dict) -> Dict:
        """根据业务流步骤查找对应的函数对象
        
        Args:
            step: 业务流步骤，如 "Token.transfer"
            function_lookup: 函数查找索引
            
        Returns:
            Dict: 匹配的函数对象，如果未找到返回None
        """
        # 策略1: 精确匹配 (合约.函数 或 文件.函数)
        if step in function_lookup['by_contract_function']:
            candidates = function_lookup['by_contract_function'][step]
            if candidates:
                return candidates[0]  # 返回第一个匹配
        
        if step in function_lookup['by_file_function']:
            candidates = function_lookup['by_file_function'][step]
            if candidates:
                return candidates[0]  # 返回第一个匹配
        
        # 策略2: 如果包含点号，尝试只匹配函数名部分
        if '.' in step:
            _, func_name = step.split('.', 1)
            if func_name in function_lookup['by_name']:
                candidates = function_lookup['by_name'][func_name]
                if candidates:
                    return candidates[0]  # 返回第一个匹配
        
        # 策略3: 直接按函数名匹配
        if step in function_lookup['by_name']:
            candidates = function_lookup['by_name'][step]
            if candidates:
                return candidates[0]  # 返回第一个匹配
        
        return None
    
    def _process_all_functions(self, config: Dict, all_business_flow_data: Dict):
        """处理所有函数"""
        # 如果开启了文件级别扫描
        if config['switch_file_code']:
            self._process_all_files(config)
        else:
            # 🆕 使用基于mermaid的业务流处理模式
            print("🎨 使用基于Mermaid的业务流处理模式")
            self._process_mermaid_business_flows(config, all_business_flow_data)
    
    def _process_mermaid_business_flows(self, config: Dict, all_business_flow_data: Dict):
        """基于Mermaid业务流的整体处理模式"""
        mermaid_flows = all_business_flow_data.get('mermaid_business_flows', {})
        
        if not mermaid_flows:
            print("❌ 未找到Mermaid业务流，跳过业务流处理")
            return
        
        print(f"\n🔄 开始处理 {len(mermaid_flows)} 个Mermaid业务流...")
        
        # 记录所有被业务流覆盖的函数（包括扩展后的）
        all_covered_functions = set()
        all_expanded_functions = []
        
        # 对每个业务流进行上下文扩展和任务创建
        for flow_name, flow_functions in mermaid_flows.items():
            print(f"\n📊 处理业务流: '{flow_name}'")
            print(f"   原始函数数: {len(flow_functions)}")
            
            # 1. 扩展业务流上下文
            expanded_functions = self._expand_business_flow_context(flow_functions, flow_name, config)
            
            print(f"   扩展后函数数: {len(expanded_functions)}")
            
            # 记录扩展后的函数
            all_expanded_functions.extend(expanded_functions)
            for func in expanded_functions:
                all_covered_functions.add(func['name'])
            
            # 2. 构建完整的业务流代码
            business_flow_code = self._build_business_flow_code_from_functions(expanded_functions)
            line_info_list = self._build_line_info_from_functions(expanded_functions)
            
            print(f"   业务流代码长度: {len(business_flow_code)} 字符")
            
            # 3. 为业务流中的每个函数创建任务
            self._create_tasks_for_business_flow(
                expanded_functions, business_flow_code, line_info_list, 
                flow_name, config
            )
        
        # 🆕 在FINE_GRAINED模式下分析业务流关联性并构造复合业务流
        if config['scan_mode'] == "COMMON_PROJECT_FINE_GRAINED":
            print(f"\n🔗 Fine Grained模式：分析业务流关联性...")
            compound_flows = self._analyze_business_flow_relationships(mermaid_flows, config)
            
            if compound_flows:
                print(f"✅ 构造了 {len(compound_flows)} 个复合业务流")
                
                # 为每个复合业务流创建任务
                for compound_name, compound_functions in compound_flows.items():
                    print(f"\n🔄 处理复合业务流: '{compound_name}'")
                    
                    # 扩展复合业务流上下文
                    expanded_compound = self._expand_business_flow_context(compound_functions, compound_name, config)
                    
                    # 记录扩展后的函数
                    all_expanded_functions.extend(expanded_compound)
                    for func in expanded_compound:
                        all_covered_functions.add(func['name'])
                    
                    # 构建复合业务流代码
                    compound_code = self._build_business_flow_code_from_functions(expanded_compound)
                    compound_line_info = self._build_line_info_from_functions(expanded_compound)
                    
                    print(f"   复合业务流代码长度: {len(compound_code)} 字符")
                    
                    # 为复合业务流创建任务
                    self._create_tasks_for_business_flow(
                        expanded_compound, compound_code, compound_line_info,
                        compound_name, config
                    )
        
        # 🆕 添加业务流覆盖度分析日志
        self._log_business_flow_coverage(all_covered_functions, all_expanded_functions)
    

    
    def _expand_business_flow_context(self, flow_functions: List[Dict], flow_name: str, config: Dict = None) -> List[Dict]:
        """扩展业务流的上下文，使用call tree和rag进行1层扩展
        
        Args:
            flow_functions: 业务流中的原始函数列表
            flow_name: 业务流名称
            config: 配置信息
            
        Returns:
            List[Dict]: 扩展后的函数列表（已去重）
        """
        print(f"   🔍 开始扩展业务流 '{flow_name}' 的上下文...")
        
        # 🆕 检查 huge_project 开关
        if config and config.get('huge_project', False):
            print(f"   🚀 检测到 huge_project=True，跳过上下文扩展，直接使用原始函数")
            return flow_functions
        
        # 存储所有扩展后的函数，使用set去重
        expanded_functions_set = set()
        expanded_functions_list = []
        
        # 首先添加原始函数
        for func in flow_functions:
            func_key = f"{func['name']}_{func['start_line']}_{func['end_line']}"
            if func_key not in expanded_functions_set:
                expanded_functions_set.add(func_key)
                expanded_functions_list.append(func)
        
        print(f"      原始函数: {len(expanded_functions_list)} 个")
        
        # 1. 使用call tree扩展上下文
        call_tree_expanded = self._expand_via_call_tree(flow_functions)
        added_via_call_tree = 0
        
        for func in call_tree_expanded:
            func_key = f"{func['name']}_{func['start_line']}_{func['end_line']}"
            if func_key not in expanded_functions_set:
                expanded_functions_set.add(func_key)
                expanded_functions_list.append(func)
                added_via_call_tree += 1
        
        print(f"      Call Tree扩展: +{added_via_call_tree} 个函数")
        
        # 2. 使用RAG扩展上下文
        rag_expanded = self._expand_via_rag(flow_functions)
        added_via_rag = 0
        
        for func in rag_expanded:
            func_key = f"{func['name']}_{func['start_line']}_{func['end_line']}"
            if func_key not in expanded_functions_set:
                expanded_functions_set.add(func_key)
                expanded_functions_list.append(func)
                added_via_rag += 1
        
        print(f"      RAG扩展: +{added_via_rag} 个函数")
        print(f"      总计: {len(expanded_functions_list)} 个函数 (去重后)")
        
        return expanded_functions_list
    
    def _expand_via_call_tree(self, functions: List[Dict]) -> List[Dict]:
        """使用call tree扩展函数上下文（1层）"""
        expanded_functions = []
        
        if not hasattr(self.project, 'call_trees') or not self.project.call_trees:
            print("      ⚠️ 未找到call trees，跳过call tree扩展")
            return expanded_functions
        
        # 从context.function_utils导入函数处理工具
        from context.function_utils import FunctionUtils
        
        # 提取函数名列表
        function_names = []
        for func in functions:
            if '.' in func['name']:
                pure_func_name = func['name'].split('.', 1)[1]
                function_names.append(pure_func_name)
        
        if not function_names:
            return expanded_functions
        
        try:
            # 使用FunctionUtils获取相关函数，返回格式为pairs
            related_text, function_pairs = FunctionUtils.extract_related_functions_by_level(
                self.project, function_names, level=1, return_pairs=True
            )
            
            # 将相关函数转换为函数对象
            for func_name, func_content in function_pairs:
                # 在functions_to_check中查找对应的函数对象
                for check_func in self.project.functions_to_check:
                    if check_func['name'].endswith('.' + func_name) and check_func['content'] == func_content:
                        expanded_functions.append(check_func)
                        break
            
        except Exception as e:
            print(f"      ❌ Call tree扩展失败: {str(e)}")
        
        return expanded_functions
    
    def _expand_via_rag(self, functions: List[Dict]) -> List[Dict]:
        """使用RAG扩展函数上下文"""
        expanded_functions = []
        
        try:
            # 检查是否有RAG处理器
            if not hasattr(self.context_factory, 'rag_processor') or not self.context_factory.rag_processor:
                print("      ⚠️ 未找到RAG处理器，跳过RAG扩展")
                return expanded_functions
            
            # 为每个函数查找相似函数
            for func in functions:
                func_content = func.get('content', '')
                if len(func_content) > 50:  # 只对有足够内容的函数进行RAG查询
                    try:
                        similar_functions = self.context_factory.search_similar_functions(
                            func['name'], k=3  # 每个函数查找3个相似函数
                        )
                        
                        # 将相似函数转换为函数对象
                        for similar_func_data in similar_functions:
                            # 在functions_to_check中查找对应的函数对象
                            similar_func_name = similar_func_data.get('name', '')
                            for check_func in self.project.functions_to_check:
                                if check_func['name'] == similar_func_name:
                                    expanded_functions.append(check_func)
                                    break
                                    
                    except Exception as e:
                        print(f"      ⚠️ 函数 {func['name']} RAG查询失败: {str(e)}")
                        continue
        
        except Exception as e:
            print(f"      ❌ RAG扩展失败: {str(e)}")
        
        return expanded_functions
    
    def _create_tasks_for_business_flow(self, expanded_functions: List[Dict], 
                                      business_flow_code: str, line_info_list: List[Dict],
                                      flow_name: str, config: Dict):
        """为业务流创建任务（整个业务流一个任务，而不是每个函数一个任务）"""
        
        print(f"   📝 为业务流 '{flow_name}' 创建任务...")
        
        # 选择一个代表性函数作为任务的主要函数（通常是第一个函数）
        representative_function = expanded_functions[0] if expanded_functions else None
        if not representative_function:
            print("   ❌ 业务流中无有效函数，跳过任务创建")
            return
        
        # 生成检查清单和业务类型分析（基于整个业务流）
        checklist, business_type_str = self._generate_checklist_and_analysis(
            business_flow_code, 
            representative_function['content'], 
            representative_function['contract_name'], 
            is_business_flow=True
        )
        
        print(f"   📋 生成的业务类型: {business_type_str}")
        print(f"   📊 业务流包含 {len(expanded_functions)} 个函数")
        
        # 为整个业务流创建任务（不是为每个函数创建）
        tasks_created = 0
        for i in range(config['actual_iteration_count']):
            # print(f"      📝 创建业务流 '{flow_name}' 的第 {i+1} 个任务...")
            
            # 使用代表性函数作为任务载体，但任务包含整个业务流的信息
            self._create_planning_task(
                representative_function, checklist, business_type_str,
                business_flow_code, line_info_list,
                if_business_flow_scan=1, config=config
            )
            tasks_created += 1
        
        print(f"   ✅ 为业务流 '{flow_name}' 成功创建 {tasks_created} 个任务")
        print(f"      每个任务包含整个业务流的 {len(expanded_functions)} 个函数的完整上下文")
    
    def _process_all_files(self, config: Dict):
        """处理所有文件 - 文件级别扫描"""
        # 只支持 pure 和 common fine grained 模式
        if config['scan_mode'] not in ['PURE', 'COMMON_PROJECT_FINE_GRAINED']:
            print(f"文件级别扫描不支持 {config['scan_mode']} 模式，跳过")
            return
        
        # 按文件路径分组函数
        files_dict = {}
        for function in self.project.functions_to_check:
            file_path = function['relative_file_path']
            if file_path not in files_dict:
                files_dict[file_path] = []
            files_dict[file_path].append(function)
        
        # 对每个文件进行处理
        for file_path, functions in tqdm(files_dict.items(), desc="Processing files"):
            self._process_single_file(file_path, functions, config)
    
    def _process_single_file(self, file_path: str, functions: List[Dict], config: Dict):
        """处理单个文件"""
        print(f"————————Processing file: {file_path}————————")
        
        # 检查是否应该排除
        if ConfigUtils.should_exclude_in_planning(self.project, file_path):
            print(f"Excluding file {file_path} in planning process based on configuration")
            return
        
        # 获取文件内容 (使用第一个函数的contract_code作为文件内容)
        if not functions:
            return
        
        file_content = functions[0]['contract_code']
        
        # 检查文件内容长度
        if len(file_content) < config['threshold']:
            print(f"File content for {file_path} is too short for <{config['threshold']}, skipping...")
            return
        
        # 创建文件级别的任务
        self._handle_file_code_planning(file_path, functions, file_content, config)
    
    def _handle_file_code_planning(self, file_path: str, functions: List[Dict], file_content: str, config: Dict):
        """处理文件代码规划"""
        # 不需要生成checklist，直接创建任务
        checklist = ""
        
        # 获取代表性函数信息（使用第一个函数的信息作为模板）
        representative_function = functions[0]
        
        # 根据模式决定循环次数
        if config['scan_mode'] == "COMMON_PROJECT_FINE_GRAINED":
            iteration_count = config['actual_iteration_count']
        else:  # PURE模式
            iteration_count = config['base_iteration_count']
        
        # 创建任务
        for i in range(iteration_count):
            self._create_file_planning_task(
                file_path, representative_function, file_content, 
                checklist, config
            )
    
    def _create_file_planning_task(
        self, 
        file_path: str, 
        representative_function: Dict, 
        file_content: str, 
        checklist: str, 
        config: Dict
    ):
        """创建文件级别的规划任务"""
        # 处理recommendation字段
        recommendation = ""
        
        # 如果是COMMON_PROJECT_FINE_GRAINED模式，设置checklist类型到recommendation
        if config['scan_mode'] == "COMMON_PROJECT_FINE_GRAINED":
            checklist_dict = VulPromptCommon.vul_prompt_common_new(self.fine_grained_counter % config['total_checklist_count'])
            if checklist_dict:
                checklist_key = list(checklist_dict.keys())[0]
                recommendation = checklist_key
                # print(f"[DEBUG🐞]📋Setting recommendation to checklist key: {checklist_key} (index: {self.fine_grained_counter % config['total_checklist_count']})")
            self.fine_grained_counter += 1
        
        task = Project_Task(
            project_id=self.project.project_id,
            name=f"FILE:{file_path}",  # 文件级别的任务名称
            content=file_content,  # 使用整个文件内容
            keyword=str(random.random()),
            business_type='',
            sub_business_type='',
            function_type='',
            rule='',
            result='',
            result_gpt4='',
            score='',
            category='',
            contract_code=file_content,  # 使用文件内容
            risklevel='',
            similarity_with_rule='',
            description=checklist,
            start_line=representative_function['start_line'],
            end_line=representative_function['end_line'],
            relative_file_path=representative_function['relative_file_path'],
            absolute_file_path=representative_function['absolute_file_path'],
            recommendation=recommendation,
            title='',
            business_flow_code=file_content,
            business_flow_lines='',
            business_flow_context='',
            if_business_flow_scan=0  # 文件级别扫描不是业务流扫描
        )
        self.taskmgr.add_task_in_one(task)
    
    def _generate_checklist_and_analysis(
        self, 
        business_flow_code: str, 
        content: str, 
        contract_name: str, 
        is_business_flow: bool
    ) -> tuple[str, str]:
        """生成检查清单和业务类型分析"""
        checklist = ""
        business_type_str = ""
        
        if self.checklist_generator:
            print(f"\n📋 为{'业务流程' if is_business_flow else '函数代码'}生成检查清单...")
            
            # 准备代码用于检查清单生成
            code_for_checklist = f"{business_flow_code}\n{content}" if is_business_flow else content
            business_description, checklist = self.checklist_generator.generate_checklist(code_for_checklist)
            
            # 写入CSV文件
            csv_file_name = "checklist_business_code.csv" if is_business_flow else "checklist_function_code.csv"
            self._write_checklist_to_csv(
                csv_file_name, contract_name, 
                business_flow_code if is_business_flow else "", 
                content, business_description, checklist
            )
            
            print(f"✅ Checklist written to {csv_file_name}")
            print("✅ 检查清单生成完成")
            
            # 如果是业务流，进行业务类型分析
            if is_business_flow:
                business_type_str = self._analyze_business_type(business_flow_code, content)
        
        return checklist, business_type_str
    
    def _write_checklist_to_csv(
        self, 
        csv_file_path: str, 
        contract_name: str, 
        business_flow_code: str, 
        content: str, 
        business_description: str, 
        checklist: str
    ):
        """将检查清单写入CSV文件"""
        with open(csv_file_path, mode='a', newline='', encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file)
            if csv_file.tell() == 0:
                csv_writer.writerow(["contract_name", "business_flow_code", "content", "business_description", "checklist"])
            csv_writer.writerow([contract_name, business_flow_code, content, business_description, checklist])
    
    def _analyze_business_type(self, business_flow_code: str, content: str) -> str:
        """分析业务类型"""
        try:
            core_prompt = CorePrompt()
            type_check_prompt = core_prompt.type_check_prompt()
            
            formatted_prompt = type_check_prompt.format(business_flow_code + "\n" + content)
            type_response = common_ask_for_json(formatted_prompt)
            print(f"[DEBUG] Claude返回的响应: {type_response}")
            
            cleaned_response = type_response
            print(f"[DEBUG] 清理后的响应: {cleaned_response}")
            
            type_data = json.loads(cleaned_response)
            business_type = type_data.get('business_types', ['other'])
            print(f"[DEBUG] 解析出的业务类型: {business_type}")
            
            # 防御性逻辑：确保business_type是列表类型
            if not isinstance(business_type, list):
                business_type = [str(business_type)]
            
            # 处理 other 的情况
            if 'other' in business_type and len(business_type) > 1:
                business_type.remove('other')
            
            # 确保列表不为空
            if not business_type:
                business_type = ['other']
            
            business_type_str = ','.join(str(bt) for bt in business_type)
            print(f"[DEBUG] 最终的业务类型字符串: {business_type_str}")
            
            return business_type_str
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON解析失败: {str(e)}")
            return 'other'
        except Exception as e:
            print(f"[ERROR] 处理业务类型时发生错误: {str(e)}")
            return 'other'
    
    def _create_planning_task(
        self, 
        function: Dict, 
        checklist: str, 
        business_type_str: str, 
        business_flow_code: str, 
        business_flow_lines, 
        if_business_flow_scan: int,
        config: Dict = None
    ):
        """创建规划任务"""
        # 处理recommendation字段
        recommendation = business_type_str
        
        # 如果是COMMON_PROJECT_FINE_GRAINED模式，设置checklist类型到recommendation
        if config and config['scan_mode'] == "COMMON_PROJECT_FINE_GRAINED":
            # 获取当前checklist类型
            checklist_dict = VulPromptCommon.vul_prompt_common_new(self.fine_grained_counter % config['total_checklist_count'])
            if checklist_dict:
                checklist_key = list(checklist_dict.keys())[0]
                recommendation = checklist_key
                # print(f"[DEBUG🐞]📋Setting recommendation to checklist key: {checklist_key} (index: {self.fine_grained_counter % config['total_checklist_count']})")
            self.fine_grained_counter += 1
        
        # 将business_flow_lines序列化为JSON字符串以便存储到数据库
        business_flow_lines_str = ""
        if business_flow_lines:
            try:
                if isinstance(business_flow_lines, (list, dict)):
                    business_flow_lines_str = json.dumps(business_flow_lines, ensure_ascii=False)
                else:
                    business_flow_lines_str = str(business_flow_lines)
            except Exception as e:
                print(f"[WARNING] 序列化business_flow_lines时出错: {e}")
                business_flow_lines_str = str(business_flow_lines)
        
        task = Project_Task(
            project_id=self.project.project_id,
            name=function['name'],
            content=function['content'],
            keyword=str(random.random()),
            business_type='',
            sub_business_type='',
            function_type='',
            rule='',
            result='',
            result_gpt4='',
            score='',
            category='',
            contract_code=function['contract_code'],
            risklevel='',
            similarity_with_rule='',
            description=checklist,
            start_line=function['start_line'],
            end_line=function['end_line'],
            relative_file_path=function['relative_file_path'],
            absolute_file_path=function['absolute_file_path'],
            recommendation=recommendation,
            title='',
            business_flow_code=business_flow_code,
            business_flow_lines=business_flow_lines_str,
            business_flow_context='',
            if_business_flow_scan=if_business_flow_scan
        )
        self.taskmgr.add_task_in_one(task) 
    
    def _build_business_flow_code_from_functions(self, functions: List[Dict]) -> str:
        """从函数列表构建业务流代码
        
        Args:
            functions: 函数列表
            
        Returns:
            str: 拼接的业务流代码
        """
        business_flow_code = ""
        
        for func in functions:
            content = func.get('content', '')
            if content:
                business_flow_code += f"\n// 函数: {func['name']}\n"
                business_flow_code += content + "\n"
        
        return business_flow_code.strip()
    
    def _build_line_info_from_functions(self, functions: List[Dict]) -> List[Dict]:
        """从函数列表构建行信息
        
        Args:
            functions: 函数列表
            
        Returns:
            List[Dict]: 行信息列表
        """
        line_info_list = []
        
        for func in functions:
            line_info = {
                'function_name': func['name'],
                'start_line': func.get('start_line', 0),
                'end_line': func.get('end_line', 0),
                'file_path': func.get('relative_file_path', '')
            }
            line_info_list.append(line_info)
        
        return line_info_list
    
    def _analyze_business_flow_relationships(self, mermaid_flows: Dict, config: Dict) -> Dict[str, List[Dict]]:
        """分析业务流之间的关联性，构造复合业务流
        
        Args:
            mermaid_flows: 原始业务流字典
            config: 扫描配置
            
        Returns:
            Dict[str, List[Dict]]: 复合业务流字典，key为复合业务流名称，value为函数列表
        """
        if len(mermaid_flows) < 2:
            print("   业务流数量少于2个，跳过关联性分析")
            return {}
        
        print(f"   开始分析 {len(mermaid_flows)} 个业务流的关联性...")
        
        # 1. 准备业务流信息用于LLM分析
        flow_summaries = []
        flow_functions_map = {}  # 保存每个流的函数信息
        
        for flow_name, flow_functions in mermaid_flows.items():
            # 提取业务流的函数名列表
            function_names = [func['name'] for func in flow_functions]
            
            # 构建业务流摘要
            summary = {
                'name': flow_name,
                'functions': function_names,
                'function_count': len(function_names)
            }
            flow_summaries.append(summary)
            flow_functions_map[flow_name] = flow_functions
        
        # 2. 调用LLM分析关联性
        try:
            relationship_analysis = self._call_llm_for_flow_relationships(flow_summaries)
            
            if not relationship_analysis:
                print("   ❌ LLM关联性分析失败")
                return {}
            
            # 3. 根据分析结果构造复合业务流
            compound_flows = self._construct_compound_flows(
                relationship_analysis, flow_functions_map
            )
            
            return compound_flows
            
        except Exception as e:
            print(f"   ❌ 业务流关联性分析失败: {str(e)}")
            return {}
    
    def _call_llm_for_flow_relationships(self, flow_summaries: List[Dict]) -> Dict:
        """调用LLM分析业务流关联性
        
        Args:
            flow_summaries: 业务流摘要列表
            
        Returns:
            Dict: LLM分析结果
        """
        
        # 构建prompt
        prompt = self._build_flow_relationship_prompt(flow_summaries)
        
        try:
            print("   🤖 调用LLM分析业务流关联性...")
            
            # 调用LLM
            response = common_ask_for_json(prompt)
            
            if isinstance(response, str):
                response = json.loads(response)
            
            print(f"   ✅ LLM分析完成，识别到 {len(response.get('related_groups', []))} 个相关组")
            return response
            
        except Exception as e:
            print(f"   ❌ LLM调用失败: {str(e)}")
            return {}
    
    def _build_flow_relationship_prompt(self, flow_summaries: List[Dict]) -> str:
        """构建业务流关联性分析的prompt
        
        Args:
            flow_summaries: 业务流摘要列表
            
        Returns:
            str: 构建的prompt
        """
        
        # 构建业务流信息字符串
        flows_info = ""
        for i, flow in enumerate(flow_summaries, 1):
            flows_info += f"\n{i}. 业务流: {flow['name']}\n"
            flows_info += f"   函数列表: {', '.join(flow['functions'])}\n"
            flows_info += f"   函数数量: {flow['function_count']}\n"
        
        prompt = f"""
你是一个智能合约业务流分析专家。请分析以下 {len(flow_summaries)} 个业务流之间的关联性，识别出哪些业务流是相互影响和相关的。

## 业务流信息:
{flows_info}

## 分析任务:
1. 分析每个业务流的功能特征
2. 识别业务流之间的依赖关系、数据交互、状态影响等关联性
3. 将相关的业务流分组

## 关联性判断标准:
- **强关联**: 业务流之间有直接的函数调用关系、共享状态变量、数据依赖
- **功能关联**: 业务流属于同一业务模块，如都涉及代币转账、权限管理、价格计算等
- **时序关联**: 业务流在执行时序上有先后依赖关系
- **状态关联**: 业务流会影响相同的合约状态或存储变量

## 输出要求:
请以JSON格式输出，包含以下字段：

```json
{{
  "analysis_summary": "整体分析总结",
  "total_flows": {len(flow_summaries)},
  "related_groups": [
    {{
      "group_name": "复合业务流的名称",
      "description": "该组业务流的关联性描述",
      "flow_names": ["相关的业务流名称1", "业务流名称2"],
      "relationship_type": "关联类型：强关联/功能关联/时序关联/状态关联",
      "priority": "优先级：high/medium/low"
    }}
  ],
  "independent_flows": ["独立的业务流名称列表"]
}}
```

## 注意事项:
1. 只有当业务流之间确实存在有意义的关联时才进行分组
2. 一个业务流可以同时属于多个相关组
3. 每个相关组至少包含2个业务流
4. 为复合业务流起有意义的名称，体现其综合功能
5. 优先识别高优先级的强关联关系

请开始分析：
"""
        
        return prompt.strip()
    
    def _construct_compound_flows(self, relationship_analysis: Dict, flow_functions_map: Dict) -> Dict[str, List[Dict]]:
        """根据关联性分析结果构造复合业务流
        
        Args:
            relationship_analysis: LLM分析结果
            flow_functions_map: 业务流到函数的映射
            
        Returns:
            Dict[str, List[Dict]]: 复合业务流字典
        """
        compound_flows = {}
        
        related_groups = relationship_analysis.get('related_groups', [])
        
        for group in related_groups:
            group_name = group.get('group_name', '')
            flow_names = group.get('flow_names', [])
            priority = group.get('priority', 'medium')
            
            if len(flow_names) < 2:
                continue
            
            print(f"   🔗 构造复合业务流: '{group_name}' (包含 {len(flow_names)} 个业务流)")
            print(f"      关联类型: {group.get('relationship_type', 'unknown')}")
            print(f"      优先级: {priority}")
            
            # 合并相关业务流的所有函数
            compound_functions = []
            function_names_seen = set()  # 去重
            
            for flow_name in flow_names:
                if flow_name in flow_functions_map:
                    for func in flow_functions_map[flow_name]:
                        func_key = f"{func['name']}_{func.get('start_line', 0)}"
                        if func_key not in function_names_seen:
                            compound_functions.append(func)
                            function_names_seen.add(func_key)
            
            if compound_functions:
                # 为复合业务流生成唯一名称
                compound_name = f"复合业务流_{group_name}_{priority}"
                compound_flows[compound_name] = compound_functions
                
                print(f"      ✅ 复合业务流包含 {len(compound_functions)} 个函数")
        
        return compound_flows
    
    def _log_business_flow_coverage(self, all_covered_functions: set, all_expanded_functions: List[Dict]):
        """记录业务流覆盖度分析"""
        total_functions = len(self.project.functions_to_check)
        covered_count = len(all_covered_functions)
        uncovered_count = total_functions - covered_count
        coverage_rate = (covered_count / total_functions * 100) if total_functions > 0 else 0
        
        print(f"\n🔍 业务流覆盖度分析:")
        print("="*80)
        print(f"📊 总函数数: {total_functions}")
        print(f"✅ 被业务流覆盖的函数数: {covered_count}")
        print(f"❌ 未被业务流覆盖的函数数: {uncovered_count}")
        print(f"📈 覆盖率: {coverage_rate:.2f}%")
        print("="*80)
        
        if uncovered_count > 0:
            print(f"\n❌ 未被业务流覆盖的函数详情 ({uncovered_count} 个):")
            print("-"*80)
            
            # 收集未覆盖函数信息
            uncovered_functions = []
            for func in self.project.functions_to_check:
                if func['name'] not in all_covered_functions:
                    uncovered_functions.append(func)
            
            # 按函数长度分组统计
            length_groups = {
                'very_short': [],    # < 50 字符
                'short': [],         # 50-200 字符  
                'medium': [],        # 200-500 字符
                'long': [],          # 500-1000 字符
                'very_long': []      # > 1000 字符
            }
            
            # 输出每个未覆盖函数的详细信息
            for i, func in enumerate(uncovered_functions, 1):
                func_length = len(func.get('content', ''))
                
                print(f"{i:3d}. 函数: {func['name']}")
                print(f"     文件: {func.get('relative_file_path', 'unknown')}")
                print(f"     合约: {func.get('contract_name', 'unknown')}")
                print(f"     长度: {func_length} 字符")
                print(f"     行号: {func.get('start_line', 'N/A')}-{func.get('end_line', 'N/A')}")
                
                # 显示函数内容预览
                content_preview = func.get('content', '')[:80].replace('\n', ' ').strip()
                if len(func.get('content', '')) > 80:
                    content_preview += "..."
                print(f"     预览: {content_preview}")
                print()
                
                # 分组统计
                if func_length < 50:
                    length_groups['very_short'].append(func)
                elif func_length < 200:
                    length_groups['short'].append(func)
                elif func_length < 500:
                    length_groups['medium'].append(func)
                elif func_length < 1000:
                    length_groups['long'].append(func)
                else:
                    length_groups['very_long'].append(func)
            
            print("-"*80)
            print("\n📊 未覆盖函数长度分布:")
            for group_name, group_functions in length_groups.items():
                if group_functions:
                    group_display = {
                        'very_short': '极短函数 (< 50字符)',
                        'short': '短函数 (50-200字符)',
                        'medium': '中等函数 (200-500字符)',
                        'long': '长函数 (500-1000字符)',
                        'very_long': '极长函数 (> 1000字符)'
                    }
                    
                    avg_length = sum(len(f.get('content', '')) for f in group_functions) / len(group_functions)
                    print(f"   {group_display[group_name]}: {len(group_functions)} 个 (平均长度: {avg_length:.0f}字符)")
                    
                    # 显示该组的函数名示例
                    func_names = [f['name'].split('.')[-1] for f in group_functions[:3]]
                    if len(group_functions) > 3:
                        func_names.append(f"... 还有{len(group_functions)-3}个")
                    print(f"     示例: {', '.join(func_names)}")
            
            # 分析未覆盖函数的文件分布
            file_distribution = {}
            for func in uncovered_functions:
                file_path = func.get('relative_file_path', 'unknown')
                if file_path not in file_distribution:
                    file_distribution[file_path] = []
                file_distribution[file_path].append(func)
            
            print(f"\n📁 未覆盖函数的文件分布:")
            for file_path, file_functions in sorted(file_distribution.items(), key=lambda x: len(x[1]), reverse=True):
                avg_length = sum(len(f.get('content', '')) for f in file_functions) / len(file_functions)
                print(f"   {file_path}: {len(file_functions)} 个函数 (平均长度: {avg_length:.0f}字符)")
            
            print("-"*80)
            
            # 给出覆盖度评估
            if coverage_rate >= 80:
                print(f"✅ 覆盖率良好 ({coverage_rate:.2f}%)！")
            elif coverage_rate >= 60:
                print(f"⚠️  覆盖率中等 ({coverage_rate:.2f}%)")
            else:
                print(f"❌ 覆盖率较低 ({coverage_rate:.2f}%)")
        else:
            print("\n🎉 所有函数均被业务流覆盖！业务流分析完美！")
        
        print("="*80) 