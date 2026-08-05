import anthropic
from typing import List, Dict
from ..config import settings
from ..models.parcel import ParcelFullData

SYSTEM_PROMPT = """אתה סוכן AI מקצועי של karka-ai — פלטפורמה ישראלית לניתוח קרקעות.

האופי שלך: מקצועי, סקרן, ישראלי, שירותי, רשמי אך לא קר. לא חנפני.

תפקידך:
- לעזור למשתמשים להבין מונחי תכנון ובנייה בישראל
- לנתח נתוני גוש/חלקה אם סופקו
- לשאול שאלות ממוקדות כדי להבין מה המשתמש באמת צריך
- להצביע על דברים שהמשתמש לא חשב לשאול
- להתכוונן אוטומטית לרמת הידע של המשתמש מהדיאלוג הראשון

כללים:
- ענה תמיד בעברית
- אל תיתן ייעוץ משפטי, הערכת שווי, או המלצות קנייה/מכירה
- אם לא סופקו נתוני חלקה — אמור זאת בצורה חיובית: "אם תיתן לי גוש וחלקה, אשלוף את הנתונים האמיתיים עבורך"
- אל תאמר שאין לך גישה למערכות — יש לך. אם לא קיבלת נתונים זה כי לא נמסרו
- תשובות ממוקדות, לא ארוכות מדי

בסוף כל תשובה הוסף בשורה נפרדת:
⚠️ המידע מוצג לצרכי לימוד בלבד ואינו מהווה ייעוץ משפטי, תכנוני, או השקעתי."""


def build_parcel_context(gush: int, helka: int, parcel_data: ParcelFullData) -> str:
    """Build context string for Claude from parcel data."""
    lines = [f"[נתוני חלקה — גוש {gush}, חלקה {helka}]"]

    # Area + status
    if parcel_data.geometry:
        geo = parcel_data.geometry
        if geo.area_sqm:
            lines.append(f'שטח רשום: {geo.area_sqm:.0f} מ"ר')

    # Agricultural flag
    if parcel_data.is_agricultural:
        lines.append("סוג: קרקע חקלאית")

    # Land use
    if parcel_data.land_use:
        lu = parcel_data.land_use[0]
        yu = lu.get("ייעוד") or lu.get("land_use") or lu.get("use_type") or ""
        if yu:
            lines.append(f"ייעוד קרקע: {yu}")

    # Taba
    if parcel_data.taba:
        names = []
        for t in parcel_data.taba[:3]:
            n = t.get("plan_name") or t.get("תכנית") or t.get("mavat_name") or ""
            if n:
                names.append(n)
        if names:
            lines.append(f'תב"עות: {", ".join(names)}')

    # iplan plans
    if parcel_data.plans:
        plan_lines = []
        for p in parcel_data.plans[:5]:
            status = f" ({p.station_desc})" if p.station_desc else ""
            plan_lines.append(f"  - {p.mavat_name}: {p.pl_name or 'ללא שם'}{status}")
        lines.append("תכניות בניה:")
        lines.extend(plan_lines)
    else:
        lines.append("תכניות בניה: לא נמצאו")

    return "\n".join(lines)


async def ask_claude(gush: int, helka: int, parcel_data: ParcelFullData, question: str) -> str:
    """Legacy single-question endpoint (kept for /api/ask compatibility)"""
    messages = [{"role": "user", "content": f"{build_parcel_context(gush, helka, parcel_data)}\n\nשאלה: {question}"}]
    return await _call_claude(messages)


async def chat_claude(messages: List[Dict[str, str]], parcel_context: str = "") -> str:
    """Full conversation history endpoint for /api/chat"""
    claude_messages = []
    for i, msg in enumerate(messages):
        content = msg["content"]
        # Inject parcel context into the last user message if available
        if parcel_context and msg["role"] == "user" and i == len(messages) - 1:
            content = f"{parcel_context}\n\n{content}"
        claude_messages.append({"role": msg["role"], "content": content})

    return await _call_claude(claude_messages)


async def generate_title(first_message: str) -> str:
    """Generate a short session title from the first user message"""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{
                "role": "user",
                "content": f"תמצת את הנושא הבא ב-3-4 מילים בעברית בלבד, ללא פסיקים, ללא נקודות:\n{first_message[:200]}"
            }]
        )
        return response.content[0].text.strip()[:50]
    except Exception:
        return first_message[:40]


async def summarize_plan(plan_name: str, plan_number: str, pdf_text: str) -> str:
    """
    Summarize a single plan PDF text into a concise planning summary.
    Called once per plan, result cached in DB.
    """
    prompt = (
        f"להלן תוכן תכנית בניה רשמית:\n"
        f"שם תכנית: {plan_name}\n"
        f"מספר תכנית: {plan_number}\n\n"
        f"{pdf_text}\n\n"
        "סכם את התכנית ב-3-5 משפטים בעברית פשוטה. "
        "התמקד ב: מה מותר לבנות, כמה יחידות/קומות/שטחים, "
        "מה הסטטוס הנוכחי, ומה השפעתה על הקרקע. "
        "אל תכלול ייעוץ השקעתי."
    )
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=60.0)
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


async def _call_claude(messages: List[Dict[str, str]]) -> str:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=90.0)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        return response.content[0].text
    except anthropic.APITimeoutError:
        raise RuntimeError("timeout")
    except anthropic.APIConnectionError as e:
        raise RuntimeError(f"connection error: {type(e).__name__}") from e
    except anthropic.AuthenticationError:
        raise RuntimeError("auth failed")
    except Exception as e:
        raise RuntimeError(f"error: {type(e).__name__}: {e}") from e
