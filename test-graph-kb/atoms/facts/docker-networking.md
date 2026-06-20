---
id: atoms/facts/docker-networking
type: fact
title: Docker Networking Modes
description: Different network configurations available in Docker
tags: [docker, network, container]
confidence: 0.88
timestamp: 2026-06-20T12:15:00Z
---

Docker Network Types:

- bridge: Default isolated network
- host: Container shares host network
- overlay: Multi-host networking (Swarm)
- macvlan: Container gets MAC address
- none: No network access

Commands:
```bash
docker network create mynet
docker network connect mynet container1
```

Related: [[atoms/methods/docker-compose-configuration]], [[atoms/methods/docker-container-setup]]