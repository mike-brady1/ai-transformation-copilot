import pandas as pd

REQUIRED_COLUMNS = {
    "machine",
    "planned_production_time_hours",
    "downtime_hours",
    "units_produced",
    "good_units",
    "ideal_cycle_time_seconds",
    "failure_count",
    "energy_kwh",
}


def compute_kpis(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df.copy()
    df["operating_time_hours"] = df["planned_production_time_hours"] - df["downtime_hours"]
    df["availability"] = df["operating_time_hours"] / df["planned_production_time_hours"]
    df["performance"] = (df["ideal_cycle_time_seconds"] * df["units_produced"]) / (
        df["operating_time_hours"] * 3600
    )
    df["quality"] = df["good_units"] / df["units_produced"]
    df["oee"] = df["availability"] * df["performance"] * df["quality"]
    df["mtbf_hours"] = df["operating_time_hours"] / df["failure_count"]
    df["mttr_hours"] = df["downtime_hours"] / df["failure_count"]
    df["energy_per_unit_kwh"] = df["energy_kwh"] / df["units_produced"]
    df["scrap_rate"] = (df["units_produced"] - df["good_units"]) / df["units_produced"]
    return df
