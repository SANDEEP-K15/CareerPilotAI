# ADR 0003: PostgreSQL and Alembic

## Status

Accepted

## Context

User-owned profiles, jobs, matches, and recommendations need a durable
relational store with migrations and ownership constraints.

## Decision

- PostgreSQL is the system of record.
- Schema changes go through Alembic from M1. No production `create_all`.
- M0 provides Compose Postgres only; no application tables yet.
- Temporal in production should not share CareerPilot's application
  schema. Local Temporal may use Compose auto-setup in M8.

Redis is not introduced until there is a measured need.

## Consequences

- Local development depends on Docker for Postgres from M1 onward.
- M0 Compose can start Postgres; the app does not connect yet.
