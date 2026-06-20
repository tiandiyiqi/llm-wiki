---
id: atoms/methods/logging-configuration
type: method
title: Logging Configuration Guide
description: Setting up structured logging for applications
tags: [logging, observability, debugging]
confidence: 0.85
timestamp: 2026-06-20T11:55:00Z
---

## Structured Logging Setup

### JSON Logging Format
```json
{
  "timestamp": "2026-06-20T12:00:00Z",
  "level": "INFO",
  "message": "User logged in",
  "context": {
    "user_id": 123,
    "ip": "192.168.1.1"
  }
}
```

### Log Levels
- DEBUG: Detailed debugging
- INFO: General information
- WARN: Warning conditions
- ERROR: Error conditions
- FATAL: Critical failures

### Aggregation Tools
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Loki + Grafana
- CloudWatch Logs

Related: [[atoms/methods/monitoring-setup]], [[atoms/facts/log-aggregation]]