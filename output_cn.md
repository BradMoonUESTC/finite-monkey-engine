# Parameter Modification

### Jetton (TON代币)合约的参数重配置机制风险分析

### 存储结构分析

```func
;; 存储结构
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

关键存储参数:
- `total_supply`: 代币总供应量
- `admin_address`: 当前管理员地址
- `next_admin_address`: 待定管理员地址
- `jetton_wallet_code`: 钱包合约代码
- `metadata_uri`: 代币元数据
- `merkle_root`: 全局默克尔树根值

### 管理功能分析

1. **管理员变更机制**:
```func
// ... 现有代码 ...
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
// ... 现有代码 ...
```

2. **合约升级机制**:
```func
if (op == op::upgrade) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    (cell new_data, cell new_code) = (in_msg_body~load_ref(), in_msg_body~load_ref());
    set_data(new_data);
    set_code(new_code);
    return ();
}
```

### 重要安全考虑:

1. **合约升级风险**:
   - `upgrade`操作允许完全替换合约代码和数据
   - 仅管理员可触发，但这是一项重要权力
   - 可能被用于修改代币行为或余额

2. **元数据修改**:
```func
if (op == op::change_metadata_uri) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    save_data(total_supply, admin_address, next_admin_address, jetton_wallet_code, begin_cell().store_slice(in_msg_body).end_cell());
    return ();
}
```

3. **管理员控制**:
   - 管理员可通过两步流程更改
   - 可以使用`drop_admin`完全移除管理员
   - 管理员通过`op::mint`控制铸币

### 查询功能:

```func
(int, int, slice, cell, cell) get_jetton_data() method_id {
    // 返回total_supply、is_mintable标志、admin_address、content和wallet_code
}

slice get_next_admin_address() method_id {
    // 返回待定管理员地址
}

int get_mintless_airdrop_hashmap_root() method_id {
    // 返回默克尔树根值
}
```

### 主要安全影响:

1. **余额影响潜力**:
   - 铸币能力: 管理员可以铸造新代币
   - 合约升级功能理论上可以修改余额计算
   - 除铸币/销毁外没有直接的余额修改功能

2. **关键参数**:
   - `merkle_root`: 用于钱包地址计算
   - `jetton_wallet_code`: 控制钱包合约部署
   - 这两个参数都影响钱包地址派生

### 交易所建议:

1. 监控管理员操作，特别是:
   - 合约升级(`op::upgrade`)
   - 铸币操作(`op::mint`)
   - 管理员变更(`op::change_admin`, `op::claim_admin`)

2. 实施额外检查:
   - 追踪总供应量变化
   - 验证钱包代码未改变
   - 监控元数据修改

3. 将升级能力视为需要额外安全措施或监控的重要风险因素

该合约包含可能影响代币行为和余额的重要管理权限，主要通过升级机制。虽然除了标准的铸币/销毁操作外没有直接的余额操作功能，但升级功能提供了此类更改的潜在途径。

---

# Minting

### TON jetton 合约铸币风险分析

### 1. 铸币功能分析

#### 关键铸币组件
```func
if (op == op::mint) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    // ... minting logic ...
    save_data(total_supply + jetton_amount, admin_address, next_admin_address, jetton_wallet_code, metadata_uri);
    return ();
}
```

**观察结果:**
- 合约有单一的`mint`操作
- 没有明确的供应上限
- 没有速率限制机制
- 没有基于时间的铸币限制
- 没有批量铸币功能

### 2. 控制权分析

#### 铸币权限
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

**要点:**
- 只有管理员可以铸币
- 管理员权限可以:
  - 转让(`change_admin`)
  - 放弃(`drop_admin`)
- 管理员操作没有时间锁控制
- 两步管理员转让流程(更改 + 认领)

### 3. 供应管理

```func
(int, slice, slice, cell, cell) load_data() impure inline {
    // ... loading total_supply and other data
}

