# Phase 2 — Qiskit Model QKT Analysis
**Runs:** `run_20260321_103850` (none/none baseline) + `run_20260324_145820` (3 new combos)
**Model:** `hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest`
**Date:** 2026-03-24
**Total runs:** 180 (45 prompts × 4 combinations)

---

## Results

| Combo | Pass | Total | Rate | 1st-attempt | Avg attempts |
|---|---:|---:|---:|---:|---:|
| `none/none` (no strategy) | 44 | 45 | 97.8% | 84.4% | 1.18 |
| `none/none/multi_turn` | 45 | 45 | **100.0%** | 93.3% | 1.07 |
| `system_prompt/qiskit_short/repair_template` | 45 | 45 | **100.0%** | 95.6% | 1.04 |
| `system_prompt/qiskit_short/multi_turn` | 45 | 45 | **100.0%** | **97.8%** | **1.02** |

---

## Key Findings

### 1. The Qiskit model barely needs IVR on QKT prompts

All three active-strategy combos reach 100%. The baseline without any strategy (none/none) already hits 97.8% with avg 1.18 attempts. IVR adds marginal value — the model almost always gets it right on the first try.

### 2. System prompt improves first-attempt rate

`qiskit_short` + MultiTurn reaches 97.8% first-attempt vs 93.3% without a system prompt. The system prompt helps the model avoid the small number of deprecated patterns it occasionally generates on attempt 1, reducing reliance on the repair loop.

### 3. Strategy barely matters at this quality level

MultiTurn (1.02 avg attempts) and RepairTemplate (1.04) are essentially equivalent. This contrasts sharply with micro-h, where MultiTurn clearly outperformed RepairTemplate. For the Qiskit model on QKT prompts, strategy choice is not a meaningful variable.

### 4. One prompt fails regardless

`QKT200-pulse-fix-03` fails in the none/none baseline (exhausts 10 attempts). It passes in all three strategy combos — suggesting it needs the repair loop but not a particular strategy. This is the same pattern seen in Phase 1 where a small number of prompts are inherently harder.

---

## Implication for Default Config

### General prompt code quality

All 6 general prompts pass on attempt 1 for the Qiskit model across all configs — IVR is invisible with any of them. Code quality varies:

| Prompt | Quality | Notes |
|---|---|---|
| `general-runtime-estimator-01` | GOOD | Most realistic: EstimatorV2, Session, SparsePauliOp — follows modern Qiskit patterns |
| `general-random-circuit-01` | GOOD | Correct `random_circuit()` usage |
| `general-bell-state-01` | GOOD | Correct H+CNOT, but trivial |
| `general-entanglement-circuit-01` | GOOD | Identical output to bell-state |
| `general-bell-runtime-01` | SUSPECT | Uses deprecated `backend.run()` instead of a Sampler primitive |
| `general-list-fake-backends-01` | BAD | Hallucinated `GenericBackendV2().backends()` API |

Note: Qiskit model wraps all output in markdown fences (```python...```) — these are stripped by the code extractor before validation, but confirm the fence-stripping requirement seen in check() analysis.

### Default prompt: `general-runtime-estimator-01`

Since IVR is invisible on all general prompts regardless, the choice should be driven by output quality and realism. `general-runtime-estimator-01` produces the most complete and realistic code — it exercises Session, EstimatorV2, SparsePauliOp, and a real backend — making it the best demonstration of what the model can generate.

IVR value is still visible on harder QKT prompts (e.g. `QKT200-pulse-fix-03` needs 2 attempts even with strategy), but for the default demo prompt `general-runtime-estimator-01` is the right choice.

### Default config: `none/none/repair_template`

This returns to the config that existed before benchmarking began — now validated by data rather than assumption:

- **No system prompt**: Adding `qiskit_short` only improves first-attempt rate from 93.3% → 97.8% — marginal gain for the complexity it adds to the example. With `none/none` the model still reaches 100% final pass rate via repair.
- **RepairTemplate over MultiTurn**: Strategy choice is essentially irrelevant for this model (1.04 vs 1.02 avg attempts). RepairTemplate is the simpler concept to explain: feedback is appended to the original instruction. MultiTurn adds no meaningful benefit here.
- **Simplicity for the reader**: The example's purpose is to demonstrate the IVR pattern. `none/none/repair_template` has no extra config to explain — the IVR mechanics are front and center.

### Configurable options to document in the example

Benchmarking established clear guidance for users who want to tune the config:

| Option | Default | Alternative | Benefit |
|---|---|---|---|
| System prompt | none | `qiskit_short` | +4.5pp first-attempt rate (93.3% → 97.8%) |
| Strategy | RepairTemplate | MultiTurn | Negligible for Qiskit model; significant for smaller models |
| Model | Qiskit model | `granite4:micro-h` | Much smaller download; lower quality (97.8% vs 100%, higher hallucination rate) |

---

## Comparison to micro-h (Phase 1)

| Model | Best QKT rate | 1st-attempt (best) | IVR contribution |
|---|---:|---:|---|
| Qiskit model | **100%** | **97.8%** | Minimal — rescues ~2% |
| granite4:micro-h | 97.8% | 91.1% | Significant — rescues ~7% |

The gap confirms the decision to use the Qiskit model as the sole example model.
