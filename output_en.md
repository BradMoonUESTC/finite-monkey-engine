# Parameter Modification

I'll analyze this Jetton (TON token) contract for potential parameter reconfiguration mechanisms that could affect token balances or security.

### Storage Structure Analysis

```func
;; Storage structure
(int, slice, slice, cell, cell) load_data() impure inline {
    slice ds = get_data().begin_parse();
    var data = (
        ds~load_coins(),     // total_supply
        ds~load_msg_addr(),  // admin_address
        ds~load_msg_addr(),  // next_admin_address
        ds~load_ref(),       // jetton_wallet_code
        ds~load_ref()        // metadata_uri
    );
    merkle_root = ds~load_uint(MERKLE_ROOT_SIZE);
    return data;
}
```

Key storage parameters:
- `total_supply`: Total token supply
- `admin_address`: Current admin address
- `next_admin_address`: Pending admin address
- `jetton_wallet_code`: Code for wallet contracts
- `metadata_uri`: Token metadata
- `merkle_root`: Global merkle root value

### Administrative Functions Analysis

1. **Admin Change Mechanism**:
```func
// ... existing code ...
if (op == op::change_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    next_admin_address = in_msg_body~load_msg_addr();
    save_data(total_supply, admin_address, next_admin_address, jetton_wallet_code, metadata_uri);
    return ();
}

if (op == op::claim_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, next_admin_address));
    save_data(total_supply, next_admin_address, address_none(), jetton_wallet_code, metadata_uri);
    return ();
}
// ... existing code ...
```

2. **Contract Upgrade Mechanism**:
```func
if (op == op::upgrade) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    (cell new_data, cell new_code) = (in_msg_body~load_ref(), in_msg_body~load_ref());
    set_data(new_data);
    set_code(new_code);
    return ();
}
```

### Significant Security Considerations:

1. **Contract Upgrade Risk**:
   - The `upgrade` operation allows complete replacement of contract code and data
   - Only admin can trigger this, but it's a significant power
   - Could potentially be used to modify token behavior or balances

2. **Metadata Modification**:
```func
if (op == op::change_metadata_uri) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    save_data(total_supply, admin_address, next_admin_address, jetton_wallet_code, begin_cell().store_slice(in_msg_body).end_cell());
    return ();
}
```

3. **Admin Control**:
   - Admin can be changed through a two-step process
   - Admin can be dropped entirely using `drop_admin`
   - Admin controls minting through `op::mint`

### Query Functions:

```func
(int, int, slice, cell, cell) get_jetton_data() method_id {
    // Returns total_supply, is_mintable flag, admin_address, content, and wallet_code
}

slice get_next_admin_address() method_id {
    // Returns pending admin address
}

int get_mintless_airdrop_hashmap_root() method_id {
    // Returns merkle root value
}
```

### Key Security Implications:

1. **Balance Impact Potential**:
   - Minting capability: Admin can mint new tokens
   - Contract upgrade capability could theoretically modify balance accounting
   - No direct balance modification functions outside of mint/burn

2. **Critical Parameters**:
   - `merkle_root`: Used in wallet address calculations
   - `jetton_wallet_code`: Controls wallet contract deployment
   - Both parameters affect wallet address derivation

### Recommendations for Exchanges:

1. Monitor admin operations, particularly:
   - Contract upgrades (`op::upgrade`)
   - Minting operations (`op::mint`)
   - Admin changes (`op::change_admin`, `op::claim_admin`)

2. Implement additional checks:
   - Track total supply changes
   - Verify wallet code hasn't changed
   - Monitor metadata modifications

3. Consider the upgrade capability as a significant risk factor that requires additional security measures or monitoring.

The contract does contain significant administrative powers that could potentially affect token behavior and balances, primarily through the upgrade mechanism. While there are no direct balance manipulation functions beyond standard mint/burn operations, the upgrade capability provides a potential vector for such changes.

---

# Minting

I'll analyze the minting risks in this TON jetton contract systematically.

### 1. Minting Functionality Analysis

#### Key Minting Components
```func
if (op == op::mint) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    // ... minting logic ...
    save_data(total_supply + jetton_amount, admin_address, next_admin_address, jetton_wallet_code, metadata_uri);
    return ();
}
```

