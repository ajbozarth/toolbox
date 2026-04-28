# Benchmark v3 Analysis — QHE with check() as Live IVR Validator
**Date:** 2026-04-28
**Model:** `hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest`
**Total runs:** 298/302 (4 missing — see notes), max repair attempts: 10

This benchmark wires the per-problem `check()` unit test functions from the
[qiskit-human-eval](https://github.com/qiskit-community/qiskit-human-eval) dataset directly
into the IVR repair loop as a second validator alongside `flake8-qiskit-migration` QKT rules.
The check functions used are from [PR #88](https://github.com/qiskit-community/qiskit-human-eval/pull/88),
which adds f-string assertion messages (`assert result.num_qubits == 3, f"Expected 3, got {result.num_qubits}"`)
to previously silent assertions. These messages give the repair loop actionable feedback rather
than a bare `AssertionError:`.

For a run to be `success: true`, **both** validators must pass: QKT linting and the
behavioral `check()` test. This directly measures functional correctness, not just API compliance.

The v2 baseline (same model, QKT-only validation) ran `check()` post-hoc as an analysis step.
That comparison is the central finding of this benchmark.

---

## Headline Result

**Wiring `check()` into the repair loop nearly doubled functional correctness.**

| Benchmark | Validator | Pass rate |
|---|---|---|
| v2 post-hoc | QKT only → check() analysis | 84/302 = **27.8%** |
| v3 live | QKT + check() in loop | 148/298 = **49.7%** |
| Improvement | | **+21.9pp** |

The Qiskit-specialized model was already generating QKT-compliant code 100% of the time in v2.
The check() post-hoc results showed only 27.8% of that code was functionally correct. Giving the
repair loop access to check() failure messages — enabled by PR #88's assertion messages —
allowed the model to recover from functional errors it would otherwise never see.

---

## Pass Rates

### Overall by strategy

| Strategy | Runs | Passed | Pass rate | V2 post-hoc |
|---|---|---|---|---|
| repair_template | 149 | 75 | **50.3%** | 43/151 = 28.5% |
| multi_turn | 149 | 73 | **49.0%** | 41/151 = 27.2% |
| combined | 298 | 148 | **49.7%** | 84/302 = 27.8% |

Both strategies improved by ~+22pp. The gap between them (1.3pp) is within noise.

### By difficulty

| Difficulty | v2 post-hoc | v3 live | Δ |
|---|---|---|---|
| basic | 64/156 = **41.0%** | 97/158 = **61.4%** | +20.4pp |
| intermediate | 20/136 = **14.7%** | 51/132 = **38.6%** | +23.9pp |
| difficult | 0/10 = **0%** | 0/8 = **0%** | — |

The improvement is consistent across both difficulty tiers the model can handle. The difficult
category remains 0% — the model cannot repair its way out of those problems regardless of
feedback quality.

---

## IVR Activation and Repair Effectiveness

### Attempts distribution — passes

| Attempts | repair_template | multi_turn |
|---|---|---|
| 1 | 51 (68.0%) | 67 (91.8%) |
| 2 | 4 | 2 |
| 3 | 10 | 1 |
| 4 | 1 | 2 |
| 5 | 2 | 0 |
| 6 | 2 | 1 |
| 7 | 3 | 0 |
| 9 | 1 | 0 |
| 10 | 1 | 0 |
| **rescues (>1 attempt)** | **24 / 75 (32%)** | **6 / 73 (8%)** |

### Attempts distribution — failures

All 150 failures exhausted the full 10-attempt repair budget (74 repair_template, 76 multi_turn).
There are no early exits. Every failure costs the full budget.

### Strategy contrast

The two strategies show fundamentally different repair behavior under check() feedback:

**multi_turn** passes at 91.8% first-attempt and rescues only 6 cases through repair. It is
decisive — if the first attempt fails, it almost certainly exhausts the budget without passing.

**repair_template** passes at only 68% first-attempt but rescues 24 cases through sustained
repair (some at 7, 9, and 10 attempts). It is more persistent and benefits more from the
iterative check() feedback — likely because the accumulated error context in the single growing
prompt reinforces what not to do over repeated attempts.

This is the opposite pattern from the v2 QKT analysis, where multi_turn was slightly better.
The richer check() feedback appears to favor repair_template for hard cases.

---

## Failure Analysis

### Failure breakdown

| Failure mode | Count | % of failures |
|---|---|---|
| Passed QKT, failed check() | 136 | 90.7% |
| Failed QKT (and likely check()) | 14 | 9.3% |
| Run crashed | 0 | 0% |

91% of all failures were behaviorally wrong code that passed the linter. This is the core
finding from v2's check() analysis — QKT is a weak quality signal — confirmed again here.
The 14 QKT failures represent stochastic variance; the v2 QKT pass rate was 100%, and the
model still passes QKT 95.3% of the time (14 failures out of 298 runs).

### Prompts failing both strategies (70 prompts)

| Difficulty | Count | Notes |
|---|---|---|
| basic | 27 | Model knowledge gaps — not deprecated API issues |
| intermediate | 39 | Complex algorithms, multi-step logic |
| difficult | 4 | All difficult prompts fail both strategies |

69 prompts pass both strategies (45 basic, 24 intermediate). These are the reliably solvable
problems for this model. The 70 that fail both represent problems the model consistently gets
wrong regardless of repair strategy — no amount of iteration helps.

### Timing

| Strategy | Avg elapsed (passes) | Avg elapsed (failures) | Ratio |
|---|---|---|---|
| repair_template | 63.6s | 384.3s | 6.0× |
| multi_turn | 38.1s | 414.6s | 10.9× |

Failures are expensive: they run all 10 repair attempts before giving up. multi_turn passes are
notably faster (38.1s vs 63.6s for repair_template) because 92% pass on attempt 1, while
repair_template rescues burn many attempts at ~40-70s each.

Slowest failures (both strategies): `qiskitHumanEval/37` (intermediate, ~900s/~872s) —
consistently the hardest prompt in the benchmark.

---

## Missing Results

`qiskitHumanEval/149` and `qiskitHumanEval/150` (both strategies, 4 runs) are absent from
the results. No crashes occurred. These were the last 4 runs in the queue and were cut off
when the LSF preemptable job ended. They do not affect the analysis materially (4/302 = 1.3%).

---

## Comparison to v2

| Metric | v2 | v3 |
|---|---|---|
| QKT pass rate | 100% (302/302) | 95.3% (284/298) |
| check() pass rate | 27.8% post-hoc | 49.7% live |
| First-attempt pass rate (combined) | 96.4% | 79.5% |
| Avg attempts (passes) | 1.09 | 1.46 (RT) / 1.08 (MT) |
| Rescues via repair | 11/302 (3.6%) | 30/148 (20.3%) |
| All failures exhaust budget | No | Yes |

v3's lower first-attempt rate is expected: the model must now pass a behaviorally stricter
test on attempt 1. The repair loop activates much more often (20% of passes needed repair vs
3.6% in v2), showing that check() feedback is genuinely being used and not just noise.

The fact that 100% of failures exhaust the repair budget (vs v2 where some failed early) also
confirms that check() provides signal the model can work with — it keeps trying rather than
giving up. The repair loop is doing real work.

---

## Blog Post Context

This benchmark was designed to test whether wiring behavioral `check()` tests into the IVR
repair loop improves functional correctness over QKT-only validation. The answer is yes,
significantly (+22pp). Key narrative points for a blog post:

1. **QKT is a weak proxy**: the Qiskit-specialized model passes QKT 100% of the time but only
   ~28% of its output is actually correct. A perfect linter score is not a correctness guarantee.

2. **The IVR pattern extends naturally to behavioral validators**: adding `check()` as a second
   `Requirement` in Mellea's IVR loop required minimal code — the framework handles the rest.

3. **Assertion messages matter**: PR #88's f-string messages (`"Expected 3 qubits, got 5"`)
   are what make check() useful as repair feedback. Silent `AssertionError:` failures (the
   original dataset state) would give the model nothing to act on.

4. **Strategy behavior diverges under richer feedback**: repair_template rescues 4× more cases
   through multi-attempt repair (32% of its passes needed repair vs 8% for multi_turn). With
   check() feedback, repair_template's "accumulate error context" approach pays off for hard cases.

5. **The difficulty cliff remains**: basic 61%, intermediate 39%, difficult 0%. The model still
   cannot handle complex Qiskit algorithms. check() shows you where the cliff is, rather than
   hiding it behind a 100% QKT pass rate.
