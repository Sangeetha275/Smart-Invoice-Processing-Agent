import smtplib
import imaplib
import email
import time
import uuid
import snowflake.connector
from datetime import datetime
from email.message import EmailMessage
from email.utils import parseaddr
from bs4 import BeautifulSoup

# ================= CONFIG =================

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"

SENDER_EMAIL = "slakshmislakshmi50@gmail.com"
SENDER_PASSWORD = "ewlr mkxa xuwp ltuz"   # Gmail App Password
MANAGER_EMAIL = "surender.s@geakminds.com"

THRESHOLD = 2000   # Business rule

# ================= SNOWFLAKE CONFIG =================

SNOWFLAKE_CONFIG = {
    "user": "SUDAROLIGOPAL",
    "password": "SudaroliNageswari@2004",
    "account": "kvuunyb-hp15737",
    "warehouse": "COMPUTE_WH",
    "database": "MOCK_INVOICE_DB",
    "schema": "PUBLIC",
    "role": "ACCOUNTADMIN"
}

SNOWFLAKE_TABLE = "MOCK_INVOICE_DB.PUBLIC.INVOICE_TABLE"

# ================= UTILS =================

def parse_amount(value):
    return float(str(value).replace(",", "").replace("₹", "").strip())


def clean_email_body(raw_body: str) -> str:
    soup = BeautifulSoup(raw_body, "html.parser")
    return soup.get_text("\n").upper().strip()

# ================= SNOWFLAKE =================

def upsert_invoice_snowflake(
    invoice_number,
    vendor_name,
    vendor_email,
    amount,
    status,
    token,
    created_at,
    updated_at
):
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    cur = conn.cursor()

    cur.execute(f"""
        MERGE INTO {SNOWFLAKE_TABLE} t
        USING (
            SELECT
                %s AS INVOICE_NUMBER,
                %s AS VENDOR_NAME,
                %s AS VENDOR_EMAIL,
                %s AS AMOUNT,
                %s AS STATUS,
                %s AS APPROVAL_TOKEN,
                %s AS CREATED_AT,
                %s AS UPDATED_AT
        ) s
        ON t.INVOICE_NUMBER = s.INVOICE_NUMBER
        WHEN MATCHED THEN UPDATE SET
            STATUS = s.STATUS,
            UPDATED_AT = s.UPDATED_AT
        WHEN NOT MATCHED THEN INSERT (
            INVOICE_NUMBER,
            VENDOR_NAME,
            VENDOR_EMAIL,
            AMOUNT,
            STATUS,
            APPROVAL_TOKEN,
            CREATED_AT,
            UPDATED_AT
        ) VALUES (
            s.INVOICE_NUMBER,
            s.VENDOR_NAME,
            s.VENDOR_EMAIL,
            s.AMOUNT,
            s.STATUS,
            s.APPROVAL_TOKEN,
            s.CREATED_AT,
            s.UPDATED_AT
        )
    """, (
        invoice_number,
        vendor_name,
        vendor_email,
        amount,
        status,
        token,
        created_at,
        updated_at
    ))

    conn.commit()
    cur.close()
    conn.close()

    print(f"📊 Snowflake updated → Invoice={invoice_number}, Status={status}")

# ================= EMAIL SEND =================

def send_manager_email(invoice, token):
    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = MANAGER_EMAIL
    msg["Subject"] = f"Approval Required: Invoice {invoice['invoice_number']}"

    msg.set_content(f"""
APPROVAL REQUIRED

Invoice Number : {invoice['invoice_number']}
Vendor         : {invoice['vendor_name']}
Amount         : {invoice['total_amount']}

Reply with ONLY ONE WORD:
APPROVED
or
REJECTED

Approval Token: {token}
""")

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.set_debuglevel(1)  # DEBUG
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

    print("📧 Manager approval email SENT")

# ================= EMAIL READ =================

def check_manager_reply(token, invoice_number, wait_seconds=300):
    print(f"⏳ Waiting for manager reply → Invoice={invoice_number}")
    end_time = time.time() + wait_seconds

    while time.time() < end_time:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(SENDER_EMAIL, SENDER_PASSWORD)
            mail.select("INBOX")

            _, data = mail.search(None, "ALL")
            mail_ids = data[0].split()

            for mail_id in reversed(mail_ids[-20:]):
                _, msg_data = mail.fetch(mail_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                if parseaddr(msg.get("From"))[1].lower() != MANAGER_EMAIL.lower():
                    continue

                if invoice_number not in msg.get("Subject", ""):
                    continue

                raw_body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() in ["text/plain", "text/html"]:
                            raw_body += part.get_payload(decode=True).decode(errors="ignore")
                else:
                    raw_body = msg.get_payload(decode=True).decode(errors="ignore")

                body = clean_email_body(raw_body)
                first_line = body.splitlines()[0]

                if token not in body:
                    continue

                mail.logout()

                if first_line.startswith("APPROVED"):
                    print("✅ Manager APPROVED")
                    return "APPROVED"

                if first_line.startswith("REJECTED"):
                    print("❌ Manager REJECTED")
                    return "REJECTED"

            mail.logout()
        except Exception as e:
            print("⚠️ IMAP retry:", e)

        time.sleep(5)

    print("⌛ Manager response TIMEOUT")
    return "NO_RESPONSE"

# ================= AUTHORIZATION AGENT =================

def authorize_invoice(invoice: dict):
    amount = parse_amount(invoice["total_amount"])
    now = datetime.utcnow().isoformat()

    # ---------- AUTO APPROVAL ----------
    if amount < THRESHOLD:
        upsert_invoice_snowflake(
            invoice["invoice_number"],
            invoice["vendor_name"],
            invoice["vendor_email"],
            amount,
            "APPROVED",
            None,
            now,
            now
        )

        print("✅ Auto-approved (below threshold)")

        # 🔥 COMMUNICATION PAYLOAD
        communication_payload = {
            "invoice_number": invoice["invoice_number"],
            "vendor_name": invoice["vendor_name"],
            "vendor_email": invoice["vendor_email"],
            "status": "APPROVED",
            "timestamp": datetime.utcnow().isoformat()
        }

        return {
            "status": "APPROVED",
            "reason": "Below threshold",
            "communication_result": communication_payload   # 🔑 IMPORTANT
        }

    # ---------- MANUAL APPROVAL ----------
    token = uuid.uuid4().hex.upper()

    # 1️⃣ Save as pending
    upsert_invoice_snowflake(
        invoice["invoice_number"],
        invoice["vendor_name"],
        invoice["vendor_email"],
        amount,
        "PENDING",
        token,
        now,
        now
    )

    # 2️⃣ SEND EMAIL
    send_manager_email(invoice, token)

    # 3️⃣ WAIT FOR RESPONSE
    decision = check_manager_reply(token, invoice["invoice_number"])

    # 4️⃣ FINAL UPDATE
    upsert_invoice_snowflake(
        invoice["invoice_number"],
        invoice["vendor_name"],
        invoice["vendor_email"],
        amount,
        decision,
        token,
        now,
        datetime.utcnow().isoformat()
    )

    # 🔥 COMMUNICATION PAYLOAD
    communication_payload = {
        "invoice_number": invoice["invoice_number"],
        "vendor_name": invoice["vendor_name"],
        "vendor_email": invoice["vendor_email"],
        "status": decision,
        "timestamp": datetime.utcnow().isoformat()
    }

    return {
        "status": decision,
        "reason": "Manager decision",
        "communication_result": communication_payload   # 🔑 IMPORTANT
    }

