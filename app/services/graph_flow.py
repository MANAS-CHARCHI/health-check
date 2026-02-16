import operator
from typing import Annotated, TypedDict, Union
from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, START, END
from app import schemas

# Define the shared state (The Whiteboard)
class AgentState(TypedDict):
    all_pages_text: list[str]
    classification: dict
    # Annotated with operator.add allows parallel agents to merge results
    extracted_results: Annotated[dict, operator.add]

# --- Nodes ---
def segregator_node(state: AgentState):
    llm = ChatBedrock(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0")
    # Preview only the first 500 chars per page
    previews = "\n".join([f"Page {i}: {t[:500]}" for i, t in enumerate(state['all_pages_text'])])
    
    structured_llm = llm.with_structured_output(schemas.DocClassification)
    mapping = structured_llm.invoke(f"Classify these pages: {previews}")
    return {"classification": mapping.dict()}

def bill_agent(state: AgentState):
    indices = state["classification"].get("bill_pages", [])
    text = " ".join([state["all_pages_text"][i] for i in indices])
    llm = ChatBedrock(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0")
    data = llm.with_structured_output(schemas.ItemizedBillSchema).invoke(text)
    return {"extracted_results": {"billing": data.dict()}}

# --- Graph Construction ---
def route_logic(state: AgentState):
    # This function triggers agents in parallel
    targets = []
    if state["classification"].get("bill_pages"): targets.append("bill_agent")
    # Add other agents (ID, Discharge) here similarly
    return targets if targets else END

workflow = StateGraph(AgentState)
workflow.add_node("segregator", segregator_node)
workflow.add_node("bill_agent", bill_agent)

workflow.add_edge(START, "segregator")
workflow.add_conditional_edges("segregator", route_logic)
workflow.add_edge("bill_agent", END)

app_graph = workflow.compile()