---
id: atoms/methods/nginx-load-balancer
type: method
title: Nginx Load Balancer Configuration
description: Setting up Nginx as a load balancer for web applications
tags: [nginx, load-balancer, proxy]
confidence: 0.85
timestamp: 2026-06-20T11:35:00Z
---

## Nginx Load Balancing

### Configuration
```nginx
upstream backend {
  least_conn;
  server backend1:3000 weight=5;
  server backend2:3000;
  server backend3:3000 backup;
}

server {
  listen 80;
  
  location / {
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }
}
```

### Strategies
- round-robin (default)
- least_conn
- ip_hash
- weight-based

Related: [[atoms/definitions/load-balancing]], [[atoms/methods/nginx-reverse-proxy]]