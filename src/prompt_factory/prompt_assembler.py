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
        "title": "Blacklist",
        "prompt": PromptAssembler.blacklist_prompt(code)
        })

        prompts.append({
            "title": "Rebase", 
            "prompt": PromptAssembler.rebase_prompt(code)
        })

        prompts.append({
            "title": "Parameter Modification",
            "prompt": PromptAssembler.parameter_modification_prompt(code)
        })

        prompts.append({
            "title": "Transfer Amount",
            "prompt": PromptAssembler.transfer_amount_prompt(code)
        })

        prompts.append({
            "title": "Transfer Time",
            "prompt": PromptAssembler.transfer_time_prompt(code)
        })

        prompts.append({
            "title": "Fee",
            "prompt": PromptAssembler.fee_prompt(code)
        })

        prompts.append({
            "title": "TxOrigin",
            "prompt": PromptAssembler.txorigin_prompt(code)
        })

        prompts.append({
            "title": "Confiscate",
            "prompt": PromptAssembler.confiscate_prompt(code)
        })

        prompts.append({
            "title": "Unintend Confiscate",
            "prompt": PromptAssembler.unintend_confiscate_prompt(code)
        })

        prompts.append({
            "title": "Pause",
            "prompt": PromptAssembler.pause_prompt(code)
        })

        prompts.append({
            "title": "Minting",
            "prompt": PromptAssembler.minting_prompt(code)
        })

        prompts.append({
            "title": "Superuser",
            "prompt": PromptAssembler.superuser_prompt(code)
        })

        prompts.append({
            "title": "Ownership Transfer",
            "prompt": PromptAssembler.ownership_transfer_prompt(code)
        })

        prompts.append({
            "title": "Assembly",
            "prompt": PromptAssembler.assembly_prompt(code)
        })

        prompts.append({
            "title": "Event Spoofing",
            "prompt": PromptAssembler.event_spoofing_prompt(code)
        })

        prompts.append({
            "title": "Upgradeable",
            "prompt": PromptAssembler.upgradeable_prompt(code)
        })

        prompts.append({
            "title": "Access Control",
            "prompt": PromptAssembler.access_control_prompt(code)
        })

        prompts.append({
            "title": "External Call",
            "prompt": PromptAssembler.external_call_prompt(code)
        })

        prompts.append({
            "title": "Signature Replay",
            "prompt": PromptAssembler.signature_replay_prompt(code)
        })

        prompts.append({
            "title": "Non Standard ERC20",
            "prompt": PromptAssembler.non_standard_erc20_prompt(code)
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

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "总体风险评估结论",
            "风险模式": ["具体的风险机制描述"],
            "关键函数": ["相关函数名称及功能"],
            "状态存储": "相关状态变量的存储结构",
            "权限控制": "权限验证机制分析",
            "代码证据": ["关键代码片段"],
            "影响范围": "对用户的实际影响"
        }}
        """
    @staticmethod
    def confiscate_prompt(code):
        return f"""
        {code}
        
        Please analyze if this token contract has Confiscation risks, which could lead to: 
        1. Contract owners can reduce any account's balance to zero without approval, essentially confiscating funds; 
        2. Users cannot prevent or revoke this operation. 
        Please analyze the contract, explain the relevant risks by comparing the risky code, no mitigation suggestions needed.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "没收风险总体结论",
            "风险模式": ["识别到的风险模式"],
            "关键函数": ["危险操作函数列表"],
            "权限缺陷": "权限控制缺失点",
            "代码证据": ["相关代码片段"],
            "用户影响": "对终端用户的影响"
        }}
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
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "tx.origin使用风险总结",
            "风险模式": ["潜在风险类型"],
            "关键函数": ["使用tx.origin的函数"],
            "攻击场景": ["可能的攻击方式"],
            "代码证据": ["相关代码片段"],
            "影响范围": "受影响的功能模块"
        }}
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
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "手续费机制风险总结",
            "风险模式": ["手续费相关风险类型"],
            "关键参数": ["手续费相关参数"],
            "权限控制": "费率修改权限分析",
            "代码证据": ["关键代码片段"],
            "用户影响": "对交易的实际影响"
        }}
        """
    @staticmethod
    def transfer_amount_prompt(code):
        return f"""
        {code}

        Analyze the functionality of this token contract and determine whether it contains significant or hidden transfer amount limits. Please explain the transfer amount limit mechanism in detail with reference to the code, covering the following details:

        Storage structure of the transfer amount limit
        Transfer amount limit management functions, including addition and removal
        Transfer amount limit query functions
        Actual restriction effects of the transfer amount limit
        Please explain the principles behind each detail with specific references to the code.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "转账限额风险总结",
            "风险模式": ["限额机制类型"],
            "关键函数": ["限额管理函数"],
            "状态存储": "限额存储结构",
            "代码证据": ["相关代码片段"],
            "用户影响": "对转账操作的影响"
        }}
        """
    @staticmethod
    def transfer_time_prompt(code):
        return f"""
        {code}
        Analyze the functionality of this token contract and determine whether it contains significant or hidden transfer time limits. Please explain the transfer time limit mechanism in detail with reference to the code, covering the following details:

        Storage structure of the transfer time limit
        Transfer time limit management functions, including addition and removal
        Transfer time limit query functions
        Actual restriction effects of the transfer time limit
        Please explain the principles behind each detail with specific references to the code.
        Please explain the principles behind each detail with specific references to the code.
        """
    @staticmethod
    def parameter_modification_prompt(code):
        return f"""
        {code}
        Analyze the functionality of this token contract and determine whether it contains significant or hidden parameter reconfiguration mechanisms.
        this mechanism can impact user balances and lead to accounting discrepancies between on-chain user balances and balances tracked by the exchange's systems.
        Please explain the parameter reconfiguration mechanism in detail with reference to the code, covering the following details:

        Storage structure of the parameter reconfiguration
        Parameter reconfiguration management functions, including addition and removal
        Parameter reconfiguration query functions
        Actual restriction effects of the parameter reconfiguration
        Please explain the principles behind each detail with specific references to the code.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "参数修改风险总结",
            "风险模式": ["参数修改机制类型"],
            "关键参数": ["可修改的关键参数"],
            "权限控制": "修改权限分析",
            "代码证据": ["相关代码片段"],
            "系统影响": "对账务系统的影响"
        }}
        """    
    @staticmethod
    def rebase_prompt(code):
        return f"""
        {code}
        Please analyze if this contract implements Rebase Token mechanisms that could lead to the following risks:

        Balance Manipulation Risks:
        Check if the contract uses elastic supply mechanisms that can silently adjust token balances
        Identify functions that can modify the rebase factor or multiplier
        Look for balance calculation logic that applies dynamic scaling factors
        Transfer Amount Inconsistency:
        Check if transfer amounts are modified by rebase factors during transactions
        Identify if there are price-based or supply-based multipliers affecting actual transfer amounts
        Look for functions that can alter the transfer calculation formula
        Implementation Details:
        Examine how the contract stores and updates the rebase factors
        Check if there are privileged roles that can trigger rebase events
        Identify the frequency and conditions for automatic rebasing
        Please analyze the contract code and point out specific code segments that implement these rebase mechanisms, explaining how they could affect user balances and transactions. No mitigation suggestions are needed - focus on identifying the risks in the implementation.

        For each risk found, highlight:

        The relevant code section
        How the rebase mechanism works
        The potential impact on user balances and transactions
        Whether the rebase events are transparent or silent to users
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "Rebase机制风险总结",
            "风险模式": ["rebase实现方式"],
            "关键函数": ["rebase相关函数"],
            "供应影响": "对代币供应量的影响",
            "代码证据": ["相关代码片段"],
            "用户影响": "对余额计算的影响"
        }}
        """
    @staticmethod
    def upgradeable_prompt(code):
        return f"""
        {code}
        Please analyze if this contract has Upgradeable risks, focusing on:

        1. Proxy Contract Mechanism:
        - Check if proxy contract pattern is used
        - Look for delegatecall related logic 
        - Identify methods for storing and updating implementation addresses
        - Check if contract inherits from Upgradeable/Proxy related contracts

        2. CREATE2 Upgrade Mechanism:
        - Check if CREATE2 opcode is used for contract deployment
        - Look for selfdestruct functionality
        - Analyze if there's redeployment initialization logic

        3. Assembly Code Check:
        - Analyze assembly code segments for delegatecall or CREATE2
        - Check if low-level opcodes implement upgradeable logic
        - Look for hidden extcodesize or extcodecopy operations

        4. Other Upgrade Related Logic:
        - Look for initialize/reinitialize functions
        - Check state variable storage slot usage
        - Identify if beacon proxy pattern is used
        - Check for uninitialized implementation contracts
        Please point out specific code implementing these upgrade mechanisms and explain how contract owners can modify contract functionality through these mechanisms.        
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "可升级性风险总结",
            "风险模式": ["升级机制类型"],
            "关键组件": ["升级相关组件"],
            "权限缺陷": "权限控制问题",
            "代码证据": ["相关代码片段"],
            "系统影响": "可升级性带来的影响"
        }}
        """
    @staticmethod
    def access_control_prompt(code):
        return f"""
        {code}
        Please analyze if this contract has Unprotected Critical Function risks, focusing on:

        Access Control Checks:
        - Identify critical functions that can modify contract state
        - Check for missing/insufficient access modifiers (onlyOwner, onlyAdmin, etc.)
        - Look for unprotected initialization functions 
        - Examine role-based access control implementation

        Critical Operations:
        - Functions that can:
          * Modify token balances
          * Change ownership/admin roles
          * Withdraw/transfer funds
          * Update core contract parameters
          * Pause/unpause functionality

        Authentication Methods:
        - Check for missing modifier declarations
        - Identify weak or bypassed authentication checks
        - Look for public/external functions that should be restricted

        State-Changing Functions:
        - Examine functions that modify:
          * Protocol configuration
          * Fee settings
          * Whitelist/blacklist
          * Emergency controls
        Please point out specific unprotected code and explain their potential impact if exploited by malicious actors.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "访问控制风险总结",
            "风险模式": ["权限缺失类型"],
            "关键函数": ["未受保护函数"],
            "权限缺陷": "访问控制缺陷",
            "代码证据": ["相关代码片段"],
            "系统影响": "可能造成的系统影响"
        }}
        """
    @staticmethod
    def unintend_confiscate_prompt(code):
        return f"""
        {code}
        Please analyze if this contract has Unintended Token Confiscation risks due to invariant states, focusing on:

        1. State-Dependent Operations:
        - Identify functions where token transfers/burns depend on contract states
        - Check critical price/rate variables that could be zero or extreme values
        - Look for conditions where tokens might be trapped without recovery

        2. Function Behavior Analysis:
        - Compare function names with actual implementation
        - Identify misleading function descriptions or comments
        - Check if function outcomes match user expectations
        - Look for state conditions that significantly alter function behavior

        3. Critical State Variables:
        - Find variables that control:
        * Token prices/rates
        * Exchange ratios
        * Fee calculations
        * Transfer conditions
        - Check their initialization and update mechanisms

        4. Edge Cases:
        - Analyze behavior when:
        * Price/rate variables are zero
        * Pools are empty/nearly empty
        * Emergency states are active
        * System parameters reach extreme values

        Please identify specific scenarios where tokens might be unintentionally confiscated and explain how these conditions could affect users.        
        
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "意外没收风险总结",
            "风险模式": ["意外没收场景"],
            "关键条件": ["触发条件"],
            "状态依赖": "状态依赖分析",
            "代码证据": ["相关代码片段"],
            "用户影响": "对资产安全的影响"
        }}
        """
    
    @staticmethod
    def external_call_prompt(code):
        return f"""
        {code}
        Please analyze if this contract has External Call to Untrusted Contract risks from a user's perspective, focusing on:

        1. External Call Patterns:
        - Identify all external calls using:
        * .call()
        * .delegatecall()
        * .staticcall()
        * low-level calls in assembly
        - Check if the called addresses can be controlled/influenced by users
        - Look for proper validation of external contract addresses

        2. User Input Influence:
        - Identify where user inputs can affect:
        * Call destinations
        * Call data
        * Value transfers
        - Check if users can manipulate call parameters

        3. Security Measures:
        - Check for missing/insufficient:
        * Reentrancy guards
        * Checks-Effects-Interactions pattern
        * Address validation
        * Return value checks
        - Look for incorrect ordering of operations

        4. Risk Assessment:
        - Identify potential attack vectors:
        * Flash loan interactions
        * Callback functions
        * Multiple contract interactions
        - Check if users' funds could be at risk during external calls

        5. Trust Assumptions:
                - Examine how contract determines trusted addresses
                - Check if users are forced to trust unknown contracts
                - Look for hardcoded vs. dynamic contract addresses

        Please highlight specific external calls that could put user funds at risk and explain potential attack scenarios.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "外部调用风险总结",
            "风险模式": ["危险调用模式"],
            "调用位置": ["风险调用点"],
            "安全漏洞": ["安全漏洞类型"],
            "代码证据": ["相关代码片段"],
            "攻击影响": "可能造成的攻击影响"
        }}
        """
    
    def signature_replay_prompt(code):
        return f"""
        {code}
