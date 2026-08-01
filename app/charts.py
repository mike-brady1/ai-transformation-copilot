import io

import matplotlib

matplotlib.use("Agg")  # no display backend needed — we only ever save to bytes
import matplotlib.pyplot as plt

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


def maturity_chart_png(maturity: dict) -> bytes:
    labels = [c.replace("_", " ").title() for c in MATURITY_CATEGORIES]
    scores = [(maturity.get(c) or {}).get("score", 0) for c in MATURITY_CATEGORIES]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(labels, scores, color="#4C78A8")
    ax.set_ylim(0, 5)
    ax.set_ylabel("Score (1-5)")
    ax.set_title("Digital Maturity by Dimension")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()


def kpi_oee_chart_png(kpi: list[dict]) -> bytes:
    machines = [row.get("machine") for row in kpi]
    oee_values = [(row.get("oee") or 0) * 100 for row in kpi]

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(machines, oee_values, color="#F58518")
    ax.set_ylim(0, 100)
    ax.set_ylabel("OEE (%)")
    ax.set_title("Overall Equipment Effectiveness by Machine")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()
