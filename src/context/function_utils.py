from typing import List, Dict, Tuple, Union, Optional
import os


class FunctionUtils:
    """函数处理相关的工具函数"""
    
    @staticmethod
    def extract_related_functions_by_level(
        project_or_project_audit, 
        function_names: List[str], 
        level: int,
        return_pairs: bool = False
    ) -> Union[str, Tuple[str, List[Tuple[str, str]]]]:
        """
        从call_trees中提取指定函数相关的上下游函数信息并扁平化处理
        
        Args:
            project_or_project_audit: 项目对象或项目审计对象
            function_names: 要分析的函数名列表
            level: 要分析的层级深度
            return_pairs: 是否返回函数名-内容对，默认False只返回拼接文本
            
        Returns:
            Union[str, Tuple[str, List[Tuple[str, str]]]]:
            - 如果return_pairs=False: 返回拼接后的函数内容文本
            - 如果return_pairs=True: 返回(拼接文本, [(函数名, 函数内容), ...])
        """
        # 🆕 检查 huge_project 开关
        huge_project = eval(os.environ.get('HUGE_PROJECT', 'False'))
        if huge_project:
            print("🚀 检测到 HUGE_PROJECT=True，跳过 call tree 相关函数提取")
            return ("", []) if return_pairs else ""
        
        # 兼容不同的项目对象
        if hasattr(project_or_project_audit, 'call_trees'):
            call_trees = project_or_project_audit.call_trees
            functions_to_check = getattr(project_or_project_audit, 'functions_to_check', [])
        else:
            # 如果传入的不是有效对象，返回空结果
            return ("", []) if return_pairs else ""
            
        def get_functions_from_tree(tree, current_level=0, max_level=level, collected_funcs=None, level_stats=None):
            if collected_funcs is None:
                collected_funcs = []
            if level_stats is None:
                level_stats = {}
            
            if not tree or current_level > max_level:
                return collected_funcs, level_stats
                
            if tree['function_data']:
                collected_funcs.append(tree['function_data'])
                level_stats[current_level] = level_stats.get(current_level, 0) + 1
                
            if current_level < max_level:
                for child in tree['children']:
                    get_functions_from_tree(child, current_level + 1, max_level, collected_funcs, level_stats)
                    
            return collected_funcs, level_stats

        all_related_functions = []
        statistics = {
            'total_layers': level,
            'upstream_stats': {},
            'downstream_stats': {}
        }
        
        seen_functions = set()  
        unique_functions = []   
        
        for func_name in function_names:
            for tree_data in call_trees:
                if tree_data['function'] == func_name:
                    if tree_data['upstream_tree']:
                        upstream_funcs, upstream_stats = get_functions_from_tree(tree_data['upstream_tree'])
                        all_related_functions.extend(upstream_funcs)
                        for level_key, count in upstream_stats.items():
                            statistics['upstream_stats'][level_key] = statistics['upstream_stats'].get(level_key, 0) + count
                            
                    if tree_data['downstream_tree']:
                        downstream_funcs, downstream_stats = get_functions_from_tree(tree_data['downstream_tree'])
                        all_related_functions.extend(downstream_funcs)
                        for level_key, count in downstream_stats.items():
                            statistics['downstream_stats'][level_key] = statistics['downstream_stats'].get(level_key, 0) + count
                        
                    for func in functions_to_check:
                        if func['name'].split('.')[-1] == func_name:
                            all_related_functions.append(func)
                            break
                            
                    break
        
        # 增强的去重处理
        function_name_content_pairs = []
        for func in all_related_functions:
            func_identifier = f"{func['name']}_{hash(func['content'])}"
            if func_identifier not in seen_functions:
                seen_functions.add(func_identifier)
                unique_functions.append(func)
                if return_pairs:
                    # 保存函数名(只取最后一部分)和内容
                    function_name_content_pairs.append((func['name'].split('.')[-1], func['content']))
        
        # 拼接所有函数内容
        combined_text_parts = []
        for func in unique_functions:
            state_vars = None
            for tree_data in call_trees:
                if tree_data['function'] == func['name'].split('.')[-1]:
                    state_vars = tree_data.get('state_variables', '')
                    break
            
            function_text = []
            if state_vars:
                function_text.append("// Contract State Variables:")
                function_text.append(state_vars)
                function_text.append("\n// Function Implementation:")
            function_text.append(func['content'])
            
            combined_text_parts.append('\n'.join(function_text))
        
        combined_text = '\n\n'.join(combined_text_parts)
        
        # 打印统计信息
        print(f"\nFunction Call Tree Statistics:")
        print(f"Total Layers Analyzed: {level}")
        print("\nUpstream Statistics:")
        for layer, count in statistics['upstream_stats'].items():
            print(f"Layer {layer}: {count} functions")
        print("\nDownstream Statistics:")
        for layer, count in statistics['downstream_stats'].items():
            print(f"Layer {layer}: {count} functions")
        print(f"\nTotal Unique Functions: {len(unique_functions)}")
        
        # 根据参数决定返回格式
        if return_pairs:
            return combined_text, function_name_content_pairs
        else:
            return combined_text
    
    @staticmethod
    def get_function_by_name(functions: List[Dict], function_name: str) -> Optional[Dict]:
        """根据函数名获取函数信息"""
        for func in functions:
            if func['name'].split('.')[-1] == function_name:
                return func
        return None
    
    @staticmethod
    def filter_functions_by_visibility(functions: List[Dict], visibility: str) -> List[Dict]:
        """根据可见性过滤函数"""
        return [func for func in functions if func.get('visibility') == visibility]
    
    @staticmethod
    def filter_functions_by_mutability(functions: List[Dict], mutability: str) -> List[Dict]:
        """根据状态可变性过滤函数"""
        return [func for func in functions if func.get('stateMutability') == mutability]
    
    @staticmethod
    def get_function_names_from_content(content: str) -> List[str]:
        """从代码内容中提取函数名"""
        import re
        # 简单的函数名提取正则表达式
        pattern = r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        matches = re.findall(pattern, content)
        return matches
    
    @staticmethod
    def group_functions_by_file(functions: List[Dict]) -> Dict[str, List[Dict]]:
        """按文件路径分组函数"""
        file_groups = {}
        for func in functions:
            file_path = func.get('relative_file_path', '')
            if file_path not in file_groups:
                file_groups[file_path] = []
            file_groups[file_path].append(func)
        return file_groups
    
    @staticmethod
    def get_function_signature(func: Dict) -> str:
        """获取函数签名"""
        name = func.get('name', '').split('.')[-1]
        visibility = func.get('visibility', '')
        mutability = func.get('stateMutability', '')
        modifiers = func.get('modifiers', [])
        
        signature_parts = [name]
        if visibility:
            signature_parts.append(visibility)
        if mutability and mutability != 'nonpayable':
            signature_parts.append(mutability)
        if modifiers:
            signature_parts.extend(modifiers)
        
        return ' '.join(signature_parts)
    
    @staticmethod
    def extract_function_calls(content: str) -> List[str]:
        """从函数内容中提取函数调用"""
        import re
        # 提取函数调用的正则表达式
        pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        matches = re.findall(pattern, content)
        # 过滤掉一些常见的非函数调用
        excluded = {'if', 'for', 'while', 'require', 'assert', 'revert'}
        return [match for match in matches if match not in excluded]
    
    @staticmethod
    def calculate_function_complexity(func: Dict) -> int:
        """计算函数复杂度（简单的行数计算）"""
        content = func.get('content', '')
        lines = content.split('\n')
        # 去掉空行和注释行
        code_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('//')]
        return len(code_lines)
    
    @staticmethod
    def get_function_dependencies(func: Dict, all_functions: List[Dict]) -> List[str]:
        """获取函数的依赖关系"""
        content = func.get('content', '')
        function_calls = FunctionUtils.extract_function_calls(content)
        
        dependencies = []
        for call in function_calls:
            for other_func in all_functions:
                if other_func['name'].split('.')[-1] == call:
                    dependencies.append(call)
                    break
        
        return dependencies
    
    @staticmethod
    def merge_function_contexts(contexts: List[str]) -> str:
        """合并多个函数上下文"""
        if not contexts:
            return ""
        
        # 去重并合并
        unique_contexts = list(set(contexts))
        return '\n\n'.join(unique_contexts) 