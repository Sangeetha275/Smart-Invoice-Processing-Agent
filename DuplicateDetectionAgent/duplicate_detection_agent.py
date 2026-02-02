import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from DB.snowflake_connection import get_snowflake_connection

load_dotenv()


class DuplicateDetectionAgent:
    """
    GenAI-powered Duplicate Detection Agent
    """

    def __init__(self):
        self.conn = get_snowflake_connection()

        self.llm = ChatGroq(
            model="openai/gpt-oss-120b",
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0
        )

    # ---------- SQL CHECKS ----------

    def _exact_duplicate(self, invoice):
        query = """
            SELECT invoice_number, vendor_name, status
            FROM INVOICES
            WHERE invoice_number = %s
              AND vendor_name = %s
            LIMIT 1
        """
        cursor = self.conn.cursor()
        cursor.execute(
            query,
            (invoice["invoice_number"], invoice["vendor_name"])
        )
        row = cursor.fetchone()
        cursor.close()
        return row

    def _near_duplicate(self, invoice):
        query = """
            SELECT invoice_number, status
            FROM INVOICES
            WHERE vendor_name = %s
              AND total_amount = %s
              AND invoice_date = %s
            LIMIT 1
        """
        cursor = self.conn.cursor()
        cursor.execute(
            query,
            (
                invoice["vendor_name"],
                invoice["total_amount"],
                invoice["invoice_date"]
            )
        )
        row = cursor.fetchone()
        cursor.close()
        return row

    # ---------- GENAI REASONING ----------

    def _reason_with_llm(self, invoice, exact, near):
        prompt = f"""
You are a finance duplicate detection agent.

Invoice Input:
{json.dumps(invoice, indent=2)}

Exact Match Result:
{exact}

Near Match Result:
{near}

Rules:
- Exact match → EXACT duplicate
- Near match → NEAR duplicate
- Else → NOT duplicate

Return ONLY JSON:
{{
  "is_duplicate": true/false,
  "duplicate_type": "EXACT | NEAR | NONE",
  "confidence": 0.0,
  "message": ""
}}
"""
        response = self.llm.invoke(prompt).content.strip()
        return json.loads(response)

    # ---------- PUBLIC METHOD ----------

    def check_duplicate(self, invoice: dict):
        """
        Entry point for LangGraph
        """
        exact = self._exact_duplicate(invoice)

        if exact:
            return self._reason_with_llm(invoice, exact, None)

        near = self._near_duplicate(invoice)

        return self._reason_with_llm(invoice, None, near)
