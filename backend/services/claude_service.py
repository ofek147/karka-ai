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
    שלב 1: חילוץ נתונים מובנים מתכנית בודדת → JSON.
    תוצאה נשמרת ב-plan_cache.summary_json.
    """
    prompt = (
        "אתה מומחה לתכנון ובנייה בישראל. קיבלת את הטקסט המלא של תכנית תכנון ישראלית.\n"
        "המשימה שלך: לחלץ את המידע הבא בדיוק, בפורמט JSON בלבד. אם מידע לא קיים בטקסט — כתוב null.\n"
        "החזר JSON בלבד — ללא טקסט לפני או אחרי, ללא markdown, ללא ```json.\n\n"
        f"שם תכנית: {plan_name}\n"
        f"מספר תכנית: {plan_number}\n\n"
        f"{pdf_text[:25000]}\n\n"
        "JSON נדרש:\n"
        "{\n"
        '  "plan_name": "שם התכנית",\n'
        '  "plan_number": "מספר התכנית",\n'
        '  "plan_size_dunam": <מספר דונמים או null>,\n'
        '  "initiator": "יוזם התכנית או null",\n'
        '  "plan_stage": "שלב התכנית (תוקף/הפקדה/בתכנון וכו\')",\n'
        '  "total_units": <מספר יחידות דיור או null>,\n'
        '  "protected_housing_units": <דיור מוגן/דיור בר-השגה או null>,\n'
        '  "commerce_employment_sqm": <מ"ר מסחר ותעסוקה או null>,\n'
        '  "public_buildings_sqm": <מ"ר מבני ציבור או null>,\n'
        '  "max_floors": <מספר קומות מקסימלי או null>,\n'
        '  "timeline_estimate": "הערכת ציר זמן לאישור סופי",\n'
        '  "plan_type": "ארצית/מחוזית/מתארית/מפורטת — בחר אחד",\n'
        '  "grants_permits": <true אם כתוב במפורש ''ניתן להוציא היתר'' או ''תוכנית שמכוחה ניתן להוציא היתרים'', false אחרת, null אם לא מוזכר>,\n'
        '  "contains_detailed_provisions": <true אם כתוב במפורש ''מכילה הוראות של תכנית מפורטת'', false אחרת, null אם לא מוזכר>,\n'
        '  "can_issue_permit": <true אם grants_permits=true, או plan_type=מפורטת ו-plan_stage=בתוקף>,\n'
        '  "warnings": ["אזהרה 1", "אזהרה 2"],\n'
        '  "positives": ["נקודה חיובית 1", "נקודה חיובית 2"]\n'
        "}\n\n"
        "כללים:\n"
        "- plan_type: תמ\"א/תתל/תמל = ארצית, תמח = מחוזית, תמ = מתארית, תב\"ע/תכנית מפורטת = מפורטת\n"
        "- grants_permits: חלץ מהטקסט בלבד — אל תנחש לפי plan_type. תת\"ל/תמ\"ל יכולות להיות true.\n"
        "- contains_detailed_provisions: חלץ מהטקסט בלבד — אל תנחש.\n"
        "- can_issue_permit: true אם grants_permits=true, או plan_type=מפורטת ו-plan_stage=בתוקף\n"
        "- warnings ו-positives: עד 5 נקודות כל אחד\n"
        "- ציר זמן: על בסיס שלב התכנית + תכניות דומות בישראל\n"
        "- רק מידע שמופיע בטקסט — אל תמציא\n"
        "- החזר JSON בלבד"
    )
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=90.0)
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    # ניקוי markdown אם Claude הוסיף בטעות
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
    return raw.strip()


async def synthesize_plans(plan_summaries_json: list, missing_plans: list | None = None) -> str:
    """
    שלב 2: סינתזה מרובת תכניות → JSON מאוחד עם כללי עדיפות.
    plan_summaries_json: רשימת dict (תוצאות שלב 1 parsed).
    missing_plans: תכניות שלא נחלצו (OCR נכשל / אין PDF) — מועברות ל-Claude להכרה.
    תוצאה משמשת לחישובי שכבה 3 ולדוח הסופי.
    """
    import json
    summaries_text = json.dumps(plan_summaries_json, ensure_ascii=False, indent=2)

    # בניית בלוק אזהרה על תכניות חסרות — Claude יקבל הקשר מפורש
    missing_block = ""
    if missing_plans:
        lines = []
        for mp in missing_plans:
            pnum = mp.get("plan_number", "")
            pname = mp.get("plan_name", "")
            reason = mp.get("reason", "לא ידוע")
            conf = mp.get("ocr_confidence")
            label = str(pnum) + (" (" + str(pname) + ")" if pname and pname != pnum else "")
            detail = "סיבה: " + str(reason)
            if conf is not None:
                detail += ", OCR confidence: " + f"{conf:.0f}" + "%"
            lines.append("  - " + label + " — " + detail)
        missing_block = (
            "\n\u26a0\ufe0f תכניות שלא נחלצו ולא נכללות בסינתזה:\n"
            + "\n".join(lines)
            + "\nחשוב: ציין ב-warnings שהניתוח עשוי להיות חלקי בגלל תכניות חסרות אלה.\n\n"
        )

    prompt = (
        "אתה מומחה לתכנון ובנייה בישראל. קיבלת מספר סיכומי תכניות הרלוונטיות לחלקה ספציפית.\n"
        "המשימה: לסנתז את כל התכניות ל-JSON אחד מאוחד. החזר JSON בלבד.\n\n"
        "כללי סינתזה:\n"
        "- תכנית בתוקף גוברת על תכנית בהפקדה\n"
        "- grants_permits=true גוברת — ללא קשר לסוג התכנית (תת\"ל/תמ\"ל ארציות יכולות לאפשר היתר ישירות)\n"
        "- אל תניח ש\"ספציפית > ארצית\" — הסתמך על grants_permits ו-contains_detailed_provisions בלבד\n"
        "- סתירה אמיתית (אין יחס ידוע בין התכניות) → ציין ב-conflicts\n"
        "- יחס ידוע (A משנה את B, C מבטלת D) → אל תציין כ-conflict\n"
        "- נתון שונה בין תכניות → קח את המחמיר (פחות יחידות / פחות קומות)\n\n"
        + missing_block
        + "סיכומי תכניות:\n" + summaries_text + "\n\n"
        + "JSON נדרש:\n"
        "{\n"
        '  "primary_plan": "שם התכנית הדומיננטית",\n'
        '  "all_plans": ["שם1", "שם2"],\n'
        '  "plan_stage": "שלב משולב",\n'
        '  "total_units": <מספר יחידות אחרי סינתזה או null>,\n'
        '  "protected_housing_units": <או null>,\n'
        '  "commerce_employment_sqm": <או null>,\n'
        '  "public_buildings_sqm": <או null>,\n'
        '  "max_floors": <או null>,\n'
        '  "plan_size_dunam": <גודל התכנית הדומיננטית או null>,\n'
        '  "initiator": "יוזם או null",\n'
        '  "timeline_estimate": "הערכת ציר זמן",\n'
        '  "warnings": ["אזהרה 1"],\n'
        '  "positives": ["נקודה חיובית 1"],\n'
        '  "conflicts": ["סתירה בין תכניות אם קיימת"],\n'
        '  "has_detailed_plan": <true אם יש לפחות תכנית מפורטת בתוקף, false אחרת>\n'
        "}\n\n"
        "כללים:\n"
        "- warnings/positives: עד 6 נקודות\n"
        "- conflicts: ריק אם אין סתירות\n"
        '- has_detailed_plan: true אם קיימת תב"ע מפורטת מאושרת, או אם תכנית כלשהי grants_permits=true\n'
        "- החזר JSON בלבד — ללא טקסט נוסף"
    )
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=90.0)
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0]
    return raw.strip()



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
