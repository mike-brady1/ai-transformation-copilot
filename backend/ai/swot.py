SWOT_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "item": {"type": "string", "description": "Short label, e.g. 'Experienced workforce'"},
        "explanation": {
            "type": "string",
            "description": "One sentence tying it to the evidence provided",
        },
    },
    "required": ["item", "explanation"],
}

SWOT_TOOL = {
    "name": "record_swot",
    "description": "Record a SWOT analysis for a client engagement based on the provided documentation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "strengths": {"type": "array", "items": SWOT_ITEM_SCHEMA},
            "weaknesses": {"type": "array", "items": SWOT_ITEM_SCHEMA},
            "opportunities": {"type": "array", "items": SWOT_ITEM_SCHEMA},
            "threats": {"type": "array", "items": SWOT_ITEM_SCHEMA},
        },
        "required": ["strengths", "weaknesses", "opportunities", "threats"],
    },
}

SYSTEM_PROMPT = (
    "You are a strategy consultant creating a SWOT analysis for a client "
    "engagement based on the documentation provided (interviews, reports). "
    "Identify concrete, specific items grounded in the evidence — not "
    "generic business platitudes. Every item needs a one-sentence "
    "explanation tied to something actually in the source material."
)

EMPTY_SWOT = {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}


def generate_swot(client, context: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        tools=[SWOT_TOOL],
        tool_choice={"type": "tool", "name": "record_swot"},
        messages=[{"role": "user", "content": context}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    return EMPTY_SWOT
