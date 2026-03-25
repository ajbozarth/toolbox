# Phase 2 Analysis — Qiskit Model QHE Results (Partial)
**Run:** `run_phase2_20260323_220911/run_20260324_001943`
**Model:** `hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest`
**Dataset:** Qiskit Human Eval (QHE), 90/151 prompts × 4 combos = 360 runs (partial — ~60% complete)
**Date:** 2026-03-24 (updated 2026-03-25)

---

## Results Summary

| Metric | Value |
|---|---|
| QKT pass rate | 360/360 (100.0%) |
| check() pass rate (of QKT passes) | 146/360 (40.6%) |
| check() pass rate (of all prompts) | 146/360 (40.6%) |
| fail_assertion | 62 |
| fail_runtime | 152 |
| skipped (QKT failed) | 0 |

### check() pass rate by combo

| context_mode | sys_prompt | strategy | check() passed | Total | Rate | fail_assertion | fail_runtime |
|---|---|---|---:|---:|---:|---:|---:|
| none | — | multi_turn | 37 | 90 | 41.1% | 16 | 37 |
| none | — | repair_template | 36 | 90 | 40.0% | 15 | 39 |
| system_prompt | qiskit_short | multi_turn | 36 | 90 | 40.0% | 16 | 38 |
| system_prompt | qiskit_short | repair_template | 37 | 90 | 41.1% | 15 | 38 |

**Finding: all four combos are statistically indistinguishable** — within 1 percentage point (40–41%). At 90 prompts this is still partial but the pattern is clear: for the Qiskit-specialized model, neither system prompt nor strategy choice meaningfully affects check() pass rate on QHE.

### check() pass rate by difficulty

| Difficulty | check() passed | QKT passed | Rate |
|---|---:|---:|---:|
| basic | 99 | 188 | 52.7% |
| intermediate | 47 | 156 | 30.1% |
| difficult | 0 | 16 | 0.0% |

---

## Key Finding: Qiskit Model vs micro-h — ~41% vs 4.2%

The Qiskit-specialized model achieves **~41% check() pass rate** on QHE prompts (90/151 prompts complete), vs micro-h's **4.2%**. This is a ~10× difference in actual correctness despite similar or better QKT pass rates (100% vs 94%). The Qiskit model is dramatically more capable at general QHE code gen — this result validates using a domain-specialized model.

Note: the earlier partial estimate (49%, 49 prompts) was higher than the current 90-prompt figure (40.6%). The additional prompts include more intermediate/difficult problems that drag the rate down.

---

## Investigation Note: Initial 0% Was a `check_analysis.py` Bug

The first run of `check_analysis.py` against these results showed 0% pass rate with 196/196 SyntaxErrors. Investigation revealed the cause: the Qiskit model returns **markdown-fenced responses** (`\`\`\`python\n...\n\`\`\`\nExplanation text.`) that are stored verbatim in `generated_code`. When `exec()` receives the raw response, the backtick fence characters cause `SyntaxError: unterminated string literal`.

`check_analysis.py` was updated with a `_strip_markdown_fences()` function that extracts the code between the opening and closing fence before `exec()`. After this fix, the 49% pass rate emerged.

**Root cause in the pipeline:** Mellea's code extractor is not stripping markdown fences for this model before returning the result. The stored `generated_code` field contains fence markers and trailing explanation text. QKT validation still passes because flake8 ignores the fence characters syntactically. This is a latent bug in the code extraction step that only surfaces when the code is actually `exec()`'d.

---

## Strategy and System Prompt Findings

With 90 prompts per combo, the pattern is now clear:

- **System prompt**: no meaningful impact (40.6% with vs 40.6% without — tied)
- **Strategy**: no meaningful impact (MT 40.6% vs RT 40.1% — within noise)

This contrasts with micro-h where MT was clearly better on QKT pass rate. For the Qiskit model on QHE, the repair loop rarely fires (100% QKT pass, near-100% first-attempt) so strategy choice is moot. Full 151-prompt results may shift these numbers slightly but are unlikely to change the conclusion.

---

## Failure Mode Analysis

### fail_runtime breakdown (152 total)

| Error type | Count |
|---|---:|
| AttributeError | 36 |
| NameError | 24 |
| QiskitError | 24 |
| TypeError | 20 |
| ModuleNotFoundError | 16 |
| CircuitError | 8 |
| ImportError | 8 |
| IndexError | 4 |
| InvalidAccountError | 4 |
| ValueError | 4 |
| RuntimeError | 4 |

**AttributeError (most common at 90 prompts):** Accessing a non-existent attribute on a real Qiskit object — the model knows the right class but calls a method or property that doesn't exist or was removed.

**NameError:** Using an identifier that was never defined or imported — often a class or function the model expected to import but didn't.

**QiskitError:** Runtime errors from Qiskit itself — wrong circuit structure, incompatible gate arguments, or backend configuration issues.

**TypeError:** Incorrect argument types or counts — API exists but is called incorrectly.

**ModuleNotFoundError / ImportError:** Hallucinated import paths — less common than for micro-h but still present.

**InvalidAccountError (4):** Code tries to connect to IBM Quantum (`QiskitRuntimeService(channel="ibm_quantum")`) — fails because no real credentials exist in the test environment.

### fail_assertion (62 total)

62 cases ran successfully but produced wrong results. This is 10× more than micro-h (6 cases), which makes sense — the Qiskit model gets far enough to execute and return an answer, but sometimes that answer is semantically wrong.

---

## Comparison with micro-h

| Metric | micro-h | Qiskit model (partial) |
|---|---:|---:|
| Prompts evaluated | 151 | 90/151 (partial) |
| QKT pass rate | 94.0% | 100.0% |
| check() pass rate | 4.2% | 40.6% |
| fail_assertion | 6 | 62 |
| fail_runtime | 130 | 152 |
| Skipped (QKT failed) | 9 | 0 |

The Qiskit model's higher `fail_assertion` count relative to micro-h is a positive signal: it means the model gets the code running more often, making semantic correctness the binding constraint rather than import or syntax errors.

---

## Next Steps

- Resume QHE benchmark for Qiskit model overnight (`--resume-phase2`) to get full 151-prompt × 4-combo results
- Fix markdown fence stripping in the benchmark pipeline itself (the Mellea code extractor should strip fences; investigate whether this affects QKT repair loop behavior)
- Compare full Qiskit model results against micro-h for definitive strategy and system prompt conclusions
- Complete QKT 3-combo run for Qiskit model (currently in progress) for migration task comparison
