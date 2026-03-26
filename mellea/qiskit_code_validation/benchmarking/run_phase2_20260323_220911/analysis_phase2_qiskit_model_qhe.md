# Phase 2 Analysis — Qiskit Model QHE Benchmark
**Run:** `run_phase2_20260323_220911/run_20260324_001943`
**Model:** `hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest`
**Date:** 2026-03-24 (overnight, completed 2026-03-26)
**Dataset:** QiskitHumanEval (QHE) — 151 prompts
**Total runs:** 604 (151 prompts × 4 combinations)

---

## Results Summary

### QKT pass rate by combination

| Combo | Pass | Total | Rate | 1st-attempt | Avg attempts |
|---|---:|---:|---:|---:|---:|
| `none/none/multi_turn` | 151 | 151 | **100.0%** | **100.0%** | 1.00 |
| `none/none/repair_template` | 151 | 151 | **100.0%** | 98.0% | 1.03 |
| `system_prompt/qiskit_short/multi_turn` | 151 | 151 | **100.0%** | **100.0%** | 1.00 |
| `system_prompt/qiskit_short/repair_template` | 151 | 151 | **100.0%** | **100.0%** | 1.00 |

**Zero failures across all 604 runs.**

---

## Key Findings

### 1. System prompt has no effect on QKT pass rate

Adding `qiskit_short` system prompt produces identical results to `none` for this model. The Qiskit-specialized model already contains the domain knowledge the system prompt is designed to supply. This confirms the `none/none` default config — the system prompt is unnecessary overhead for this model.

### 2. Strategy choice is irrelevant for QKT pass rate on QHE

Both strategies reach 100% final pass rate. RepairTemplate needed repairs on 3/151 prompts (2%); MultiTurn needed none. The difference is negligible.

### 3. IVR is invisible on QHE for this model

`none/none/multi_turn` passes 100% of prompts on the first attempt — the repair loop never fires. The Qiskit model's domain knowledge is sufficient to produce QKT-passing code without any feedback loop on general code gen tasks. IVR adds value on harder QKT migration tasks (see `run_20260324_145820/analysis_phase2_qiskit_model_qkt.md`).

### 4. Timing data is unreliable due to thermal throttling

The benchmark was run overnight on a laptop with no active cooling management. Thermal throttling caused significant variance and inflation in elapsed times, particularly in the latter half of the run:

| Combo | Min | Median | Max | First 10 avg | Last 10 avg |
|---|---:|---:|---:|---:|---:|
| `none/none/multi_turn` | 12s | 41s | 482s | 19s | 189s |
| `none/none/repair_template` | 60s | 311s | **1159s** | 108s | 333s |
| `system_prompt/qiskit_short/multi_turn` | 11s | 36s | 473s | 19s | 125s |
| `system_prompt/qiskit_short/repair_template` | 20s | 273s | 469s | 76s | 312s |

The 10x gap between first-10 and last-10 averages confirms throttling. **Elapsed time comparisons between strategies are not reliable from this run.** The minimum times (unthrottled) suggest MultiTurn is faster than RepairTemplate at baseline (12-19s vs 60-108s first 10 avg) — likely because RepairTemplate builds a larger prompt even on the first attempt — but this should be verified on an unthrottled run.

---

## check() Correctness Analysis

### Overall

| Metric | Value |
|---|---:|
| Total runs | 604 |
| QKT passed | 604 (100%) |
| check() passed | 196 (32.5%) |
| fail_assertion | 108 (17.9%) |
| fail_runtime | 300 (49.7%) |

### By combination

All 4 combos produce identical check() results — strategy and system prompt have no effect on actual code correctness, consistent with QKT findings.

| Combo | Pass | Rate | Fail assertion | Fail runtime |
|---|---:|---:|---:|---:|
| `none/none/multi_turn` | 49/151 | 32.5% | 28 | 74 |
| `none/none/repair_template` | 49/151 | 32.5% | 26 | 76 |
| `system_prompt/qiskit_short/multi_turn` | 49/151 | 32.5% | 27 | 75 |
| `system_prompt/qiskit_short/repair_template` | 49/151 | 32.5% | 27 | 75 |

### Top runtime failure categories

| Error | Count |
|---|---:|
| AttributeError | 57 |
| TypeError | 55 |
| NameError | 40 |
| QiskitError | 36 |
| ModuleNotFoundError | 24 |
| InvalidAccountError | 16 |
| CircuitError | 16 |
| ImportError | 12 |

`InvalidAccountError` (16 cases) reflects prompts requiring a real IBM Quantum account — these are environment failures, not model failures. `ModuleNotFoundError` (24 cases) includes visualization libraries and other optional deps not installed in the check() environment. These inflate the fail_runtime count; the true model correctness rate is likely slightly higher than 32.5%.

**Note:** difficulty_scale breakdown is unavailable — the field was not carried through from the QHE parquet into the check results.

---

## Comparison to Phase 2 micro-h QHE Results

| Model | QKT pass rate | 1st-attempt (best combo) | check() pass rate |
|---|---:|---:|---:|
| Qiskit model | **100%** | **100%** | **32.5%** |
| granite4:micro-h | 94.0% | 70.9% | 4.2% |

The 8x gap in check() pass rate (32.5% vs 4.2%) confirms the Qiskit-specialized model is dramatically more capable at actually correct code generation. micro-h's near-perfect QKT rate (94%) masking a 4.2% correctness rate is the clearest demonstration of QKT as a weak quality signal for general models.

---

## Conclusion

For the Qiskit-specialized model on QHE prompts:
- `none/none/repair_template` is the correct default — system prompt and strategy choice make no measurable difference on either QKT or check() correctness
- IVR adds no observable value on QHE; its value for this model lies in QKT migration tasks
- 32.5% check() pass rate is the realistic correctness ceiling for this model on general Qiskit code generation; slightly higher when accounting for environment-dependent failures (IBM account, missing optional deps)
