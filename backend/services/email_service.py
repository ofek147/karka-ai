"""
Email service — Resend.com by default.
If RESEND_API_KEY not set, logs magic link to console.
"""
import logging
from ..config import settings

logger = logging.getLogger(__name__)

FRONTEND_URL = "https://karka-ai.co.il"


async def send_magic_link(email: str, token: str) -> bool:
    link = f"{FRONTEND_URL}/auth/verify?token={token}"

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
            logger.info(f"[EMAIL OK] Sent to {email} | status={r.status_code} | id={r.json().get('id')}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL FAIL] to={email} error={e}")
        return False
