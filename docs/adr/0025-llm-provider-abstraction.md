# ADR 0025: LLM provider abstraction

## Status

Accepted

## Context

M13 needs a provider- and model-neutral way to call LLMs without vendor SDKs
in domain or application layers, without real HTTP integrations yet, and
without changing M0–M12 behavior.

## Decision

- `LlmPort` in ports defines `LlmRequest`, `LlmResponse`, `LlmMessage`,
  `LlmUsage`, and normalized `LlmError` values.
- `LlmProviderKey` and `LlmModelId` are opaque identifiers, not vendor enums.
- Usage metadata includes token counts and optional **provider-reported**
  cost (`LlmReportedCost`). CareerPilot never fabricates currency amounts
  (ADR 0011).
- `CostManagerPort.record_llm_usage` observes completions; failures to
  record must not fail the business operation.
- `LlmProviderRegistry` registers zero or more providers; duplicates and
  unknown lookups are application errors.
- `LlmSettings` (`LLM__*`) holds optional provider, credential, and default
  model configuration without requiring any provider at boot.
- `InvokeLlmUseCase` resolves provider/model defaults and returns structured
  `LlmCompletionResult` values.
- M13 ships only in-process fakes for tests. No OpenRouter/Anthropic/OpenAI
  adapters, no Executive/Planner LLM behavior, and no production prompts.

## Consequences

- M14+ can add infrastructure adapters and semantic matching behind `LlmPort`.
- M12 orchestration remains deterministic until explicitly wired to an LLM
  planner in a later milestone.
