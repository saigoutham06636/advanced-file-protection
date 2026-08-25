import resend
import threading

def _send_pin_via_resend_sync(recipient_email: str, pin: str) -> None:
    html_body = f"""
    <p>A file has been encrypted for you using the Advanced File Protection System.</p>
    <p><strong>6-Digit PIN:</strong> {pin}</p>
    <p><small>Note: Treat this PIN as sensitive information. Do not share it with unauthorized users.</small></p>
    """
    
    params = {
        "from": "onboarding@resend.dev",
        "to": [recipient_email],
        "subject": "File Encrypted: Decryption PIN",
        "html": html_body,
    }
    
    try:
        email_response = resend.Emails.send(params)
        print(f"[Resend] Successfully sent email to {recipient_email}. Response: {email_response}")
    except Exception as e:
        print(f"[Resend] Failed to send email to {recipient_email}: {e}")

def send_pin_via_resend(recipient_email: str, pin: str) -> None:
    """Send the key email in a background thread so that the GUI does not block."""
    thread = threading.Thread(
        target=_send_pin_via_resend_sync,
        args=(recipient_email, pin),
        daemon=True,
    )
    thread.start()