Please analyze if this contract has Signature Replay Risk (Off-chain Signature) vulnerabilities, focusing on:

1. Signature Implementation:
- Identify all signature-related functions
- Check compliance with EIP-712 standards
- Look for proper signature construction methods
- Examine ECDSA signature verification logic

2. Replay Attack Prevention:
- Check for nonce implementation:
  * Nonce initialization
  * Nonce increment logic
  * Nonce validation
- Look for timestamp/deadline checks
- Identify domain separator usage
- Check for chain ID validation

3. Critical Security Components:
- Verify presence of:
  * structHash construction
  * _hashTypedDataV4 usage
  * ECDSA.recover implementation
  * Signer address validation
  * ERC1271 support for contract signers

4. Vulnerable Patterns:
- Look for:
  * Missing nonce mechanisms
  * Unused deadline parameters
  * Incomplete signature validation
  * Improper error handling
  * Weak/missing domain separation

5. Recovery and Verification:
- Check address recovery process
- Examine signature component handling (v,r,s)
        - Look for proper validation of recovered addresses
        - Verify error handling in recovery process

        Please identify specific signature-related vulnerabilities and explain potential replay attack scenarios.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "签名重放风险总结",
            "风险模式": ["签名缺陷类型"],
            "关键参数": ["缺失的安全参数"],
            "验证缺陷": "签名验证问题",
            "代码证据": ["相关代码片段"],
            "攻击场景": ["可能的攻击方式"]
        }}
        """
    

    @staticmethod
    def event_spoofing_prompt(code):
        return f"""
        {code}
        Please analyze if this contract has Event Spoofing risks, focusing on:

