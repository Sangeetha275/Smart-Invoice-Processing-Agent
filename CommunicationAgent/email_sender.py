import smtplib
from email.message import EmailMessage
from CommunicationAgent.config import (
    SMTP_SERVER,
    SMTP_PORT,
    EMAIL_ADDRESS,
    EMAIL_PASSWORD
)

 
def send_email(to_email, subject, body):
 
    if not to_email:
        raise ValueError("Recipient email is empty")
 
    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email.strip()
    msg["Subject"] = subject
    msg.set_content(body)
 
 
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
 
    return {
        "to": to_email,
        "subject": subject,
        "body": body,
        "status": "Email Sent"
    }