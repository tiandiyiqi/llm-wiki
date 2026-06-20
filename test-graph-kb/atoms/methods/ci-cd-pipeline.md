---
id: atoms/methods/ci-cd-pipeline
type: method
title: CI/CD Pipeline Setup
description: Setting up continuous integration and deployment pipelines
tags: [ci-cd, automation, devops, github-actions]
confidence: 0.88
timestamp: 2026-06-20T12:00:00Z
---

## CI/CD Pipeline with GitHub Actions

### Workflow Example
```yaml
name: Deploy Pipeline

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm install
      - run: npm test
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: docker build -t app:v1 .
      - run: docker push registry/app:v1
```

### Stages
1. Build
2. Test
3. Security scan
4. Deploy to staging
5. Deploy to production

Related: [[atoms/definitions/containerization]], [[atoms/methods/docker-container-setup]]