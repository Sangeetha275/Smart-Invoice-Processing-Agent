from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from DocumentExtractAgent.invoice_extraction_agent import process_invoice
from DuplicateDetectionAgent.duplicate_detection_agent import DuplicateDetectionAgent
from ValidationAgent.validation_agent import validate_invoice_from_json


# -------------------- STATE --------------------
class InvoiceState(TypedDict):
    file_path: str
    extracted_invoice: dict
    duplicate_result: Optional[dict]
    validation_result: Optional[dict]


# -------------------- NODES --------------------

import json

def document_extraction_node(state: InvoiceState):
    extracted = process_invoice(state["file_path"])

    # 🔑 FIX: Convert string JSON → dict
    if isinstance(extracted, str):
        extracted = json.loads(extracted)

    return {"extracted_invoice": extracted}



def duplicate_detection_node(state: InvoiceState):
    agent = DuplicateDetectionAgent()
    result = agent.check_duplicate({
        "invoice_number": state["extracted_invoice"]["invoice_number"],
        "vendor_name": state["extracted_invoice"]["vendor_name"],
        "invoice_date": state["extracted_invoice"]["invoice_date"],
        "total_amount": state["extracted_invoice"]["total_amount"]
    })
    return {"duplicate_result": result}


def validation_node(state: InvoiceState):
    invoice = state["extracted_invoice"]

    # -------------------- ENRICH REQUIRED FIELDS --------------------
    total_amount = float(invoice.get("total_amount", 0))

    # Default assumptions for POC
    gst_rate = invoice.get("gst_rate", 18)          # default 18%
    interstate = invoice.get("interstate", True)    # default interstate

    # Calculate amount_without_gst if missing
    if "amount_without_gst" not in invoice:
        invoice["amount_without_gst"] = round(
            total_amount / (1 + gst_rate / 100), 2
        )

    # Ensure required keys exist
    invoice["gst_rate"] = gst_rate
    invoice["interstate"] = interstate

    # -------------------- CALL VALIDATION AGENT --------------------
    result = validate_invoice_from_json(invoice)
    return {"validation_result": result}



# -------------------- ROUTER --------------------

def route_after_duplicate(state: InvoiceState):
    if state["duplicate_result"]["is_duplicate"]:
        return "end"
    return "validate"


# -------------------- BUILD GRAPH --------------------

graph = StateGraph(InvoiceState)

graph.add_node("extract", document_extraction_node)
graph.add_node("duplicate", duplicate_detection_node)
graph.add_node("validate", validation_node)

graph.set_entry_point("extract")

graph.add_edge("extract", "duplicate")

graph.add_conditional_edges(
    "duplicate",
    route_after_duplicate,
    {
        "end": END,
        "validate": "validate"
    }
)

graph.add_edge("validate", END)

invoice_workflow = graph.compile()
