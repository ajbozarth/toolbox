# Benchmark Analysis Summary
**Run:** `benchmark_20260320_174220.json` — 45 prompts × 8 configurations = 360 cases
**Model:** `granite4:micro-h` | **Overall:** 309/360 passed (85.8%)
**Analyses:** Claude, Bob (IBM), Copilot, Grok

---

## Consensus Findings (all 4 agents agree)

1. **Grounding alone is the worst configuration (77.8%)** — worse than no context at all (82.2%). The ~6,300-token QKT rule dump overwhelms the small model without a system prompt to anchor interpretation.

2. **`inline` is the best system prompt variant** — the short, condensed prompt (22 lines) consistently outperforms `chat` (83 lines) and `codegen` (227 lines). Bigger is not better for this model size.

3. **`success: true` does not mean runnable code.** Every agent flagged this as the critical limitation. The QKT validator only checks for deprecated API usage — hallucinated but non-deprecated APIs pass cleanly.

4. **The repair loop helps but has a ceiling.** Most passes occur within 1–3 attempts, but several prompts hit the 10-attempt budget repeatedly regardless of configuration.

---

## Per-configuration results

| Configuration | Pass rate |
|---|---|
| `both/inline` | **93.3%** |
| `both/codegen` | 91.1% |
| `system_prompt/inline` | 91.1% |
| `system_prompt/chat` | 91.1% |
| `both/chat` | 84.4% |
| `none` | 82.2% |
| `system_prompt/codegen` | 75.6% |
| `grounding` | 77.8% |

---

## Key Disagreement: Does grounding help or hurt?

This is the sharpest split across the analyses:

| Agent | Recommendation | Reasoning |
|---|---|---|
| **Grok** | `both/inline` | Inline expertise prevents model from being overwhelmed by grounding; synergistic |
| **Bob** | `both/inline` | Best pass rate; synergistic combination |
| **Claude** | `both/codegen` | Only config with 0% hallucination rate in passing cases, despite lower raw pass rate |
| **Copilot** | `system_prompt/inline` | Grounding always hurts; avoid it entirely for this model size |

The disagreement hinges on whether you optimize for **raw QKT pass rate** (`both/inline`) or **code quality of passing cases** (`both/codegen` or `system_prompt/inline`). Given that pass rate is already partially misleading due to false positives, this distinction matters.

---

## Hardest prompts

All agents flagged the same prompts as consistently difficult:

| Prompt | Pass/8 | Why |
|---|---|---|
| `multi-deprecated-basicaer-01` | 3/8 | Requires simultaneous fix of 3 deprecated patterns |
| `QKT100-execute-fix-01` | 4/8 | `execute()` removal + Aer migration together |
| `QKT100-generate-01` | 4/8 | Model keeps reintroducing `qiskit.Aer`/`qiskit.execute` |
| `QKT200/201-generate-*` | 4/8 | Qiskit 2.0 pulse API entirely removed |

No prompt failed all 8 configurations — every prompt had at least one successful config.

---

## False positive concern (Claude only)

Claude flagged a systematic issue: **`QKT200-pulse-fix-*` prompts appear to be false positives across all configurations.** The validator catches `qiskit.pulse.*` deprecated imports but not incorrect replacement imports (e.g. pulse shapes imported from `qiskit.circuit.library` where they don't exist). If pulse migration is a real use case, validator coverage needs to be extended.

---

## Recommended default

**`both/inline`** for highest pass rate. **`both/codegen`** if code quality of passing cases matters more than raw numbers (0% hallucination rate in Claude's analysis).

Either way: **avoid `grounding` alone** and **avoid `system_prompt/codegen`** (worst of each group).

---

## Next steps (cross-agent consensus)

1. **Add execution-based validation** — running generated code is the only reliable quality signal. All 4 agents raised this independently.
2. **Re-run with `max_repair_attempts=5`** to isolate whether context actually helps or the repair loop is masking it (the 82.2% `none` baseline is suspiciously high).
3. **Investigate grounding format** — the raw rule dump may not be the right format for a small model; examples-based grounding or a condensed subset might work better.
4. **Larger model comparison** — test the same benchmark with `granite4:small-h` or the Qiskit-specialized model to see if model size changes which configuration wins.
