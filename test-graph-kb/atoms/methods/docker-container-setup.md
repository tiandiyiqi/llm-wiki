---
id: atoms/methods/docker-container-setup
type: method
title: Docker Container Setup
description: Steps to create and run Docker containers for applications
tags: [docker, container, deployment]
confidence: 0.88
timestamp: 2026-06-20T11:00:00Z
---

## Docker Container Setup Guide

### Prerequisites
- Install Docker Engine
- Verify installation: `docker --version`

### Steps

1. **Create Dockerfile**
   ```dockerfile
   FROM node:18-alpine
   WORKDIR /app
   COPY package*.json ./
   RUN npm install
   COPY . .
   CMD ["npm", "start"]
   ```

2. **Build Image**
   ```bash
   docker build -t myapp:v1 .
   ```

3. **Run Container**
   ```bash
   docker run -d -p 3000:3000 myapp:v1
   ```

Related: [[atoms/definitions/containerization]], [[atoms/methods/docker-compose-configuration]]