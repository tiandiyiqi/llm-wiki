---
id: atoms/facts/prometheus-metrics
type: fact
title: Prometheus Metric Types
description: Four core metric types in Prometheus
tags: [prometheus, metrics, monitoring]
confidence: 0.90
timestamp: 2026-06-20T12:25:00Z
---

Prometheus Metric Types:

- Counter: Cumulative value (requests_total)
- Gauge: Point-in-time value (memory_usage)
- Histogram: Distribution (request_duration)
- Summary: Similar to histogram with quantiles

Query examples:
```promql
rate(http_requests_total[5m])
avg(node_memory_usage_bytes)
histogram_quantile(0.95, request_duration)
```

Related: [[atoms/methods/monitoring-setup]]