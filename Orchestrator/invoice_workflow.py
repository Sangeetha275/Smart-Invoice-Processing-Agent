from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from DocumentExtractAgent.invoice_extraction_agent import process_invoice
from DuplicateDetectionAgent.duplicate_detection_agent import DuplicateDetectionAgent


# -------------------- STATE --------------------
class InvoiceState(TypedDict):
    file_path: str
    invoice_data: dict
    duplicate_result: Optional[dict]


# -------------------- NODES --------------------

def document_extraction_node(state: InvoiceState):
    """
    Calls your existing document extraction agent
    """
    invoice_data = process_invoice(state["file_path"])
    return {"invoice_data": invoice_data}


def duplicate_detection_node(state: InvoiceState):
    """
    Calls duplicate detection agent
    """
    agent = DuplicateDetectionAgent()
    result = agent.check_duplicate(state["invoice_data"])
    return {"duplicate_result": result}


# -------------------- ROUTER --------------------

def route_after_duplicate(state: InvoiceState):
    """
    If duplicate found → stop flow (UI will handle)
    Else → continue later (validation agent)
    """
    if state["duplicate_result"]["is_duplicate"]:
        return "end"
    return "end"  # later → validation


# -------------------- BUILD GRAPH --------------------

graph = StateGraph(InvoiceState)

graph.add_node("extract", document_extraction_node)
graph.add_node("duplicate", duplicate_detection_node)

graph.set_entry_point("extract")

graph.add_edge("extract", "duplicate")

graph.add_conditional_edges(
    "duplicate",
    route_after_duplicate,
    {
        "end": END
    }
)

invoice_workflow = graph.compile()
print(invoice_workflow)
