"""Enhanced Security Audit Prompts.

This module provides comprehensive security audit prompts covering
2024-2025 vulnerability patterns with language-specific considerations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional


class PromptCategory(Enum):
    """Categories of security prompts."""

    VULNERABILITY_DETECTION = "vulnerability_detection"
    ECONOMIC_ANALYSIS = "economic_analysis"
    CODE_REVIEW = "code_review"
    POC_GENERATION = "poc_generation"
    LANGUAGE_SPECIFIC = "language_specific"
    CROSS_PROTOCOL = "cross_protocol"


@dataclass
class SecurityPrompt:
    """A security audit prompt template."""

    name: str
    category: PromptCategory
    template: str
    variables: List[str]
    language: Optional[str] = None  # None for language-agnostic


class SecurityPrompts:
    """Enhanced security audit prompts for comprehensive vulnerability coverage.

    Includes:
    - Complete vulnerability checklist (low-hanging fruit + deep logic exploits)
    - Economic impact analysis requirements
    - Attack vector simulation
    - PoC code generation
    - Cross-protocol interaction risks
    - Language-specific prompts (Solidity, Rust/Solana, Move, Cairo)
    - Monad-specific considerations (parallel execution, high-throughput)
    """

    # Comprehensive vulnerability checklist
    VULNERABILITY_CHECKLIST = """
## Security Audit Checklist (2024-2025)

### LOW-HANGING FRUIT ($5K-$250K potential bugs)
1. [ ] Unchecked external call returns
2. [ ] Missing access control on critical functions
3. [ ] Reentrancy (ERC-777/ERC-1155/read-only variants)
4. [ ] Signature replay (EIP-2612, EIP-1271, cross-chain)
5. [ ] Uninitialized/double-initialize proxies
6. [ ] Delegatecall in upgradable contracts
7. [ ] Blockhash/timestamp dependence for randomness
8. [ ] tx.origin authentication
9. [ ] ERC20 approve race conditions
10. [ ] Missing slippage/deadline checks
11. [ ] Fee-on-transfer token accounting bugs
12. [ ] Emergency withdraw without timelock
13. [ ] Hard-coded addresses (multi-chain issues)
14. [ ] Selfdestruct in libraries/proxies
15. [ ] Incorrect decimals handling

### DEEP LOGIC/ECONOMIC EXPLOITS ($500K-$10M+ potential bugs)
1. [ ] Flash Loan Oracle Manipulation
2. [ ] Governance Flash-Vote Attacks
3. [ ] Vault Share Inflation via Donation (first depositor)
4. [ ] Cross-Protocol Composability Exploits
5. [ ] MEV/Sandwich Attack Vulnerability
6. [ ] Proxy Storage Collision
7. [ ] TWAP Oracle Window Attacks
8. [ ] Logical Reentrancy via ERC-777/1155 Hooks
9. [ ] Forced Ether Injection via SELFDESTRUCT
10. [ ] Read-Only Reentrancy
11. [ ] Permit/EIP-712 Signature Malleability
12. [ ] Bridge Replay Attacks
13. [ ] Rounding Drift/Precision Loss
14. [ ] Griefing via Spam/Dust
15. [ ] Emergency Pause Bypass
16. [ ] Flash-Mint Token Exploits
17. [ ] Rebase Token + Snapshot Timing Attacks
18. [ ] Multicall Double-Spend
19. [ ] Profit Cap Bypass via Partial Closes
20. [ ] Funding Rate Drain
21. [ ] Leverage Clamping Bypass
22. [ ] Loss Socialization Token Inflation
23. [ ] Bridge Verifier Logic Flaws
24. [ ] Arbitrary Call Dispatch in Cross-Chain Gateways
"""

    @staticmethod
    def get_comprehensive_audit_prompt(code: str, context: str = "") -> str:
        """Get comprehensive audit prompt for Solidity code.

        Args:
            code: Contract source code
            context: Additional context about the protocol

        Returns:
            Formatted audit prompt
        """
        return f"""You are an expert smart contract security auditor specializing in finding high-value vulnerabilities.

## Context
{context if context else "Analyze the following smart contract for security vulnerabilities."}

## Target Code
```solidity
{code}
```

## Audit Requirements

### 1. Vulnerability Detection
{SecurityPrompts.VULNERABILITY_CHECKLIST}

