MATURITY_CATEGORIES = [
    "leadership",
    "operations",
    "technology",
    "data",
    "supply_chain",
    "automation",
    "sustainability",
    "cybersecurity",
    "workforce",
]

DIMENSION_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
            "description": "1 (ad hoc/immature) to 5 (best-in-class)",
        },
        "justification": {
            "type": "string",
            "description": "One sentence tied to specific evidence in the documents",
        },
    },
    "required": ["score", "justification"],
}

MATURITY_TOOL = {
    "name": "record_digital_maturity",
    "description": (
        "Score a client's digital maturity across 9 dimensions based on the provided documentation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {category: DIMENSION_SCHEMA for category in MATURITY_CATEGORIES},
        "required": MATURITY_CATEGORIES,
    },
}

SYSTEM_PROMPT = (
    "You are a digital transformation consultant assessing a client's "
    "digital maturity across 9 dimensions, each scored 1 (ad hoc, "
    "immature) to 5 (best-in-class). Base every score on specific "
    "evidence in the documents provided. If the documents contain NO "
    "evidence for a dimension, score it 3 and say so explicitly in the "
    "justification (e.g. 'Insufficient evidence in provided "
    "documents') — do not invent evidence or assume best/worst case."
)


def generate_digital_maturity(client, context: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=[MATURITY_TOOL],
        tool_choice={"type": "tool", "name": "record_digital_maturity"},
        messages=[{"role": "user", "content": context}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    return {}
