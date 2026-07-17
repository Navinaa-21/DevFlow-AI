import smtplib
import logging
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.server = settings.SMTP_SERVER
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL

    def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Helper to send an email using SMTP."""
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email

        try:
            # If no username is provided, we can simulate sending to console (useful for local dev without credentials)
            if not self.username:
                logger.info("--- MOCK EMAIL ---")
                logger.info(f"To: {to_email}")
                logger.info(f"Subject: {subject}")
                logger.info(f"Body:\n{body}")
                logger.info("------------------")
                return True

            with smtplib.SMTP(self.server, self.port) as server:
                # server.starttls() # Enable this if the SMTP server requires TLS
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            # Do not raise exception here, as we don't want to crash the request if email fails, 
            # though depending on business rules, we might want to raise it.
            return False

    def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        subject = "Reset your password"
        body = f"""Hello,

We received a request to reset your password.

Click the link below to reset it:
{reset_link}

This link expires in 30 minutes.

If you didn't request this, you can safely ignore this email.
"""
        return self._send_email(to_email, subject, body)

    def send_invitation_email(self, to_email: str, token: str, workspace_name: str, inviter_name: str, role: str) -> bool:
        invite_link = f"{settings.FRONTEND_URL}/invitations/{token}"
        subject = f"You're invited to join {workspace_name}"
        body = f"""Hello,

{inviter_name} has invited you to join {workspace_name} as a {role.capitalize()}.

Click the button below to accept your invitation.

This invitation expires in 7 days.

{invite_link}

If you weren't expecting this invitation, you can ignore this email.
"""
        return self._send_email(to_email, subject, body)

    def send_verification_email(self, to_email: str, verification_token: str) -> bool:
        verification_link = f"{settings.FRONTEND_URL}/verify?token={verification_token}"
        subject = "Verify your email address"
        body = f"""Hello,

Please verify your email address by clicking the link below:
{verification_link}

If you didn't create an account, you can safely ignore this email.
"""
        return self._send_email(to_email, subject, body)
