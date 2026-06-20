---
id: atoms/facts/api-rate-limiting
type: fact
title: API Rate Limiting Strategies
description: Common rate limiting approaches for APIs
tags: [api, rate-limit, throttling]
confidence: 0.85
timestamp: 2026-06-20T12:20:00Z
---

Rate Limiting Algorithms:

- Token bucket: Fixed tokens refill over time
- Sliding window: Smooth request distribution
- Fixed window: Count requests per time window
- Leaky bucket: Constant outflow rate

Implementation:
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;
```

Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`

Related: [[atoms/methods/api-design-best-practices]], [[atoms/definitions/rest-api]]