# Benchmark Analysis: granite4:micro-h Qiskit Code Generation

**Run:** `benchmark_20260320_174220.json`
**Overall: 309/360 passed (85.8%)** — 45 prompts × 8 context configurations, up to 10 repair attempts each.

---

## 1. Pass Rate by Context Mode

| Mode | Cases | Passed | Pass% |
|------|-------|--------|-------|
| `none` | 45 | 37 | **82.2%** |
| `grounding` | 45 | 35 | **77.8%** |
| `system_prompt` (all variants) | 135 | 116 | **85.9%** |
| `both` (all variants) | 135 | 121 | **89.6%** |

**Key finding: grounding alone (77.8%) performs *worse* than no context (82.2%).** The ~6300-token QKT rules appear to overwhelm this small model without a system prompt to anchor interpretation.

Per-category pass rates:

| Category | none | grounding | sys_prompt | both |
|----------|------|-----------|-----------|------|
| general | 83% | 67% | 78% | **94%** |
| multi_rule | 50% | 50% | 67% | **83%** |
| qiskit1_imports | **100%** | 63% | 83% | 83% |
| qiskit1_kwargs | 100% | 100% | 100% | 89% |
| qiskit1_methods | 83% | 83% | 89% | **100%** |
| qiskit2_imports | 88% | 88% | **92%** | 83% |
| qiskit2_kwargs | 67% | 100% | 89% | **100%** |
| qiskit2_methods | 67% | 67% | 83% | 83% |

Notable: grounding alone *destroys* `qiskit1_imports` (100% → 63%) but perfectly fixes `qiskit2_kwargs` (67% → 100%). The `both` mode is the most consistent across categories.

---

## 2. System Prompt Variant Comparison

**system_prompt mode (no grounding):**

| Variant | Pass% | Notes |
|---------|-------|-------|
| `chat` | **91.1%** | Best on general (100%), qiskit1_imports (100%), qiskit2_methods (100%) |
| `inline` | **91.1%** | Best on qiskit2_imports (100%), qiskit1_methods (100%) |
| `codegen` | 75.6% | Weakest — collapses on general (50%) and qiskit1_imports (50%) |

**both mode (system_prompt + grounding):**

| Variant | Pass% | Notes |
|---------|-------|-------|
| `inline` | **93.3%** | Highest of any single configuration |
| `codegen` | 91.1% | Strong on qiskit2_methods (100%), general (100%), multi_rule (100%) |
| `chat` | 84.4% | Degrades significantly from 91.1%; collapses on qiskit2_methods (50%) |

Pattern: `inline` and `codegen` benefit from adding grounding; `chat` is hurt by it.

---

## 3. Repair Efficiency

**Across all 309 successful cases:**
- Attempt 1 (no repair needed): **61.8%**
- Attempt 2: 16.5%
- Attempt 3+: **21.7%** — including cases going all the way to attempt 10

**Average attempts for successful cases:**

| Config | Avg attempts | 1st-pass% |
|--------|-------------|-----------|
| `none` | 1.95 | 68% |
| `grounding` | 1.91 | 63% |
| `both/chat` | **1.79** | **74%** — most efficient |
| `both/inline` | 1.93 | 64% |
| `system_prompt/codegen` | 2.21 | 62% |
| `system_prompt/chat` | 2.20 | 61% |
| `both/codegen` | 2.17 | 51% — lowest 1st-pass |
| `system_prompt/inline` | 2.68 | 54% — most repair-dependent |

More context does NOT universally reduce repairs. `both/chat` is most efficient; `system_prompt/inline` is the most repair-dependent despite a decent overall pass rate.

---

## 4. Code Quality Flags (Critical Review)

**94 quality issues found in 309 "successful" cases — affecting 30.4%.**

Quality issues by mode (fraction of successful cases with issues):

| Mode | Issue rate |
|------|-----------|
| `none` | 18.9% |
| `grounding` | **2.9%** |
| `system_prompt` | 19.0% |
| `both` | **5.8%** |
| `both/codegen` | **0.0%** — only config with zero issues |

**Top hallucinated/broken patterns in passing code:**

| Pattern | Occurrences |
|---------|------------|
| `IBMQ.*` (provider removed entirely) | 13 |
| `Gaussian`/`GaussianSquare` from wrong module | 13 |
| `qiskit.aero.*` / `qiskit.Aer` (misspelled, non-existent) | 12 |
| `qiskit.execute` (removed in Qiskit 1.0) | 11 |
| `BasicAer` (removed in Qiskit 1.0) | 6 |
| `QuantumInstance` (deprecated) | 5 |
| Truncated `qisk` import (hallucination) | 5 |

**Selected critical false positives:**

