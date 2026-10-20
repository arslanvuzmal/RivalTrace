import logging
import re
from pathlib import Path
import resend
from app.core.config import settings

logger = logging.getLogger(__name__)

def send_briefing(client_email: str, client_name: str, html_content: str) -> bool:
    """
    Sends the weekly briefing email using the Resend API.
    
    Args:
        client_email: Recipient email address.
        client_name: Recipient name.
        html_content: The rendered HTML email body.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    if settings.demo_mode:
        # Demo mode: write the briefing where it can be opened instead of emailing it.
        out = Path("demo/out")
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"briefing-{re.sub(r'[^a-z0-9]+', '-', client_name.lower()).strip('-')}.html"
        path.write_text(html_content, encoding="utf-8")
        logger.info(f"Demo mode: briefing for {client_name} written to {path}")
        return True

    if not settings.resend_api_key:
        logger.error("RESEND_API_KEY is not configured.")
        return False
        
    resend.api_key = settings.resend_api_key
    
    try:
        logger.info(f"Sending briefing email to {client_email} ({client_name})")
        
        response = resend.Emails.send({
            "from": settings.from_email,
            "to": [client_email],
            "subject": f"Your Weekly Competitive Briefing - {client_name}",
            "html": html_content
        })
        
        logger.info(f"Email sent successfully. Resend ID: {response.get('id')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {client_email}. Error: {str(e)}")
        return False