**Observations:**
- The contract has a single `mint` operation
- No explicit supply caps
- No rate limiting mechanisms
- No time-based restrictions on minting
- No batch minting functionality

### 2. Control Analysis

#### Minting Authority
```func
// Admin control functions
if (op == op::change_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    next_admin_address = in_msg_body~load_msg_addr();
    // ...
}

if (op == op::drop_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    save_data(total_supply, address_none(), address_none(), jetton_wallet_code, metadata_uri);
    // ...
}
```

**Key Points:**
- Only the admin can mint tokens
- Admin privileges can be:
  - Transferred (`change_admin`)
  - Renounced (`drop_admin`)
- No timelock controls on admin actions
- Two-step admin transfer process (change + claim)

### 3. Supply Management

```func
(int, slice, slice, cell, cell) load_data() impure inline {
    // ... loading total_supply and other data
}

// Supply tracking in mint operation
save_data(total_supply + jetton_amount, admin_address, next_admin_address, jetton_wallet_code, metadata_uri);
```

**Analysis:**
- Total supply is tracked but not capped
- No maximum supply limit
- No minting schedule or vesting
- Supply can be reduced through burning

### 4. Risk Assessment

#### Major Risks:
1. **Unlimited Minting**: The admin can mint any amount at any time
2. **No Rate Limiting**: No cooldown between mints
3. **No Supply Cap**: Potential for infinite inflation
4. **Centralized Control**: Single admin has complete minting authority

#### Mitigating Factors:
1. Admin can be renounced using `drop_admin`
2. Burns are properly tracked and reduce total supply
3. Transparent supply tracking through `get_jetton_data()`

### 5. Implementation Details

```func
send_to_jetton_wallet(to_address, jetton_wallet_code, ton_amount, master_msg, TRUE);
save_data(total_supply + jetton_amount, admin_address, next_admin_address, jetton_wallet_code, metadata_uri);
```

**Technical Implementation:**
- Proper balance updates
- Accurate supply tracking
- Basic error handling through `throw_unless`
- Bounced message handling for failed mints

### Recommendations for Improvement

1. **Supply Cap**:
   - Implement maximum supply limit
   - Add checks in mint function

2. **Rate Limiting**:
   - Add cooldown period between mints
   - Implement maximum mint amount per transaction

3. **Access Control**:
   - Consider multi-signature requirement for minting
   - Add timelock for large mints

4. **Transparency**:
   - Add mint events/logging
   - Implement mint scheduling/vesting

### Conclusion

This contract has significant minting risks due to:
1. Unlimited minting capability
2. No rate limiting
3. Centralized control
4. Lack of protective mechanisms

While the implementation is technically sound, the lack of restrictions on minting could lead to potential value dilution for token holders. The only protection is the ability to renounce admin rights, which is irreversible.

---

# Superuser

I'll analyze the contract for Superuser risks systematically.

### 1. Privileged Functions Analysis

The contract implements several admin-only functions, controlled by the check `equal_slices_bits(sender_address, admin_address)`:

```func
// Key admin functions:

if (op == op::mint) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    // Allows admin to mint tokens to any address
}

if (op == op::change_metadata_uri) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    // Allows admin to change token metadata
}

if (op == op::upgrade) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    // Allows admin to upgrade contract code and data
}
```

### 2. Control Structure

The contract implements a two-step ownership transfer pattern:

```func
if (op == op::change_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    next_admin_address = in_msg_body~load_msg_addr();
    // Step 1: Current admin nominates new admin
}

if (op == op::claim_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, next_admin_address));
    save_data(total_supply, next_admin_address, address_none(), jetton_wallet_code, metadata_uri);
    // Step 2: Nominated admin must claim ownership
}
```

There's also a `drop_admin` function that can remove admin control entirely:
```func
if (op == op::drop_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    save_data(total_supply, address_none(), address_none(), jetton_wallet_code, metadata_uri);
}
```

### 3. Critical Parameters

Key controllable parameters include:
- Total supply (via minting)
- Metadata URI
- Contract code (via upgrade)
- Admin address

