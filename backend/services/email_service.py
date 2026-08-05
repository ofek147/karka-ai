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
    pdf_bytes: bytes,
) -> bool:
    """
    Send the completed report PDF to the user's email via Resend.
    Attaches the PDF directly to the email.
    """
    import base64
    display_name = name or "שלום"
    filename = f"karkAi-report-{gush}-{helka}.pdf"
    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    if not settings.resend_api_key:
        logger.warning(f"[EMAIL DEV MODE] Would send report to {email} (gush={gush}, helka={helka})")
        return True

    html = f"""
<div dir="rtl" style="font-family:sans-serif;max-width:520px;margin:auto;padding:28px">
  <h2 style="margin-top:0">kark<span style="color:#c4a044;font-style:italic">A</span>i</h2>
  <p>{display_name},</p>
  <p>הדוח התכנוני עבור <strong>גוש {gush}, חלקה {helka}</strong> מוכן ומצורף למייל זה.</p>
  <p style="color:#64748b;font-size:13px">הדוח כולל ניתוח תכנוני מבוסס מידע רשמי מתכניות בניה, ייעודי קרקע, ותמונת לוויין.</p>
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0">
  <p style="color:#94a3b8;font-size:12px">karkAi — ניתוח קרקעות חכם</p>
</div>"""

    try:
        payload = {
            "from": "karkAi <noreply@karka-ai.co.il>",
            "to": [email],
            "subject": f"דוח תכנוני — גוש {gush}, חלקה {helka}",
            "html": html,
            "attachments": [
                {
                    "filename": filename,
                    "content": pdf_b64,
                    "type": "application/pdf",
                    "disposition": "attachment",
                }
            ],
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
