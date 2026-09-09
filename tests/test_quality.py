import pandas as pd
from src.quality_checks import profile_dataframe, safe_rate

def test_delivery_quality_profile_detects_duplicates():
    df = pd.DataFrame({"order_id": ["a", "a", "b"], "delay_days": [0, 2, None]})
    report = profile_dataframe(df)
    assert int(report.loc[report["column"] == "order_id", "duplicate_count"].iloc[0]) == 1
    assert int(report.loc[report["column"] == "delay_days", "missing_count"].iloc[0]) == 1

def test_safe_rate_for_on_time_orders():
    assert safe_rate(8, 10) == 0.8
    assert safe_rate(0, 0) == 0.0
