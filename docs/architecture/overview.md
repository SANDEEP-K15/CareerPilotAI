# Architecture overview

CareerPilot AI is the career intelligence backend. Clients (REST, web,
CLI, Hermes/Telegram, future surfaces) call versioned HTTP APIs. Hermes
must never own domain logic. Removing Hermes must not disable the product.

## Layering

Dependencies point inward only.

```
apps / api / worker
        ↓
application (use cases)
        ↓
domain  ←  ports (interfaces)
        ↑
infrastructure (adapters: job sources, Postgres, Temporal, LLM, …)
```

- **domain** — canonical Job, profile, recommendation, errors. No
  frameworks. No provider schemas.
- **application** — use cases. Talks to ports. Provider-neutral.
- **ports** — `JobSourcePort` (M2), repositories, later LLM, workflows,
  cost, notifications, browser.
- **infrastructure** — the only place vendor SDKs and HTTP provider
  clients live.
- **api / worker** — delivery. Thin.

## Job discovery

Job discovery is a subsystem, not a scraper and not a single vendor.

```
Use case → JobSourceRegistry → N adapters implementing JobSourcePort
                ↓
         normalized errors + RawJob
                ↓
         Normalizer → canonical Job
                ↓
         deterministic dedupe / filter / match / rank
```

No job provider is a platform dependency. The registry must operate when
zero, one, or many adapters are configured. One unavailable source must
not abort the whole search when others succeed (from M5/M8).

**Adzuna** is the first *validation* adapter (M3). It is not the product
goal, not a required runtime, and not allowed to leak into domain or
application code.

AI agents (M9+) orchestrate reasoning through application services. They
do not implement SQL, provider HTTP, or Temporal clients.

## First production slice (M1–M8)

User/profile foundation, job source abstraction, at least one real
adapter for validation, normalize, persist, dedupe, search API,
deterministic matching, daily recommendation workflow, tests,
observability, docs.

## Durable work

Temporal is the workflow engine from M8. Workflows stay deterministic;
I/O lives in activities. An in-process event bus is not a substitute.

## Safety

Submitting applications, sending recruiter messages, or changing
externally visible data requires durable human approval (M18+). LLM
output cannot grant permissions or execute privileged actions.

## Related documents

- [Implementation plan](../implementation-plan.md)
- [ADR index](../adr/README.md)
