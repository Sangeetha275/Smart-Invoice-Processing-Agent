import streamlit as st
import tempfile
import os
import json

from DocumentExtractAgent.invoice_extraction_agent import process_invoice
from Orchestrator.invoice_workflow import invoice_workflow

st.set_page_config(page_title="AI Invoice Processor", layout="wide")
st.title("🧾 Smart Invoice Processing")

uploaded_file = st.file_uploader(
    "Upload Invoice",
    type=["pdf", "png", "jpg", "jpeg", "txt"]
)

if uploaded_file:
    ext = os.path.splitext(uploaded_file.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(uploaded_file.getbuffer())
        file_path = tmp.name

    # ---------------- STEP 1: EXTRACTION ONLY ----------------
    with st.spinner("Extracting invoice..."):
        extracted = process_invoice(file_path)

    if isinstance(extracted, str):
        extracted = json.loads(extracted)

    # ---------------- STEP 2: ENSURE VENDOR EMAIL ----------------
    if not extracted.get("vendor_email"):
        st.warning("⚠️ Vendor email not found in invoice")

        vendor_email = st.text_input(
            "Enter Vendor Email (required to proceed)",
            placeholder="vendor@example.com"
        )

        if not vendor_email:
            st.stop()

        extracted["vendor_email"] = vendor_email

    st.success("✅ Mandatory data captured. Running full workflow.")

    # ---------------- STEP 3: RUN FULL WORKFLOW ----------------
    with st.spinner("Running duplicate, validation & authorization agents..."):
        result = invoice_workflow.invoke({
            "file_path": file_path,
            "extracted_invoice": extracted
        })

    # -------------------- TABS --------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📄 Extracted Invoice",
            "🔍 Duplicate Check",
            "✅ GST Validation",
            "🧠 Authorization",
            "📣 Communication"
        ]
    )

    # ---------------- TAB 1 ----------------
    with tab1:
        st.json(result["extracted_invoice"])

    # ---------------- TAB 2 ----------------
    with tab2:
        dup = result["duplicate_result"]
        if dup["is_duplicate"]:
            st.error(f"🚨 DUPLICATE ({dup['duplicate_type']})")
            st.write(dup["message"])
            st.write(f"Confidence: {dup['confidence']}")
        else:
            st.success("✅ No duplicate found")
            st.write(f"Confidence: {dup['confidence']}")

    # ---------------- TAB 3 ----------------
    with tab3:
        if result.get("validation_result"):
            st.json(result["validation_result"])
        else:
            st.info("Validation skipped")

    # ---------------- TAB 4 ----------------
    with tab4:
        auth = result.get("authorization_result")
        if auth:
            st.success("Authorization executed")
            st.json(auth)
        else:
            st.info("Authorization not executed")

    # ---------------- TAB 5 (NEW) ----------------
    with tab5:
        st.subheader("📣 Communication Agent Output")

        auth = result.get("authorization_result")
        comm = result.get("communication_result")

        if not auth:
            st.info("Workflow not completed yet.")
            st.stop()

        status = auth.get("status")

        # -------- FINAL DECISION --------
        st.markdown("### 🧠 Final Decision")

        if status == "APPROVED":
            st.success("✅ Invoice Approved")

        elif status == "REJECTED":
            st.error("❌ Invoice Rejected")

        elif status == "PENDING":
            st.warning("⏳ Awaiting Manager Approval")

        elif status == "NO_RESPONSE":
            st.warning("⌛ No response from manager within SLA")

        else:
            st.info(f"Status: {status}")

        st.write(f"**Reason:** {auth.get('reason')}")

        st.divider()

        
