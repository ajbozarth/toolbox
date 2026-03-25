# Phase 2 Analysis — micro-h QHE Results
**Run:** `run_phase2_20260323_220911/run_20260323_220911`
**Model:** `granite4:micro-h`
**Dataset:** Qiskit Human Eval (QHE), 151 prompts
**Config:** `system_prompt/qiskit_short/multi_turn` (Phase 1 winning config)
**Date:** 2026-03-24

---

## Results Summary

| Metric | Value |
|---|---|
| QKT pass rate | 142/151 (94.0%) |
| check() pass rate (of QKT passes) | 6/142 (4.2%) |
| check() pass rate (of all prompts) | 6/151 (4.0%) |
| fail_assertion | 6 |
| fail_runtime | 130 |
| skipped (QKT failed) | 9 |

### check() pass rate by difficulty

| Difficulty | check() passed | QKT passed | Rate |
|---|---:|---:|---:|
| basic | 6 | 71 | 8.5% |
| intermediate | 0 | 66 | 0.0% |
| difficult | 0 | 5 | 0.0% |

---

## Key Finding: QKT is a Near-Useless Signal for General Code Gen

The Phase 1 winning config achieves 94% QKT pass rate on QHE prompts but only **4.2% check() pass rate** — a 22× gap. This confirms and quantifies the concern raised in Phase 0: QKT validation catches deprecated API patterns but is blind to everything else that makes code incorrect or unrunnable.

This is not a surprising result — QKT was designed for migration validation, not general correctness — but the magnitude of the gap is significant.

---

## Failure Mode Analysis

### 1. Entry point not defined (most common)
Many results show `entry_point 'X' not defined after exec`. The model is not completing the function stub correctly — instead generating top-level scripts, wrapping the logic outside the expected function, or using a different function name. QHE prompts are function stubs (e.g. `def create_quantum_circuit(n_qubits): """..."""`) that expect the model to fill in the body while preserving the signature. micro-h frequently ignores the stub structure.

### 2. SyntaxError: invalid syntax (<string>, line 1)
A large cluster of prompts in the 53–109 range produce syntax errors on exec despite passing QKT. This likely means QKT's flake8 runner received an empty or stripped string (e.g. the code extractor removed markdown fences leaving nothing), while the actual generated content was syntactically broken. These are QKT false positives.

### 3. Systematic API hallucination: `generate_preset_pass_manager(level=...)`
At least 5 prompts (18–22, 29) fail with `TypeError: generate_preset_pass_manager() got an unexpected keyword argument 'level'`. The correct parameter is `optimization_level`. This is a consistent hallucination — the model conflates the old `transpile(optimization_level=...)` API with the new pass manager, using `level=` instead.

### 4. Missing imports / NameError
Numerous `NameError` failures where the model uses a name (`np`, `sqrt`, `Parameter`, `Statevector`, etc.) without importing it. QKT has no visibility into these.

### 5. Wrong import paths / non-existent APIs
`ImportError` on hallucinated paths like `from qiskit.circuit.library import Unitary`, `from qiskit.ibm_runtime import ...`, `from qiskit.aer import AerSimulator`. These pass QKT because they use no deprecated patterns — the APIs just don't exist.

### 6. Assertion failures (6 cases)
Only 6 results ran successfully but produced the wrong answer. The rarity of this category is itself a finding: the code almost never gets far enough to be semantically wrong — it fails earlier at import or structure.

---

## Interpretation

The IVR pattern with QKT as the validator does real work for **migration tasks** (fixing deprecated APIs) — this is what Phase 0 and Phase 1 demonstrated. But for **general code gen** (QHE-style function completion), QKT provides almost no correctness signal. The model can generate syntactically broken code, use wrong import paths, miss imports entirely, or ignore the expected function signature — all while passing QKT.

The 4.2% check() rate is consistent with Phase 0's manual quality review finding (~39% BAD for micro-h with best context), but is stricter: check() requires both correct structure and correct behavior, while GOOD/BAD rated runnability.

---

## What Would Help

For QHE-style prompts, a useful validator would need to check:
- Does the generated code define the expected function name?
- Does the code have valid Python syntax?
- Do all imports resolve?

Even these three checks (without running check()) would eliminate the majority of failures. QKT alone catches none of them.

Note: check() itself as a repair-loop validator was evaluated and rejected in Phase 1 planning — bare `assert` statements produce no diagnostic output on failure, giving the model no signal to repair against. That conclusion holds.

---

## Next Steps

- Run check() on Qiskit model partial results (49 prompts × 4 combos) to compare
- Resume QHE benchmark for Qiskit model overnight (`--resume-phase2`) to get full 151-prompt results
- Complete QKT 3-combo run for Qiskit model (currently running) for apples-to-apples migration task comparison
