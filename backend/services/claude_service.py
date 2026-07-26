import anthropic
from ..config import settings
from ..models.parcel import ParcelFullData

SYSTEM_PROMPT = """אתה עוזר מומחה בתחום תכנון ובניה בישראל.
תפקידך: להסביר נתוני תכנון קרקע לאנשים פרטיים בשפה פשוטה וברורה.

כללים:
- ענה תמיד בעברית
- היה ידידותי וברור — כמו מסביר לחבר, לא כמו עורך דין
- אל תיתן המלצות השקעה או ייעוץ משפטי
- אם אין מידע מספיק — אמור זאת בכנות
- תשובה קצרה: 3-5 משפטים מקסימום

בסוף כל תשובה הוסף תמיד בשורה נפרדת:
⚠️ המידע מוצג לצרכי לימוד בלבד ואינו מהווה ייעוץ משפטי, תכנוני, או השקעתי."""


def build_user_prompt(gush: int, helka: int, parcel_data: ParcelFullData, question: str) -> str:
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

    return f"""נתוני חלקה:
גוש: {gush}, חלקה: {helka}{area}

תכניות בניה רלוונטיות:
{plans_text}

שאלת המשתמש: {question}"""


async def ask_claude(gush: int, helka: int, parcel_data: ParcelFullData, question: str) -> str:
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": build_user_prompt(gush, helka, parcel_data, question)}
            ]
        )
        return message.content[0].text
    except anthropic.APIConnectionError as e:
        raise RuntimeError(f"Anthropic connection failed: {type(e).__name__}: {e}") from e
    except anthropic.AuthenticationError as e:
        raise RuntimeError(f"Anthropic auth failed — check ANTHROPIC_API_KEY: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Anthropic error: {type(e).__name__}: {e}") from e
