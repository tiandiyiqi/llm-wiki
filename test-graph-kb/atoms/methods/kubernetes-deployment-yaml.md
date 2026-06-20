---
id: atoms/methods/kubernetes-deployment-yaml
type: method
title: Kubernetes Deployment YAML
description: Creating deployment manifests for Kubernetes
tags: [kubernetes, yaml, deployment]
confidence: 0.80
timestamp: 2026-06-20T11:15:00Z
---

## Kubernetes Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:v1
        ports:
        - containerPort: 3000
---
apiVersion: v1
kind: Service
metadata:
  name: myapp-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 3000
  selector:
    app: myapp
```

Apply: `kubectl apply -f deployment.yaml`

Related: [[atoms/methods/kubernetes-cluster-setup]], [[atoms/definitions/kubernetes]]