# Qiskit Code Generation Research Summary
**Date:** March 2026
**Model under test:** `granite4:micro-h` (small), `granite4:small-h` (medium), `hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF` (large, Qiskit-specialized)
**Framework:** Mellea Instruct-Validate-Repair (IVR) pattern
**Validator:** `flake8-qiskit-migration` QKT rules
**Benchmark:** 45 prompts covering QKT100–QKT202 rules + general Qiskit tasks

---

## Research Questions

1. Can system prompts and/or grounding context help a small model produce output quality closer to a large Qiskit-specialized model?
2. Is any small model configuration reliable enough to enable this example as an e2e IVR test?

---

## What We Tested

### Context configurations (micro-h only, 360 runs)
A 2×2 matrix of context modes was benchmarked across 3 system prompt variants:

| `context_mode` | System prompt | QKT grounding rules |
|---|:---:|:---:|
| `none` | — | — |
| `system_prompt` | ✓ | — |
| `grounding` | — | ✓ |
| `both` | ✓ | ✓ |

System prompt variants: `inline` (22-line condensed), `chat` (83-line qiskit-studio), `codegen` (227-line structured).

### Model comparison (none/none, 45 runs each)
All three models run without any context to establish quality baselines.

---

## Results

### 1. Context modes — pass rate (micro-h)

| Configuration | Pass rate |
|---|---|
| `both/inline` | **93.3%** |
| `both/codegen` | 91.1% |
| `system_prompt/inline` | 91.1% |
| `system_prompt/chat` | 91.1% |
| `both/chat` | 84.4% |
| `none/none` | 82.2% |
| `grounding/none` | 77.8% |
| `system_prompt/codegen` | 75.6% |

Key finding: **grounding alone (77.8%) performs worse than no context (82.2%).** The ~6,300-token QKT rule dump overwhelms micro-h without a system prompt to anchor it. Context improves raw pass rate by up to 11 points (`both/inline`), but see quality findings below.

### 2. Model comparison — pass rate (none/none)

| Model | Pass rate | Avg attempts (passes) | 1st-attempt pass rate |
|---|---|---|---|
| Qiskit model (specialized) | **97.8%** | 1.18 | 84.4% |
| granite4:small-h | 82.2% | 1.49 | 57.8% |
| granite4:micro-h | 82.2% | 1.95 | 68% |

Notably, small-h and micro-h achieve the same raw pass rate without context, but small-h uses fewer attempts on average — it converges more reliably. The Qiskit model is in a different league: 84% of its passes require no repair at all.

### 3. Code quality — the critical finding

QKT validation is a weak quality signal. Passing QKT means "no deprecated API patterns detected" — it cannot catch hallucinated APIs, wrong import paths, or semantically broken code.

Deep code review of passing results:

| Model / config | GOOD (runnable) | SUSPECT | BAD (hard runtime error) |
|---|---|---|---|
| Qiskit model, none/none | **76%** (28/37) | 19% (7/37) | 5% (2/37) |
| granite4:small-h, none/none | 51% (19/37) | 24% (9/37) | **24%** (9/37) |
| granite4:micro-h, both/codegen | 41% (17/41) | 20% (8/41) | **39%** (16/41) |

**The QKT pass rate is largely a false positive signal for small models.** Nearly 1 in 4 small-h passes and nearly 2 in 5 micro-h passes would raise a hard error at runtime (`ImportError`, `AttributeError`, or `NameError`).

### 4. Recurring hallucination patterns in small models

Both granite models share the same failure modes regardless of context configuration:

| Pattern | Impact |
|---|---|
| `IBMQ` imports (removed in Qiskit 1.0) | Appears even after repair, QKT doesn't catch it |
| `FlowController` (removed in Qiskit 1.0) | Both models hallucinate a non-existent subclass API |
| `from qiskit import X` for things in `qiskit.circuit.library` | Wrong import path, raises `ImportError` |
| `qiskit.aero.*` / `qiskit.Aer` vs `qiskit_aer` | Misspelling or wrong package, common |
| Fabricated submodule paths | e.g. `qiskit.qasm2.load_qasm_file`, `qiskit.visualization.print_statevector` |
| `execute()` re-introduced during repair | Model reverts to removed API under repair pressure |

Context (system prompt + grounding) reduces the frequency of some of these but does not eliminate them — the model doesn't have the knowledge to reliably produce correct replacements.

---

## Answer to Research Question 1

