import asyncio
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

# --- Phase 1: Planning Phase ---
async def planning_phase(code_snippet: str) -> dict:
    planning_model = OpenAIModel(
        model_name="openai-planning-model",
        base_url="http://127.0.0.1:11434/v1"
    )
    planning_agent = Agent(planning_model, retries=3, result_type=dict)
    prompt = (
        f"Analyze the following code and extract its business flow as JSON:\n\n{code_snippet}"
    )
    planning_result = await planning_agent.run(prompt)
    print("[Planning] Result:", planning_result)
    return planning_result

# --- Phase 2: Scanning Phase with Dynamic Governor ---
# Import the dynamic governor from above
from dynamic_governor import DynamicGovernor, governed_task

async def scanning_phase(business_flow: dict) -> dict:
    scanning_model = OpenAIModel(
        model_name="openai-scanning-model",
        base_url="http://127.0.0.1:11434/v1"
    )
    scanning_agent = Agent(scanning_model, retries=3, result_type=dict)
    prompt = (
        f"Given the business flow JSON:\n{business_flow}\n"
        f"Identify potential vulnerabilities and output a JSON summary."
    )
    # Initialize dynamic governor for this phase
    governor = DynamicGovernor(initial_limit=5, window_size=10)
    # Wrap the scanning API call in a governed task:
    async def scan_call(p):
        return await scanning_agent.run(p)
    scanning_result = await governed_task(scan_call, governor, prompt)
    print("[Scanning] Result:", scanning_result)
    return scanning_result

# --- Phase 3: Confirmation Phase ---
async def confirmation_phase(scan_result: dict) -> dict:
    confirmation_model = OpenAIModel(
        model_name="openai-confirmation-model",
        base_url="http://127.0.0.1:11434/v1"
    )
    confirmation_agent = Agent(confirmation_model, retries=3, result_type=dict)
    prompt = (
        f"Review the following scan result:\n{scan_result}\n"
        f"Confirm or refute the findings and output your conclusion in JSON."
    )
    confirmation_result = await confirmation_agent.run(prompt)
    print("[Confirmation] Result:", confirmation_result)
    return confirmation_result

# Phase 4: Final Aggregation / Message Pump
async def final_phase(confirmation_data: dict, run_context):
    final_model = OpenAIModel(
        model_name="openai-final-model",
        base_url="http://127.0.0.1:11434/v1"
    )
    final_agent = Agent(final_model, retries=3, result_type=str)
    prompt = (
        f"Aggregate the following confirmation data into a final report in Markdown:\n{confirmation_data}\n "
        f"Output the final report."
    )
    async with final_agent.run_stream(prompt) as stream:
        async for message in stream.stream():
            # Inject output into the local RunContext for rendering.
            run_context.update_markdown(message)

# Main Pipeline: Chaining all phases together.
async def main_pipeline(run_context):
    # In practice, the code snippet might come from your project audit/planning module.
    code_snippet = """
    function transfer(address recipient, uint256 amount) public returns (bool) {
         // business logic here...
    }
    """
    plan_result = await planning_phase(code_snippet)
    scan_result = await scanning_phase(plan_result)
    confirmation_result = await confirmation_phase(scan_result)
    await final_phase(confirmation_result, run_context)