### 2. Analysis Methodology
For each potential vulnerability found:
1. **Identify**: Describe the vulnerability pattern
2. **Locate**: Specify exact line numbers and function names
3. **Analyze**: Explain the root cause and attack vector
4. **Impact**: Calculate potential economic impact
5. **Exploit**: Describe step-by-step exploitation
6. **Mitigate**: Provide specific fix recommendations

### 3. Economic Impact Assessment
For each finding, provide:
- Maximum potential loss (in USD terms)
- Attack capital required
- Flash loan availability for attack
- Estimated attacker profit
- Attack complexity (trivial/low/medium/high)
- Time to execute

### 4. Priority Rating
Rate each finding:
- **CRITICAL**: Immediate fund loss, >$1M risk
- **HIGH**: Significant fund loss, $100K-$1M risk
- **MEDIUM**: Limited fund loss, $10K-$100K risk
- **LOW**: Minimal impact, <$10K risk
- **INFO**: Best practice violation, no direct risk

### 5. Output Format
For each finding provide:
```
## [SEVERITY] Finding Title

**Location**: Contract.sol:L123-L130

**Description**: Clear explanation of the vulnerability

**Attack Vector**:
1. Step 1
2. Step 2
3. Step 3

**Impact**: $X potential loss

**Proof of Concept**:
```solidity
// Attack code
```

**Recommendation**: Specific mitigation steps

**References**: Related CVEs, past incidents
```

Focus on HIGH and CRITICAL vulnerabilities first. Be thorough but precise.
"""

    @staticmethod
    def get_economic_impact_prompt(code: str, finding: str) -> str:
        """Get prompt for economic impact analysis.

        Args:
            code: Contract source code
            finding: Description of the finding to analyze

        Returns:
            Formatted economic analysis prompt
        """
        return f"""You are a DeFi economics expert analyzing the economic impact of a smart contract vulnerability.

## Vulnerability Finding
{finding}

## Target Code
```solidity
{code}
```

## Economic Analysis Requirements

### 1. Attack Economics
Calculate and provide:
- **Capital Required**: Minimum capital to execute attack
- **Flash Loan Availability**: Available flash loan liquidity for attack
- **Gas Costs**: Estimated transaction costs
- **Protocol Fees**: Any fees paid during attack
- **Net Profit**: Expected attacker profit after all costs

### 2. Attack Feasibility
Analyze:
- **Technical Complexity**: Lines of attack code needed
- **Time Window**: Required timing precision
- **Competition Risk**: MEV/frontrunning considerations
- **Detection Risk**: Likelihood of detection before profit extraction

### 3. Historical Context
Reference similar exploits:
- Past incidents with similar patterns
- Actual losses from comparable vulnerabilities
- Timeline from discovery to exploitation

### 4. Risk Quantification
Provide:
- **Probability of Exploitation**: 0-100%
- **Maximum Loss Scenario**: Worst case fund loss
- **Expected Loss**: Probability-weighted loss
- **Risk Score**: 1-100 overall risk rating

### 5. Attack Profitability Matrix
| Scenario | Capital | Profit | Complexity | Likelihood |
|----------|---------|--------|------------|------------|
| Min      |         |        |            |            |
| Expected |         |        |            |            |
| Max      |         |        |            |            |

Be quantitative and reference real-world data where possible.
"""

    @staticmethod
    def get_poc_generation_prompt(code: str, vulnerability: str) -> str:
        """Get prompt for PoC code generation.

        Args:
            code: Vulnerable contract source code
            vulnerability: Description of the vulnerability

        Returns:
            Formatted PoC generation prompt
        """
        return f"""You are a security researcher generating a proof-of-concept exploit for a smart contract vulnerability.

## Vulnerability Description
{vulnerability}

## Target Contract
```solidity
{code}
```

## PoC Requirements

### 1. Foundry Test Format
Generate a complete Foundry test that:
- Sets up the test environment (fork mainnet if needed)
- Deploys necessary contracts
- Executes the attack steps
- Validates successful exploitation
- Shows profit extraction

### 2. Attack Steps
Document each step:
1. Initial state setup
2. Attack transaction sequence
3. State changes verification
4. Profit validation

### 3. Template
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";

