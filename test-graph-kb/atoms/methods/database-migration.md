---
id: atoms/methods/database-migration
type: method
title: Database Migration Strategy
description: Best practices for database schema migrations
tags: [database, migration, schema, sql]
confidence: 0.85
timestamp: 2026-06-20T11:25:00Z
---

## Database Migration Best Practices

### Principles
1. Always use version-controlled migration scripts
2. Test migrations on staging first
3. Include rollback scripts
4. Never modify existing migrations

### Example (PostgreSQL)
```sql
-- Migration: Add user roles
-- Version: 003

CREATE TABLE user_roles (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  role VARCHAR(50) NOT NULL
);

-- Rollback
DROP TABLE user_roles;
```

### Tools
- Django migrations
- Rails migrations
- Flyway (Java)
- Prisma (Node.js)

Related: [[atoms/definitions/database]], [[atoms/facts/postgresql-features]]