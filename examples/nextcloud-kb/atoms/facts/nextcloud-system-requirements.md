---
type: fact
title: Nextcloud System Requirements
description: Minimum and recommended system requirements for Nextcloud server
resource: https://docs.nextcloud.com/server/latest/admin_manual/installation/system_requirements.html
tags:
  - requirements
  - nextcloud
  - server
timestamp: 2026-06-18T10:30:00Z
---

# Nextcloud System Requirements

## Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| Database | MySQL/MariaDB, PostgreSQL, or Oracle |
| Web Server | Apache or Nginx |
| PHP | 8.0+ (8.1+ recommended) |
| Memory | 512 MB minimum |
| Storage | Depends on user data |

## Recommended Requirements

| Component | Recommendation |
|-----------|----------------|
| Database | MariaDB 10.3+ or PostgreSQL 12+ |
| PHP | 8.2+ with required extensions |
| Memory | 4 GB+ |
| Storage | SSD with enough space for user data + 10% |

## Required PHP Extensions

- ctype
- dom
- fileinfo
- gd
- iconv (recommended)
- intl
- json
- mbstring
- openssl
- pcre
- PDO
- session
- SimpleXML
- XMLWriter
- zip
- zlib

## Related

- [[nextcloud-installation-ubuntu-apache]] - Installation guide

# Citations

[1] [Nextcloud System Requirements](https://docs.nextcloud.com/server/latest/admin_manual/installation/system_requirements.html)