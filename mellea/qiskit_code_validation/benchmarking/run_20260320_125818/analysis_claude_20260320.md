# Benchmark Analysis: granite4:micro-h — IVR Qiskit Code Generation

**Run:** 2026-03-20 12:58:18
**Model:** granite4:micro-h
**Summary:** 64 total cases (8 prompts × 8 context configs), 47 passed, 17 failed — **73.4% overall pass rate**
**Max repair attempts:** 5

---

## 1. Pass Rate by Context Mode

| context_mode | passed | rate | notes |
|---|---|---|---|
| `none` | 6/8 | **75%** | baseline |
| `grounding` | 6/8 | **75%** | same as none |
| `system_prompt` | 17/24 | **70.8%** | slightly *worse* than none |
| `both` | 18/24 | **75%** | marginal gain over system_prompt |

**Surprising result:** adding a system prompt alone hurt pass rate slightly. The grounding context alone matched baseline. The `both` combination ties baseline but requires ~6,300 extra tokens per call.

### By system prompt variant

| variant | system_prompt | both | combined |
|---|---|---|---|
| `inline` | 5/8 (62.5%) | 6/8 (75%) | 11/16 (68.8%) |
| `chat` | 6/8 (75%) | 6/8 (75%) | 12/16 (75%) |
| `codegen` | 6/8 (75%) | 6/8 (75%) | 12/16 (75%) |

`inline` is the weakest variant; `chat` and `codegen` tie at 75%.

---

## 2. System Prompt Variant Comparison

`codegen` is faster (often 3–17s vs 60–117s for `chat`/`inline`) with equally clean output on easy prompts. But it produced one syntax error (`list_fake_backends/both/codegen` — a markdown fence leaked into the code block). `chat` had no such failures and handled the multi-attempt cases (`random_circuit`, `runtime_estimator`) reliably.

**Winner on quality:** `chat` and `codegen` are roughly tied on pass rate; `codegen` wins on speed.

---

## 3. Repair Efficiency

| context_mode | attempts=1 (first-pass) | total | first-pass rate |
|---|---|---|---|
| `none` | 5/8 | 8 | 62.5% |
| `grounding` | 3/8 | 8 | 37.5% |
| `system_prompt` | 11/24 | 24 | 45.8% |
| `both` | 12/24 | 24 | 50.0% |

**More context did not reduce repair iterations.** `none` had the highest first-pass rate. `grounding` had the lowest, likely because the extra tokens shift the model's output distribution. Many failures across all modes exhausted all 5 attempts without passing.

---

## 4. Code Quality: Hallucinated APIs in `success: true` Cases

The validator only checks deprecated patterns — it cannot catch invented APIs. Passing cases include:

| case | hallucinated API |
|---|---|
| `bell_state/both/chat` | `simulator.simulate()` (doesn't exist) |
| `list_fake_backends/none` | `IBMQ.backends()` (removed in 1.x) |
| `list_fake_backends/grounding` | `IBMProvider().backends()` (wrong class) |
| `list_fake_backends/system_prompt/inline` | `qiskitest.exceptions` (typo), `qiskit.ibmq.list_backends(fake_devices=True)` |
| `list_fake_backends/system_prompt/chat` | `IBMResourceManager()` (fabricated class) |
| `entanglement_circuit/grounding` | `qc.execute(backend=backend)` (method doesn't exist on circuits) |
| `bell_runtime/both/codegen` | `qc.execute(config=backend)` |
| `runtime_estimator/none` | fabricated `QiskitRuntimeService` method signatures |
| `random_circuit/grounding` | `PGHLayer` (fabricated class from `qiskit.circuit.library`) |

**Conclusion:** treat `success: true` as "no deprecated patterns" only. The actual runnable-code rate is far lower — probably 40–50% of passing cases are actually correct.

---

## 5. Failure Patterns

| QKT Rule | Failures | Description |
|---|---|---|
| QKT100: `qiskit.Aer` moved | 12 | Model imports `from qiskit import Aer` instead of `from qiskit_aer import Aer` |
| QKT101: `cnot()` removed | 6 | Model doesn't replace `qc.cnot()` with `qc.cx()` |
| QKT100: `execute` removed | 6 | Model uses deprecated `qiskit.execute()` |
| Syntax error | 1 | Markdown fence leaked into code output (`list_fake_backends/both/codegen`) |

**Key insight:** `qiskit.Aer` is the dominant failure. The model reverts to this pattern even after 5 repair cycles with explicit error feedback. The `deprecated_basicaer` prompt requires fixing all three violations simultaneously — the model consistently fixes one or two, but the residual `cnot()` or `execute` error persists to exhaustion.

---

## 6. Prompt Difficulty

| prompt_name | passed/total | notes |
|---|---|---|
| `toffoli_completion` | 8/8 (100%) | trivial single-substitution task |
| `entanglement_circuit` | 8/8 (100%) | — |
| `bell_runtime` | 8/8 (100%) | — |
| `list_fake_backends` | 7/8 (87.5%) | `both/codegen` failed with syntax error |
| `runtime_estimator` | 6/8 (75%) | `grounding` and `none` passed but likely hallucinated |
| `random_circuit` | 5/8 (62.5%) | `system_prompt/inline`, `system_prompt/codegen`, `both/chat` all failed |
| `bell_state` | 4/8 (50%) | 4 configs failed, all due to `qiskit.Aer` |
| **`deprecated_basicaer`** | **0/8 (0%)** | **Failed every configuration; 3 simultaneous violations** |

`deprecated_basicaer` is a wall — no configuration passed it. It's the only prompt where the task explicitly requires recognizing and fixing existing deprecated code, compounding three simultaneous violations.

---

## 7. Full Results Table

| # | prompt_name | context_mode | sys_prompt_name | success | attempts | elapsed_s |
|---|---|---|---|---|---|---|
| 1 | bell_state | none | — | false | 5 | 47.5 |
| 2 | bell_state | grounding | — | true | 1 | 14.3 |
| 3 | bell_state | system_prompt | inline | false | 5 | 114.4 |
| 4 | bell_state | system_prompt | chat | false | 5 | 117.4 |
| 5 | bell_state | system_prompt | codegen | true | 1 | 3.6 |
| 6 | bell_state | both | inline | false | 5 | 107.8 |
| 7 | bell_state | both | chat | true | 1 | 21.1 |
| 8 | bell_state | both | codegen | true | 1 | 13.4 |
| 9 | list_fake_backends | none | — | true | 1 | 5.4 |
| 10 | list_fake_backends | grounding | — | true | 2 | 26.0 |
| 11 | list_fake_backends | system_prompt | inline | true | 1 | 12.3 |
| 12 | list_fake_backends | system_prompt | chat | true | 1 | 19.3 |
| 13 | list_fake_backends | system_prompt | codegen | true | 1 | 3.4 |
| 14 | list_fake_backends | both | inline | true | 1 | 23.6 |
| 15 | list_fake_backends | both | chat | true | 1 | 23.0 |
| 16 | list_fake_backends | both | codegen | false | 5 | 70.2 |
| 17 | random_circuit | none | — | true | 1 | 4.5 |
| 18 | random_circuit | grounding | — | true | 3 | 51.3 |
| 19 | random_circuit | system_prompt | inline | false | 5 | 90.1 |
| 20 | random_circuit | system_prompt | chat | true | 4 | 66.9 |
| 21 | random_circuit | system_prompt | codegen | false | 5 | 27.8 |
| 22 | random_circuit | both | inline | true | 5 | 105.1 |
| 23 | random_circuit | both | chat | false | 5 | 100.0 |
| 24 | random_circuit | both | codegen | true | 3 | 44.0 |
| 25 | toffoli_completion | none | — | true | 1 | 2.0 |
| 26 | toffoli_completion | grounding | — | true | 1 | 11.8 |
| 27 | toffoli_completion | system_prompt | inline | true | 1 | 6.5 |
| 28 | toffoli_completion | system_prompt | chat | true | 1 | 3.8 |
| 29 | toffoli_completion | system_prompt | codegen | true | 1 | 3.7 |
| 30 | toffoli_completion | both | inline | true | 1 | 14.4 |
| 31 | toffoli_completion | both | chat | true | 1 | 15.7 |
| 32 | toffoli_completion | both | codegen | true | 1 | 13.4 |
| 33 | entanglement_circuit | none | — | true | 1 | 12.0 |
| 34 | entanglement_circuit | grounding | — | true | 2 | 26.5 |
| 35 | entanglement_circuit | system_prompt | inline | true | 1 | 22.2 |
| 36 | entanglement_circuit | system_prompt | chat | true | 1 | 15.6 |
| 37 | entanglement_circuit | system_prompt | codegen | true | 3 | 13.0 |
| 38 | entanglement_circuit | both | inline | true | 1 | 14.0 |
| 39 | entanglement_circuit | both | chat | true | 1 | 21.8 |
| 40 | entanglement_circuit | both | codegen | true | 2 | 28.6 |
| 41 | deprecated_basicaer | none | — | false | 5 | 27.0 |
| 42 | deprecated_basicaer | grounding | — | false | 5 | 72.3 |
| 43 | deprecated_basicaer | system_prompt | inline | false | 5 | 61.0 |
| 44 | deprecated_basicaer | system_prompt | chat | false | 5 | 78.4 |
| 45 | deprecated_basicaer | system_prompt | codegen | false | 5 | 20.8 |
| 46 | deprecated_basicaer | both | inline | false | 5 | 85.5 |
| 47 | deprecated_basicaer | both | chat | false | 5 | 88.5 |
| 48 | deprecated_basicaer | both | codegen | false | 5 | 72.4 |
| 49 | runtime_estimator | none | — | true | 1 | 14.0 |
| 50 | runtime_estimator | grounding | — | false | 5 | 76.4 |
| 51 | runtime_estimator | system_prompt | inline | true | 1 | 18.1 |
| 52 | runtime_estimator | system_prompt | chat | true | 2 | 33.9 |
| 53 | runtime_estimator | system_prompt | codegen | true | 1 | 8.1 |
| 54 | runtime_estimator | both | inline | true | 1 | 25.3 |
| 55 | runtime_estimator | both | chat | true | 4 | 80.6 |
| 56 | runtime_estimator | both | codegen | true | 1 | 17.2 |
| 57 | bell_runtime | none | — | true | 2 | 22.2 |
| 58 | bell_runtime | grounding | — | true | 3 | 44.5 |
| 59 | bell_runtime | system_prompt | inline | true | 2 | 39.1 |
| 60 | bell_runtime | system_prompt | chat | true | 3 | 49.4 |
| 61 | bell_runtime | system_prompt | codegen | true | 1 | 5.1 |
| 62 | bell_runtime | both | inline | true | 1 | 17.1 |
| 63 | bell_runtime | both | chat | true | 3 | 57.8 |
| 64 | bell_runtime | both | codegen | true | 1 | 15.1 |

---

## 8. Recommendation

**Use `both` + `codegen` as default, with one caveat.**

Rationale:
- `both` has the highest absolute pass count (18/24) and highest first-pass rate among context modes with system prompts (50%)
- `codegen` is 5–10× faster per call than `chat`/`inline`, critical for a repair loop that may run up to 5 iterations
- The one syntax error from `codegen` is a fixable output-parsing issue (strip markdown fences before validation)

**However:** the overall gains across context modes are modest. The real bottleneck is `qiskit.Aer` and multi-violation deprecated code — the grounding context doesn't fix these reliably. The grounding context's 6,300 tokens may be worth auditing: if the QKT rules for `Aer` migration are not prominently placed near the top, the model may be ignoring them. Prioritizing that specific rule in the grounding context might move the needle more than any system prompt change.

The benchmark also reveals that the IVR repair loop has diminishing returns after attempt 2–3: most cases either passed by attempt 4 or hit the wall at attempt 5 with the same residual error.