// Supply tracking in mint operation
save_data(total_supply + jetton_amount, admin_address, next_admin_address, jetton_wallet_code, metadata_uri);
```

**分析:**
- 总供应量被追踪但未设上限
- 没有最大供应限制
- 没有铸币计划或归属期
- 供应量可以通过销毁减少

### 4. 风险评估

#### 主要风险:
1. **无限铸币**: 管理员可以随时铸造任意数量
2. **无速率限制**: 铸币之间没有冷却期
3. **无供应上限**: 可能导致无限通胀
4. **中心化控制**: 单一管理员拥有完整的铸币权限

#### 缓解因素:
1. 可以通过`drop_admin`放弃管理员权限
2. 正确追踪销毁并减少总供应量
3. 通过`get_jetton_data()`实现透明的供应量追踪

### 5. 实现细节

```func
send_to_jetton_wallet(to_address, jetton_wallet_code, ton_amount, master_msg, TRUE);
save_data(total_supply + jetton_amount, admin_address, next_admin_address, jetton_wallet_code, metadata_uri);
```

**技术实现:**
- 正确的余额更新
- 准确的供应量追踪
- 通过`throw_unless`进行基本错误处理
- 处理失败铸币的退回消息

### 改进建议

1. **供应上限**:
   - 实现最大供应限制
   - 在铸币函数中添加检查

2. **速率限制**:
   - 添加铸币之间的冷却期
   - 实现每次交易的最大铸币量

3. **访问控制**:
   - 考虑铸币需要多重签名
   - 为大额铸币添加时间锁

4. **透明度**:
   - 添加铸币事件/日志
   - 实现铸币计划/归属

### 结论

该合约存在显著的铸币风险，原因如下:
1. 无限铸币能力
2. 没有速率限制
3. 中心化控制
4. 缺乏保护机制

虽然技术实现是合理的，但缺乏铸币限制可能导致代币持有者价值被稀释。唯一的保护是可以放弃管理员权限，但这是不可逆的。

---

# Superuser

我将对合约进行 Superuser 风险的系统性分析。

### 1. 特权函数分析

该合约实现了几个仅管理员可用的函数，通过检查 `equal_slices_bits(sender_address, admin_address)` 进行控制：

```func
// 关键管理员函数：

if (op == op::mint) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    // 允许管理员向任何地址铸造代币
}

if (op == op::change_metadata_uri) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    // 允许管理员更改代币元数据
}

if (op == op::upgrade) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    // 允许管理员升级合约代码和数据
}
```

### 2. 控制结构

该合约实现了两步所有权转移模式：

```func
if (op == op::change_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    next_admin_address = in_msg_body~load_msg_addr();
    // 第1步：当前管理员提名新管理员
}

if (op == op::claim_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, next_admin_address));
    save_data(total_supply, next_admin_address, address_none(), jetton_wallet_code, metadata_uri);
    // 第2步：被提名的管理员必须认领所有权
}
```

还有一个可以完全移除管理员控制的 `drop_admin` 函数：
```func
if (op == op::drop_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    save_data(total_supply, address_none(), address_none(), jetton_wallet_code, metadata_uri);
}
```

### 3. 关键参数

可控制的关键参数包括：
- 总供应量（通过铸造）
- 元数据 URI
- 合约代码（通过升级）
- 管理员地址

### 4. 风险评估

主要的中心化风险：

1. **无限铸币权力**：管理员可以无限制地铸造代币，可能导致：
   - 代币价值稀释
   - 市场操纵
   - 没有铸币上限或时间锁定限制

2. **代码升级风险**：管理员可以通过 `op::upgrade` 升级整个合约代码，这可能：
   - 改变代币机制
   - 修改用户余额
   - 添加恶意功能
   - 没有时间锁定或社区审查流程

3. **元数据控制**：管理员可以随意更改元数据 URI，影响：
   - 代币信息
   - 显示属性
   - 外部引用

### 5. 安全措施

积极的安全特性：
1. 两步所有权转移降低了转移风险
2. 能够通过 `drop_admin` 永久移除管理员控制
3. 管理员和用户操作之间明确分离

缺失的安全特性：
1. 没有铸币上限或限制
2. 关键操作没有时间锁定
3. 没有多重签名要求
4. 没有紧急暂停功能
5. 没有管理员操作事件发送

### 建议

1. **铸币控制**：
   - 实现最大供应量上限
   - 添加铸币速率限制
   - 考虑大额铸币的时间锁定

2. **升级安全**：
   - 为升级添加时间锁定
   - 实现升级提案/审查系统
   - 添加版本控制

3. **管理措施**：
   - 考虑多重签名管理员控制
   - 添加管理员操作事件通知
   - 为关键参数更改实现时间锁定

4. **透明度**：
   - 添加管理员操作日志
   - 实现变更通知系统
   - 添加公开升级提案期

由于赋予管理员地址广泛的权力，特别是在铸币和升级方面，该合约存在显著的中心化风险。虽然它包含了一些安全特性，如两步所有权转移，但缺少许多可以降低中心化风险的现代保护机制。

---

# Ownership Transfer

### Jetton (TON代币)合约的所有权转移机制及其安全性分析

### 1. 所有权转移机制

该合约通过两个主要操作实现两步所有权转移模式：

```func
// 第一步 - 当前管理员发起转移
if (op == op::change_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    next_admin_address = in_msg_body~load_msg_addr();
    save_data(total_supply, admin_address, next_admin_address, jetton_wallet_code, metadata_uri);
    return ();
}

