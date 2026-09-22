# Evaluation

**NOT IMPLEMENTED** in M0.

This tree is for AI quality evaluation, which is separate from
deterministic unit and integration tests.

| Path | Future purpose |
|---|---|
| `agent_tests/` | Agent contract and behavior evaluations |
| `prompt_regression/` | Prompt snapshot / structured-output regression |
| `benchmarks/` | Relevance, ranking consistency, latency, tokens, cost |

Live provider evaluations are opt-in and credential-dependent. The default
CI suite must not require paid APIs.

Do not treat passing `pytest` as evidence of ranking or explanation quality.
