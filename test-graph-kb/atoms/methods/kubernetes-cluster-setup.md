---
id: atoms/methods/kubernetes-cluster-setup
type: method
title: Kubernetes Cluster Setup
description: Setting up a local or production Kubernetes cluster
tags: [kubernetes, k8s, cluster, minikube]
confidence: 0.82
timestamp: 2026-06-20T11:10:00Z
---

## Kubernetes Setup Guide

### Local Development (Minikube)
```bash
# Install minikube
brew install minikube

# Start cluster
minikube start

# Verify
kubectl cluster-info
```

### Production Setup
Use managed services:
- AWS EKS
- Google GKE
- Azure AKS

Related: [[atoms/definitions/kubernetes]], [[atoms/methods/kubernetes-deployment-yaml]]