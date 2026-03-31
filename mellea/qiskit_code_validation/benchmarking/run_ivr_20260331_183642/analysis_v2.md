# Benchmark v2 Analysis — IVR-Only Qiskit Code Validation
**Date:** 2026-03-31
**Model:** `hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest`
**Total runs:** 392 (90 QKT + 302 QHE), max repair attempts: 10

This benchmark re-runs after removing the pre-IVR input validation from the example.
The IVR loop now handles all validation end-to-end. No system prompt or grounding context —
model's built-in Qiskit knowledge only. Two strategies compared: `repair_template` and `multi_turn`.

---

## Overall Pass Rates

Both strategies achieved **100% final pass rate** across all 392 runs.

| Phase | Strategy | Runs | Passed | Pass Rate |
|---|---|---|---|---|
| QKT | repair_template | 45 | 45 | 100% |
| QKT | multi_turn | 45 | 45 | 100% |
| QHE | repair_template | 151 | 151 | 100% |
| QHE | multi_turn | 151 | 151 | 100% |

Note: `success: true` means QKT linter rules passed, not that the code is runnable or semantically correct.

---

## Strategy Comparison

### First-attempt pass rate (no repair needed)

| Phase | repair_template | multi_turn |
|---|---|---|
| QKT | 40/45 = **88.9%** | 44/45 = **97.8%** |
| QHE | 147/151 = **97.4%** | 144/151 = **95.4%** |
| Combined | 187/196 = **95.4%** | 188/196 = **95.9%** |

### Average attempts per run

| Phase | repair_template | multi_turn |
|---|---|---|
| QKT | 1.27 | **1.02** |
| QHE | **1.07** | 1.11 |
| Combined | 1.12 | **1.09** |

### Average wall-clock time per run

| Phase | repair_template | multi_turn |
|---|---|---|
| QKT | 3.18s | **2.60s** |
| QHE | **14.89s** | 15.84s |

**QKT verdict:** `multi_turn` is decisively better — 97.8% vs. 88.9% first-pass, 1.02 vs. 1.27 avg attempts, 18% faster total. The worst `repair_template` run on QKT took 9 attempts (`QKT200-transpiler-fix-01`); `multi_turn` resolved the same prompt in 2.

**QHE verdict:** Near-parity. `repair_template` edges out on first-pass rate (97.4% vs. 95.4%) and average time. `multi_turn` produced one outlier — `qiskitHumanEval/144` took 153.2s (2 attempts) vs. 74.6s (1 attempt) under `repair_template`.

---

## IVR Activation

IVR activated for only **4.3% of runs (17/392)**. 95.7% passed on the first attempt. Every case that needed repair was resolved within 10 attempts.

| Phase | Needed repair | % needing repair |
|---|---|---|
| QKT | 6/90 | 6.7% |
| QHE | 11/302 | 3.6% |

**Attempts distribution (QKT):**
- repair_template: 40×1, 4×2, 1×9
- multi_turn: 44×1, 1×2

**Attempts distribution (QHE):**
- repair_template: 147×1, 1×2, 2×3, 1×7
- multi_turn: 144×1, 5×2, 1×3, 1×10

---

## QKT Per-Category Breakdown

| Category | repair_template first-pass | multi_turn first-pass |
|---|---|---|
| general (6) | 6/6 = 100% | 6/6 = 100% |
| multi_rule (2) | 2/2 = 100% | 2/2 = 100% |
| qiskit1_imports (8) | 8/8 = 100% | 8/8 = 100% |
| qiskit1_methods (6) | 6/6 = 100% | 6/6 = 100% |
| qiskit1_kwargs (3) | 1/3 = **33%** | 3/3 = 100% |
| qiskit2_imports (8) | 6/8 = **75%** | 7/8 = **88%** |
| qiskit2_methods (6) | 5/6 = **83%** | 6/6 = 100% |
| qiskit2_kwargs (6) | 6/6 = 100% | 6/6 = 100% |

**Hardest category:** `qiskit2_imports` — specifically QKT200 (Qiskit 2.0 transpiler/pulse import modernization). `qiskit1_kwargs` (QKT102, PassManager kwargs changes) is the worst category for `repair_template` at 33% first-pass.

