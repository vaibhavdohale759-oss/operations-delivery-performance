from __future__ import annotations

from pathlib import Path
import pandas as pd

def profile_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a compact, machine-readable data-quality profile."""
    duplicate_counts = pd.Series(
        {column: int(df[column].duplicated(keep="first").sum()) for column in df.columns},
        dtype="int64",
    )
    return pd.DataFrame({
        "column": df.columns,
        "dtype": [str(dtype) for dtype in df.dtypes],
        "row_count": len(df),
        "missing_count": [int(value) for value in df.isna().sum()],
        "unique_count": [int(value) for value in df.nunique(dropna=True)],
        "duplicate_count": [int(duplicate_counts[column]) for column in df.columns],
    })

def write_quality_report(df: pd.DataFrame, output_path: Path, key_column: str | None = None) -> None:
    report = profile_dataframe(df)
    if key_column and key_column in df.columns:
        duplicate_keys = int(df[key_column].duplicated().sum())
        report["duplicate_key_count"] = duplicate_keys
    report.to_csv(output_path, index=False)

def safe_rate(numerator: float, denominator: float) -> float:
    """Return a ratio without allowing a zero denominator to create NaN/inf."""
    return float(numerator / denominator) if denominator else 0.0

def roi_proxy(responses: float, response_value: float, customers: float, contact_cost: float) -> float:
    """Calculate a transparent ROI proxy from provided assumptions."""
    cost = customers * contact_cost
    return ((responses * response_value) - cost) / cost if cost else 0.0
