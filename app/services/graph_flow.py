import operator
from typing import Annotated, TypedDict, List
from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, START, END
from app import schemas

# 1. State Definition
class AgentState(TypedDict):
    all_pages_text: List[str]
    classification: dict
    # This reducer ensures parallel agents merge their dicts rather than overwriting
    extracted_results: Annotated[dict, operator.add]

# 2. Specialist Agent Nodes
def segregator_node(state: AgentState):
    llm = ChatBedrock(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0")
    # Send page previews to the segregator to map indices to types
    previews = "\n".join([f"Page {i}: {t[:500]}" for i, t in enumerate(state['all_pages_text'])])
    
    structured_llm = llm.with_structured_output(schemas.DocClassification)
    mapping = structured_llm.invoke(f"Classify these medical claim pages: {previews}")
    return {"classification": mapping.dict()}

def id_agent(state: AgentState):
    indices = state["classification"].get("id_pages", [])
    if not indices: return {"extracted_results": {}}
    
    text = " ".join([state["all_pages_text"][i] for i in indices])
    llm = ChatBedrock(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0")
    data = llm.with_structured_output(schemas.IDSchema).invoke(text)
    return {"extracted_results": {"patient_id": data.dict()}}

def bill_agent(state: AgentState):
    indices = state["classification"].get("bill_pages", [])
    if not indices: return {"extracted_results": {}}
    
    text = " ".join([state["all_pages_text"][i] for i in indices])
    llm = ChatBedrock(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0")
    data = llm.with_structured_output(schemas.ItemizedBillSchema).invoke(text)
    return {"extracted_results": {"billing": data.dict()}}

def discharge_agent(state: AgentState):
    indices = state["classification"].get("discharge_pages", [])
    if not indices: return {"extracted_results": {}}
    
    text = " ".join([state["all_pages_text"][i] for i in indices])
    llm = ChatBedrock(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0")
    data = llm.with_structured_output(schemas.DischargeSchema).invoke(text)
    return {"extracted_results": {"medical_summary": data.dict()}}

# 3. Parallel Routing Logic
def route_logic(state: AgentState):
    """Determines which agents to trigger based on classification."""
    targets = []
    classif = state["classification"]
    
    if classif.get("id_pages"): targets.append("id_agent")
    if classif.get("bill_pages"): targets.append("bill_agent")
    if classif.get("discharge_pages"): targets.append("discharge_agent")
    
    # If no specific pages identified, go to END; otherwise run list in parallel
    return targets if targets else END

# 4. Graph Construction
workflow = StateGraph(AgentState)

# Add all specialist nodes
workflow.add_node("segregator", segregator_node)
workflow.add_node("id_agent", id_agent)
workflow.add_node("bill_agent", bill_agent)
workflow.add_node("discharge_agent", discharge_agent)

# Define connections
workflow.add_edge(START, "segregator")

# Fan-out: The router returns a list of nodes to run at the same time
workflow.add_conditional_edges("segregator", route_logic)

# Fan-in: All parallel agents must finish before going to END
workflow.add_edge("id_agent", END)
workflow.add_edge("bill_agent", END)
workflow.add_edge("discharge_agent", END)

app_graph = workflow.compile()