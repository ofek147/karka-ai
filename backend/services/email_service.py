"""
Email service — Resend.com.
If RESEND_API_KEY not set, logs to console (dev mode).
"""
import logging
from typing import Optional
import httpx
from ..config import settings

logger = logging.getLogger(__name__)


async def send_report_ready(
    email: str,
    name: Optional[str],
    gush: int,
    helka: int,
    text: str,
) -> bool:
    """
    Send the completed report as a plain-text email via Resend.
    """
    display_name = name or "שלום"

    if not settings.resend_api_key:
        logger.warning(f"[EMAIL DEV MODE] Would send report to {email} (gush={gush}, helka={helka})")
        return True

    # Convert plain text to simple HTML (preserve line breaks)
    text_html = "<br>".join(
        f"<strong>{line}</strong>" if line and not line.startswith(" ") and line.endswith(":")
        else line
        for line in text.replace("&", "&amp;").replace("<", "&lt;").splitlines()
    )

    html = f"""
<div dir="rtl" style="font-family:sans-serif;max-width:600px;margin:auto;padding:28px;color:#1a1a1a">
  <h2 style="margin-top:0;color:#0d1829">kark<span style="color:#c4a044;font-style:italic">A</span>i</h2>
  <p>{display_name}, הדוח התכנוני שלך מוכן:</p>
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:16px 0">
  <div style="line-height:1.8;font-size:14px">{text_html}</div>
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0">
  <p style="color:#94a3b8;font-size:12px">karkAi — ניתוח קרקעות חכם</p>
</div>"""

    try:
        payload = {
            "from": "karkAi <noreply@karka-ai.co.il>",
            "to": [email],
            "subject": f"דוח תכנוני — גוש {gush}, חלקה {helka}",
            "html": html,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            )
            r.raise_for_status()
        logger.info(f"[email] Report sent to {email}")
        return True
    except Exception as e:
        logger.error(f"[email] Failed to send report to {email}: {e}")
        return False


async def send_magic_link(email: str, token: str) -> bool:
    link = f"{settings.frontend_url}/auth/verify?token={token}"

    if not settings.resend_api_key:
        logger.warning(f"[EMAIL DEV MODE] Magic link for {email}: {link}")
        return True

    try:
        import httpx
        payload = {
            "from": "karkAi <noreply@karka-ai.co.il>",
            "to": [email],
            "subject": "הקישור לכניסה שלך ל-karkAi",
            "html": f"""
<div dir="rtl" style="font-family:sans-serif;max-width:480px;margin:auto;padding:24px">
  <h2 style="color:#0d1829">kark<span style="color:#c4a044;font-style:italic">A</span>i</h2>
  <p>לחץ על הכפתור להתחברות:</p>
  <a href="{link}" style="display:inline-block;background:#c4a044;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;margin:16px 0">
    כניסה לkarkAi
  </a>
  <p style="color:#64748b;font-size:12px">הקישור בתוקף ל-30 דקות. אם לא ביקשת כניסה, התעלם.</p>
</div>""",
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                timeout=10,
            )
            r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Email send failed to {email}: {e}")
        return False
