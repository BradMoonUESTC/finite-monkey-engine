import json
from typing import List, Dict, Tuple
from prompt_factory.prompt_assembler import PromptAssembler
from openai_api.openai import common_ask_confirmation, common_ask_for_json


class CheckUtils:
    """Utility functions class for vulnerability checking"""
    
    @staticmethod
    def get_code_to_analyze(task) -> str:
        """Get code to be analyzed"""
        function_code = task.content
        if_business_flow_scan = task.if_business_flow_scan
        business_flow_code = task.business_flow_code
        business_flow_context = task.business_flow_context
        
        return business_flow_code + "\n" + business_flow_context if if_business_flow_scan == "1" else function_code
    
    @staticmethod
    def is_task_already_processed(task) -> bool:
        """Check if task has already been processed"""
        result_CN = task.get_result_CN()
        category_mark = task.get_category()
        
        return (result_CN is not None and len(result_CN) > 0 and result_CN != "None" and
                category_mark is not None and len(category_mark) > 0)
    
    @staticmethod
    def process_round_response(round_response: str) -> str:
        """
        Process response from each analysis round, extract result status with defensive programming
        
        Args:
            round_response: Response from current round
            
        Returns:
            str: Extracted result status
        """
        prompt_translate_to_json = PromptAssembler.brief_of_response()
        
        # Use common_ask_for_json to get JSON response
        round_json_response = str(common_ask_for_json(round_response + "\n" + prompt_translate_to_json))
        print("\n📋 JSON Response Length:")
        print(len(round_json_response))
        
        try:
            cleaned_response = round_json_response
            print(f"\n🔍 Cleaned response: {cleaned_response}")
            
            # Parse JSON
            response_data = json.loads(cleaned_response)
            
            # Get result status, use get method to provide default value
            result_status = response_data.get("result", "not sure").lower()
            
            print(f"\n🎯 Extracted result status: {result_status}")
            print(f"📏 Result status length: {len(result_status)}")
            
            # Validate result status validity
            valid_statuses = {"yes", "no", "need creator to decide", "confirmed"}
            if not any(status in result_status for status in valid_statuses):
                print("\n⚠️ Invalid result status - marked as 'not sure'")
                return "not sure"
            
            return result_status
        
        except json.JSONDecodeError as e:
            print(f"\n⚠️ JSON parsing error: {str(e)} - marked as 'not sure'")
            return "not sure"
        except Exception as e:
            print(f"\n⚠️ Unexpected error: {str(e)} - marked as 'not sure'")
            return "not sure"
    
    @staticmethod
    def collect_analysis_results_by_rounds(analysis_collection: List, round_results: List[List[str]]) -> Tuple[str, str]:
        """Collect and format analysis results by rounds - new confirmation logic"""
        print("\n📊 Starting round-by-round analysis of confirmation results...")
        
        strong_confirmation_found = False
        round_summaries = []
        
        for round_num, round_result in enumerate(round_results, 1):
            yes_count = sum(1 for r in round_result if "yes" in r or "confirmed" in r)
            no_count = sum(1 for r in round_result if "no" in r and "vulnerability" in r)
            total_count = len(round_result)
            
            round_summary = f"Round {round_num}: {yes_count} yes, {no_count} no, {total_count} total requests"
            round_summaries.append(round_summary)
            print(f"   {round_summary}")
            
            # Check if strong confirmation criteria are met
            if yes_count >= 3 or (yes_count >= 2 and no_count == 0):
                strong_confirmation_found = True
                print(f"   ✅ Round {round_num} meets strong confirmation criteria!")
        
        # Determine final result based on new logic
        if strong_confirmation_found:
            response_final = "yes"
            print("\n⚠️ Final result: Vulnerability confirmed (strong confirmation round found)")
            decision_reason = "Found at least one round of strong confirmation (3 yes or 2 yes with no no)"
        else:
            # If no strong confirmation, use improved overall logic
            all_results = [result for round_result in round_results for result in round_result]
            total_yes = sum(1 for r in all_results if "yes" in r or "confirmed" in r)
            total_no = sum(1 for r in all_results if "no" in r and "vulnerability" in r)
            
            # Improved judgment logic: compare yes and no counts
            if total_yes >= 2 and total_yes > total_no:
                response_final = "yes"
                print("\n⚠️ Final result: Vulnerability confirmed (overall more yes)")
                decision_reason = f"Overall confirmation: {total_yes} yes > {total_no} no"
            elif total_no >= 2 and total_no > total_yes:
                response_final = "no"
                print("\n✅ Final result: No vulnerability (overall more no)")
                decision_reason = f"Overall negation: {total_no} no > {total_yes} yes"
            elif total_yes >= 2 and total_no >= 2 and total_yes == total_no:
                response_final = "not sure"
                print("\n❓ Final result: Uncertain (equal yes and no counts)")
                decision_reason = f"Split result: {total_yes} yes = {total_no} no"
            elif total_yes >= 2:
                response_final = "yes"
                print("\n⚠️ Final result: Vulnerability confirmed (overall 2+ confirmations)")
                decision_reason = f"Overall confirmation: {total_yes} yes, {total_no} no"
            elif total_no >= 2:
                response_final = "no"
                print("\n✅ Final result: No vulnerability (overall 2+ negations)")
                decision_reason = f"Overall negation: {total_yes} yes, {total_no} no"
            else:
                response_final = "not sure"
                print("\n❓ Final result: Uncertain (unclear results)")
                decision_reason = f"Unclear results: {total_yes} yes, {total_no} no"
        
        # Generate detailed analysis report
        detailed_report = []
        detailed_report.append("=== Round-by-Round Confirmation Analysis Report ===")
        for summary in round_summaries:
            detailed_report.append(summary)
        detailed_report.append(f"Decision basis: {decision_reason}")
        detailed_report.append(f"Final result: {response_final}")
        
        final_response = "\n".join(detailed_report)
        
        # Add final conclusion to analysis collection
        analysis_collection.append("=== Final Conclusion (New Logic) ===")
        analysis_collection.append(f"Result: {response_final}")
        analysis_collection.append(f"Decision basis: {decision_reason}")
        analysis_collection.extend(detailed_report)
        
        return response_final, final_response
    
    @staticmethod
    def collect_analysis_results(analysis_collection: List, confirmation_results: List[str]) -> Tuple[str, str]:
        """Collect and format analysis results - compatibility method"""
        # For backward compatibility, if simple list is passed, use original logic
        yes_count = sum(1 for r in confirmation_results if "yes" in r or "confirmed" in r)
        no_count = sum(1 for r in confirmation_results if "no" in r and "vulnerability" in r)
        
        if yes_count >= 2:
            response_final = "yes"
            print("\n⚠️ Final result: Vulnerability confirmed (2+ confirmations)")
        elif no_count >= 2:
            response_final = "no"
            print("\n✅ Final result: No vulnerability (2+ negations)")
        else:
            response_final = "not sure"
            print("\n❓ Final result: Uncertain (unclear results)")
        
        final_response = "\n".join([f"Round {i+1} Analysis:\n{resp}" for i, resp in enumerate(confirmation_results)])
        
        # Add final conclusion
        analysis_collection.append("=== Final Conclusion ===")
        analysis_collection.append(f"Result: {response_final}")
        analysis_collection.append(f"Detailed description: {final_response}")
        
        return response_final, final_response
    
    @staticmethod
    def format_analysis_results(analysis_collection: List) -> str:
        """Format all collected results"""
        formatted_results = "\n\n".join(str(item or '').strip() for item in analysis_collection)
        # Clean string before updating database
        return formatted_results.replace('\x00', '')
    
    @staticmethod
    def update_task_results(task_manager, task_id: int, result: str, response_final: str, 
                           final_response: str, formatted_results: str):
        """Update task results to database"""
        task_manager.update_result(task_id, result, response_final, final_response)
        task_manager.update_category(task_id, formatted_results)
    
    @staticmethod
    def should_skip_early(result_status: str) -> bool:
        """Determine if should exit early"""
        return "no" in result_status
    
    @staticmethod
    def perform_confirmation_round(code_to_be_tested: str, result: str, 
                                 round_num: int, request_num: int) -> str:
        """Execute confirmation round"""
        prompt = PromptAssembler.assemble_vul_check_prompt_final(code_to_be_tested, result)
        sub_round_response = common_ask_confirmation(prompt)
        
        print(f"\n📋 Round {round_num + 1} Request {request_num + 1} result length: {len(sub_round_response)}")
        
        return sub_round_response
    
    @staticmethod
    def print_task_summary(time_cost: float, confirmation_count: int, response_final: str):
        """Print task summary"""
        print("\n=== Task Summary ===")
        print(f"⏱️ Time cost: {time_cost:.2f} seconds")
        print(f"📝 Analyses performed: {confirmation_count}")
        print(f"🏁 Final status Length: {len(response_final)}")
        print("=" * 80 + "\n") 