### 4. Risk Assessment

Major centralization risks:

1. **Unlimited Minting Power**: The admin can mint unlimited tokens, potentially leading to:
   - Token value dilution
   - Market manipulation
   - No minting caps or timelock restrictions

2. **Code Upgrade Risk**: The admin can upgrade the entire contract code via `op::upgrade`, which could:
   - Change token mechanics
   - Modify user balances
   - Add malicious functionality
   - No timelock or community review process

3. **Metadata Control**: Admin can change metadata URI at will, affecting:
   - Token information
   - Display properties
   - External references

### 5. Security Measures

Positive security features:
1. Two-step ownership transfer reduces transfer risks
2. Ability to permanently remove admin control via `drop_admin`
3. Clear separation between admin and user operations

Missing security features:
1. No minting caps or limits
2. No timelock on critical operations
3. No multi-signature requirements
4. No emergency pause functionality
5. No event emissions for admin actions

### Recommendations

1. **Minting Controls**:
   - Implement maximum supply cap
   - Add minting rate limits
   - Consider timelock for large mints

2. **Upgrade Safety**:
   - Add timelock for upgrades
   - Implement upgrade proposal/review system
   - Add version control

3. **Administrative**:
   - Consider multi-signature admin control
   - Add event notifications for admin actions
   - Implement timelocks for critical parameter changes

4. **Transparency**:
   - Add logging for admin operations
   - Implement change notification system
   - Add public upgrade proposal period

The contract has significant centralization risks due to the broad powers given to the admin address, particularly around minting and upgrades. While it includes some safety features like two-step ownership transfer, it lacks many modern protection mechanisms that could reduce centralization risks.

---

# Ownership Transfer

I'll analyze the ownership transfer mechanisms and their security implications for users in this Jetton (TON token) contract.

### 1. Ownership Transfer Mechanisms

The contract implements a two-step ownership transfer pattern through two main operations:

```func
// First step - Current admin initiates transfer
if (op == op::change_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    next_admin_address = in_msg_body~load_msg_addr();
    save_data(total_supply, admin_address, next_admin_address, jetton_wallet_code, metadata_uri);
    return ();
}

// Second step - New admin claims ownership
if (op == op::claim_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, next_admin_address));
    save_data(total_supply, next_admin_address, address_none(), jetton_wallet_code, metadata_uri);
    return ();
}
```

### 2. Administrative Powers

The admin has several powerful capabilities:

1. **Minting Power**:
```func
if (op == op::mint) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    // ... minting logic
}
```

2. **Metadata Control**:
```func
if (op == op::change_metadata_uri) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    save_data(total_supply, admin_address, next_admin_address, jetton_wallet_code, begin_cell().store_slice(in_msg_body).end_cell());
    return ();
}
```

3. **Contract Upgrade Capability**:
```func
if (op == op::upgrade) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    (cell new_data, cell new_code) = (in_msg_body~load_ref(), in_msg_body~load_ref());
    set_data(new_data);
    set_code(new_code);
    return ();
}
```

### 3. Risk Assessment for Users

1. **Minting Risk**:
   - The admin can mint unlimited tokens, potentially leading to inflation
   - No maximum supply cap
   - Users' token value could be diluted through excessive minting

2. **Contract Upgrade Risk**:
   - Admin can completely replace contract code
   - No upgrade limitations or timelock
   - Could potentially modify token behavior or user balances

3. **Metadata Manipulation**:
   - Admin can change token metadata at will
   - Could affect token representation and market perception

4. **Ownership Concentration**:
   - Single admin model with full powers
   - No multi-signature or DAO governance
   - No time-delays on critical operations

### 4. User Protection Features

1. **Two-Step Transfer**:
   - Ownership transfer requires explicit claim
   - Prevents accidental transfers to wrong addresses
   - However, doesn't protect against malicious admin actions

2. **Admin Renunciation**:
```func
if (op == op::drop_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    save_data(total_supply, address_none(), address_none(), jetton_wallet_code, metadata_uri);
    return ();
}
```
   - Admin can permanently renounce control
   - Once renounced, no new admin can be appointed

