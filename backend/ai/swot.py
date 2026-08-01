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


def format_swot_as_text(swot: dict) -> str:
    """Turns a SWOT result back into plain text — used as the input to
    the next step in the pipeline (Roadmap generation), which reasons
    over the distilled findings rather than the raw documents again."""
    lines = []
    for category in ["strengths", "weaknesses", "opportunities", "threats"]:
        lines.append(f"{category.upper()}:")
        for entry in swot.get(category, []):
            lines.append(f"- {entry.get('item')}: {entry.get('explanation')}")
    return "\n".join(lines)


def format_weaknesses_as_text(swot: dict) -> str:
    """Just the Weaknesses quadrant, as plain text — the Technology
    Recommendation Engine maps problems to fixes, so it only needs the
    problems, not the full SWOT."""
    return "\n".join(
        f"- {entry.get('item')}: {entry.get('explanation')}"
        for entry in swot.get("weaknesses", [])
    )
