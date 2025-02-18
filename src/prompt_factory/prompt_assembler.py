from prompt_factory.core_prompt import CorePrompt
from prompt_factory.periphery_prompt import PeripheryPrompt
from prompt_factory.vul_prompt import VulPrompt
from prompt_factory.vul_check_prompt import VulCheckPrompt
class PromptAssembler:
    def assemble_prompt_common(code):
        ret_prompt=code+"\n"\
                    +PeripheryPrompt.role_set_rust_common()+"\n"\
                    +PeripheryPrompt.task_set_blockchain_common()+"\n"\
                    +CorePrompt.core_prompt_assembled()+"\n"\
                    +VulPrompt.vul_prompt_common()+"\n"\
                    +PeripheryPrompt.guidelines()+"\n"\
                    +PeripheryPrompt.jailbreak_prompt()

                    
        return ret_prompt
    def assemble_prompt_pure(code):
        ret_prompt=code+"\n"\
                    +PeripheryPrompt.role_set_solidity_common()+"\n"\
                    +PeripheryPrompt.task_set_blockchain_common()+"\n"\
                    +CorePrompt.core_prompt_pure()+"\n"\
                    +PeripheryPrompt.guidelines()+"\n"\
                    +PeripheryPrompt.jailbreak_prompt()

                    
        return ret_prompt
    def assemble_prompt_for_specific_project(code, business_type):
        vul_prompts = []
        for type in business_type:
            if type == "chainlink":
                vul_prompts.append(VulPrompt.vul_prompt_chainlink())
            elif type == "dao":
                vul_prompts.append(VulPrompt.vul_prompt_dao())
            elif type == "inline assembly":
                vul_prompts.append(VulPrompt.vul_prompt_inline_assembly())
            elif type == "lending":
                vul_prompts.append(VulPrompt.vul_prompt_lending())
            elif type == "liquidation":
                vul_prompts.append(VulPrompt.vul_prompt_liquidation())
            elif type == "liquidity manager":
                vul_prompts.append(VulPrompt.vul_prompt_liquidity_manager())
            elif type == "signature":
                vul_prompts.append(VulPrompt.vul_prompt_signature_replay())
            elif type == "slippage":
                vul_prompts.append(VulPrompt.vul_prompt_slippage())
            elif type == "univ3":
                vul_prompts.append(VulPrompt.vul_prompt_univ3())
            elif type == "other":
                vul_prompts.append(VulPrompt.vul_prompt_common())

        combined_vul_prompt = "\n\n".join(vul_prompts)
        
        ret_prompt = code+"\n"\
                    +PeripheryPrompt.role_set_solidity_common()+"\n"\
                    +PeripheryPrompt.task_set_blockchain_common()+"\n"\
                    +CorePrompt.core_prompt_assembled()+"\n"\
                    +combined_vul_prompt+"\n"\
                    +PeripheryPrompt.guidelines()+"\n"\
                    +PeripheryPrompt.jailbreak_prompt()
                    
        return ret_prompt
    def assemble_optimize_prompt(code):
        ret_prompt=code+"\n"\
                    +PeripheryPrompt.role_set_rust_common()+"\n"\
                    +PeripheryPrompt.task_set_blockchain_common()+"\n"\
                    +CorePrompt.optimize_prompt()+"\n"
        return ret_prompt
    def assemble_vul_check_prompt(code,vul):
        ret_prompt=code+"\n"\
                +str(vul)+"\n"\
                +VulCheckPrompt.vul_check_prompt_claude_no_overflow()+"\n"
        return ret_prompt
    def assemble_vul_check_prompt_final(code,vul):
        ret_prompt=code+"\n"\
                +str(vul)+"\n"\
                +VulCheckPrompt.vul_check_prompt_claude_no_overflow_final()+"\n"
        return ret_prompt

    def brief_of_response():
        return """Based on the analysis response, please translate the response to JSON format. 
        The JSON format should be one of the following:
        {'brief of response':'xxx','result':'yes'} 
        {'brief of response':'xxx','result':'no'} 
        {'brief of response':'xxx','result':'need creator to decide'}
        
        The 'brief of response' should contain a concise summary of the analysis,
        and the 'result' should reflect the final conclusion about the vulnerability's existence."""