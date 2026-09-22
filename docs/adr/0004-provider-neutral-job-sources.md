# ADR 0004: Provider-neutral job sources

## Status

Accepted

## Context

The product goal is reliable personalized job discovery across sources.
Coupling domain or application logic to one vendor would make every new
source a rewrite. Scraping unauthorized sites is out of scope.

## Decision

- Job discovery is a subsystem behind `JobSourcePort` and a registry (M2).
- Domain and application code depend only on the port, registry, and
  canonical Job. They must not import provider SDKs, provider DTOs, or
  provider-specific configuration types.
- Adapters live under `infrastructure/jobsources/`.
- Capabilities (search, detail, pagination, credentials required) are
  declared honestly. Do not fabricate API features.
- The system must run with a provider missing, misconfigured, or down.
- No unauthorized scraping.

## Consequences

- Adding a source is an infrastructure change plus tests and docs.
- Application search/matching/recommendation code stays stable.
- Configuration may list enabled sources; none is structurally required.
