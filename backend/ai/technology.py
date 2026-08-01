TECH_RECOMMENDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "problem": {"type": "string", "description": "The operational problem being addressed"},
        "recommendation": {"type": "string", "description": "The initiative name, e.g. 'Predictive Maintenance'"},
        "technology": {"type": "string", "description": "Technology category, e.g. 'IoT Sensors'"},
        "platform": {
            "type": "string",
            "description": "A specific real-world platform or vendor, e.g. 'Azure IoT', 'AWS IoT Core', 'PTC ThingWorx'",
        },
        "expected_return": {"type": "string", "enum": ["Low", "Medium", "High"]},
    },
    "required": ["problem", "recommendation", "technology", "platform", "expected_return"],
}

TECH_RECOMMENDATION_TOOL = {
    "name": "record_technology_recommendations",
    "description": "Recommend a specific technology and platform for each operational problem listed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "recommendations": {"type": "array", "items": TECH_RECOMMENDATION_SCHEMA},
        },
        "required": ["recommendations"],
    },
}

SYSTEM_PROMPT = (
    "You are a technology consultant recommending specific solutions for "
    "a client's operational problems. For each problem listed, recommend "
    "ONE concrete technology solution: a named initiative, the category "
    "of technology, and a SPECIFIC real-world platform or vendor product "
    "(e.g. 'Azure IoT', 'AWS IoT Core', 'PTC ThingWorx', 'Snowflake') — "
    "use your knowledge of real technology platforms, this doesn't need "
    "to come from the client's documents. Also estimate expected ROI."
)

EMPTY_RECOMMENDATIONS = {"recommendations": []}


def generate_technology_recommendations(client, problems_text: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        tools=[TECH_RECOMMENDATION_TOOL],
        tool_choice={"type": "tool", "name": "record_technology_recommendations"},
        messages=[{"role": "user", "content": problems_text}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    return EMPTY_RECOMMENDATIONS
