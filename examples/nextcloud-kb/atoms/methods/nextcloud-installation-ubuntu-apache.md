---
type: method
title: Nextcloud Ubuntu Apache Installation
description: Standard installation process for Nextcloud on Ubuntu using Apache web server
resource: https://docs.nextcloud.com/server/latest/admin_manual/installation/
tags:
  - installation
  - ubuntu
  - apache
  - nextcloud
timestamp: 2026-06-18T10:00:00Z
---

# Nextcloud Ubuntu Apache Installation Guide

## Overview

This guide covers the standard installation process for Nextcloud on Ubuntu Server using Apache as the web server.

## Prerequisites

- Ubuntu Server 22.04 or later
- Apache 2.4+
- PHP 8.0+
- MySQL/MariaDB or PostgreSQL
- root or sudo access

## Installation Steps

### 1. Install Apache and PHP

```bash
sudo apt update
sudo apt install apache2 libapache2-mod-php
sudo apt install php php-gd php-mysql php-curl php-mbstring php-intl
sudo apt install php-gmp php-bcmath php-xml php-imagick php-zip
```

### 2. Configure Apache

Enable required modules:

```bash
sudo a2enmod rewrite
sudo a2enmod headers
sudo a2enmod env
sudo a2enmod dir
sudo a2enmod mime
```

### 3. Download Nextcloud

```bash
cd /tmp
wget https://download.nextcloud.com/server/releases/latest.tar.bz2
tar -xjf latest.tar.bz2
sudo cp -r nextcloud /var/www/
```

### 4. Set Permissions

```bash
sudo chown -R www-data:www-data /var/www/nextcloud
sudo chmod -R 755 /var/www/nextcloud
```

## Related

- [[nextcloud-system-requirements]] - System requirements
- [[nextcloud-config-php-extensions]] - PHP extension configuration

# Citations

[1] [Nextcloud Official Documentation](https://docs.nextcloud.com/server/latest/admin_manual/installation/)
[2] [Ubuntu Server Guide](https://ubuntu.com/tutorials/install-and-configure-nextcloud#1-overview)
