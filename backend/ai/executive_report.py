from backend.ai.digital_maturity import MATURITY_CATEGORIES

EXECUTIVE_SUMMARY_TOOL = {
    "name": "record_executive_summary",
    "description": "Write the narrative sections of a consulting executive report from already-completed findings.",
    "input_schema": {
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": "2-3 paragraph high-level summary for a C-suite audience",
            },
            "current_situation": {
                "type": "string",
                "description": "1-2 paragraph description of the client's current state",
            },
            "key_findings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 bullet-point findings",
            },
            "financial_impact": {
                "type": "string",
                "description": "1-2 paragraph estimate of financial impact, referencing the ROI/cost figures provided",
            },
            "next_steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 concrete next steps",
            },
        },
        "required": [
            "executive_summary",
            "current_situation",
            "key_findings",
            "financial_impact",
            "next_steps",
        ],
    },
}

SYSTEM_PROMPT = (
    "You are a senior strategy consultant writing the narrative sections "
    "of an executive report. You have been given completed findings "
    "(SWOT, digital maturity, roadmap, technology recommendations, KPIs) "
    "for this engagement — some may be missing if that analysis hasn't "
    "been run yet, in which case work with what's provided rather than "
    "inventing the missing pieces. Synthesize what's provided into a "
    "compelling, C-suite-appropriate narrative — do not invent facts not "
    "supported by the findings given."
)

EMPTY_NARRATIVE = {
    "executive_summary": "",
    "current_situation": "",
    "key_findings": [],
    "financial_impact": "",
    "next_steps": [],
}


def generate_executive_narrative(client, findings_text: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=[EXECUTIVE_SUMMARY_TOOL],
        tool_choice={"type": "tool", "name": "record_executive_summary"},
        messages=[{"role": "user", "content": findings_text}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    return EMPTY_NARRATIVE


def format_findings_as_text(
    client_name: str,
    industry: str,
    swot: dict | None,
    roadmap: dict | None,
    maturity: dict | None,
    technology: dict | None,
    kpi: list[dict] | None,
) -> str:
    """Compiles whatever findings are available into one text blob for the
    narrative-generation call. Each section is independently optional —
    the report should work with a partial set, not require every module
    to have been run first."""
    lines = [f"CLIENT: {client_name} ({industry})", ""]

    if swot:
        lines.append("SWOT ANALYSIS:")
        for category in ["strengths", "weaknesses", "opportunities", "threats"]:
            lines.append(f"{category.title()}:")
            for entry in swot.get(category, []):
                lines.append(f"- {entry.get('item')}: {entry.get('explanation')}")
        lines.append("")
    else:
        lines.append("SWOT ANALYSIS: not yet generated.\n")

    if maturity:
        lines.append(f"DIGITAL MATURITY: Overall {maturity.get('overall')}/5")
        for category in MATURITY_CATEGORIES:
            entry = maturity.get(category) or {}
            label = category.replace("_", " ").title()
            lines.append(f"- {label}: {entry.get('score')}/5 — {entry.get('justification')}")
        lines.append("")
    else:
        lines.append("DIGITAL MATURITY: not yet generated.\n")

    if roadmap:
        lines.append("ROADMAP:")
        for horizon, label in [
            ("quick_wins", "Quick Wins"),
            ("medium_term", "Medium-Term"),
            ("long_term", "Long-Term"),
        ]:
            for item in roadmap.get(horizon, []):
                lines.append(
                    f"- [{label}] {item.get('initiative')} "
                    f"(Cost: {item.get('estimated_cost')}, ROI: {item.get('expected_return')})"
                )
        lines.append("")
    else:
        lines.append("ROADMAP: not yet generated.\n")

    if technology:
        lines.append("TECHNOLOGY RECOMMENDATIONS:")
        for rec in technology.get("recommendations", []):
            lines.append(
                f"- {rec.get('problem')} -> {rec.get('recommendation')} "
                f"via {rec.get('platform')} (ROI: {rec.get('expected_return')})"
            )
        lines.append("")
    else:
        lines.append("TECHNOLOGY RECOMMENDATIONS: not yet generated.\n")

    if kpi:
        lines.append("KPI SUMMARY:")
        for row in kpi:
            lines.append(
                f"- {row.get('machine')}: OEE {row.get('oee')}, "
                f"MTBF {row.get('mtbf_hours')}h, MTTR {row.get('mttr_hours')}h"
            )
        lines.append("")
    else:
        lines.append("KPI DATA: not yet generated.\n")

    return "\n".join(lines)
