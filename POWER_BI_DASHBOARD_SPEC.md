# Power BI Dashboard Specification

## Dashboard objective

Give operations managers a recurring view of delivery reliability, SLA performance, cancellations, regional variation, and freight-cost exposure.

## Page 1: Executive operations scorecard

Use KPI cards for total orders, delivered orders, cancellation rate, on-time delivery rate, average delivery days, average delay among late orders, and average freight share. Add a monthly on-time delivery trend and a stacked column chart for order status.

## Page 2: Regional performance

Use a filled map or ranked bar chart by customer state. Display delivered orders, on-time rate, average delivery days, average delay, and freight share. Apply a minimum-volume filter so small samples do not dominate the ranking.

## Page 3: SLA and root-cause analysis

Use a scatter chart comparing promised delivery days with actual delivery days. Add a table of late orders grouped by state and a decomposition tree for order status, state, product category, and freight share. Include a slicer for purchase month.

## Suggested measures

```DAX
Orders = DISTINCTCOUNT(orders[order_id])

Delivered Orders = CALCULATE([Orders], orders[order_status] = "delivered")

Cancelled Orders = CALCULATE([Orders], orders[order_status] = "canceled")

Cancellation Rate = DIVIDE([Cancelled Orders], [Orders])

On-Time Delivery Rate =
DIVIDE(
    CALCULATE([Delivered Orders], orders[on_time] = 1),
    [Delivered Orders]
)

Average Delivery Days = AVERAGE(orders[delivery_days])

Average Freight Share = AVERAGE(orders[freight_share_pct])
```

## Design notes

Use blue for on-time performance, red for delays and cancellations, and amber for freight-cost exposure. Display the minimum-volume threshold used for regional comparisons. Add a note that delivery metrics are calculated only for delivered orders and that incomplete timestamps are excluded from time-based measures.
