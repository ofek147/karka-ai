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
    plans_text = ""
    if parcel_data.plans:
        plans_list = []
        for p in parcel_data.plans[:5]:
            status = f" ({p.station_desc})" if p.station_desc else ""
            plans_list.append(f"- {p.mavat_name}: {p.pl_name or 'ללא שם'}{status}")
        plans_text = "\n".join(plans_list)
    else:
        plans_text = "לא נמצאו תכניות בניה רשומות"

    area = ""
    if parcel_data.geometry and parcel_data.geometry.area_sqm:
        area = f"\nשטח החלקה: {parcel_data.geometry.area_sqm:.0f} מ\"ר"

    return f"""[נתוני חלקה אוטומטיים — גוש {gush}, חלקה {helka}{area}]
תכניות בניה:
{plans_text}"""


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
            model="claude-haiku-4-5",
            max_tokens=20,
            messages=[{
                "role": "user",
                "content": f"תמצת את הנושא הבא ב-3-4 מילים בעברית בלבד, ללא פסיקים, ללא נקודות:\n{first_message[:200]}"
            }]
        )
        return response.content[0].text.strip()[:50]
    except Exception:
        return first_message[:40]


async def _call_claude(messages: List[Dict[str, str]]) -> str:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        return response.content[0].text
    except anthropic.APIConnectionError as e:
        raise RuntimeError(f"Anthropic connection failed: {type(e).__name__}: {e}") from e
    except anthropic.AuthenticationError as e:
        raise RuntimeError("Anthropic auth failed — check ANTHROPIC_API_KEY") from e
    except Exception as e:
        raise RuntimeError(f"Anthropic error: {type(e).__name__}: {e}") from e
