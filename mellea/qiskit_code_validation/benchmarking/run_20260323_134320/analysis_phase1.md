# Phase 1 Benchmark Analysis
**Run:** `run_20260323_134320`
**Model:** `granite4:micro-h`
**Date:** 2026-03-23
**Total runs:** 315 (45 prompts × 7 combinations)
**Overall pass rate:** 296/315 (94.0%)

---

## Results Summary

### Pass rate by combination

| Context / Prompt / Strategy | Pass | Total | Rate | 1st-attempt | Avg attempts | Avg time |
|---|---:|---:|---:|---:|---:|---:|
| `none/none/repair_template` | 40 | 45 | 88.9% | 66.7% | 2.40 | 108.8s |
| `system_prompt/inline/repair_template` | 41 | 45 | 91.1% | 80.0% | 1.91 | 81.5s |
| `system_prompt/inline/multi_turn` | 44 | 45 | **97.8%** | 80.0% | 1.51 | 50.0s |
| `system_prompt/qiskit_short/repair_template` | 41 | 45 | 91.1% | 75.6% | 2.11 | 96.3s |
| **`system_prompt/qiskit_short/multi_turn`** | **44** | **45** | **97.8%** | **91.1%** | **1.36** | **40.6s** |
| `system_prompt/qiskit/repair_template` | 42 | 45 | 93.3% | 77.8% | 1.80 | 81.5s |
| `system_prompt/qiskit/multi_turn` | 44 | 45 | **97.8%** | 86.7% | 1.33 | 42.0s |

**Winner: `system_prompt/qiskit_short/multi_turn`** — ties for highest pass rate (97.8%), highest first-attempt rate (91.1%), second-lowest avg attempts (1.36), and fastest average time (40.6s).

---

## Key Findings

### 1. MultiTurn consistently beats RepairTemplate

Across all three system prompts, MultiTurnStrategy outperforms RepairTemplateStrategy significantly on final pass rate (97.8% vs 91.1–93.3%) and substantially on efficiency (avg attempts 1.33–1.51 vs 1.80–2.11).

| Prompt | RT pass | MT pass | RT 1st-att | MT 1st-att | RT avg att | MT avg att |
|---|---:|---:|---:|---:|---:|---:|
| `inline` | 91.1% | 97.8% | 80.0% | 80.0% | 1.91 | 1.51 |
| `qiskit_short` | 91.1% | 97.8% | 75.6% | **91.1%** | 2.11 | 1.36 |
| `qiskit` | 93.3% | 97.8% | 77.8% | 86.7% | 1.80 | 1.33 |

**This contradicts the coworker's finding** that RepairTemplate edges out MultiTurn. Their benchmark used the Qiskit-specialized model; our result is on micro-h. This is consistent with the architectural explanation: RepairTemplate appends feedback to the instruction (system-side), which may suit a model already well-trained on Qiskit. MultiTurn adds feedback as a new user message, which appears more effective for a smaller general model where an explicit conversational correction is easier to act on.

### 2. `qiskit_short` is the best system prompt

With MultiTurn, all three prompts reach 97.8% final pass rate — but `qiskit_short` achieves the highest first-attempt rate (91.1% vs 80.0% for `inline` and 86.7% for `qiskit`). This means the model needs fewer repairs when given the short Qiskit prompt. The full `qiskit` prompt likely adds noise from the error mitigation code blocks; `qiskit_short` keeps only the core directives.

With RepairTemplate, `qiskit` (93.3%) edges out `inline` and `qiskit_short` (both 91.1%) — but since MultiTurn is the clear winner for this model, `qiskit_short` + MultiTurn is the recommended configuration.

### 3. System prompt matters, but strategy matters more

The pass rate gap between no context (88.9%) and best context (97.8%) is 8.9 points. The gap between RepairTemplate and MultiTurn within the same system prompt is consistently 6–7 points. Strategy choice is nearly as impactful as context presence.

### 4. One prompt fails regardless of configuration

`QKT100-execute-fix-01` fails in all 7 combinations — the only prompt to do so. Three others fail across multiple combinations:

