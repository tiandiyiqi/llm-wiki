---
id: atoms/methods/nextcloud-deployment
type: method
title: Nextcloud Deployment Guide
description: Complete guide for deploying Nextcloud self-hosted cloud
tags: [nextcloud, cloud, deployment, self-hosted]
confidence: 0.85
timestamp: 2026-06-20T13:05:00Z
---

## Nextcloud Deployment

### Quick Install (Docker)
```bash
docker run -d \
  -p 8080:80 \
  -v nextcloud_data:/var/www/html \
  nextcloud
```

### Production Setup
1. Install prerequisites (PHP, MySQL/MariaDB)
2. Download Nextcloud archive
3. Configure web server (Nginx/Apache)
4. Run installer
5. Configure SSL ([[atoms/methods/ssl-certificate-setup]])

### Integration
- LDAP authentication
- Collabora Online (document editing)
- Nextcloud Talk (video calls)

Related: [[atoms/definitions/web-application]], [[atoms/methods/docker-container-setup]]