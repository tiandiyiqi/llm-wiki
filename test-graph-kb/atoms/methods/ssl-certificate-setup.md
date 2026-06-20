---
id: atoms/methods/ssl-certificate-setup
type: method
title: SSL Certificate Setup with Let's Encrypt
description: Setting up free SSL certificates using Certbot
tags: [ssl, tls, security, certbot]
confidence: 0.90
timestamp: 2026-06-20T11:45:00Z
---

## SSL Certificate Setup

### Using Certbot
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d example.com -d www.example.com

# Auto-renewal
sudo certbot renew --dry-run
```

### Nginx SSL Config
```nginx
server {
  listen 443 ssl http2;
  ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
  
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256;
}
```

Related: [[atoms/methods/nginx-reverse-proxy]], [[atoms/facts/https-security]]