# FiniteMonkey

<p align="center">
  <img src="image.jpeg" width="500">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg">
  <img src="https://img.shields.io/badge/version-1.0-green.svg">
  <img src="https://img.shields.io/badge/bounties-$60,000+-yellow.svg">
</p>

FiniteMonkey is an intelligent vulnerability mining engine based on large language models, requiring no pre-trained knowledge base or fine-tuning. Its core feature is using task-driven and prompt engineering approaches to guide models in vulnerability analysis through carefully designed prompts.

## 🌟 Core Concepts

- **Task-driven rather than problem-driven**
- **Prompt-driven rather than code-driven**
- **Focus on prompt design rather than model design**
- **Leverage "deception" and hallucination as key mechanisms**

## 🏆 Achievements

As of May 2024, this tool has helped discover over $60,000 worth of bug bounties.

## 📋 Prerequisites

### Python Environment
- Python 3.11 (recommended, as Python 3.12 has package compatibility issues)
- Use conda for environment management:
```bash
conda create -n py311 python=3.11
conda activate py311
```

### PostgreSQL Database
1. Install PostgreSQL:
```bash
# Install and start PostgreSQL (macOS)
brew install postgresql
brew services start postgresql
initdb /usr/local/var/postgres -E utf8

# Connect to database
psql postgres

# Check databases
\l

# Set password for database user
\password [your_username]

# Exit connection
exit
```

