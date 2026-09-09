-- SQLite-ready queries for the operations and delivery project.

-- 1. Executive delivery KPIs
SELECT
    COUNT(*) AS delivered_orders,
    ROUND(AVG(on_time) * 100, 2) AS on_time_rate_pct,
    ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
    ROUND(AVG(CASE WHEN delay_days > 0 THEN delay_days END), 2) AS avg_delay_days_late_orders,
    ROUND(AVG(freight_share_pct), 2) AS avg_freight_share_pct
FROM orders
WHERE order_status = 'delivered';

-- 2. Monthly delivery performance
SELECT purchase_month,
       COUNT(*) AS delivered_orders,
       ROUND(AVG(on_time) * 100, 2) AS on_time_rate_pct,
       ROUND(AVG(delivery_days), 2) AS avg_delivery_days
FROM orders
WHERE order_status = 'delivered'
GROUP BY purchase_month
ORDER BY purchase_month;

-- 3. High-volume regional performance
SELECT customer_state,
       COUNT(*) AS delivered_orders,
       ROUND(AVG(on_time) * 100, 2) AS on_time_rate_pct,
       ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
       ROUND(AVG(freight_share_pct), 2) AS avg_freight_share_pct
FROM orders
WHERE order_status = 'delivered'
GROUP BY customer_state
HAVING COUNT(*) >= 100
ORDER BY on_time_rate_pct ASC;

-- 4. Cancellation and order-status overview
SELECT order_status,
       COUNT(*) AS orders,
       ROUND(AVG(payment_value), 2) AS avg_order_value
FROM orders
GROUP BY order_status
ORDER BY orders DESC;

-- 5. Late-delivery root-cause prioritization by state
SELECT customer_state,
       COUNT(*) AS late_orders,
       ROUND(AVG(delay_days), 2) AS avg_delay_days,
       ROUND(AVG(payment_value), 2) AS avg_order_value
FROM orders
WHERE order_status = 'delivered' AND delay_days > 0
GROUP BY customer_state
HAVING COUNT(*) >= 100
ORDER BY avg_delay_days DESC;

-- Advanced SQL: rolling three-month on-time performance.
WITH monthly AS (
    SELECT purchase_month, AVG(on_time) * 100 AS on_time_rate_pct
    FROM orders
    WHERE order_status = 'delivered'
    GROUP BY purchase_month
)
SELECT purchase_month, ROUND(on_time_rate_pct, 2) AS on_time_rate_pct,
       ROUND(AVG(on_time_rate_pct) OVER (ORDER BY purchase_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_3_month_rate_pct,
       ROUND(on_time_rate_pct - LAG(on_time_rate_pct) OVER (ORDER BY purchase_month), 2) AS month_over_month_change_pct
FROM monthly
ORDER BY purchase_month;
