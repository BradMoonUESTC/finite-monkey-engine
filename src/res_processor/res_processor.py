# res_processor.py
import pandas as pd
from tqdm import tqdm
from openai_api.openai import ask_claude
import concurrent.futures
from threading import Lock

class ResProcessor:
    def __init__(self, df):
        self.df = df
        self.lock = Lock()

    def process(self):
        # Get unique results that need translation
        results_to_translate = self.df['扫描结果'].dropna().unique()
        
        translated_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_result = {
                executor.submit(self._translate_result, result): result 
                for result in results_to_translate
            }
            
            with tqdm(total=len(results_to_translate), desc="翻译结果") as pbar:
                for future in concurrent.futures.as_completed(future_to_result):
                    result = future_to_result[future]
                    try:
                        translation = future.result()
                        with self.lock:
                            translated_results[result] = translation
                            pbar.update(1)
                    except Exception as e:
                        print(f"翻译失败: {result}")
                        print(f"错误: {e}")
                        translated_results[result] = result

        # Create a new DataFrame with translations
        new_df = self.df.copy()
        new_df['中文结果'] = new_df['扫描结果'].map(lambda x: translated_results.get(x, x) if pd.notna(x) else '')
        
        # Select and rename final columns
        final_df = new_df[[
            '中文结果',
            '扫描结果',
            '漏洞分类',
            '是否有此风险',
            '合约名称',
            '项目ID',
            '任务ID'
        ]]
        
        return final_df

    def _translate_result(self, result):
        if not result or pd.isna(result):
            return ''
            
        translate_prompt = f"""请将以下风险分析结果翻译成中文：
{result}
只需要直接输出翻译结果，按原文翻译，不能丢失任何原始信息，无需其他解释,避免出现markdown语法的一级标题。
"""
        try:
            translated_text = ask_claude(translate_prompt)
            return translated_text.strip()
        except Exception as e:
            print(f"Translation error: {e}")
            return result