| Prompt | Combinations failed |
|---|---:|
| `QKT100-execute-fix-01` | 7/7 |
| `QKT100-generate-01` | 4/7 |
| `QKT101-qasm-fix-01` | 4/7 |
| `QKT200-generate-01` | 3/7 |

These are likely genuinely hard prompts for this model size, not configuration-sensitive failures.

---

## Recommendation

**Winning config: `system_prompt/qiskit_short/multi_turn`**

- Highest first-attempt pass rate (91.1%) — least reliance on repair loop
- Tied best final pass rate (97.8%)
- Fastest average run time (40.6s) — shorter prompt + fewer repairs
- Simpler prompt is easier to maintain and less likely to degrade with model updates

Use `system-prompt-qiskit-short.md` as the system prompt going forward. The full `system-prompt-qiskit-stripped.md` can be kept in `benchmarking/` for reference.

---

## Comparison to Previous Benchmark (Phase 0)

| Config | Phase 0 rate | Phase 1 rate |
|---|---:|---:|
| `none/none` (baseline) | 82.2% | 88.9% |
| `system_prompt/inline/repair_template` (prev best) | 91.1% | 91.1% |
| **`system_prompt/qiskit_short/multi_turn` (new winner)** | — | **97.8%** |

The baseline improved (82.2% → 88.9%) possibly due to the strategy now being `RepairTemplate` explicitly vs whatever default was used previously. The new winner adds 6.7 points over the previous best configuration.

---

## Next Step

Code quality review (GOOD/SUSPECT/BAD) on a sample of `system_prompt/qiskit_short/multi_turn` passing results to confirm the 97.8% pass rate is not inflated by false positives, before proceeding to Phase 2.

---

## Changes Applied Based on This Analysis

- **System prompt inlined:** `system-prompt-qiskit-short.md` content moved inline into `qiskit_code_validation.py` as `QISKIT_SYSTEM_PROMPT`. The file is kept in `benchmarking/prompts/` for reference.
- **Default demo prompt updated:** Changed from the deprecated `BasicAer + execute` snippet (`multi-deprecated-basicaer-01`) to `general-bell-runtime-01`:
  ```python
  from qiskit import QuantumCircuit
  from qiskit_ibm_runtime import QiskitRuntimeService

  # define a Bell circuit and run it in ibm_salamanca using QiskitRuntimeService
  ```
  Rationale: the old default passed on attempt 1 with the winning config, making the repair loop invisible. `general-bell-runtime-01` is a realistic prompt that needs 3 attempts under `RepairTemplateStrategy`, demonstrating IVR value. All non-QKT prompts pass reliably with both strategies under `qiskit_short`.

### Post-selection finding: general prompt output quality (micro-h)

After selecting `general-bell-runtime-01` as the default, a follow-up review compared the generated code for all 6 general prompts under `system_prompt/qiskit_short/repair_template`. **QKT pass ("success") does not imply usable code for any of them:**

| Prompt | Attempts | Output quality |
|---|---|---|
| `general-bell-state-01` | 1 | Hallucinated — `Manager()` / `manager.manager`, no Bell circuit |
| `general-list-fake-backends-01` | 1 | Hallucinated — `IBMConnection` doesn't exist in Qiskit |
| `general-random-circuit-01` | 1 | Wrong — manually builds uniform H circuit, ignores `random_circuit()` |
| `general-entanglement-circuit-01` | 1 | Partially correct — CNOT chain without initial Hadamard; not entangled from \|0⟩ |
| `general-runtime-estimator-01` | 1 | Ignored prompt — detailed 4-step spec (Session, Estimator, SparsePauliOp) discarded; returned generic circuit function |
| `general-bell-runtime-01` | 3 | Hallucinated — apology preamble, never runs circuit, calls undefined `main()`, closing comment says "prints Hello World" |

**Conclusion:** micro-h cannot reliably produce correct code for open-ended "generate" prompts. The default prompt choice shows the IVR repair loop working (3 attempts → QKT pass), but the resulting code would fail at runtime. This is consistent with Phase 2's finding that micro-h achieves only 4.2% check() pass rate on QHE. The default prompt is appropriate for demonstrating QKT-based IVR mechanics, but the generated output should not be presented as an example of correct Qiskit code.
