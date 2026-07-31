PAIN_POINT_TOOL = {
    "name": "record_pain_points",
    "description": "Record the operational pain points found in a consulting interview transcript.",
    "input_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "pain_point": {"type": "string", "description": "Short name of the problem"},
                        "severity": {"type": "string", "enum": ["Low", "Medium", "High"]},
                        "business_impact": {
                            "type": "string",
                            "description": "Why this matters, in business terms",
                        },
                        "recommendation": {
                            "type": "string",
                            "description": "A concrete initiative that addresses it",
                        },
                    },
                    "required": ["pain_point", "severity", "business_impact", "recommendation"],
                },
            }
        },
        "required": ["findings"],
    },
}

SYSTEM_PROMPT = (
    "You are a digital transformation consultant analyzing a stakeholder "
    "interview transcript for a manufacturing client. Identify concrete "
    "operational pain points, not vague complaints. For each one, assess "
    "its severity, its business impact, and a specific recommendation "
    "(a named initiative, not generic advice)."
)


def analyze_transcript(client, transcript: str) -> list[dict]:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        tools=[PAIN_POINT_TOOL],
        # Forces this exact tool call rather than letting Claude choose to
        # reply in free text — guarantees structured output every time.
        tool_choice={"type": "tool", "name": "record_pain_points"},
        messages=[{"role": "user", "content": transcript}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input["findings"]

    return []
