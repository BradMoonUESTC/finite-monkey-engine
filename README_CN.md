# Finite Monkey Engine v3.0

面向区块链代码审计的自动化扫描流水线：**Planning → Reasoning → Validation**（三段均可由 Codex CLI 驱动），结果落库到 PostgreSQL，并导出报告。

## v3.0 更新要点（简洁版）

- **Planning**：不再依赖 RAG / chunks / call graph / call tree。只保留 tree-sitter 的函数解析结果，并通过 Codex 抽取业务流（Gi/Fi）。最终落库任务为 **Fi × checklist(rule_key)**。
- **Reasoning**：扫描阶段改为用 **Codex CLI** 执行（把 `business_flow_code + prompt` 输入进去），输出保持原有 **多漏洞 JSON**，并沿用原逻辑拆分写入 `project_finding`。
- **Validation**：对 `project_finding` 进行 Codex 确认（误报/真实漏洞/成本/影响等），写回 `validation_status` 与 `validation_record`。
- **工作目录约束**：Codex 执行严格 `--cd <project_root>`，其中 `project_root` 必须由 `src/dataset/agent-v1-c4/datasets.json[project_id].path` 决定（位于 `src/dataset/agent-v1-c4` 下）。
- **方案文档**：已整理到 `docs/`（planning/coverage/validation/reasoning 的设计说明）。

## 🚀 v2.0 版本升级亮点

**Finite Monkey Engine v2.0** 带来了重大架构升级和功能增强：

### 🔥 核心升级
- **🎯 精准语言支持**：使用tree-sitter整个函数解析和上下文系统，专注4种核心语言（Solidity/Rust/C++/Move），提供最优分析体验
- **🧠 RAG架构优化**：全新LanceDB合并式2表架构，查询效率提升300%
- **📊 智能上下文理解**：多维度embedding技术，代码理解能力显著增强
- **⚡ 性能优化**：统一存储策略，减少50%内存占用，提升并发处理能力
- **🔍 深度业务分析**：增强的业务流可视化和跨合约依赖分析

## 🎯 项目简介

Finite Monkey Engine 是一个先进的AI驱动代码安全分析平台，**专注于区块链和系统级代码安全审计**。通过集成多种AI模型和先进的静态分析技术，为核心编程语言项目提供全面、智能的安全审计解决方案。

### 🌍 多语言支持

平台基于Tree-sitter解析引擎和函数级分析架构，**v2.0版本专注于4种核心语言**，提供最优的分析体验：

**✅ 当前全面支持的语言:**
- **Solidity** (.sol) - 以太坊智能合约，完整Tree-sitter支持
- **Rust** (.rs) - Solana生态，Substrate，系统级编程
- **C/C++** (.c/.cpp/.cxx/.cc/.C/.h/.hpp/.hxx) - 区块链底层、节点客户端
- **Move** (.move) - Aptos, Sui区块链语言

**🔄 计划支持的语言（后续版本）:**
- ~~**Cairo** (.cairo) - StarkNet智能合约语言~~
- ~~**Tact** (.tact) - TON区块链智能合约~~
- ~~**FunC** (.fc/.func) - TON区块链原生语言~~
- ~~**FA** (.fr) - 函数式智能合约语言~~
- ~~**Python** (.py) - Web3、DeFi后端项目~~
- ~~**JavaScript/TypeScript** (.js/.ts) - Web3前端、Node.js项目~~
- ~~**Go** (.go) - 区块链基础设施、TEE项目~~
- ~~**Java** (.java) - 企业级区块链应用~~

> 💡 **v2.0设计理念**: 专注核心语言，提供深度优化的分析能力。基于函数粒度的代码分析架构，理论上可扩展到任何编程语言，后续版本将逐步支持更多语言。

### 💎 v2.0核心优势
- 🧠 **多AI模型支持**: 集成Claude-4 Sonnet、GPT-4、DeepSeek等主流AI模型
- 🚀 **RAG架构升级**: 全新LanceDB合并式2表架构，查询效率提升300%
- 📊 **业务流可视化**: 自动生成Mermaid业务流程图，支持跨合约依赖分析
- 🔍 **深度安全分析**: 专注4种核心语言，提供最优分析精度
- ⚡ **高效并发处理**: 优化内存管理，支持大规模项目并行分析
- 🎯 **智能上下文理解**: 多维度embedding技术，代码理解能力显著增强
- 🌐 **精简高效架构**: 专注核心语言，减少50%维护复杂度