**System prompts and grounding context do not make small models produce code as reliable as the Qiskit-specialized model.** They inflate the QKT pass rate (82% → 93%) by helping the model avoid deprecated patterns, but the false positive rate in those passes remains high. The core issue is model knowledge: small models know what to avoid but not reliably what to replace it with.

The best context configuration (`both/inline`) raises micro-h's raw pass rate above small-h's baseline, but at worse code quality. Small-h without context produces more actually-runnable code than micro-h with best-case context.

---

## Answer to Research Question 2

**The example can be enabled as a test, but prompt choice matters significantly.**

Prompts that are reliable across all micro-h configurations AND produce GOOD quality code:

| Recommended test prompt | Why |
|---|---|
| `QKT101-bind-fix-01` | `bind_parameters` → `assign_parameters`; unambiguous, GOOD quality across models |
| `QKT101-mct-fix-01` | `mct` → `mcx`; simple, reliable, GOOD quality |
| `QKT200-transpiler-fix-01` | Real pass replacements, GOOD quality |
| `multi-toffoli-completion-01` | Multi-rule fix, GOOD quality, interesting demo value |
| `general-entanglement-circuit-01` | Clean generate task, no external deps, GOOD quality |

The current test prompt (`BasicAer + execute + cnot` fix) is `multi-deprecated-basicaer-01`, which passes only 3/8 configurations and fails all 10 attempts in most — the worst possible choice for a reliable test.

**Recommended test config:** `both/inline` with one of the prompts above. For a test that demonstrates IVR value, pick a prompt that occasionally needs 1–2 repairs (not one that trivially passes on attempt 1).

---

## IVR Pattern Assessment

The IVR pattern itself works as intended — the repair loop successfully uses QKT validation feedback to guide the model toward passing code. The issue is that "passing QKT" is not equivalent to "correct code."

| Model | IVR contribution |
|---|---|
| Qiskit model | Minimal — 84% pass first attempt; IVR adds marginal value |
| granite4:small-h | Moderate — 58% first-attempt, IVR rescues ~24% more |
| granite4:micro-h | Significant — 54–68% first-attempt (varies by config), IVR rescues ~15–30% more |

For small models, IVR is doing real work. But it's recovering from deprecated-API mistakes, not from knowledge gaps — when the model doesn't know the correct replacement, it either hallucinates something that happens to pass QKT, or it exhausts the repair budget.

---

## Work Plan

### Phase 1 — System prompt and strategy benchmark

**Goal:** Determine the best system prompt and strategy combination for small model code gen.

**Benchmark runs** (granite4:micro-h, `system_prompt` context mode only):
- Prompt variants: `inline` (current baseline), `system-prompt-qiskit-stripped` (production prompt stripped of safety content; stronger technical content but ~90 lines vs 22), and at least one further-shortened variant. GHE candidates also exist pending permissions check.
- Strategy variants: `RepairTemplateStrategy` and `MultiTurnStrategy` at the temperature used in prior runs
- Model: granite4:micro-h (primary); Qiskit model none/none as quality ceiling reference (use existing `run_20260321_103850` data — no re-run needed)

**Analysis sub-tasks:**
- QKT pass rate comparison across prompt × strategy combinations
- Code quality review (GOOD/SUSPECT/BAD) on passing results for top configurations
- Strategy comparison: coworker found RepairTemplate edges out MultiTurn at higher temp on the Qiskit model; confirm whether this holds for small models
- Grounding context follow-up: prior benchmark showed grounding context performing *worse* than no context (77.8% vs 82.2%) due to poor content (rule definitions with no correct-API examples) and architectural placement (injected into the user message, not a separate message). If system prompt alone is insufficient, revisit with better content (Qiskit pattern docs, before/after migration examples), noting the placement limitation remains.

### Phase 2 — Qiskit Human Eval dataset integration

**Goal:** Run the existing benchmark pipeline against the community-standard QHE corpus to get results comparable to published model benchmarks.