contract ExploitTest is Test {{
    // Contract instances
    
    function setUp() public {{
        // Fork mainnet at specific block
        // vm.createSelectFork(vm.rpcUrl("mainnet"), BLOCK);
        
        // Setup contracts
    }}
    
    function testExploit() public {{
        // Record initial balances
        uint256 balanceBefore = ...;
        
        // Execute attack
        // Step 1: ...
        // Step 2: ...
        // Step 3: ...
        
        // Validate profit
        uint256 balanceAfter = ...;
        uint256 profit = balanceAfter - balanceBefore;
        
        console.log("Profit:", profit);
        assertGt(profit, 0, "Attack should be profitable");
    }}
}}
```

### 4. Safety Notes
- Add comments for educational purposes
- Include cleanup steps if applicable
- Note any prerequisites (minimum balances, specific block, etc.)

Generate working, well-commented exploit code.
"""

    @staticmethod
    def get_solana_audit_prompt(code: str, context: str = "") -> str:
        """Get Solana/Rust specific audit prompt.

        Args:
            code: Rust/Anchor source code
            context: Additional context

        Returns:
            Formatted Solana audit prompt
        """
        return f"""You are an expert Solana smart contract security auditor specializing in Anchor programs.

## Context
{context if context else "Analyze the following Solana program for security vulnerabilities."}

## Target Code
```rust
{code}
```

## Solana-Specific Vulnerability Checklist

### Account Validation Issues
1. [ ] Missing signer checks
2. [ ] Missing owner checks
3. [ ] Account type confusion / type cosplay
4. [ ] Missing discriminator validation
5. [ ] PDA seed/bump verification issues

### CPI (Cross-Program Invocation) Issues
6. [ ] Arbitrary CPI to untrusted programs
7. [ ] Missing CPI privilege checks
8. [ ] Incorrect program ID validation

### Arithmetic Issues
9. [ ] Integer overflow without checked_* methods
10. [ ] Precision loss in token calculations
11. [ ] Incorrect decimal handling

### State Management
12. [ ] Duplicate mutable accounts
13. [ ] Account closing without proper cleanup
14. [ ] Rent exemption violations
15. [ ] Reinitialization vulnerabilities

### Economic Attacks
16. [ ] Flash loan vulnerabilities (Solend, Mango patterns)
17. [ ] Oracle manipulation (Pyth, Switchboard)
18. [ ] Liquidation manipulation

### Anchor-Specific
19. [ ] Missing constraint validations
20. [ ] Incorrect has_one usage
21. [ ] seeds/bump derivation issues

## Analysis Format
For each finding:
```
## [SEVERITY] Finding Title

**Account(s) Affected**: account_name (AccountInfo/Account<T>)

**Description**: Clear explanation

**Attack Vector**:
1. Attacker creates malicious account with X properties
2. Attacker calls instruction Y
3. Program fails to validate Z

**Impact**: Fund loss amount / DoS / etc.

**Recommendation**: 
- Add constraint: `#[account(constraint = ...)]`
- Use Anchor's typed accounts
- Add explicit checks

**Code Fix**:
```rust
// Before
pub account: AccountInfo<'info>,

// After
#[account(
    constraint = account.owner == expected_owner,
    signer
)]
pub account: Signer<'info>,
```
```

Focus on Solana-specific patterns. Reference Sealevel Attacks repository where applicable.
"""

    @staticmethod
    def get_move_audit_prompt(code: str, platform: str = "aptos") -> str:
        """Get Move (Aptos/Sui) specific audit prompt.

        Args:
            code: Move source code
            platform: "aptos" or "sui"

        Returns:
            Formatted Move audit prompt
        """
        platform_specific = ""
        if platform == "sui":
            platform_specific = """
### Sui-Specific Checks
- [ ] Object ownership verification
- [ ] Transfer authority checks
- [ ] TxContext validation
- [ ] Shared vs owned object security
"""
        else:
            platform_specific = """
### Aptos-Specific Checks
- [ ] SignerCapability protection
- [ ] Resource account security
- [ ] Coin registration issues
"""

        return f"""You are an expert Move smart contract security auditor for {platform.title()}.

## Target Code
```move
{code}
```

## Move-Specific Vulnerability Checklist

### Resource Handling
1. [ ] Resources not properly stored/moved/destroyed
2. [ ] Resource leakage
3. [ ] Uninitialized resources

### Capability Security
4. [ ] Capability leakage to unauthorized modules
5. [ ] SignerCapability exposure
6. [ ] Witness pattern violations

### Access Control
7. [ ] Missing signer verification
8. [ ] Public functions without guards
9. [ ] Module visibility issues

### Type Safety
10. [ ] Generic type confusion
11. [ ] Phantom type issues
12. [ ] Type cosplay attacks

### Arithmetic
13. [ ] Overflow/underflow (u64/u128)
14. [ ] Division by zero
15. [ ] Precision loss

{platform_specific}

## Analysis Format
For each finding:
```
## [SEVERITY] Finding Title

