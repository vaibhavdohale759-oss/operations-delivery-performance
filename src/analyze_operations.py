from pathlib import Path
from quality_checks import write_quality_report
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGURES = ROOT / "figures"
REPORTS = ROOT / "reports"
FIGURES.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)
sns.set_theme(style="whitegrid", palette="deep")

orders = pd.read_csv(DATA / "olist_orders_dataset.csv")
customers = pd.read_csv(DATA / "olist_customers_dataset.csv")
items = pd.read_csv(DATA / "olist_order_items_dataset.csv")
payments = pd.read_csv(DATA / "olist_order_payments_dataset.csv")

for col in ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]:
    orders[col] = pd.to_datetime(orders[col], errors="coerce")

# One row per order with operational and commercial measures.
order_items = items.groupby("order_id", as_index=False).agg(
    item_count=("order_item_id", "count"),
    product_value=("price", "sum"),
    freight_value=("freight_value", "sum"),
)
order_payments = payments.groupby("order_id", as_index=False).agg(payment_value=("payment_value", "sum"))
base = (orders.merge(customers[["customer_id", "customer_unique_id", "customer_state"]], on="customer_id", how="left")
        .merge(order_items, on="order_id", how="left")
        .merge(order_payments, on="order_id", how="left"))
base["item_count"] = base["item_count"].fillna(0)
base["product_value"] = base["product_value"].fillna(0)
base["freight_value"] = base["freight_value"].fillna(0)
base["payment_value"] = base["payment_value"].fillna(0)
base["delivery_days"] = (base["order_delivered_customer_date"] - base["order_purchase_timestamp"]).dt.total_seconds() / 86400
base["promised_days"] = (base["order_estimated_delivery_date"] - base["order_purchase_timestamp"]).dt.total_seconds() / 86400
base["delay_days"] = (base["order_delivered_customer_date"] - base["order_estimated_delivery_date"]).dt.total_seconds() / 86400
base["on_time"] = (base["delay_days"] <= 0).astype("Int64")
base["freight_share_pct"] = base["freight_value"] / base["payment_value"].replace(0, pd.NA) * 100
base["purchase_month"] = base["order_purchase_timestamp"].dt.to_period("M").astype(str)
base.to_csv(REPORTS / "cleaned_order_operations.csv", index=False)
write_quality_report(base, REPORTS / "data_quality_report.csv", key_column="order_id")

# Operational scope: delivered orders have observed delivery and delay metrics.
delivered = base[base["order_status"] == "delivered"].copy()
summary = {
    "orders_analyzed": len(base),
    "delivered_orders": len(delivered),
    "cancelled_orders": int(base["order_status"].eq("canceled").sum()),
    "cancellation_rate_pct": round(base["order_status"].eq("canceled").mean() * 100, 2),
    "on_time_delivery_rate_pct": round(delivered["on_time"].mean() * 100, 2),
    "late_deliveries": int((delivered["on_time"] == 0).sum()),
    "avg_delivery_days": round(delivered["delivery_days"].mean(), 2),
    "avg_delay_days_late_orders": round(delivered.loc[delivered["delay_days"] > 0, "delay_days"].mean(), 2),
    "avg_freight_share_pct": round(delivered["freight_share_pct"].mean(), 2),
    "total_payment_value": round(base["payment_value"].sum(), 2),
}
pd.DataFrame([summary]).to_csv(REPORTS / "summary_metrics.csv", index=False)

conn = sqlite3.connect(REPORTS / "operations_analysis.sqlite")
base.to_sql("orders", conn, if_exists="replace", index=False)
queries = {
    "monthly_delivery": """
        SELECT purchase_month, COUNT(*) AS delivered_orders,
               ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
               ROUND(AVG(on_time) * 100, 2) AS on_time_rate_pct,
               ROUND(AVG(delay_days), 2) AS avg_delay_days
        FROM orders
        WHERE order_status = 'delivered'
        GROUP BY purchase_month
        ORDER BY purchase_month;
    """,
    "state_performance": """
        SELECT customer_state, COUNT(*) AS delivered_orders,
               ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
               ROUND(AVG(on_time) * 100, 2) AS on_time_rate_pct,
               ROUND(AVG(freight_share_pct), 2) AS avg_freight_share_pct
        FROM orders
        WHERE order_status = 'delivered'
        GROUP BY customer_state
        HAVING COUNT(*) >= 100
        ORDER BY on_time_rate_pct ASC;
    """,
    "status_summary": """
        SELECT order_status, COUNT(*) AS orders,
               ROUND(AVG(payment_value), 2) AS avg_order_value,
               ROUND(AVG(freight_share_pct), 2) AS avg_freight_share_pct
        FROM orders
        GROUP BY order_status
        ORDER BY orders DESC;
    """,
    "late_order_root_causes": """
        SELECT customer_state, order_status,
               COUNT(*) AS orders,
               ROUND(AVG(delay_days), 2) AS avg_delay_days,
               ROUND(AVG(payment_value), 2) AS avg_order_value
        FROM orders
        WHERE order_status = 'delivered' AND delay_days > 0
        GROUP BY customer_state, order_status
        HAVING COUNT(*) >= 100
        ORDER BY avg_delay_days DESC;
    """,
}
for name, query in queries.items():
    pd.read_sql_query(query, conn).to_csv(REPORTS / f"{name}.csv", index=False)
conn.close()

# Chart 1: monthly on-time rate.
monthly = (delivered.groupby("purchase_month", as_index=False)
           .agg(on_time_rate=("on_time", "mean"), delivered_orders=("order_id", "count")))
monthly["on_time_rate"] *= 100
plt.figure(figsize=(11, 5))
sns.lineplot(data=monthly, x="purchase_month", y="on_time_rate", marker="o", color="#2563eb", linewidth=2.5)
plt.title("Monthly on-time delivery rate")
plt.xlabel(""); plt.ylabel("On-time rate (%)"); plt.xticks(rotation=45)
plt.ylim(0, 105)
plt.tight_layout(); plt.savefig(FIGURES / "monthly_on_time_rate.png", dpi=160); plt.close()

# Chart 2: state delivery performance for high-volume states.
state = (delivered.groupby("customer_state", as_index=False)
         .agg(delivered_orders=("order_id", "count"), on_time_rate=("on_time", "mean")))
state = state[state["delivered_orders"] >= 500].sort_values("on_time_rate")
state["on_time_rate"] *= 100
plt.figure(figsize=(9, 6))
sns.barplot(data=state, x="on_time_rate", y="customer_state", color="#dc2626")
plt.title("On-time delivery rate by high-volume customer state")
plt.xlabel("On-time rate (%)"); plt.ylabel("State")
plt.xlim(0, 105)
plt.tight_layout(); plt.savefig(FIGURES / "state_on_time_rate.png", dpi=160); plt.close()

# Chart 3: delivery time versus promised time.
plt.figure(figsize=(8, 5))
sns.scatterplot(data=delivered.sample(min(12000, len(delivered)), random_state=42), x="promised_days", y="delivery_days", alpha=0.25, s=18, color="#7c3aed")
max_value = max(delivered[["promised_days", "delivery_days"]].max())
plt.plot([0, max_value], [0, max_value], linestyle="--", color="#111827", label="On-time boundary")
plt.title("Actual delivery time versus promised delivery time")
plt.xlabel("Promised delivery window (days)"); plt.ylabel("Actual delivery time (days)"); plt.legend()
plt.tight_layout(); plt.savefig(FIGURES / "actual_vs_promised_delivery.png", dpi=160); plt.close()

print(pd.Series(summary))
print("Analysis complete.")