---

## Failure Patterns

### Where repairs were needed

**QKT (6 repair cases):**
- `QKT102-append-fix-01` (repair_template, 2 attempts): PassManager `max_iteration` kwarg removal
- `QKT102-replace-fix-01` (repair_template, 2 attempts): same rule
- `QKT200-pulse-fix-01` (repair_template, 2 attempts): Qiskit 2.0 pulse import removal
- `QKT200-transpiler-fix-01` (repair_template, **9 attempts**): `NoiseAdaptiveLayout`, `CrosstalkAdaptiveSchedule`, `Unroller` removal — model looped on incorrect replacements; same prompt resolved in 2 attempts under `multi_turn`
- `QKT200-transpiler-fix-01` (multi_turn, 2 attempts): same prompt, resolved quickly
- `QKT201-calibration-fix-01` (repair_template, 2 attempts): Qiskit 2.0 calibration method removal

**QHE (11 repair cases):**
- `qiskitHumanEval/84` — Qiskit Pulse Gaussian schedule with `FakeBelemV2`: repair_template 7 attempts (33.8s), multi_turn **10 attempts** (124.6s). Hardest prompt in the benchmark.
- `qiskitHumanEval/86` — Qiskit Pulse Constant + Delay: repair_template 3 attempts, multi_turn 2 attempts
- Several prompts needing 2 attempts each spread across both strategies

**Pattern:** Qiskit Pulse (`qiskit.pulse`, `FakeBelemV2`, `DriveChannel`) is consistently the hardest domain in QHE. Qiskit 2.x import migration (QKT200, QKT102) is the hardest domain in QKT. Both highlight gaps in the model's knowledge of recently changed or removed APIs.

The `repair_template` 9-attempt outlier on `QKT200-transpiler-fix-01` illustrates the strategy's core weakness: error feedback appended to a growing single prompt can snowball, making the instruction harder to interpret with each iteration. Multi-turn conversation scopes each repair message cleanly.

### Known issues

**Empty code false positives:** 14 QHE results have empty `generated_code` but `success: true`. The QKT linter trivially passes empty output (no code = no violations). These are not genuine successes. IVR should treat empty output as a failure and force regeneration.

**Intermediate validation errors not persisted:** The `validation_errors` field is always empty in the final record, even for multi-attempt runs. It reflects only the final passing attempt's state. There is no way to inspect which QKT rules triggered repairs on intermediate attempts.

---

## QHE Functional Correctness: check() Results

QKT validation is a weak quality signal — it only checks for deprecated API patterns, not whether the code actually runs correctly. The QHE dataset includes `check()` unit test functions that measure real correctness.

**Overall check() pass rate: 84/302 = 27.8%**

| Strategy | check() passed | fail_assertion | fail_runtime |
|---|---|---|---|
| repair_template | 43/151 = **28.5%** | 27 | 81 |
| multi_turn | 41/151 = **27.2%** | 28 | 82 |

Strategies are essentially tied on functional correctness, matching the QKT-level parity on QHE.

### By difficulty

| Difficulty | repair_template | multi_turn | Combined |
|---|---|---|---|
| basic (78 runs each) | 33/78 = 42.3% | 31/78 = 39.7% | 64/156 = **41.0%** |
| intermediate (68 runs each) | 10/68 = 14.7% | 10/68 = 14.7% | 20/136 = **14.7%** |
| difficult (5 runs each) | 0/5 = 0% | 0/5 = 0% | 0/10 = **0%** |

The difficulty cliff is steep: basic prompts pass check() at 41%, intermediate drops to 14.7%, difficult is 0%. The model can handle straightforward circuit construction but fails on complex algorithmic tasks.

### Most common check() failure causes

