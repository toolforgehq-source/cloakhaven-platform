"""
Email Service

Handles all transactional emails for Cloak Haven:
- Email verification
- Password reset
- Score update alerts
- Dispute notifications

Supports SMTP and SendGrid API providers.
"""

import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from app.config import settings

logger = logging.getLogger("cloakhaven.email")


class EmailServiceError(Exception):
    pass


def _send_via_smtp(to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send an email via SMTP."""
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.APP_NAME} <{settings.FROM_EMAIL}>"
    msg["To"] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_PORT != 25:
                server.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.error("SMTP send failed: %s", e)
        return False


def _send_via_sendgrid(to_email: str, subject: str, html_body: str) -> bool:
    """Send an email via SendGrid API (no extra dependencies)."""
    if not settings.SENDGRID_API_KEY:
        return False

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": settings.FROM_EMAIL, "name": settings.APP_NAME},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}],
    }

    req = Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req) as resp:
            return resp.status in (200, 201, 202)
    except URLError as e:
        logger.error("SendGrid send failed: %s", e)
        return False


def _send_email(to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send an email using the configured provider."""
    if settings.EMAIL_PROVIDER == "sendgrid" and settings.SENDGRID_API_KEY:
        return _send_via_sendgrid(to_email, subject, html_body)
    return _send_via_smtp(to_email, subject, html_body, text_body)


def send_verification_email(to_email: str, token: str, full_name: str) -> bool:
    """Send email verification link."""
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 40px;">
            <h1 style="color: #0F172A; font-size: 28px; margin: 0;">
                <span style="color: #6366F1;">CH</span> Cloak Haven
            </h1>
        </div>
        <h2 style="color: #1E293B;">Verify your email, {full_name}</h2>
        <p style="color: #475569; line-height: 1.6;">
            Welcome to Cloak Haven. Click the button below to verify your email address
            and start your reputation audit.
        </p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{verify_url}"
               style="background-color: #6366F1; color: white; padding: 14px 32px;
                      border-radius: 8px; text-decoration: none; font-weight: 600;
                      display: inline-block;">
                Verify Email
            </a>
        </div>
        <p style="color: #94A3B8; font-size: 14px;">
            If you didn't create a Cloak Haven account, you can safely ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 32px 0;" />
        <p style="color: #94A3B8; font-size: 12px; text-align: center;">
            &copy; 2026 Cloak Haven. All rights reserved.<br />
            <a href="{settings.FRONTEND_URL}/privacy" style="color: #94A3B8;">Privacy Policy</a> &middot;
            <a href="{settings.FRONTEND_URL}/terms" style="color: #94A3B8;">Terms of Service</a>
        </p>
    </div>
    """

    return _send_email(to_email, "Verify your email — Cloak Haven", html)


def send_password_reset_email(to_email: str, token: str) -> bool:
    """Send password reset link."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 40px;">
            <h1 style="color: #0F172A; font-size: 28px; margin: 0;">
                <span style="color: #6366F1;">CH</span> Cloak Haven
            </h1>
        </div>
        <h2 style="color: #1E293B;">Reset your password</h2>
        <p style="color: #475569; line-height: 1.6;">
            You requested a password reset. Click the button below to set a new password.
            This link expires in 1 hour.
        </p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{reset_url}"
               style="background-color: #6366F1; color: white; padding: 14px 32px;
                      border-radius: 8px; text-decoration: none; font-weight: 600;
                      display: inline-block;">
                Reset Password
            </a>
        </div>
        <p style="color: #94A3B8; font-size: 14px;">
            If you didn't request this, you can safely ignore this email.
        </p>
    </div>
    """

    return _send_email(to_email, "Reset your password — Cloak Haven", html)


def send_score_update_email(to_email: str, full_name: str, old_score: int, new_score: int) -> bool:
    """Send score change notification."""
    change = new_score - old_score
    direction = "increased" if change > 0 else "decreased"
    change_color = "#10B981" if change > 0 else "#EF4444"

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 40px;">
            <h1 style="color: #0F172A; font-size: 28px; margin: 0;">
                <span style="color: #6366F1;">CH</span> Cloak Haven
            </h1>
        </div>
        <h2 style="color: #1E293B;">Your score has {direction}</h2>
        <div style="text-align: center; margin: 24px 0;">
            <div style="display: inline-block; padding: 24px 40px; background: #F1F5F9; border-radius: 16px;">
                <span style="font-size: 48px; font-weight: 700; color: #0F172A;">{new_score}</span>
                <span style="font-size: 18px; color: {change_color}; margin-left: 8px;">
                    ({'+' if change > 0 else ''}{change})
                </span>
            </div>
        </div>
        <p style="color: #475569; line-height: 1.6;">
            Hi {full_name}, your Cloak Haven score has {direction} from {old_score} to {new_score}.
            Visit your dashboard to see the details.
        </p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{settings.FRONTEND_URL}/dashboard"
               style="background-color: #6366F1; color: white; padding: 14px 32px;
                      border-radius: 8px; text-decoration: none; font-weight: 600;
                      display: inline-block;">
                View Dashboard
            </a>
        </div>
    </div>
    """

    return _send_email(to_email, f"Your Cloak Haven score has {direction}", html)


def send_dispute_update_email(
    to_email: str,
    full_name: str,
    dispute_status: str,
    finding_title: str,
) -> bool:
    """Send dispute status update."""
    status_text = {
        "reviewing": "is now being reviewed",
        "overturned": "has been overturned in your favor",
        "upheld": "has been upheld after review",
    }.get(dispute_status, f"status is now: {dispute_status}")

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 40px;">
            <h1 style="color: #0F172A; font-size: 28px; margin: 0;">
                <span style="color: #6366F1;">CH</span> Cloak Haven
            </h1>
        </div>
        <h2 style="color: #1E293B;">Dispute Update</h2>
        <p style="color: #475569; line-height: 1.6;">
            Hi {full_name}, your dispute for "{finding_title}" {status_text}.
        </p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{settings.FRONTEND_URL}/dashboard"
               style="background-color: #6366F1; color: white; padding: 14px 32px;
                      border-radius: 8px; text-decoration: none; font-weight: 600;
                      display: inline-block;">
                View Details
            </a>
        </div>
    </div>
    """

    return _send_email(to_email, "Dispute Update — Cloak Haven", html)