// 第二步 - 新管理员认领所有权
if (op == op::claim_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, next_admin_address));
    save_data(total_supply, next_admin_address, address_none(), jetton_wallet_code, metadata_uri);
    return ();
}
```

### 2. 管理权限

管理员拥有几项强大的功能：

1. **铸币权限**:
```func
if (op == op::mint) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    // ... 铸币逻辑
}
```

2. **元数据控制**:
```func
if (op == op::change_metadata_uri) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    save_data(total_supply, admin_address, next_admin_address, jetton_wallet_code, begin_cell().store_slice(in_msg_body).end_cell());
    return ();
}
```

3. **合约升级能力**:
```func
if (op == op::upgrade) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    (cell new_data, cell new_code) = (in_msg_body~load_ref(), in_msg_body~load_ref());
    set_data(new_data);
    set_code(new_code);
    return ();
}
```

### 3. 用户风险评估

1. **铸币风险**:
   - 管理员可以无限制铸币，可能导致通货膨胀
   - 没有最大供应量上限
   - 用户代币价值可能因过度铸币而被稀释

2. **合约升级风险**:
   - 管理员可以完全替换合约代码
   - 没有升级限制或时间锁
   - 可能修改代币行为或用户余额

3. **元数据操作**:
   - 管理员可以随意更改代币元数据
   - 可能影响代币展示和市场认知

4. **所有权集中**:
   - 单一管理员模式拥有全部权限
   - 没有多重签名或DAO治理
   - 关键操作没有时间延迟

### 4. 用户保护功能

1. **两步转移**:
   - 所有权转移需要明确认领
   - 防止意外转移到错误地址
   - 但不能防止恶意管理员行为

2. **管理员放弃权限**:
```func
if (op == op::drop_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    save_data(total_supply, address_none(), address_none(), jetton_wallet_code, metadata_uri);
    return ();
}
```

   - 管理员可以永久放弃控制权
   - 一旦放弃，无法指定新管理员

### 用户安全建议

1. **信任评估**:
   - 验证初始管理员地址
   - 通过`get_next_admin_address()`方法监控管理员变更
   - 对于有活跃管理员的代币要保持谨慎

2. **风险缓解**:
   - 考虑管理员的声誉和过往记录
   - 监控铸币事件
   - 注意合约可能随时被升级

3. **缺失的保护机制**:
   - 没有最大供应量上限
   - 没有铸币速率限制
   - 没有管理员操作的时间锁
   - 没有紧急暂停功能

### 结论

从用户角度来看，该合约对管理员要求很高的信任度。管理员拥有不受限制的权力：
- 无限制铸币
- 升级合约
- 修改元数据
- 转移所有权

虽然两步所有权转移为防止意外转移提供了一些安全保障，但它无法保护用户免受恶意管理员行为的影响。用户在与该代币交互之前应该仔细考虑这些风险，特别是在DeFi应用中，代币行为的一致性至关重要。

---

# Upgradeable

我将为您分析合约的升级相关风险：

### 1. 直接升级机制

合约通过`op::upgrade`操作具有直接升级机制：

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

主要观察：
- 管理员可以直接替换代码和数据
- 使用`set_code()`更新合约逻辑
- 使用`set_data()`更新合约存储
- 受管理员专属访问控制保护

### 2. 存储布局

合约使用结构化存储模式：

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

### 3. 管理员控制机制

合约有几个管理员相关功能：

1. 更改管理员：
```func
if (op == op::change_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    next_admin_address = in_msg_body~load_msg_addr();
    // ...
}
```

2. 认领管理员：
```func
if (op == op::claim_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, next_admin_address));
    save_data(total_supply, next_admin_address, address_none(), jetton_wallet_code, metadata_uri);
    // ...
}
```

3. 移除管理员：
```func
if (op == op::drop_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    save_data(total_supply, address_none(), address_none(), jetton_wallet_code, metadata_uri);
    // ...
}
```

### 升级风险评估：

1. **代理合约机制**：
- 未使用传统代理模式
- 无delegatecall等效功能
- 直接代码替换而非基于代理的升级

2. **CREATE2机制**：
- 未发现CREATE2等效功能
- 无自毁功能
- 无重新部署初始化逻辑

3. **汇编代码**：
- 不存在低级汇编代码
- 使用高级FunC操作

4. **其他升级考虑**：
- 无显式初始化函数
- 存储布局定义良好且一致
- 无信标代理模式
- 管理员控制通过两步转移正确实现

### 安全影响：

1. **无限升级权限**：
- 管理员可完全控制替换合约代码
- 对新代码内容无限制
- 无时间锁定或治理机制

2. **管理员控制风险**：
- 两步管理员转移提供一定安全性
- 可通过`drop_admin`移除管理员
- 无多重签名或DAO治理

3. **存储一致性**：
- 新代码必须保持兼容的存储布局
- 如果升级不遵循结构，存在存储损坏风险

### 建议：

1. 考虑添加：
- 升级时间锁定机制
- 升级版本控制
- 升级过程中的存储布局验证
- 多重签名或DAO治理升级

2. 实现：
- 升级事件/通知
- 紧急暂停功能
- 升级提案/审查期

3. 文档：
- 升级的存储布局要求
- 管理员责任和限制
- 升级程序和安全检查

该合约具有重要的升级能力，但缺乏复杂的安全机制。管理员对合约有很大的修改权限，如果管理员密钥被泄露，这可能构成安全风险。

---

# Non Standard ERC20

我将分析这个合约的 ERC-20 合规性，但首先需要注意的是，这实际上是一个 TON (The Open Network) Jetton 合约，而不是以太坊 ERC-20 合约。Jetton 是 TON 对应的 ERC-20 代币，但它们遵循不同的标准和模式。让我们分析主要差异：

### 1. 标准接口合规性

该合约遵循 TEP-74 (TON Enhancement Proposal) Jetton 标准，与 ERC-20 有根本性的不同：

#### 主要差异：

1. **架构**:
```func
() recv_internal(int msg_value, cell in_msg_full, slice in_msg_body)
```

- 使用 TON 的异步消息传递架构，而不是以太坊的同步函数调用
- 操作通过操作码处理（如 `op::mint`、`op::burn_notification`），而不是直接的函数调用

2. **状态管理**:
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

- 使用 TON 的基于单元格的存储，而不是以太坊的键值存储
- 实现双合约系统：Minter 和 Wallet 合约（ERC-20 使用单一合约）

### 2. 函数行为分析

#### 非标准特性：

1. **钱包代码存储**:
```func
cell jetton_wallet_code    // 存储单个钱包合约的代码
```

- 每个用户的代币由独立的钱包合约管理
- 在 ERC-20 中没有直接对应项

2. **管理控制**:
```func
if (op == op::change_admin) {
    throw_unless(error::not_owner, equal_slices_bits(sender_address, admin_address));
    next_admin_address = in_msg_body~load_msg_addr();
```

- 实现管理员转移功能
- 包含 `drop_admin` 操作用于放弃所有权

### 3. 代币属性

1. **元数据处理**:
```func
cell build_content_cell(slice metadata_uri) inline {
    cell content_dict = new_dict();
    content_dict~set_token_snake_metadata_entry("uri"H, metadata_uri);
    return create_token_onchain_metadata(content_dict);
}
```

- 使用 TON 特定的元数据格式
- 在合约存储中存储元数据 URI

2. **默克尔根集成**:
```func
global int merkle_root;
```

- 实现代币操作的默克尔树验证
- 在标准 ERC-20 中不存在

### 4. 自定义特性

1. **Gas 管理**:
```func
raw_reserve(ONE_TON, RESERVE_REGULAR); // 为存储费用预留
```

- 实现 TON 特定的 gas 处理
- 管理消息转发费用

2. **工作链验证**:
```func
check_same_workchain(to_address);
```

- 实现跨工作链转账限制
- 在 ERC-20 中没有对应项

### 集成/兼容性问题

1. **DApp 集成**:
- 为 ERC-20 代币构建的 DApp 无法直接与此合约交互
- 需要 TON 特定的集成方法
- 消息传递模型与以太坊的直接调用模型不同

2. **钱包兼容性**:
- 与标准 ERC-20 钱包不兼容
- 需要 TON 特定的钱包实现

3. **安全模型**:
- 使用 TON 的安全模式（消息退回、gas 管理）
- 与 ERC-20 的错误处理方式不同

### 集成建议

1. 与现有系统集成时：
- 构建 ERC-20 兼容性的适配层
- 实现消息传递转换层
- 考虑跨链桥需求

2. 前端集成：
- 使用 TON 特定的库
- 实现适当的消息处理
- 考虑异步操作模型

这个合约对 TON 来说实现得很好，但不应被视为 ERC-20 代币。它是为 TON 的独特架构和功能设计的根本不同的代币标准。

---

