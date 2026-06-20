---
id: atoms/methods/nginx-reverse-proxy
type: method
title: Nginx Reverse Proxy Setup
description: Configuring Nginx as a reverse proxy server
tags: [nginx, proxy, reverse-proxy]
confidence: 0.87
timestamp: 2026-06-20T11:40:00Z
---

## Nginx Reverse Proxy

### Basic Configuration
```nginx
server {
  listen 80;
  server_name example.com;
  
  location /api/ {
    proxy_pass http://localhost:3000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_cache_bypass $http_upgrade;
  }
  
  location /static/ {
    alias /var/www/static/;
  }
}
```

### Benefits
- SSL termination
- Static file serving
- Caching
- Load balancing (see [[atoms/methods/nginx-load-balancer]])

Related: [[atoms/definitions/web-application]], [[atoms/methods/ssl-certificate-setup]]