- **`QKT200-pulse-fix-01`** (passes all 8 configs): Every configuration imports pulse shapes from `qiskit.circuit.library` — those classes don't exist there. The validator only checks for `qiskit.pulse.*` deprecated usage, so this entire prompt's results are systematic false positives across all 8 configs.
- **`general-bell-state-01`** (both/inline, 8 attempts): Uses `qiskit.aero.statevector_simulator` (non-existent module) — passes only because the misspelling isn't a QKT rule.
- **`QKT100-generate-01`** (system_prompt/inline, 10 attempts): Uses `QuantumInstance`, `qiskit.aero`, and `qi.execute` — all broken APIs, passes QKT clean.
- **`general-list-fake-backends-01`** (passes 8/8): Only 2 of 8 configs use plausibly correct modern APIs; the rest use `IBMQ.backends()`, `IBMProvider`, or nonexistent `qiskit_ibm_runtime.Runtime()` patterns.

---

## 5. Failure Patterns

**51 failures total (14.2%).**

| QKT Rule | Occurrences in failures | Meaning |
|----------|------------------------|---------|
| QKT100 | 60 | Qiskit 1.x removals (Aer, execute, IBMQ, qiskit.extensions) |
| QKT200 | 25 | qiskit.pulse.* entirely removed in Qiskit 2.0 |
| QKT201 | 5 | c_if, calibrations removed |
| QKT101 | 3 | Qiskit 1.x method removals |
| Syntax errors | 7 | Invalid Python — especially in `grounding` and `both/codegen` |

**Failure rate by category:**

| Category | Failures | Fail rate |
|----------|---------|----------|
| `multi_rule` | 5/16 | **31.2%** — hardest |
| `qiskit2_methods` | 10/48 | 20.8% |
| `qiskit1_imports` | 11/64 | 17.2% |
| `general` | 8/48 | 16.7% |
| `qiskit2_imports` | 8/64 | 12.5% |
| `qiskit1_methods` | 4/48 | 8.3% |
| `qiskit2_kwargs` | 4/48 | 8.3% |
| `qiskit1_kwargs` | 1/24 | 4.2% — easiest |

Pattern: `qiskit1_imports` failures are almost entirely QKT100 recurring — the model keeps re-introducing `qiskit.Aer` or `qiskit.execute` even after correction. Notably, `none` mode has zero `qiskit1_imports` failures; grounding and system prompts actually cause regressions here.

---

## 6. Prompt Difficulty

**10 hardest prompts (passes out of 8 configurations):**

| Prompt ID | Category | Pass/8 |
|-----------|----------|--------|
| `multi-deprecated-basicaer-01` | multi_rule | 3/8 |
| `QKT100-execute-fix-01` | qiskit1_imports | 4/8 |
| `QKT100-generate-01` | qiskit1_imports | 4/8 |
| `QKT200-generate-02` | qiskit2_imports | 4/8 |
| `QKT201-generate-01` | qiskit2_methods | 4/8 |
| `QKT201-generate-02` | qiskit2_methods | 4/8 |
| `general-bell-state-01` | general | 5/8 |
| `general-random-circuit-01` | general | 5/8 |
| `QKT100-opflow-fix-01` | qiskit1_imports | 6/8 |
| `QKT101-generate-01` | qiskit1_methods | 6/8 |

**No prompt failed all 8 configurations.** 17 prompts achieved a perfect 8/8.

The model's conceptual blind spots: `qiskit.execute` removal (QKT100), Qiskit 2.0 pulse API removal (QKT200/QKT201), and multi-rule scenarios.

---

## 7. Recommendation

**Recommended default: `both/codegen`**

| Metric | `both/codegen` | `both/inline` (runner-up) |
|--------|---------------|--------------------------|
| Pass rate | 91.1% | **93.3%** |
| Code quality issues | **0.0%** | 14.3% |
| Avg attempts | 2.17 | 1.93 |
| 1st-pass rate | 51% | 64% |

`both/inline` has the highest raw pass rate (93.3%) but significant hallucination issues in its successes (6 cases with broken APIs). `both/codegen` is the only configuration that produced **zero hallucinated or broken APIs** across all 41 successes — the pass/fail flag is actually trustworthy for this config.

**Trade-offs:**
- `both/codegen` has the lowest 1st-pass rate (51%), so the repair loop is doing more work per case — higher token cost.
- If latency/cost matters more, `both/chat` (avg 1.79 attempts, 74% 1st-pass, 84.4% overall) is a reasonable alternative.
- If grounding is too expensive in tokens, `system_prompt/chat` or `system_prompt/inline` (both 91.1%) are the best grounding-free options, though quality issues rise to ~19–25%.

**Critical caveat:** The entire `QKT200-pulse-fix-*` category appears to be a systematic false positive — the QKT validator doesn't catch wrong-module imports for pulse shapes. If pulse migration is a real use case, the validator coverage needs to be extended before results in this category are meaningful.
