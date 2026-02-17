import operator
from typing import Annotated, TypedDict, List
from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, START, END
from app import schemas
from dotenv import load_dotenv
import os
load_dotenv()

def merge_dicts(existing: dict, new_obj: dict) -> dict:
    if isinstance(new_obj, list):
        return new_obj
    return {**existing, **new_obj}

# State
class AgentState(TypedDict):
    all_pages_text: List[str]
    classification: Annotated[dict, merge_dicts]
    extracted_results: Annotated[dict, merge_dicts]

# Segregator
def segregator_node(state: AgentState):
    
    llm = ChatBedrock(model_id=os.getenv("CLASSIFICATION_MODEL_ID"), region_name="us-east-1", model_kwargs={"inferenceConfig": {"temperature": 0}})
    # Send page to segregator to map indices to types
    previews = "\n".join([f"Page {i}: {t[:2000]}" for i, t in enumerate(state['all_pages_text'])])
    prompt = f"""
        Analyze the following medical document pages and map their PAGE INDEX to the correct category.
        Categories:
        - id_pages: Identity cards, passports, or insurance cards.
        - bill_pages: Invoices, itemized charges, or financial statements.
        - discharge_pages: Clinical summaries, doctor's notes, or discharge instructions.
        Document Pages:
    {previews}
    """
    structured_llm = llm.with_structured_output(schemas.DocClassification)
    mapping = structured_llm.invoke(prompt)
    return {"classification": mapping.model_dump()}

def id_agent(state: AgentState):
    indices = state["classification"].get("id_pages", [])
    if not indices: 
        return {}
    
    text = " ".join([state["all_pages_text"][i] for i in indices])
    llm = ChatBedrock(model_id=os.getenv("CLASSIFICATION_MODEL_ID"), region_name="us-east-1", model_kwargs={"inferenceConfig": {"temperature": 0}})
    data = llm.with_structured_output(schemas.IDSchema).invoke(text)
    return {"extracted_results": {"identification": data.model_dump()}}

def bill_agent(state: AgentState):
    indices = state["classification"].get("bill_pages", [])
    if not indices: 
        return {}
    
    text = " ".join([state["all_pages_text"][i] for i in indices])
    llm = ChatBedrock(model_id=os.getenv("CLASSIFICATION_MODEL_ID"), region_name="us-east-1", model_kwargs={"inferenceConfig": {"temperature": 0}})
    data = llm.with_structured_output(schemas.ItemizedBillSchema).invoke(text)
    return {"extracted_results": {"billing": data.model_dump()}}

def discharge_agent(state: AgentState):
    indices = state["classification"].get("discharge_pages", [])
    if not indices: 
        return {}
    
    text = " ".join([state["all_pages_text"][i] for i in indices])
    llm = ChatBedrock(model_id=os.getenv("CLASSIFICATION_MODEL_ID"), region_name="us-east-1", model_kwargs={"inferenceConfig": {"temperature": 0}})
    data = llm.with_structured_output(schemas.DischargeSchema).invoke(text)
    return {"extracted_results": {"medical_summary": data.model_dump()}}

# Parallel Routing
def route_logic(state: AgentState):
    targets = []
    classif = state["classification"]
    if classif.get("id_pages"): targets.append("id_agent")
    if classif.get("bill_pages"): targets.append("bill_agent")
    if classif.get("discharge_pages"): targets.append("discharge_agent")    
    # If no specific pages identified, go to END; otherwise run list in parallel
    return targets if targets else END

# Graph
workflow = StateGraph(AgentState)

# Add all specialist nodes
workflow.add_node("segregator", segregator_node)
workflow.add_node("id_agent", id_agent)
workflow.add_node("bill_agent", bill_agent)
workflow.add_node("discharge_agent", discharge_agent)

def join_node(state: AgentState):
    results = state.get("extracted_results", {})
    ordered_list = []
    if "identification" in results:
        ordered_list.append(("identification", results["identification"]))
    if "medical_summary" in results:
        ordered_list.append(("medical_summary", results["medical_summary"]))
    if "billing" in results:
        ordered_list.append(("billing", results["billing"]))
    return {"extracted_results": ordered_list}

workflow.add_node("join_point", join_node)

# Define connections
workflow.add_edge(START, "segregator")

# Fan-out: The router returns a list of nodes to run at the same time
workflow.add_conditional_edges("segregator", route_logic)

# Fan-in: All parallel agents must finish before going to END
workflow.add_edge("id_agent", "join_point")
workflow.add_edge("bill_agent", "join_point")
workflow.add_edge("discharge_agent", "join_point")

workflow.add_edge("join_point", END)

app_graph = workflow.compile()