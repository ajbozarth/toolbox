# Benchmark Analysis Summary: Qiskit Code Generation
**Model:** `granite4:micro-h`
**Benchmark:** 64 cases (8 prompts × 8 context configurations)
**Analyses reviewed:** Claude, Bob (IBM), Copilot, Grok, Gemini
**Ground truth stats:** `analyze_results.py` (computed directly from JSON)
**Note:** Qiskit model (`mistral-small-3.2-24b-qiskit-GGUF`) analysis pending.

---

## Verified Statistics (ground truth)

| Context mode | Pass rate | First-try pass | Avg attempts |
|---|---|---|---|
| `none` | 75.0% (6/8) | 62.5% | 2.13 |
| `grounding` | 75.0% (6/8) | 25.0% | 2.75 |
| `system_prompt` | 70.8% (17/24) | 50.0% | 2.54 |
| `both` | 75.0% (18/24) | 54.2% | 2.50 |

| System prompt variant | Pass rate |
|---|---|
| `inline` | 68.8% (11/16) |
| `chat` | 75.0% (12/16) |
| `codegen` | 75.0% (12/16) |

| Prompt | Pass rate |
|---|---|
| `toffoli_completion` | 100% (8/8) |
| `entanglement_circuit` | 100% (8/8) |
| `bell_runtime` | 100% (8/8) |
| `list_fake_backends` | 87.5% (7/8) |
| `runtime_estimator` | 87.5% (7/8) |
| `random_circuit` | 62.5% (5/8) |
| `bell_state` | 50.0% (4/8) |
| `deprecated_basicaer` | **0% (0/8)** |

**Top QKT violations in failures:** QKT100 (Aer moved): 20, QKT101 (cnot removed): 7, syntax error: 1

---

## Where the Agents Agreed

All 5 agents converged on the following:

1. **`deprecated_basicaer` is impossible for this model** — 0/8 across every configuration. Requires fixing 3 simultaneous deprecated APIs (`BasicAer`, `execute`, `cnot`); the repair loop can't converge.

2. **`inline` system prompt is the weakest variant** — consistently lowest pass rate (68.8%) and highest repair iterations. The condensed prompt is too easily ignored.

3. **`chat` and `codegen` outperform `inline`** — both reach 75%, with `codegen` producing cleaner, more minimal code.

4. **`success: true` ≠ runnable code** — all agents flagged this as a critical limitation. Common hallucinations found in passing cases:
   - `from qiskit.quantum_info import StatevectorSimulator` (doesn't exist)
   - `IBMResourceManager()`, `PGHLayer`, `qiskitest.exceptions` (fabricated)
   - `qc.execute(config=backend)` (method doesn't exist on circuits)
   - Estimated true runnable rate: **40–65%** of passing cases (agents varied in estimate)

5. **QKT100 (`qiskit.Aer` moved) is the dominant failure** — the model stubbornly reverts to `from qiskit import Aer` even after multiple repair cycles with explicit error feedback.

6. **The repair loop has diminishing returns** — cases that don't pass by attempt 2–3 almost always exhaust all 5 attempts with the same residual error.

---

## Where the Agents Disagreed

### 1. Overall recommendation: `none` vs `both + codegen`

This was the sharpest disagreement:

| Agent | Recommendation | Reasoning |
|---|---|---|
| **Copilot** | `none` | Highest first-try rate (62.5%), fewest avg attempts (2.13), no token overhead |
| **Claude** | `both + codegen` | Highest absolute passes, codegen speed advantage |
| **Bob** | `both + codegen` | Reported 93.8% for `both`* |
| **Grok** | `both + codegen` | Best first-try + fewest iterations with codegen |
| **Gemini** | `both + codegen` (or `chat`) | Best balance of pass rate and repair efficiency |

*Bob's numbers for `none` (50%) and `both` (93.8%) differ from ground truth (both 75%) — Bob appears to have counted mode totals differently (treated `none` as 16 cases instead of 8). His directional conclusions may still be valid but the specific percentages should not be relied on.

### 2. Does grounding context help?

- **Copilot & Claude:** Adding grounding actually *increased* average repair attempts (2.75 for `grounding` vs 2.13 for `none`), suggesting it overwhelms the small model.
- **Bob & Grok:** Grounding substantially helped, boosting performance.
- **Ground truth verdict:** Pass rate is identical (75%) but first-try rate for `grounding` is the *lowest* at 25% — the model passes eventually but needs more repairs. Copilot/Claude are correct that it doesn't help on first attempt.

### 3. How useful is the system prompt?

- **Copilot:** System prompts *hurt* slightly (70.8% vs 75% baseline).
- **Grok:** `codegen` system prompt clearly superior, dramatically reduces failures.
- **Ground truth:** `system_prompt` mode alone is the only mode below 75%. The system prompt helps *when combined with grounding* (`both` mode), not on its own.

---

## Key Findings for the Team

1. **The IVR pattern works** — 73.4% overall pass rate on a very small model with no Qiskit fine-tuning, rising to 75% with the right configuration.

2. **Context helps quality, not quantity** — The 6,300-token QKT grounding context doesn't reliably prevent the most common failure (Aer import) and may increase repair iterations. It's worth exploring whether a shorter, higher-priority grounding doc (focused on the top 3–4 violations) outperforms the full ruleset.

3. **Prompt design matters more than context mode** — The hardest prompt (`deprecated_basicaer`) failed across all 8 configurations. Prompt difficulty is a stronger predictor of failure than context configuration.

4. **QKT validation is necessary but not sufficient** — All agents flagged this. The next meaningful step is adding an execution validator (actually run the generated code) to catch hallucinated APIs. This would likely halve the apparent pass rate but give a more honest signal.

5. **`codegen` is the right system prompt for a code-generation task** — Produces minimal, focused output that is less prone to verbose hallucinations. The one syntax error it produced (markdown fence leak) is a known fixable issue in output parsing.

---

## Recommendation

**Default configuration: `both` + `codegen`**

Rationale: ties for highest pass rate (75%), produces the cleanest code, and the speed advantage of `codegen` is significant in a repair loop that may run up to 5 iterations.

**With the caveat:** pass rate differences between configurations are small (68.8%–75%). The bigger wins will come from:
- Adding an execution validator
- Improving the `deprecated_basicaer` prompt or accepting it as out-of-scope for this model size
- Auditing the grounding context to front-load the most commonly violated rules

---

*This summary will be updated once the Qiskit model (`mistral-small-3.2-24b-qiskit-GGUF`) analysis completes.*