**Module**: module_name::function_name

**Description**: Clear explanation

**Attack Vector**:
1. Attacker calls function with malicious parameters
2. Validation X is missing
3. Resource Y is compromised

**Impact**: Quantified impact

**Recommendation**: 
```move
// Fixed code with proper checks
public entry fun secure_function(
    account: &signer,
    // ... params
) {{
    assert!(signer::address_of(account) == @admin, ERROR_UNAUTHORIZED);
    // ...
}}
```
```

Focus on Move-specific patterns unique to {platform.title()}.
"""

    @staticmethod
    def get_cairo_audit_prompt(code: str) -> str:
        """Get Cairo/StarkNet specific audit prompt.

        Args:
            code: Cairo source code

        Returns:
            Formatted Cairo audit prompt
        """
        return f"""You are an expert Cairo smart contract security auditor for StarkNet.

## Target Code
```cairo
{code}
```

## Cairo-Specific Vulnerability Checklist

### Felt Arithmetic
1. [ ] Felt252 overflow (prime field arithmetic)
2. [ ] Division truncation issues
3. [ ] Comparison edge cases at field boundary

### Storage Security
4. [ ] Storage collision between contracts
5. [ ] Uninitialized storage reads
6. [ ] Storage variable shadowing

### L1-L2 Messaging
7. [ ] Message replay attacks
8. [ ] Missing message consumption
9. [ ] L1Handler authentication
10. [ ] Cross-layer reentrancy

### Access Control
11. [ ] Missing get_caller_address checks
12. [ ] Contract account vs EOA distinction
13. [ ] Proxy/delegate call authorization

### Cryptographic Issues
14. [ ] Signature validation flaws
15. [ ] Pedersen hash collision considerations
16. [ ] ECDSA edge cases

### Cairo-Specific Patterns
17. [ ] Assert vs return error handling
18. [ ] Reverted state on panic
19. [ ] Library call authorization
20. [ ] Upgradability issues (replace_class)

## Analysis Format
For each finding:
```
## [SEVERITY] Finding Title

**Contract/Function**: contract_name::function_name

**Cairo Version**: 0.x / 1.x

**Description**: Clear explanation

**Attack Vector**:
1. Step 1
2. Step 2

**Impact**: Quantified impact

**Recommendation**: 
```cairo
// Cairo 1.x fix
#[external(v0)]
fn secure_function(ref self: ContractState, ...) {{
    let caller = get_caller_address();
    assert(caller == self.owner.read(), 'Unauthorized');
    // ...
}}
```
```

Focus on StarkNet/Cairo-specific patterns.
"""

    @staticmethod
    def get_monad_audit_prompt(code: str) -> str:
        """Get Monad-specific audit prompt (parallel EVM).

        Args:
            code: Solidity source code for Monad

        Returns:
            Formatted Monad audit prompt
        """
        return f"""You are an expert smart contract security auditor for Monad (parallel EVM).

## Target Code
```solidity
{code}
```

## Monad-Specific Considerations

### Parallel Execution Risks
Monad executes transactions in parallel where possible. This introduces:

1. [ ] **State Dependency Conflicts**
   - Transactions touching same state may execute non-deterministically
   - Consider read-after-write dependencies

2. [ ] **MEV in Parallel Context**
   - Parallel execution changes MEV dynamics
   - Sandwich attacks may behave differently

3. [ ] **High-Throughput Patterns**
   - 10,000+ TPS means faster attack execution
   - Batched attacks more feasible

4. [ ] **Optimistic Execution**
   - State reads may be speculative
   - Rollback implications

### Standard EVM Checks
{SecurityPrompts.VULNERABILITY_CHECKLIST}

### Monad-Specific Analysis
For each finding, additionally consider:
- Impact of parallel execution on the vulnerability
- Whether attack scales with Monad's throughput
- State dependency implications

## Analysis Format
Standard format with additional section:

**Monad-Specific Impact**:
- Parallel execution implications
- Throughput-scaled attack potential
- State conflict analysis

Focus on high-throughput attack scenarios.
"""

    @staticmethod
    def get_cross_protocol_prompt(contracts: List[Dict], protocol_context: str = "") -> str:
        """Get cross-protocol analysis prompt.

        Args:
            contracts: List of contract info dicts with 'name' and 'code'
            protocol_context: Context about protocol interactions

        Returns:
            Formatted cross-protocol audit prompt
        """
        contract_sections = []
        for i, contract in enumerate(contracts):
            contract_sections.append(f"""
### Contract {i + 1}: {contract.get('name', 'Unknown')}
```solidity
{contract.get('code', '')}
```
""")

        contracts_text = "\n".join(contract_sections)

        return f"""You are an expert DeFi security auditor analyzing cross-protocol interactions.

## Protocol Context
{protocol_context if protocol_context else "Analyze the following contracts for cross-protocol vulnerabilities."}

## Contracts
{contracts_text}

## Cross-Protocol Vulnerability Analysis

### 1. Composability Risks
Analyze interactions between:
- This protocol and external protocols
- Flash loan providers
- Price oracles
- Governance systems
- Bridge contracts

### 2. Attack Vectors
Check for:
1. [ ] Flash loan oracle manipulation paths
2. [ ] Cross-protocol reentrancy
3. [ ] Governance attack via borrowed tokens
4. [ ] Bridge message replay
5. [ ] Cascading liquidations
6. [ ] Composable MEV opportunities

### 3. Dependency Analysis
Map:
- External contract dependencies
- Oracle dependencies
- Token dependencies
- Upgrade dependencies

### 4. Protocol Invariants
Identify and validate:
- Economic invariants that must hold
- State invariants across contracts
- Timing assumptions

### 5. Attack Path Enumeration
For each potential attack:
1. Entry point (which external protocol)
2. Capital requirements (flash loan availability)
3. Transaction sequence
4. Profit extraction method
5. Required timing

## Output Format
```
## [SEVERITY] Cross-Protocol Attack: [Name]