The [qiskit-human-eval](https://github.com/qiskit-community/qiskit-human-eval) dataset ([HuggingFace](https://huggingface.co/datasets/Qiskit/qiskit_humaneval)) contains 151 Qiskit code generation problems (basic/intermediate/difficult) with canonical solutions and `check()` unit tests. Unlike our QKT corpus it is general code gen, not migration — the two are complementary.

**Code changes:**
- Adapt benchmark to load QHE prompts (field mapping: `task_id`, `prompt`, `entry_point`, difficulty)
- Run same pipeline (QKT validation, IVR, winning config from Phase 1) against QHE corpus
- Post-run analysis: run `check()` on generated code as *analysis only* (not wired into the repair loop) to measure actual correctness alongside QKT pass rate — this bridges the false-positive gap identified in Phase 1

**Benchmark runs (overnight):**
1. `granite4:micro-h` + winning prompt + MultiTurn — winning config from Phase 1
2. Qiskit model + `none/none` + RepairTemplate — quality ceiling baseline (no published QHE results from model team; own run needed for apples-to-apples since published scores won't include IVR)
3. Qiskit model + `none/none` + MultiTurn — strategy comparison on specialized model without context
4. Qiskit model + winning prompt + RepairTemplate — does the winning prompt help or hurt the specialized model
5. Qiskit model + winning prompt + MultiTurn — strategy comparison on specialized model with context

Phase 1 established MT > RT for micro-h; combos 2–5 test whether the same flip holds for the Qiskit model (coworker found RT ≥ MT without context; unknown with system prompt).

Total: 151 × 5 = 755 runs, ~12-14 hours.

**Note:** A few known buggy QHE tests (issues #42, #17) should be excluded from analysis.

**~~Phase 3 — `check()` as a live validator~~** *Removed after investigation.*

The QHE `check()` functions use bare `assert` statements with no custom messages. Assertion failures (the interesting case — code ran but produced the wrong answer) produce no diagnostic output: `"Test assertion failed: "`. Only runtime exceptions (ImportError, TypeError, etc.) produce traceback detail, but those are already partially addressed by QKT validation. Without actionable feedback from `check()` failures, wiring it into the repair loop would not give the model meaningful signal to repair against.

---

### Pre-PR cleanup (after work above is complete)
- **Roll back temp commit** — before starting cleanup, soft-reset the temp commit (`git reset --soft HEAD~1`) so all changes are unstaged and the full git diff is visible for review
- **Remove micro-h from the example entirely** — micro-h produces hallucinated or broken code for all 6 general prompts under the intended default config (see `run_20260323_134320/analysis_phase1.md`). The example should use only the Qiskit-specialized model, with a comment explaining why (domain-specialized model required for reliable code gen). The `# model_id = "granite4:micro-h"` commented-out lines should be removed rather than kept as alternatives.
- **Keep `# pytest: ollama, llm, qualitative` skip marker** — the Qiskit model requires a large local download; add a comment in the test file noting this is the reason for the skip
- **Update default prompt to `general-runtime-estimator-01`** — produces the most realistic and complete Qiskit code (EstimatorV2, Session, SparsePauliOp). All general prompts pass on attempt 1 for the Qiskit model so IVR visibility is not a differentiator; quality is. See `run_20260324_145820/analysis_phase2_qiskit_model_qkt.md` for full quality breakdown.
- **Default config: `none/none/repair_template`** — validated by Phase 2 QKT data. System prompt adds only marginal first-attempt gain (93.3% → 97.8%); RepairTemplate and MultiTurn are equivalent for this model. Document the tuning options in the example with benchmarked numbers: system prompt (+4.5pp first-attempt), strategy (negligible for Qiskit model), model (micro-h as smaller alternative with lower quality).
- Enable the example as a test using the winning config; remove `pytest.mark.skip` from non-model-download-gated markers
- Simplify `context_mode` handling in `qiskit_code_validation.py` — remove unused modes, hard-code the winning system prompt, remove the `context_mode` variable and supporting blocks
- Remove `get_qkt_rules_text()` from `validation_helpers.py` if grounding context is dropped entirely (leave until confirmed not needed)
- Move unused system prompt files (`system-prompt.md`, `system-prompt-codegen.md`, losing variants) into `benchmarking/` for reference once winning prompt is confirmed — covered by `.gitignore`, kept out of the example root
- Update README Context Modes section (currently removed preemptively) and Changing the Model section to reflect final simplified code
- Copy `benchmarking/` to `~/workspace/ai/toolbox/mellea/qiskit_code_validation/` for permanent personal reference — protects against future `git reset --hard` or clean checkouts

---

## Data

| Run | Model | Config | Prompts | Results |
|---|---|---|---|---|
| `run_20260320_174220` | granite4:micro-h | all 8 combinations | 45 | 360 cases, 309/360 passed |
| `run_20260321_103850` | Qiskit model | none/none | 45 | 45 cases, 44/45 passed |
| `run_20260321_112157` | granite4:small-h | none/none | 45 | 45 cases, 37/45 passed |
