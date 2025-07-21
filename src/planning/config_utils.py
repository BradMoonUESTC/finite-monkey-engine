import json
import os
import sys
import os.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import Dict, Any


class ConfigUtils:
    """配置相关的工具函数"""
    
    @staticmethod
    def should_exclude_in_planning(project, relative_file_path: str) -> bool:
        """
        判断一个文件路径是否应该在planning过程中被排除
        
        Args:
            project: 项目对象
            relative_file_path: 相对文件路径
            
        Returns:
            bool: 如果应该排除返回True，否则返回False
        """
        try:
            # 读取datasets.json文件
            datasets_path = "src/dataset/agent-v1-c4/datasets.json"
            if not os.path.exists(datasets_path):
                print(f"数据集配置文件不存在: {datasets_path}")
                return False
                
            with open(datasets_path, 'r', encoding='utf-8') as f:
                datasets = json.load(f)
                
            # 在datasets中查找与project_id匹配的配置
            project_id = project.project_id
            if project_id not in datasets:
                return False
                
            project_config = datasets[project_id]
            
            # 检查是否开启了exclude_in_planning选项
            exclude_in_planning = project_config.get('exclude_in_planning', 'false')
            if isinstance(exclude_in_planning, str):
                exclude_in_planning = exclude_in_planning.lower() == 'true'
            if not exclude_in_planning:
                return False
                
            # 检查文件路径是否包含任何排除目录 
            # 注意这里配置是 exclude_directory (单数)
            exclude_directories = project_config.get('exclude_directory', [])
            for directory in exclude_directories:
                if directory in relative_file_path:
                    print(f"排除目录 '{directory}' 匹配到文件: {relative_file_path}")
                    return True
                    
            return False
        except Exception as e:
            print(f"检查排除设置时出错: {str(e)}")
            return False
    
    @staticmethod
    def get_visibility_filter_by_language(functions) -> callable:
        """根据编程语言获取可见性过滤器"""
        language_patterns = {
            '.rust': lambda f: True,  # No visibility filter for Rust
            '.python': lambda f: True,  # No visibility filter for Python
            '.move': lambda f: f['visibility'] == 'public',
            '.fr': lambda f: f['visibility'] == 'public',
            '.java': lambda f: f['visibility'] in ['public', 'protected'],
            '.cairo': lambda f: f['visibility'] == 'public',
            '.tact': lambda f: f['visibility'] == 'public',
            '.func': lambda f: f['visibility'] == 'public',
            '.go': lambda f: True
        }

        def get_file_extension(funcs):
            for func in funcs:
                file_path = func['relative_file_path']
                for ext in language_patterns:
                    if file_path.endswith(ext):
                        return ext
            return None

        file_ext = get_file_extension(functions)
        return language_patterns.get(file_ext, lambda f: True)
    
    @staticmethod
    def get_scan_configuration() -> Dict[str, Any]:
        """获取扫描配置"""
        scan_mode = os.getenv('SCAN_MODE', '')
        
        # 获取基础循环次数
        base_iteration_count = int(os.environ.get('BUSINESS_FLOW_COUNT', 1))
        
        # 获取所有checklist的数量
        total_checklist_count = 0
        if scan_mode == "COMMON_PROJECT_FINE_GRAINED":
            from prompt_factory.vul_prompt_common import VulPromptCommon
            vul_checklists = VulPromptCommon.vul_prompt_common_new()
            total_checklist_count = len(vul_checklists)
        
        # 计算实际循环次数
        actual_iteration_count = base_iteration_count * total_checklist_count if scan_mode == "COMMON_PROJECT_FINE_GRAINED" else base_iteration_count
        
        return {
            'scan_mode': scan_mode,
            'base_iteration_count': base_iteration_count,
            'total_checklist_count': total_checklist_count,
            'actual_iteration_count': actual_iteration_count,
            'threshold': int(os.getenv("THRESHOLD_OF_PLANNING", 200)),
            'switch_business_code': eval(os.environ.get('SWITCH_BUSINESS_CODE', 'True')),
            'switch_file_code': eval(os.environ.get('SWITCH_FILE_CODE', 'False')),
            'cross_contract_scan': os.getenv("CROSS_CONTRACT_SCAN") == "True",
            'huge_project': eval(os.environ.get('HUGE_PROJECT', 'False'))  # 🆕 新增 huge_project 开关
        } 