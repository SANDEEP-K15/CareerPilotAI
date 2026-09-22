# ADR 0008: Hermes is a client of the API

## Status

Accepted

## Context

Hermes is an external interface, not CareerPilot. Core logic in Hermes
would prevent a web/CLI/API-only deployment.

## Decision

- CareerPilot owns domain, persistence, workflows, and agents.
- Hermes (and Telegram) communicate only through stable `/api/v1` APIs.
- No Hermes imports in `domain`, `application`, or `ports`.
- Hermes integration is M15. Until then, HTTP is the contract.
- CareerPilot remains fully functional if Hermes is removed.

## Consequences

- Client-specific identity (Telegram user id) is a link on a User, not
  the User primary key.
- Notification adapters are infrastructure, not Hermes business rules.
