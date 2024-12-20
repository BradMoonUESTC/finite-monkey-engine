# prompt_assembler.py
from prompt_factory.core_prompt import CorePrompt
from prompt_factory.periphery_prompt import PeripheryPrompt 
from prompt_factory.vul_check_prompt import VulCheckPrompt

class PromptAssembler:
    @staticmethod
    def assemble_prompt(code):
        prompts = []
        
        # Collect all defined prompts with their titles

        prompts.append({
            "title": "blacklist",
            "prompt": PromptAssembler.blacklist_prompt(code)
        })

        
        return prompts



    @staticmethod
    def blacklist_prompt(code):
        return f"""
        {code}
        
        Analyze the functionality of this token contract and determine whether it contains significant or hidden blacklist mechanisms. Please explain the blacklist mechanism in detail with reference to the code, covering the following details:

        Storage structure of the blacklist
        Blacklist management functions, including addition and removal
        Blacklist query functions
        Actual restriction effects of the blacklist
        Please explain the principles behind each detail with specific references to the code.
        """
    @staticmethod
    def confiscate_prompt(code):
        return f"""
        {code}
        
        Please analyze if this token contract has Confiscation risks, which could lead to: 
        1. Contract owners can reduce any account's balance to zero without approval, essentially confiscating funds; 
        2. Users cannot prevent or revoke this operation. 
        Please analyze the contract, explain the relevant risks by comparing the risky code, no mitigation suggestions needed.

        """
    @staticmethod
    def txorigin_prompt(code):
        return f"""
        {code}
        Analyze the functionality of this token contract and determine whether it uses tx.origin as the source of funds for transfers and assess any associated risks. Please explain in detail the transfer mechanism based on tx.origin with reference to the code, including:

        How tx.origin is used in transfer functions
        Potential security risks and vulnerabilities associated with using tx.origin
        The detailed principles and logic behind the tx.origin-based transfer implementation
        Any possible attack vectors or exploitation scenarios
        """
    @staticmethod
    def fee_prompt(code):
        return f"""
        {code}
        Analyze the functionality of this token contract and determine whether it contains transaction tax mechanisms, or whether fees are automatically deducted during transfers, sales, or purchases, or if there are reductions in the received amount during transfers. If such mechanisms exist, please examine:

        Whether there is a cap on transfer fees
        Whether contract owners or privileged users can modify the transfer fee percentages
        What the maximum limits are for these fees
        Please explain in detail the transaction tax mechanism with reference to the code, including:

        The fee calculation logic
        Different fee rates for different types of transactions (if any)
        Fee collection and distribution mechanisms
        Fee modification capabilities and restrictions
        Any special conditions or exemptions for certain addresses
        How the fees are actually deducted and processed during transactions
        Please explain each detail and principle with specific references to the contract code.
        """
