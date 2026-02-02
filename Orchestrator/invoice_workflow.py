import json
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from DocumentExtractAgent.invoice_extraction_agent import process_invoice
from DuplicateDetectionAgent.duplicate_detection_agent import DuplicateDetectionAgent
from ValidationAgent.validation_agent import validate_invoice_from_json
from AuthorizationAgent.authorization_agent import authorize_invoice

# 🔹 NEW IMPORT
from CommunicationAgent.communication_node import communicate_invoice_status


# -------------------- STATE --------------------
class InvoiceState(TypedDict):
    file_path: str
    extracted_invoice: dict
    duplicate_result: Optional[dict]
    validation_result: Optional[dict]
    authorization_result: Optional[dict]
    communication_result: Optional[dict]   # ✅ NEW


# -------------------- NODES --------------------
def document_extraction_node(state: InvoiceState):
    if "extracted_invoice" in state:
        return {"extracted_invoice": state["extracted_invoice"]}

    extracted = process_invoice(state["file_path"])

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

    vendor_gst = invoice.get("gst_number", "").strip()
    total_amount = float(invoice.get("total_amount", 0))

    if not vendor_gst:
        return {
            "validation_result": {
                "validation_status": "GST_NOT_PROVIDED",
                "message": "GST number not present. Validation skipped.",
                "confidence_score": 40
            }
        }

    invoice["gst_rate"] = invoice.get("gst_rate", 18)
    invoice["interstate"] = invoice.get("interstate", True)
    invoice["amount_without_gst"] = round(
        total_amount / (1 + invoice["gst_rate"] / 100), 2
    )

    result = validate_invoice_from_json(invoice)
    return {"validation_result": result}


def authorization_node(state: InvoiceState):
    invoice = state["extracted_invoice"]

    # 🔒 SAFETY CHECK: vendor email must exist
    vendor_email = invoice.get("vendor_email", "").strip()

    if not vendor_email:
        return {
            "authorization_result": {
                "status": "SKIPPED",
                "reason": "Vendor email missing. Authorization skipped."
            },
            "communication_result": None
        }

    # ✅ Call authorization agent (already creates payload)
    auth_result = authorize_invoice(invoice)

    return {
        "authorization_result": {
            "status": auth_result["status"],
            "reason": auth_result["reason"]
        },
        # 🔥 PASS COMMUNICATION PAYLOAD TO GRAPH/UI
        "communication_result": auth_result.get("communication_result")
    }






# 🔹 NEW COMMUNICATION NODE
def communication_node(state: InvoiceState):
    result = communicate_invoice_status(
        state["extracted_invoice"],
        state["authorization_result"]
    )
    return {"communication_result": result}


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
graph.add_node("authorize", authorization_node)
graph.add_node("communicate", communication_node)   # ✅ NEW

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

graph.add_edge("validate", "authorize")
graph.add_edge("authorize", "communicate")   # ✅ NEW
graph.add_edge("communicate", END)            # ✅ NEW

invoice_workflow = graph.compile()