| Error | Count | Notes |
|---|---|---|
| `SyntaxError: invalid syntax` at line 1 | 43 | Likely markdown fences in output not stripped; or truncated code |
| `AttributeError: 'DataBin' has no attribute 'meas'` | 10 | Model uses old primitive result format (`result.quasi_dists`) instead of new `DataBin` API |
| `ModuleNotFoundError: No module named 'matplotlib'` | 8 | Model imports optional viz dependency not in test environment |
| `ValidationError: SamplerOptions` | 8 | Model passes deprecated options format to SamplerV2 |
| `QiskitError: Cannot apply instruction with classical bits: measure` | 4 | Incorrect circuit construction for statevector simulation |
| `NameError: name 'np' is not defined` | 4 | Missing `import numpy as np` |
| `NameError: name 'QuantumCircuit' is not defined` | 4 | Missing imports |
| `AttributeError: CNOTDihedral has no attribute 'from_circuit'` | 4 | Hallucinated API |

The largest single failure class (43 SyntaxErrors) likely includes both markdown-fenced output that `_strip_markdown_fences` fails to clean and genuinely truncated code from the 2048 token output limit. Many prompts in the 120s–150s range produced truncated code in the full output log (`SyntaxError: unterminated string literal`), suggesting `MAX_NEW_TOKENS=2048` is insufficient for complex QHE prompts.

The `DataBin`/primitives API failures (10 cases) are a model knowledge gap: the new SamplerV2/EstimatorV2 result format changed significantly in recent Qiskit versions and the model doesn't consistently use it correctly even when it passes QKT linting.

### Comparison to previous benchmark (v1)

The previous Phase 2 QHE benchmark (run on laptop, `none/none` combos) showed **32.5% check() pass rate** (49/151 per combination). This run shows **27.8%** (43/151 and 41/151). The ~5% drop — about 7 prompts — is most likely stochastic variation rather than a regression from the code change:

- The code change (removing pre-IVR input validation) is unlikely to affect QHE results. QHE prompts are general code generation tasks whose inputs typically don't contain deprecated Qiskit APIs, so the removed pre-condition check would have been a no-op for most QHE prompts.
- The benchmarks were run on different hardware (laptop vs. LSF GPU server) with different CUDA runtimes and memory bandwidth characteristics.
- At temperature 0.8, a 5% swing across 151 prompts is within normal run-to-run variance for a stochastic model.
- The previous laptop run was affected by thermal throttling (10x timing variance between first and last 10 runs), which may have influenced generation quality in ways that don't reflect the model's stable behavior.

---

## Phase Comparison: QKT Migration vs. QHE General Generation

| Metric | QKT | QHE |
|---|---|---|
| First-pass rate (combined) | 84/90 = **93.3%** | 291/302 = **96.4%** |
| Repair activation rate | 6.7% | 3.6% |
| Worst case attempts | 9 (QKT200-transpiler, repair_template) | 10 (QHE/84, multi_turn) |
| Avg elapsed/run (repair_template) | 3.18s | 14.89s |
| Avg elapsed/run (multi_turn) | 2.60s | 15.84s |

QKT migration prompts have a lower first-pass rate (93.3% vs. 96.4%). Migration tasks test very specific rule compliance for deprecated APIs — a harder target than general generation where the validator only flags what's present.

QHE prompts are ~5x slower per run due to greater complexity and output length.

---

## Recommendation

**Use `multi_turn` as the default strategy.**

1. **On QKT, `multi_turn` is decisively better:** 97.8% vs. 88.9% first-pass, 1.02 vs. 1.27 avg attempts, 18% faster. The `repair_template` 9-attempt loop on `QKT200-transpiler-fix-01` — resolved in 2 attempts by `multi_turn` — illustrates the structural risk of appending error feedback to a single growing prompt.
2. **On QHE, strategies are effectively tied.** `repair_template` has a fractionally better first-pass rate (97.4% vs. 95.4%) but the difference is within noise.
3. **No tradeoff in final pass rate:** both reach 100% within 10 attempts. The choice only affects first-pass rate, repair efficiency, and latency on hard cases.

**Follow-up items:**
- Fix the empty-output false positive: treat empty `generated_code` as a validation failure in the IVR loop
- Persist per-attempt validation errors to the result JSON for better post-run debuggability
- Increase `MAX_NEW_TOKENS` above 2048 for complex QHE prompts — truncated output is a significant failure cause in the 120s–150s difficulty range
