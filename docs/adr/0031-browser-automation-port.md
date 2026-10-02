# ADR 0031: Browser automation port

## Status

Accepted

## Context

M20 application workflows will need provider-neutral browser control separate
from approvals (M18) and from job/LLM providers. Vendor SDKs must not appear
in domain or application layers.

## Decision

- Define `BrowserAutomationPort` to open sessions and `BrowserSessionPort` for
  navigate, inspect, fill, click, screenshot, and close.
- Use structured DTOs (`BrowserNavigationResult`, `BrowserPageSnapshot`,
  `BrowserInteractionResult`, `BrowserArtifact`) and `BrowserError` with
  retryable classification (`BrowserErrorCode`).
- Ship `FakeBrowserAutomationPort` for contract tests; no real browser in M19.
- M19 does not submit applications or consume approvals; it only defines the
  automation boundary.

## Consequences

- Playwright/Selenium adapters can land in infrastructure later without
  changing domain contracts.
- No HTTP surface in M19; orchestration wiring arrives with M20.
