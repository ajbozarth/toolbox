# QKT Migration Benchmark Analysis (granite4:micro-h)

Based on the benchmark results for [`benchmark_20260320_174220.json`](benchmark_20260320_174220.json), here is a detailed analysis of the performance across 45 prompts and 8 context configurations.

> [!NOTE]
> Raw statistics for this run can be found in [`analysis_antigravity_stats_20260320_174220.txt`](analysis_antigravity_stats_20260320_174220.txt).

### 1. Pass Rate by Context Mode
Combining both a system prompt and grounding context proved to be the most effective strategy for ensuring the model avoids deprecated Qiskit APIs.

| `context_mode` | Pass Rate | First Try Pass | Avg attempts |
| :--- | :--- | :--- | :--- |
| `none` | 82.2% | **67.6%** | 1.95 |
| `grounding` | 77.8% | 62.9% | **1.91** |
| `system_prompt`| 85.9% | 58.6% | 2.37 |
| `both` | **89.6%** | 62.8% | 1.97 |

*   **Key Insight:** The `both` mode achieved the highest pass rate (89.6%), indicating that the model benefits from both high-level expertise (System Prompt) and low-level technical rules (Grounding). Interestingly, `grounding` alone performed worse than `none`, suggesting that raw technical rules without framing can be confusing for a small model.

### 2. System Prompt Variant Comparison
Within the `system_prompt` and `both` modes, the condensed **`inline`** prompt significantly outperformed the longer "Studio" prompts.

| `sys_prompt_name` | Pass Rate | Note |
| :--- | :--- | :--- |
| **`inline`** | **92.2%** | Focused, ~22 lines. Best for small models. |
| **`chat`** | 87.8% | Conversational/Teaching style. |
| **`codegen`** | 83.3% | Longest prompt (~227 lines). Likely caused "Lost in the Middle" effects. |

### 3. Repair Efficiency
The **Repair Loop** was highly active, with successes requiring ~2 iterations on average.
*   **Context vs. Iterations:** Successful runs in `system_prompt` mode took the most iterations (2.37), while `both` mode was more efficient (1.97). This suggests that providing the technical rules (grounding) helps the model converge on the fix faster once it has been steered by a system prompt.
*   **First-Pass Success:** High in `none` mode (67.6%), but this mode failed on almost all complex migration tasks (see multi-rule failures).

### 4. Code Quality Review (Beyond Pass/Fail) ⚠️
While the "success" flag indicates the absence of deprecated Qiskit 1.0/2.0 patterns, a manual review of passing cases reveals significant logical and API hallucinations:

*   **API Misuse:** In `QKT100-qasm-fix-01`, the model used `qiskit.qasm2.dumps()` (exporting) to handle a request for parsing a QASM file. It passed the "deprecated check" but created un-runnable code.
*   **Defeatist Logic:** In `QKT201-calibration-fix-01`, the model incorrectly claimed that pulse calibration methods were entirely removed from Qiskit and simply printed `qc.num_qubits` instead.
*   **Context Overload:** In `QKT100-opflow-fix-01`, instead of fixing the `opflow` import, the model pivoted to generating a `ZZFeatureMap`, failing the spirit of the prompt while satisfying the migration linting rules.

### 5. Failure Patterns
The 51 failed cases across all configurations show clear "stubborn" behaviors:
*   **QKT100 (API Removal):** 11 occurrences of `qiskit.Aer` being used despite explicitly being told it moved to `qiskit_aer`.
*   **`qiskit.execute`:** 9 instances where the model could not move away from the deprecated `execute()` function, which is the most common pattern in older Qiskit tutorials.
*   **Syntax Degradation:** A small percentage of failures involved invalid Python syntax introduced during the repair attempts.

### 6. Prompt Difficulty
*   **Hardest:** `multi-deprecated-basicaer-01` (**37.5% pass rate**). This requires multiple simultaneous migrations and was the most consistent point of failure.
*   **Moderate:** `QKT100-execute-fix-01` and `QKT200-generate-02` (50% pass). Tasks requiring new workflow patterns (Transpile -> Run) instead of single-line import fixes were much harder.
*   **Easy:** `qiskit1_kwargs` and `qiskit1_methods` (**88-100% pass**). Simple method name swaps or argument removals are well within the model's capabilities.

### 7. Recommendation
**Recommended Configuration: `both` with the `inline` system prompt.**

For a small model like `granite4:micro-h`, a **short, high-density system prompt** combined with **technical grounding context** provides the best steering. However, because the model frequently hallucinates *valid-sounding but incorrect* modern APIs, I recommend adding **Syntax Validation** and **Import Verification** (runtime checks) to the IVR loop to verify that the replacement APIs actually exist in the target environment.