2. Install pgAdmin from [https://www.pgadmin.org/download/](https://www.pgadmin.org/download/) for database management
   - Host: 127.0.0.1
   - Port: 5432
   - Username: your database owner username
   - Password: as set above

### AI API Configuration
Purchase AI API access from [https://platform.closeai-asia.com/account/billing](https://platform.closeai-asia.com/account/billing)
Get your API key from Developer Mode -> Key Management

## 🛠️ Installation & Setup

### 1. Get the Code
```bash
git clone https://github.com/BradMoonUESTC/finite-monkey-engine.git
cd finite-monkey-engine
pip install -r requirements.txt
```

### 2. Database Setup
Execute the SQL file `src/db.sql` in pgAdmin to create the required tables. If you encounter ownership errors, modify `OWNER TO "postgres"` to use your actual database username.

### 3. Sample Data (Optional)
Download the `concise_project_code` directory from [Google Drive](https://drive.google.com/drive/folders/1M3Fn3FOBX2EFAvBkXG4GVOT0ZlCmJgjQ) and place the files in `finite-monkey-engine/src/dataset/agent-v1-c4/`

### 4. Environment Configuration
Create `src/.env` file with the following configuration:

```env
# Database connection URL using PostgreSQL
DATABASE_URL=postgresql://postgres:1234@127.0.0.1:5432/postgres

# Base URL for all LLM requests (LLM proxy platform) used for API requests
OPENAI_API_BASE="localhost:3010"

# Model name used for text embeddings
EMBEDDING_MODEL="text-embedding-3-large"
EMBEDDING_API_BASE="api.openai-proxy.org"
EMBEDDING_API_KEY="your-embedding-api-key"

# JSON model configuration
JSON_MODEL_API_BASE="api.openai-proxy.org"
JSON_MODEL_API_KEY="your-json-model-api-key"

# API key for LLM proxy platform
OPENAI_API_KEY="your-openai-api-key"

# Confirmation model selection, using DeepSeek model
CONFIRMATION_MODEL="DEEPSEEK"

# OpenAI model selection, using GPT-4.1
OPENAI_MODEL="gpt-4.1"

# Claude model selection, using Claude 4 Sonnet version
CLAUDE_MODEL=claude-4-sonnet

# Vulnerability scanning model
VUL_MODEL=claude-4-sonnet

# Scan mode settings
# Available options: 
# - SPECIFIC_PROJECT (specific project checklist)
# - OPTIMIZE (code suggestion mode)
# - COMMON_PROJECT (common project checklist single query)
# - PURE_SCAN (pure scanning)
# - CHECKLIST (automatic checklist generation)
# - CHECKLIST_PIPELINE (checklist generation + pipeline)
# - COMMON_PROJECT_FINE_GRAINED (common project checklist individual queries, 10x cost increase)
# - JUST_ASK (simple audit agent prompt with Gemini model, similar planning as COMMON_PROJECT_FINE_GRAINED)
SCAN_MODE=PURE_SCAN

# API service provider selection
# Available options: OPENAI / AZURE / CLAUDE / DEEPSEEK
AZURE_OR_OPENAI="OPENAI"

# Maximum number of threads for confirmation phase
MAX_THREADS_OF_CONFIRMATION=50

# Maximum number of threads for scanning phase
MAX_THREADS_OF_SCAN=10

# Business flow repeat count (number of hallucinations triggered, higher number means more hallucinations, more output, longer time)
BUSINESS_FLOW_COUNT=1

# Whether to enable function code scanning
SWITCH_FUNCTION_CODE=False

# Whether to enable business code scanning
SWITCH_BUSINESS_CODE=True

# Maximum number of confirmation rounds
MAX_CONFIRMATION_ROUNDS=2

# Number of requests per confirmation round
REQUESTS_PER_CONFIRMATION_ROUND=3

# JSON model ID
JSON_MODEL_ID="gpt-4.1"

# Whether to enable internet search
ENABLE_INTERNET_SEARCH=False

# Set the number of iterations for project types of a specific language generation
PROJECT_TYPE_ITERATION_ROUNDS=3

# Set the number of iterations for checklist generation
CHECKLIST_ITERATION_ROUNDS=3

# Whether to enable dialogue mode
ENABLE_DIALOGUE_MODE=False

# Whether to enable cross-contract scanning
CROSS_CONTRACT_SCAN=True

# Length threshold for planning phase
THRESHOLD_OF_PLANNING=50
```

### 5. Project Configuration
Edit `src/dataset/agent-v1-c4/datasets.json` to configure your projects:

```json
{
    "YourProjectName": {
        "path": "relative_path_to_your_project",
        "files": [],
        "functions": [],
        "exclude_in_planning": "true",
        "exclude_directory": ["access", "errors", "events", "lib", "storage"]
    }
}
```

**Planning Optimization Notes:**
- `THRESHOLD_OF_PLANNING`: Functions shorter than this value will be treated as context rather than main scanning targets
- `exclude_in_planning` and `exclude_directory`: Contracts in specified directories will be treated as context only

## 🚀 Usage

### Running with Sample Data
1. Choose a project name from `src/dataset/agent-v1-c4/datasets.json`
2. Edit `src/main.py` line 146 to set the `project_id`:
```python
if __name__ == '__main__':
    switch_production_or_test = 'test'  # prod / test
    if switch_production_or_test == 'test':
        start_time = time.time()
        db_url_from = os.environ.get("DATABASE_URL")
        engine = create_engine(db_url_from)
        
        dataset_base = "./src/dataset/agent-v1-c4"
        projects = load_dataset(dataset_base)
        project_id = 'YourProjectName'  # Set your project name here
        project_path = ''
        project = Project(project_id, projects[project_id])
```
3. Run the scanner:
```bash
python src/main.py
```

### Running with New Projects
1. Place your code in `finite-monkey-engine/src/dataset/agent-v1-c4/` (recommended to include only files that need auditing)
2. Add project configuration to `src/dataset/agent-v1-c4/datasets.json`
3. Update `project_id` in `src/main.py`
4. Execute `python src/main.py`

### Analyzing Results
Check the `project_tasks_amazing_prompt` database table for scan results. Each record requires manual analysis to determine if it represents a valid vulnerability.

## 🌈 Supported Languages

- Solidity (.sol)
- Rust (.rs)
- Python (.py)
- Move (.move)
- Cairo (.cairo)
- Tact (.tact)
- Func (.fc)
- Java (.java)
- Pseudo-Solidity (.fr) - For scanning Solidity pseudocode

## 📊 Scan Results Guide

1. If interrupted due to network/API issues, resume scanning using the same project_id in main.py
2. Results include detailed annotations:
   - Focus on entries marked "yes" in result column
   - Filter "dont need In-project other contract" in category column
   - Check specific code in business_flow_code column
   - Find code location in name column

## 📝 License

Apache License 2.0

## 🤝 Contributing

Pull Requests welcome!

---

*Note: Project name inspired by [Large Language Monkeys paper](https://arxiv.org/abs/2407.21787v1)*