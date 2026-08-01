SUSTAINABILITY_TOOL = {
    "name": "record_sustainability_analysis",
    "description": "Estimate sustainability metrics and recommend improvement opportunities for a client engagement.",
    "input_schema": {
        "type": "object",
        "properties": {
            "emissions_factor_kg_co2_per_kwh": {
                "type": "number",
                "description": "Assumed grid emissions factor used for the CO2 estimate, e.g. 0.45 for a mixed industrial grid",
            },
            "emissions_factor_assumption": {
                "type": "string",
                "description": "One sentence explaining the assumption behind this factor",
            },
            "waste_assessment": {
                "type": "string",
                "description": "Qualitative assessment of waste generation based on the documents, or 'Insufficient evidence in provided documents' if not covered",
            },
            "transportation_assessment": {
                "type": "string",
                "description": "Qualitative assessment of transportation-related emissions/inefficiency based on the documents, or 'Insufficient evidence in provided documents' if not covered",
            },
            "opportunities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "initiative": {
                            "type": "string",
                            "description": "e.g. 'Solar integration', 'Electric forklifts', 'Route optimization'",
                        },
                        "description": {"type": "string"},
                        "estimated_impact": {"type": "string", "enum": ["Low", "Medium", "High"]},
                    },
                    "required": ["initiative", "description", "estimated_impact"],
                },
            },
        },
        "required": [
            "emissions_factor_kg_co2_per_kwh",
            "emissions_factor_assumption",
            "waste_assessment",
            "transportation_assessment",
            "opportunities",
        ],
    },
}

SYSTEM_PROMPT = (
    "You are a sustainability consultant. You are given a client's total "
    "energy consumption and production volume, plus supporting "
    "documentation. Estimate a reasonable grid emissions factor (kg CO2 "
    "per kWh) and explain your assumption — you do not have the client's "
    "actual grid mix, so be transparent this is an estimate. Assess waste "
    "and transportation based ONLY on evidence in the documents; if there "
    "is none, say so explicitly rather than inventing detail. Recommend "
    "concrete sustainability initiatives (e.g. solar integration, electric "
    "forklifts, route optimization, predictive energy management) grounded "
    "in the client's actual situation."
)

# Global average grid intensity, kg CO2/kWh — fallback only, used if
# Claude's response doesn't include a usable factor.
DEFAULT_EMISSIONS_FACTOR = 0.475


def generate_sustainability_analysis(
    client, energy_kwh: float, units_produced: float, document_context: str
) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        tools=[SUSTAINABILITY_TOOL],
        tool_choice={"type": "tool", "name": "record_sustainability_analysis"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Total energy consumption: {energy_kwh} kWh\n"
                    f"Total units produced: {units_produced}\n\n"
                    f"Supporting documentation:\n{document_context}"
                ),
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    return {}