## 🚀 v2.0主要特性

### 🧠 增强AI驱动分析
- **多模型协同**: Claude-4 Sonnet、GPT-4等AI模型智能协作
- **RAG增强理解**: 基于LanceDB的多维度上下文感知技术
- **业务逻辑深度分析**: 深度理解DeFi协议、治理机制和代币经济学
- **智能漏洞发现**: AI辅助的复杂漏洞模式识别

### 📊 升级版业务流可视化
- **智能图表生成**: 自动分析代码生成Mermaid业务流程图
- **多层次分析展示**: 支持项目级、文件夹级、函数级可视化
- **跨合约依赖跟踪**: 清晰展示复杂的合约交互关系
- **实时交互式图表**: 动态展示代码结构和调用链

### 🔍 全面安全检测体系
- **精准漏洞检测**: 专注核心语言，提供更精准的漏洞识别
- **跨合约深度分析**: 多合约交互分析和复杂依赖关系跟踪
- **业务场景审查**: 针对不同DeFi场景的专业安全分析
- **智能误报过滤**: AI辅助减少误报，提升分析准确性

### ⚡ v2.0架构优化
- **LanceDB 2表架构**: 统一存储策略，查询效率提升300%
- **多维度Embedding**: 内容、名称、自然语言三重embedding技术
- **内存优化管理**: 减少50%内存占用，支持更大规模项目
- **并发处理升级**: 优化线程管理，提升分析速度

## 📁 项目架构

```
finite-monkey-engine/
├── src/
│   ├── main.py                 # 主入口文件
│   ├── planning/               # 智能任务规划模块
│   ├── validating/             # 漏洞检测验证模块
│   ├── context/                # 上下文管理和RAG处理
│   ├── reasoning/              # 推理分析模块
│   ├── dao/                    # 数据访问层
│   ├── library/                # 解析库和工具
│   ├── openai_api/            # AI API集成
│   └── prompt_factory/         # 提示工程管理
├── knowledges/                 # 领域知识库
├── docker-compose.yml          # Docker部署配置
└── requirements.txt            # 依赖包列表
```

## ⚙️ 环境配置

### 快速配置

1. **复制环境变量模板**：
   ```bash
   cp env.example .env
   ```

2. **编辑 `.env` 文件**，配置你的API密钥和首选项

### 核心环境变量

```bash
# 数据库配置（必需）
DATABASE_URL=postgresql://postgres:1234@127.0.0.1:5432/postgres

# Codex（v3.0 reasoning/planning/validation 使用，必需）
CODEX_MODEL=gpt-5.2
CODEX_SANDBOX=read-only
CODEX_ASK_FOR_APPROVAL=never
CODEX_TIMEOUT_SEC=1800

# 兼容旧模型配置（仍可能用于某些辅助流程）
OPENAI_API_BASE="api.openai-proxy.org"  # LLM代理平台
OPENAI_API_KEY="sk-xxxxxx"  # API密钥

# 扫描模式配置
SCAN_MODE=COMMON_PROJECT_FINE_GRAINED   # 推荐模式：通用项目CHECKLIST逐个提问
# 可选模式：PURE_SCAN（纯扫描）
SCAN_MODE_AVA=False                     # 扫描模式高级功能
COMPLEXITY_ANALYSIS_ENABLED=True        # 启用复杂度分析

# 性能调优
MAX_THREADS_OF_SCAN=10                  # 扫描阶段最大线程数
MAX_THREADS_OF_CONFIRMATION=50          # 确认阶段最大线程数
BUSINESS_FLOW_COUNT=4                   # 业务流程重复数量（触发幻觉的数量）

# 高级功能配置
IGNORE_FOLDERS=node_modules,build,dist,test,tests,.git  # 忽略的文件夹

# 检查清单配置
CHECKLIST_PATH=src/knowledges/checklist.xlsx  # 检查清单文件路径
CHECKLIST_SHEET=Sheet1                  # 检查清单工作表名称

# 运行控制（v3.0 常用）
CMD=detect_vul                 # detect_vul / planning_only
STOP_AFTER_PLANNING=false      # true 时：main.py 正常流程跑到 planning 后在 reasoning 前停止
```

> 📝 **完整配置**: 查看 `env.example` 文件了解所有可配置选项和详细说明

### AI模型配置详情

基于 `src/openai_api/model_config.json` 的实际配置：