**Attack Path**:
Protocol A → Protocol B → Target → Profit

**Prerequisites**:
- Flash loan of $X from Y
- Price manipulation via Z

**Transaction Sequence**:
1. Borrow X from A
2. Deposit to B to manipulate price
3. Exploit target at manipulated price
4. Repay loan, extract profit

**Economic Impact**:
- Capital: $X (flash loaned)
- Profit: $Y
- Complexity: High

**Mitigation**:
- Use TWAP oracle
- Add cross-protocol reentrancy guards
```

Focus on realistic attack paths with quantified economics.
"""

    @staticmethod
    def get_all_prompts() -> Dict[str, SecurityPrompt]:
        """Get all available security prompts.

        Returns:
            Dictionary of prompt name to SecurityPrompt
        """
        return {
            "comprehensive_audit": SecurityPrompt(
                name="Comprehensive Security Audit",
                category=PromptCategory.VULNERABILITY_DETECTION,
                template="See get_comprehensive_audit_prompt()",
                variables=["code", "context"],
                language="solidity",
            ),
            "economic_impact": SecurityPrompt(
                name="Economic Impact Analysis",
                category=PromptCategory.ECONOMIC_ANALYSIS,
                template="See get_economic_impact_prompt()",
                variables=["code", "finding"],
            ),
            "poc_generation": SecurityPrompt(
                name="PoC Code Generation",
                category=PromptCategory.POC_GENERATION,
                template="See get_poc_generation_prompt()",
                variables=["code", "vulnerability"],
                language="solidity",
            ),
            "solana_audit": SecurityPrompt(
                name="Solana/Anchor Audit",
                category=PromptCategory.LANGUAGE_SPECIFIC,
                template="See get_solana_audit_prompt()",
                variables=["code", "context"],
                language="rust",
            ),
            "move_audit": SecurityPrompt(
                name="Move (Aptos/Sui) Audit",
                category=PromptCategory.LANGUAGE_SPECIFIC,
                template="See get_move_audit_prompt()",
                variables=["code", "platform"],
                language="move",
            ),
            "cairo_audit": SecurityPrompt(
                name="Cairo/StarkNet Audit",
                category=PromptCategory.LANGUAGE_SPECIFIC,
                template="See get_cairo_audit_prompt()",
                variables=["code"],
                language="cairo",
            ),
            "monad_audit": SecurityPrompt(
                name="Monad (Parallel EVM) Audit",
                category=PromptCategory.LANGUAGE_SPECIFIC,
                template="See get_monad_audit_prompt()",
                variables=["code"],
                language="solidity",
            ),
            "cross_protocol": SecurityPrompt(
                name="Cross-Protocol Analysis",
                category=PromptCategory.CROSS_PROTOCOL,
                template="See get_cross_protocol_prompt()",
                variables=["contracts", "protocol_context"],
            ),
        }
