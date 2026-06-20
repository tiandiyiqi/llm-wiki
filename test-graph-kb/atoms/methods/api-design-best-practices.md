---
id: atoms/methods/api-design-best-practices
type: method
title: API Design Best Practices
description: Guidelines for designing RESTful APIs
tags: [api, rest, design, best-practices]
confidence: 0.90
timestamp: 2026-06-20T11:20:00Z
---

## REST API Design Guidelines

### URL Structure
- Use nouns: `/users`, `/orders`
- Use plural convention
- Hierarchical: `/users/{id}/orders`

### HTTP Methods
- GET: Read (no body modification)
- POST: Create
- PUT/PATCH: Update
- DELETE: Remove

### Response Codes
- 200: Success
- 201: Created
- 400: Bad request
- 404: Not found
- 500: Server error

### Versioning
- URL: `/api/v1/users`
- Header: `Accept: application/vnd.api.v1+json`

Related: [[atoms/definitions/rest-api]], [[atoms/facts/api-rate-limiting]]