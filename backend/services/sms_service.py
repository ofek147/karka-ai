"""
SMS service — Twilio by default.
If TWILIO_* env vars not set, logs OTP to console (for local/beta testing).
"""
import logging
from ..config import settings

logger = logging.getLogger(__name__)


async def send_otp_sms(phone: str, code: str) -> bool:
    """Returns True if sent, False on failure."""
    if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_phone):
        # Dev/beta mode — print to Railway logs
        logger.warning(f"[SMS DEV MODE] OTP for {phone}: {code}")
        return True

    try:
        import httpx
        auth = (settings.twilio_account_sid, settings.twilio_auth_token)
        data = {
            "To": phone,
            "From": settings.twilio_from_phone,
            "Body": f"קוד הכניסה שלך ל-karkAi: {code}\nבתוקף ל-10 דקות.",
        }
        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
        async with httpx.AsyncClient() as client:
            r = await client.post(url, data=data, auth=auth, timeout=10)
            r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"SMS send failed: {e}")
        return False