1. Event Emission Analysis:
- Compare event emissions with actual state changes
- Check if events accurately reflect:
  * Balance changes
  * Transfer amounts
  * Account addresses
  * Transaction details
- Identify missing event emissions

2. State Change Tracking:
- Map state-changing functions to their events
- Look for:
  * Functions that modify balances without events
  * Incorrect amount reporting in events
  * Wrong address parameters in events
  * Mismatched event types

3. Critical Event Verification:
- Check accuracy of events for:
  * Token transfers
  * Balance updates
  * Ownership changes
  * Parameter modifications
  * Protocol state changes

4. Common Spoofing Patterns:
- Identify:
  * Events with incorrect parameters
  * Missing critical events
  * Events that don't match actual operations
  * Misleading event names or parameters
  * Events emitted in wrong order

        Please highlight specific instances where events might mislead external applications or users about the contract's true state and explain the potential impact on tracking systems.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "事件欺骗风险总结",
            "风险模式": ["事件不一致类型"],
            "关键事件": ["风险事件名称"],
            "状态差异": "事件与状态差异",
            "代码证据": ["相关代码片段"],
            "监控影响": "对监控系统的影响"
        }}
        """
    
    @staticmethod
    def non_standard_erc20_prompt(code):
        return f"""
        {code}
Please analyze if this contract has Non-standard ERC-20 implementation issues, focusing on:

