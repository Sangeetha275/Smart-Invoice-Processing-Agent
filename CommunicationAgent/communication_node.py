from CommunicationAgent.email_generator import generate_email
from CommunicationAgent.email_sender import send_email


def communicate_invoice_status(invoice, authorization_result):
    """
    Sends email to vendor based on final invoice status
    """

    status = authorization_result.get("status")
    reason = authorization_result.get("reason")

    subject, body = generate_email(
        vendor_name=invoice["vendor_name"],
        invoice_number=invoice["invoice_number"],
        invoice_date=invoice.get("invoice_date", ""),
        status=status,
        reason=reason
    )

    try:
        result = send_email(
            to_email=invoice["vendor_email"],
            subject=subject,
            body=body
        )

        print("📧 EMAIL SENT SUCCESSFULLY")
        print(result)

        return {
            "email_status": "SENT",
            "email_details": result
        }

    except Exception as e:
        print("❌ EMAIL FAILED")
        print(str(e))

        return {
            "email_status": "FAILED",
            "error": str(e)
        }
