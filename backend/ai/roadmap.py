ROADMAP_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "initiative": {"type": "string", "description": "Name of the initiative"},
        "business_value": {"type": "string", "description": "Why it matters, in business terms"},
        "estimated_cost": {"type": "string", "enum": ["Low", "Medium", "High"]},
        "complexity": {"type": "string", "enum": ["Low", "Medium", "High"]},
        "implementation_effort": {"type": "string", "description": "Roughly what it takes to implement"},
        # Named "expected_return" rather than "expected_roi" deliberately:
        # Claude has such a strong prior toward capitalizing "ROI" as an
        # acronym that it sometimes emits "expected_ROI" instead of the
        # exact schema key, silently breaking downstream parsing.
        # Confirmed this happening in practice before renaming — avoiding
        # acronym-shaped field names in tool schemas sidesteps it.
        "expected_return": {"type": "string", "enum": ["Low", "Medium", "High"]},
        "dependencies": {"type": "string", "description": "What needs to happen first, or 'None'"},
    },
    "required": [
        "initiative",
        "business_value",
        "estimated_cost",
        "complexity",
        "implementation_effort",
        "expected_return",
        "dependencies",
    ],
}

ROADMAP_TOOL = {
    "name": "record_roadmap",
    "description": "Record a digital transformation roadmap organized into three time horizons.",
    "input_schema": {
        "type": "object",
        "properties": {
            "quick_wins": {"type": "array", "items": ROADMAP_ITEM_SCHEMA, "description": "0-3 months"},
            "medium_term": {"type": "array", "items": ROADMAP_ITEM_SCHEMA, "description": "3-12 months"},
            "long_term": {"type": "array", "items": ROADMAP_ITEM_SCHEMA, "description": "12-36 months"},
        },
        "required": ["quick_wins", "medium_term", "long_term"],
    },
}

SYSTEM_PROMPT = (
    "You are a strategy consultant building a digital transformation "
    "roadmap from a SWOT analysis. Organize initiatives into three time "
    "horizons: Quick Wins (0-3 months, fast/low-complexity), Medium-Term "
    "(3-12 months), Long-Term (12-36 months, major transformation). "
    "Every initiative should trace back to a specific weakness or "
    "opportunity in the SWOT below, not be generic advice."
)

EMPTY_ROADMAP = {"quick_wins": [], "medium_term": [], "long_term": []}


def generate_roadmap(client, swot_text: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=[ROADMAP_TOOL],
        tool_choice={"type": "tool", "name": "record_roadmap"},
        messages=[{"role": "user", "content": swot_text}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    return EMPTY_ROADMAP
