---
id: atoms/methods/monitoring-setup
type: method
title: Application Monitoring Setup
description: Setting up Prometheus and Grafana for application monitoring
tags: [monitoring, prometheus, grafana, observability]
confidence: 0.83
timestamp: 2026-06-20T11:50:00Z
---

## Monitoring Stack Setup

### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'app'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
```

### Grafana Dashboards
- Import standard dashboards
- Create custom visualizations
- Set up alerting rules

Key metrics: CPU, memory, request latency, error rate

Related: [[atoms/facts/prometheus-metrics]], [[atoms/methods/logging-configuration]]