**重要警告** 必须根据你的LLM平台设置正确的模型名称！
**重要警告** 必须根据你的LLM平台设置正确的模型名称！
**重要警告** 例如在openrouter中，sonnet 4需要设置为anthropic/sonnet-4

```json
{
  "openai_general": "gpt-4.1",
  "code_assumptions_analysis": "claude-sonnet-4-20250514",
  "vulnerability_detection": "claude-sonnet-4-20250514",
  "initial_vulnerability_validation": "deepseek-reasoner",
  "vulnerability_findings_json_extraction": "gpt-4o-mini",
  "additional_context_determination": "deepseek-reasoner",
  "comprehensive_vulnerability_analysis": "deepseek-reasoner",
  "final_vulnerability_extraction": "gpt-4o-mini",
  "structured_json_extraction": "gpt-4.1",
  "embedding_model": "text-embedding-3-large"
}
```

### 推荐配置方案

#### 🚀 快速开始配置（小项目 < 50个文件）
```bash
SCAN_MODE=PURE_SCAN
COMPLEXITY_ANALYSIS_ENABLED=False
MAX_THREADS_OF_SCAN=3
BUSINESS_FLOW_COUNT=2
```

#### 🏢 企业级配置（大项目 > 100个文件）
```bash
SCAN_MODE=COMMON_PROJECT_FINE_GRAINED
COMPLEXITY_ANALYSIS_ENABLED=True
MAX_THREADS_OF_SCAN=8
MAX_THREADS_OF_CONFIRMATION=30
BUSINESS_FLOW_COUNT=4
```

#### 💰 成本优化配置
```bash
SCAN_MODE=PURE_SCAN
BUSINESS_FLOW_COUNT=1
MAX_THREADS_OF_SCAN=3
MAX_THREADS_OF_CONFIRMATION=10
COMPLEXITY_ANALYSIS_ENABLED=False
```

## 🚀 快速开始

### 环境要求
- **Python 3.10+**
- **PostgreSQL 13+**（必需，用于存储分析结果）
- **AI API密钥**（支持OpenAI、Claude、DeepSeek等多种模型）

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/your-org/finite-monkey-engine.git
cd finite-monkey-engine

# 2. 安装Python依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp env.example .env
# 编辑 .env 文件，填入你的API密钥和数据库配置

# 4. 初始化数据库
psql -U postgres -d postgres -f project_task.sql

# 5. 配置项目数据集
# 编辑 src/dataset/agent-v1-c4/datasets.json 添加你的项目配置

# 6. 运行分析
python src/main.py
```

## 📊 使用指南

### 数据库初始化

使用提供的SQL文件初始化PostgreSQL数据库：

```bash
# 连接到PostgreSQL数据库
psql -U postgres -d postgres

# 执行SQL文件创建表结构
\i project_task.sql

# 或者直接使用命令行
psql -U postgres -d postgres -f project_task.sql
```

### 项目配置

在 `src/dataset/agent-v1-c4/datasets.json` 中配置你的项目：

```json
{
  "your_project_id": {
    "path": "your_project_folder_name",
    "files": [], //无需设置，未来版本将禁用
    "functions": [], //无需设置，未来版本将禁用
    "exclude_in_planning": "false", //无需设置为true，未来版本将禁用
    "exclude_directory": [] //无需设置，未来版本将禁用
  }
}
```

### 运行分析

1. **修改项目ID**: 在 `src/main.py` 中设置你的项目ID
```python
project_id = 'your_project_id'
```

2. **执行分析**:
```bash
python src/main.py
```

3. **查看结果**: 
   - 数据库中的详细分析记录
   - `output.xlsx` 报告文件
   - Mermaid业务流程图（如果启用）

### 输出文件说明

- **Excel报告**: 详细的漏洞发现和分析结果
- **Mermaid图表**: `src/codebaseQA/mermaid_output/` 目录下的业务流程图
- **数据库记录**: 完整的分析过程和结果存储

## 🎯 最佳实践建议

### 性能优化
1. **大项目处理**: 设置 `HUGE_PROJECT=True` 和适当的线程数
2. **API成本控制**: 使用 `gpt-4-mini` 进行初步分析
3. **内存管理**: 大项目建议设置 `SWITCH_FILE_CODE=False`

### 准确性提升
1. **业务流分析**: 保持 `SWITCH_BUSINESS_CODE=True` 获得更好的上下文理解
2. **多轮确认**: 设置适当的 `MAX_CONFIRMATION_ROUNDS`
3. **专业模型**: 重要项目使用 Claude-4 Sonnet 或 GPT-4

### 安全建议
1. **API密钥安全**: 使用环境变量，不要硬编码
2. **网络访问**: 生产环境建议关闭 `ENABLE_INTERNET_SEARCH`
3. **数据备份**: 定期备份分析数据库

## 🔧 故障排除

### 常见问题

**Q: API调用失败**
```bash
# 检查API密钥和网络连接
export OPENAI_API_KEY=your_key
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

