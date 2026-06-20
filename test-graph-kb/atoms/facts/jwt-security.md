---
id: atoms/facts/jwt-security
type: fact
title: JWT Security Considerations
description: Security best practices for JWT tokens
tags: [jwt, security, token, authentication]
confidence: 0.92
timestamp: 2026-06-20T12:10:00Z
---

JWT Security Best Practices:

- Use short expiration times (15-30 minutes)
- Store refresh tokens securely
- Never store JWTs in localStorage (use httpOnly cookies)
- Always validate signature
- Use strong signing algorithm (RS256 > HS256)
- Include only minimal claims

Attack vectors: token theft, replay attacks

Related: [[atoms/definitions/authentication]], [[atoms/methods/oauth-integration]]