1. Standard Interface Compliance:
- Verify implementation of required ERC-20 functions:
  * totalSupply()
  * balanceOf(address)
  * transfer(address,uint256)
  * transferFrom(address,address,uint256)
  * approve(address,uint256)
  * allowance(address,address)
- Check standard events:
  * Transfer
  * Approval

2. Function Behavior Analysis:
- Check for non-standard behaviors in:
  * Transfer mechanics
  * Approval process
  * Balance updates
  * Fee handling
  * Token burning/minting
- Look for unexpected revert conditions

3. Token Properties:
- Verify standard properties:
  * decimals() implementation
  * name() and symbol()
  * Token divisibility
- Check for non-standard:
  * Fee mechanisms
  * Blacklisting features
  * Pause functionality
  * Rebasing mechanisms

4. Custom Features:
- Identify non-standard additions:
  * Custom transfer conditions
  * Special minting rules
  * Unique burning mechanisms
  * Modified approval process
  * Extra state variables

        Please highlight specific deviations from the ERC-20 standard and explain potential integration or compatibility issues.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "ERC20标准兼容性总结",
            "标准偏离": ["不符合标准的表现"],
            "关键差异": ["主要差异点"],
            "兼容问题": ["兼容性问题"],
            "代码证据": ["相关代码片段"],
            "系统影响": "对交易所的影响"
        }}
        """
    
    @staticmethod
    def pause_prompt(code):
        return f"""
        {code}