### Security Recommendations for Users

1. **Trust Assessment**:
   - Verify initial admin address
   - Monitor admin changes through `get_next_admin_address()` method
   - Be cautious of tokens with active admins

2. **Risk Mitigation**:
   - Consider admin's reputation and track record
   - Monitor minting events
   - Be aware that contract can be upgraded at any time

3. **Missing Protections**:
   - No maximum supply cap
   - No minting rate limits
   - No timelock on admin actions
   - No emergency pause functionality

### Conclusion

From a user's perspective, this contract presents significant trust requirements in the admin. The admin has unrestricted powers to:
- Mint unlimited tokens
- Upgrade the contract
- Modify metadata
- Transfer ownership

While the two-step ownership transfer provides some safety against accidental transfers, it doesn't protect users from malicious admin actions. Users should carefully consider these risks before interacting with the token, especially in DeFi applications where token behavior consistency is crucial.

---

# Upgradeable

I'll analyze the contract for upgrade-related risks:

### 1. Direct Upgrade Mechanism

The contract has a direct upgrade mechanism through the `op::upgrade` operation:

```func
if (op == op::upgrade) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    (cell new_data, cell new_code) = (in_msg_body~load_ref(), in_msg_body~load_ref());
    in_msg_body.end_parse();
    set_data(new_data);
    set_code(new_code);
    return ();
}
```

Key observations:
- The admin can directly replace both code and data
- Uses `set_code()` to update contract logic
- Uses `set_data()` to update contract storage
- Protected by admin-only access control

### 2. Storage Layout

The contract uses a structured storage pattern:

```func
;; storage#_ total_supply:Coins admin_address:MsgAddress next_admin_address:MsgAddress jetton_wallet_code:^Cell metadata_uri:^Cell = Storage;
(int, slice, slice, cell, cell) load_data() impure inline {
    slice ds = get_data().begin_parse();
    var data = (
        ds~load_coins(),        ;; total_supply
        ds~load_msg_addr(),     ;; admin_address
        ds~load_msg_addr(),     ;; next_admin_address
        ds~load_ref(),          ;; jetton_wallet_code
        ds~load_ref()           ;; metadata url
    );
    merkle_root = ds~load_uint(MERKLE_ROOT_SIZE);
    ds.end_parse();
    return data;
}
```

### 3. Admin Control Mechanisms

The contract has several admin-related functions:

1. Change Admin:
```func
if (op == op::change_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    next_admin_address = in_msg_body~load_msg_addr();
    // ...
}
```

2. Claim Admin:
```func
if (op == op::claim_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, next_admin_address));
    save_data(total_supply, next_admin_address, address_none(), jetton_wallet_code, metadata_uri);
    // ...
}
```

3. Drop Admin:
```func
if (op == op::drop_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    save_data(total_supply, address_none(), address_none(), jetton_wallet_code, metadata_uri);
    // ...
}
```

### Upgrade Risks Assessment:

1. **Proxy Contract Mechanism**:
- No traditional proxy pattern used
- No delegatecall equivalent
- Direct code replacement instead of proxy-based upgrades

2. **CREATE2 Mechanism**:
- No CREATE2 equivalent found
- No self-destruct functionality
- No redeployment initialization logic

3. **Assembly Code**:
- No low-level assembly code present
- Uses high-level FunC operations

4. **Other Upgrade Considerations**:
- No explicit initialization function
- Storage layout is well-defined and consistent
- No beacon proxy pattern
- Admin controls are properly implemented with two-step transfer

### Security Implications:

1. **Unlimited Upgrade Power**:
- The admin has complete control to replace contract code
- No restrictions on what new code can contain
- No timelock or governance mechanism

2. **Admin Control Risks**:
- Two-step admin transfer provides some safety
- Admin can be removed via `drop_admin`
- No multi-signature or DAO governance

3. **Storage Consistency**:
- New code must maintain compatible storage layout
- Risk of storage corruption if upgrade doesn't respect structure

### Recommendations:

1. Consider adding:
- Upgrade timelock mechanism
- Version control for upgrades
- Storage layout verification in upgrade process
- Multi-signature or DAO governance for upgrades