**Q: 内存不足**
```bash
# 调整配置减少内存使用
HUGE_PROJECT=True
SWITCH_FILE_CODE=False
MAX_THREADS_OF_SCAN=3
```

**Q: 分析速度慢**
```bash
# 增加并发线程（注意API限制）
MAX_THREADS_OF_SCAN=8
MAX_THREADS_OF_CONFIRMATION=5
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/新功能`)
3. 提交更改 (`git commit -m '添加新功能'`)
4. 推送到分支 (`git push origin feature/新功能`)
5. 创建 Pull Request

## 📄 许可证

Apache License 2.0 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系我们

- **邮箱**: nerbonic@gmail.com
- **推特**: [@xy9301](https://x.com/xy9301)
- **交流群**: [https://t.me/+4-s4jDfy-ig1M2Y1](https://t.me/+4-s4jDfy-ig1M2Y1)

## 🚀 v2.0版本重大架构升级

**Finite Monkey Engine v2.0** 带来了全栈式架构重构，四大核心系统全面升级：

### 🌳 1. Tree-sitter底层解析引擎重构
**完全替代传统解析方案，代码分析精度提升300%**

- **🔧 全新解析架构**：基于Tree-sitter的统一解析引擎
  - 支持Solidity、Rust、C++、Move四种核心语言
  - 语法树精确解析，消除传统正则表达式的不准确性
  - 函数级粒度分析，支持复杂嵌套结构

- **📊 Call Tree & Call Graph革新**：
  - **准确率提升90%**：基于AST的精确函数调用关系分析
  - **深度追踪**：支持跨文件、跨合约的调用链分析  
  - **实时构建**：动态生成调用图，支持增量更新
  - **可视化增强**：自动生成Mermaid调用关系图

### 📋 2. 智能Planning复杂度评估系统
**避免无效扫描，降低分析成本60%**

- **🎯 多维度复杂度评估**：
  - **代码复杂度**：基于圈复杂度、函数深度的智能评估
  - **风险优先级**：根据函数敏感性、外部调用频率排序
  - **资源消耗预估**：预测分析所需时间和AI Token消耗
  - **批次优化**：智能分组，提升并行处理效率

- **💡 成本优化策略**：
  - **过滤无效任务**：自动跳过简单getter/setter函数
  - **智能采样**：对相似功能函数进行代表性分析
  - **增量分析**：仅分析变更部分，避免重复扫描
  - **优先级队列**：高风险函数优先处理

---

## 📊 v2.0性能提升总览

| 核心指标 | v1.0 | v2.0 | 提升幅度 |
|---------|------|------|---------|
| 代码解析准确率 | 75% | 95% | **+27%** |
| Call Graph准确性 | 60% | 94% | **+57%** |
| 无效扫描过滤率 | 20% | 80% | **+300%** |
| RAG检索相关性 | 65% | 92% | **+42%** |
| 漏洞检测准确率 | 72% | 91% | **+26%** |
| 分析成本(Token) | 100% | 40% | **-60%** |

## 🔄 v2.0迁移指南

### 兼容性说明
- ✅ **完全向后兼容**：现有配置和数据无需修改
- ✅ **平滑升级**：支持增量迁移，零停机部署
- ✅ **智能识别**：自动识别项目类型，应用最优分析策略

### 推荐配置优化
```yaml
# v2.0推荐配置
tree_sitter:
  enabled: true
  languages: ["solidity", "rust", "cpp", "move"]
  
planning:
  complexity_threshold: "medium"
  cost_optimization: true
  parallel_workers: 4

rag:
  query_dimensions: ["function", "call_relation", "code_block", "architecture"]
  context_accumulation: true
  
validation:
  max_iterations: 10
  language_mode: "auto"  # auto/zh/en
```

---

**🎉 Finite Monkey Engine v2.0 - 让代码安全分析更智能、更专业、更高效！**