Please analyze if this token contract has Pause mechanism risks, focusing on:

1. Pause Functionality:
- Identify pause-related components:
  * Pause state variables
  * Pause/unpause functions
  * whenNotPaused modifiers
  * Emergency stop mechanisms
- Check pause authorization controls

2. Affected Functions:
- Map which core functions are pausable:
  * transfer
  * transferFrom
  * approve
  * mint/burn
  * trading functions
- Look for pause impact on:
  * User operations
  * Protocol features
  * Third-party integrations

3. Control Analysis:
- Examine pause control:
  * Who can pause/unpause
  * Single owner vs multisig
  * Timelock mechanisms
  * Emergency scenarios
- Check for ownership renouncement possibilities

4. Risk Assessment:
- Evaluate potential impacts:
  * Token holder restrictions
  * Locked funds scenarios
  * Market implications
  * Integration failures
- Check for pause duration limits

5. Recovery Mechanisms:
- Identify unpause conditions
- Check for permanent pause risks
- Look for bypass methods
- Examine emergency procedures

        Please highlight specific pause mechanisms that could affect token holders and explain potential scenarios where pausing could impact users.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "暂停机制风险总结",
            "风险模式": ["暂停控制类型"],
            "关键函数": ["暂停相关函数"],
            "权限分析": "暂停权限控制",
            "代码证据": ["相关代码片段"],
            "用户影响": "对交易可用性的影响"
        }}
        """
    
    @staticmethod
    def superuser_prompt(code):
        return f"""
        {code}
Please analyze if this token contract has Superuser risks, focusing on:

1. Privileged Functions:
- Identify functions with access controls:
  * onlyOwner modifier
  * onlyAdmin
  * onlyRole
  * Custom access modifiers
- Map privileged operations:
  * Fee adjustments
  * Parameter changes
  * Token minting/burning
  * Protocol configuration

2. Control Analysis:
- Examine ownership structure:
  * Single owner vs multisig
  * Role hierarchy
  * Owner capabilities
  * Transfer mechanisms
- Check for:
  * Ownership renouncement
  * Timelock implementations
  * Emergency powers

3. Critical Parameters:
- Identify owner-controlled variables:
  * Fees
  * Limits
  * Addresses
  * Protocol parameters
- Check impact of parameter changes

4. Risk Assessment:
- Evaluate centralization risks:
  * Single points of failure
  * Concentration of power
  * Potential abuse scenarios
  * Impact on users
- Check governance mechanisms

5. Security Measures:
- Look for protective features:
  * Value limits
  * Timelock delays
  * Multi-signature requirements
  * Change notification events

Please highlight specific privileged functions that could affect token holders and explain potential centralization risks.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "超级权限风险总结",
            "风险模式": ["特权滥用类型"],
            "关键权限": ["特权函数列表"],
            "控制缺陷": "权限控制问题",
            "代码证据": ["相关代码片段"],
            "系统影响": "对去中心化的影响"
        }}
        """
    
    @staticmethod
    def minting_prompt(code):
        return f"""
        {code}
Please analyze if this token contract has Minting risks, focusing on:

1. Minting Functionality:
- Identify minting-related components:
  * Mint functions (_mint, mint)
  * Access controls on minting
  * Supply increase mechanisms
  * Batch minting capabilities
- Check for:
  * Supply caps
  * Rate limits
  * Time restrictions

2. Control Analysis:
- Examine minting authority:
  * Who can mint
  * Minting conditions
  * Supply management
  * Owner privileges
- Look for:
  * Ownership status
  * Renouncement possibilities
  * Timelock controls