2. Implement:
- Upgrade events/notifications
- Emergency pause functionality
- Upgrade proposal/review period

3. Document:
- Storage layout requirements for upgrades
- Admin responsibilities and limitations
- Upgrade procedures and safety checks

The contract has significant upgrade capabilities but lacks sophisticated safety mechanisms. The admin has substantial power to modify the contract, which could be a security risk if the admin key is compromised.

---

# Non Standard ERC20

I'll analyze this contract for ERC-20 compliance, but first, it's important to note that this is actually a TON (The Open Network) Jetton contract, not an Ethereum ERC-20 contract. Jettons are TON's equivalent to ERC-20 tokens, but they follow different standards and patterns. Let's analyze the key differences:

### 1. Standard Interface Compliance

This contract follows the TEP-74 (TON Enhancement Proposal) Jetton standard, which is fundamentally different from ERC-20:

#### Key Differences:

1. **Architecture**:
```func
() recv_internal(int msg_value, cell in_msg_full, slice in_msg_body)
```
- Uses TON's asynchronous message-passing architecture instead of Ethereum's synchronous function calls
- Operations are handled through op codes (like `op::mint`, `op::burn_notification`) rather than direct function calls

2. **State Management**:
```func
(int, slice, slice, cell, cell) load_data() impure inline {
    slice ds = get_data().begin_parse();
    var data = (
        ds~load_coins(),      // total_supply
        ds~load_msg_addr(),   // admin_address
        ds~load_msg_addr(),   // next_admin_address
        ds~load_ref(),        // jetton_wallet_code
        ds~load_ref()         // metadata_uri
    );
```
- Uses TON's cell-based storage instead of Ethereum's key-value storage
- Implements a two-contract system: Minter and Wallet contracts (ERC-20 uses a single contract)

### 2. Function Behavior Analysis

#### Non-standard Features:

1. **Wallet Code Storage**:
```func
cell jetton_wallet_code    // Stores the code for individual wallet contracts
```
- Each user's tokens are managed by a separate wallet contract
- No direct equivalent in ERC-20

2. **Administrative Controls**:
```func
if (op == op::change_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    next_admin_address = in_msg_body~load_msg_addr();
```
- Implements admin transfer functionality
- Includes `drop_admin` operation for renouncing ownership

### 3. Token Properties

1. **Metadata Handling**:
```func
cell build_content_cell(slice metadata_uri) inline {
    cell content_dict = new_dict();
    content_dict~set_token_snake_metadata_entry("uri"H, metadata_uri);
    return create_token_onchain_metadata(content_dict);
}
```
- Uses TON-specific metadata format
- Stores metadata URI in contract storage

2. **Merkle Root Integration**:
```func
global int merkle_root;
```
- Implements merkle tree verification for token operations
- Not present in standard ERC-20

### 4. Custom Features

1. **Gas Management**:
```func
raw_reserve(ONE_TON, RESERVE_REGULAR); // reserve for storage fees
```
- Implements TON-specific gas handling
- Manages message forwarding fees

2. **Workchain Validation**:
```func
check_same_workchain(to_address);
```
- Implements cross-workchain transfer restrictions
- No equivalent in ERC-20

### Integration/Compatibility Issues

1. **DApp Integration**:
- DApps built for ERC-20 tokens cannot directly interact with this contract
- Requires TON-specific integration methods
- Message-passing model differs from Ethereum's direct call model

2. **Wallet Compatibility**:
- Not compatible with standard ERC-20 wallets
- Requires TON-specific wallet implementation

3. **Security Model**:
- Uses TON's security patterns (message bouncing, gas management)
- Different error handling approach from ERC-20

### Recommendations for Integration

1. When integrating with existing systems:
- Build adapter layers for ERC-20 compatibility
- Implement message-passing translation layers
- Consider cross-chain bridge requirements

2. For front-end integration:
- Use TON-specific libraries
- Implement proper message handling
- Account for asynchronous operation model

This contract is well-implemented for TON but should not be considered an ERC-20 token. It's a fundamentally different token standard designed for TON's unique architecture and capabilities.

---

