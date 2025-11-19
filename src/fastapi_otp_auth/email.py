from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Default configuration
from fastapi_otp_auth.config import settings

# ... (imports)

class EmailService:
    """The service class that needs configuration to initialize."""
    def __init__(self, smtp_server: str, port: int, username: str, password: str):
        # The parameters needed for configuration are accepted here
        self.smtp_server = smtp_server
        self.port = port
        self.username = username
        self.password = password
        
        # Configure the email client with proper Mailhog settings
        self.config = ConnectionConfig(
            MAIL_USERNAME=self.username,
            MAIL_PASSWORD=self.password,
            MAIL_FROM=self.username,
            MAIL_SERVER=self.smtp_server,
            MAIL_PORT=self.port,
            MAIL_FROM_NAME=settings.mail_from_name,
            MAIL_STARTTLS=False,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=False
        )

    async def send_email(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """The core function to send the email asynchronously."""
        try:
            message = MessageSchema(
                subject=subject,
                recipients=[recipient],
                body=body,
                subtype="html"
            )
            
            fm = FastMail(self.config)
            await fm.send_message(message)
            return {"status": "success", "message": "Email sent"}
        except Exception as e:
            # In a real app, you might want to log this error
            logger.error(f"Error sending email: {e}")
            return {"status": "error", "message": f"Failed to send email: {str(e)}"}

def get_email_service() -> EmailService:
    """
    A factory function that instantiates and returns a configured EmailService.
    """
    return EmailService(
        smtp_server=settings.smtp_server, 
        port=settings.smtp_port, 
        username=settings.smtp_username, 
        password=settings.smtp_password
    )