3. Supply Management:
- Analyze supply mechanics:
  * Initial supply
  * Maximum supply
  * Minting schedule
  * Supply tracking
- Check for:
  * Supply inflation risks
  * Distribution patterns
  * Market impact potential

4. Risk Assessment:
- Evaluate potential abuse:
  * Unrestricted minting
  * Supply manipulation
  * Value dilution risks
  * Impact on holders
- Look for:
  * Minting limits
  * Cooling periods
  * Emergency controls

5. Implementation Details:
- Check minting logic:
  * Balance updates
  * Total supply tracking
  * Event emissions
  * Error handling

Please highlight specific minting capabilities that could affect token value and explain potential inflation risks.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "铸币权限风险总结",
            "风险模式": ["铸币控制类型"],
            "关键函数": ["铸币相关函数"],
            "供应影响": "对代币供应的影响",
            "代码证据": ["相关代码片段"],
            "经济影响": "对代币经济的影响"
        }}
        """
    @staticmethod
    def ownership_transfer_prompt(code):
        return f"""
        {code}
Please analyze if this token contract has Ownership Transfer risks in the scope of user, focusing on:

1. Ownership Transfer Functionality:
- Identify ownership mechanisms:
  * transferOwnership functions
  * acceptOwnership patterns
  * Role assignment functions
  * Authority delegation

2. Access Control:
- Map privileged capabilities:
  * Owner permissions
  * Administrative functions
  * Role management
  * Critical operations
- Examine:
  * Permission hierarchy
  * Role separation
  * Access limitations

4. Risk Assessment:
- Evaluate transfer implications:
  * Contract control changes
  * Permission transitions
  * Impact on functionality
  * User protection
- Consider:
  * Malicious owner scenarios
  * Protocol manipulation risks
  * Recovery options

5. Implementation Details:
- Analyze transfer process:
  * State updates
  * Permission changes
  * Event logging
  * Error handling
- Check for:
  * Ownership renouncement
  * Transfer limitations
  * Security features

Please highlight specific ownership transfer mechanisms and explain potential risks from malicious ownership.
        Please explain the principles behind each detail with specific references to the code.
        Remember, this ownership risk is in the scope of user, not for the owner.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "所有权转移风险总结",
            "风险模式": ["转移机制类型"],
            "关键流程": ["转移相关函数"],
            "权限缺陷": "转移控制问题",
            "代码证据": ["相关代码片段"],
            "用户影响": "对用户资产的影响"
        }}
        """
    
    @staticmethod
    def assembly_prompt(code):
        return f"""
        {code}
Please analyze if this contract has Assembly usage risks, focusing on:

1. Assembly Location Detection:
- Identify assembly code blocks:
  * inline assembly
  * assembly functions
  * low-level calls
  * memory manipulation
- Map assembly usage in:
  * Core functions
  * Administrative operations
  * State modifications
  * External calls

2. Functionality Analysis:
- Examine assembly purpose:
  * Storage manipulation
  * Memory operations
  * Return data handling
  * Address operations
- Check for:
  * Compiler bypass
  * Gas optimization
  * Custom implementations
  * EVM direct access

3. Risk Assessment:
- Evaluate complexity:
  * Code readability
  * Maintenance challenges
  * Audit difficulty
  * Bug potential
- Look for:
  * Memory safety
  * Stack manipulation
  * Pointer arithmetic
  * Type safety bypass

4. Security Implications:
- Check for dangerous patterns:
  * Unsafe type casting
  * Memory corruption
  * Storage manipulation
  * Control flow issues
- Analyze:
  * Input validation
  * Error handling
  * Safety checks
  * State consistency

5. Documentation Review:
- Check documentation for:
  * Assembly usage justification
  * Security considerations
  * Implementation details
  * Known limitations
- Look for:
  * Comments clarity
  * Logic explanation
  * Risk disclosure

Please highlight specific assembly usage patterns and explain potential risks from low-level operations.
        Please explain the principles behind each detail with specific references to the code.

        请用JSON格式输出分析结果，包含以下字段：
        {{
            "总结": "汇编代码风险总结",
            "风险模式": ["汇编使用类型"],
            "关键代码": ["汇编代码位置"],
            "安全缺陷": "潜在安全问题",
            "代码证据": ["相关代码片段"],
            "维护影响": "对代码可维护性的影响"
        }}
        """