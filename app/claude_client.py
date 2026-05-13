import os
import anthropic
from app.models import UnifiedMessage, QueryType


# Static property context loaded per property_id.
# In production this would be fetched from the properties table.
PROPERTY_CONTEXT: dict[str, str] = {
    "villa-b1": """
Property: Villa B1, Assagao, North Goa
Bedrooms: 3 | Max guests: 6 | Private pool: Yes
Check-in: 2pm | Check-out: 11am
Base rate: INR 18,000 per night (up to 4 guests)
Extra guest: INR 2,000 per night per person
WiFi password: Nistula@2024
Caretaker: Available 8am to 10pm
Chef on call: Yes, pre-booking required
Availability April 20 to 24: Available
Cancellation policy: Free cancellation up to 7 days before check-in
""".strip()
}

FALLBACK_CONTEXT = "Property details are not available in the current context."

# Tone instructions per query type — keeps brand voice consistent
# while adjusting the register to match the guest's situation.
TONE_GUIDE: dict[QueryType, str] = {
    QueryType.pre_sales_availability: (
        "warm and specific. Address the exact dates asked about, "
        "state availability clearly, and invite the guest to confirm."
    ),
    QueryType.pre_sales_pricing: (
        "clear and transparent. Give exact numbers from the property "
        "context. Break down the calculation if multiple guests are asked about."
    ),
    QueryType.post_sales_checkin: (
        "friendly and practical. Give the guest exactly what they need "
        "without padding. If it is the WiFi password, just give it."
    ),
    QueryType.special_request: (
        "accommodating and honest. Confirm what is definitely possible, "
        "and flag anything that needs to be arranged rather than making "
        "promises you cannot guarantee."
    ),
    QueryType.complaint: (
        "empathetic and calm. Acknowledge the problem first before "
        "anything else. Do not be defensive. Give a concrete next step "
        "with a specific timeframe. Do not use hollow phrases like "
        "'sorry for the inconvenience'."
    ),
    QueryType.general_enquiry: (
        "friendly and informative. Answer what is asked and nothing more."
    ),
}


def build_system_prompt(property_id: str, query_type: QueryType) -> str:
    context = PROPERTY_CONTEXT.get(property_id, FALLBACK_CONTEXT)
    tone = TONE_GUIDE.get(query_type, "warm and professional.")

    return f"""You are a guest communications assistant for Nistula, a luxury villa brand in Goa, India.
Your job is to draft replies to guest messages on behalf of the Nistula team.

Tone: {tone}

Property context you must use when answering:
{context}

Hard rules:
- Never invent information that is not in the property context above.
- If the guest asks something you cannot answer from context, say you will confirm shortly.
- Address the guest by their first name only.
- Keep replies under 120 words unless the query genuinely requires more.
- Do not use em dashes.
- Do not start the reply with "I hope" or "I wanted to" or any filler opener.
- Sound like a real person, not a chatbot or a template.
- Do not sign off with a name or title.
"""


def get_drafted_reply(message: UnifiedMessage) -> str:
    """
    Calls Claude with property context and query-type-specific tone
    instructions. Returns the drafted reply text.
    Raises an exception on API failure — handled in main.py.
    """
    from dotenv import load_dotenv
    load_dotenv(override=True)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in environment.")

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = build_system_prompt(message.property_id, message.query_type)

    user_prompt = (
        f"Guest name: {message.guest_name}\n"
        f"Source channel: {message.source.value}\n"
        f"Query type: {message.query_type.value}\n"
        f"Message: {message.message_text}\n\n"
        f"Draft a reply to this guest message."
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text.strip()