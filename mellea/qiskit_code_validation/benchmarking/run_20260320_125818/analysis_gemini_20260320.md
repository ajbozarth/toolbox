# QKT Migration Benchmark Analysis (granite4:micro-h)

Based on the benchmark results for `granite4:micro-h`, here is a detailed analysis of the performance across various context configurations and prompt categories.

### 1. Pass Rate by Context Mode
While the overall pass rates are relatively consistent, the "mode" of context had a significant impact on **how** the model arrived at the solution:

| `context_mode` | Pass Rate | First Try Pass | Avg attempts |
| :--- | :--- | :--- | :--- |
| `none` | 75.0% (6/8) | **62.5%** | 2.12 |
| `grounding` | 75.0% (6/8) | 25.0% | **2.75** |
| `system_prompt`| 70.8% (17/24) | 50.0% | 2.54 |
| `both` | **75.0% (18/24)** | 54.2% | 2.50 |

*   **Key Insight:** `grounding` (QKT rules only) actually made the model perform worse on the first attempt (25% pass), causing it to rely heavily on the **Repair Loop**. Conversely, `both` provided a better balance, yielding the highest volume of total passes (18).

### 2. System Prompt Variant Comparison
Within the `system_prompt` and `both` modes, we tested three agent variants:

*   **`chat` & `codegen`:** Both tied at **75.0% pass rate**. These larger, more structured prompts (83-227 lines) significantly improved the model's baseline adherence to modern APIs compared to a baseline.
*   **`inline`:** Performed worst at **68.8%**. The condensed rules (~22 lines) were often ignored by the model in favor of its pre-trained (deprecated) knowledge.

### 3. Repair Efficiency
The **Repair Loop** was critical for this small model.
*   **Context vs. Iterations:** Adding grounding (`grounding` or `both`) increased the average number of attempts. This suggests that while grounding provides the "correct" rules, the 6,300-token context might slightly overwhelm the model's small context window on the first pass, requiring the validation feedback (which is shorter and more targeted) to "guide" it to the goal.
*   **First Attempt Success:** The `none` mode had a high first-pass rate on simple prompts but failed completely on anything involving complex migrations.

### 4. Code Quality Review (The "Runnable" Test) ⚠️
As noted in the README, `success: true` only means it passed linting for **deprecated** Qiskit 1.0/2.0 APIs. A manual review of "passing" cases reveals significant hallucinations:

*   **Hallucinated APIs:** In `bell_runtime`, the model generated `qc.execute(config=backend)` (line 778). This is a total hallucination; `QuantumCircuit` objects in Qiskit have no `execute` method.
*   **Wrong Result Access:** In `runtime_estimator`, the model used `result[0].value` (line 682) instead of the correct `EstimatorResult` attributes like `.values` or `.metadata`.
*   **Logic vs. Validation:** The model frequently used `RandomGate(num_qubits=2)` to satisfy a request for a "random circuit," which is technically a gate but doesn't produce the multi-layered circuit the prompt expected.

### 5. Failure Patterns
Analyzing the 17 failed cases reveals consistent struggles:
*   **QKT100 (API Removal):** This was the cause of **20 violations** in failed final attempts. The model is extremely stubborn about importing `qiskit.Aer` and `qiskit.execute`, which were staple APIs for years.
*   **QKT101 (Method Removal):** 7 violations. The model continues to try using `.toffoli()` and `.cnot()` even when grounding context explicitly tells it to use `.ccx()` and `.cx()`.

### 6. Prompt Difficulty
*   **Impossible:** `deprecated_basicaer` (**0% pass**). No configuration could stop the model from trying to use `BasicAer` and `execute()`. This prompt serves as a "stress test" for migration, and the model failed it across the board.
*   **Hard:** `bell_state` (50%) and `random_circuit` (62.5%). These often failed because the model treated them as "easy" and defaulted to its outdated training data.
*   **Easy:** `toffoli_completion`, `entanglement_circuit`, and `bell_runtime` (**100% pass**). Providing a code stub or a very specific runtime request seems to keep the model on track.

### 7. Recommendation
**Recommended Configuration: `both` with the `codegen` or `chat` system prompt.**

While `codegen` and `chat` performed similarly in pass rate, **`codegen`** produced more concise code with fewer conversational filler hallucinations. Using **`both`** (Expertise + Rules) provides the model with enough "signals" that it needs to use modern APIs, while the **Repair Loop** acts as the final safety net to fix the inevitable hallucinations.

**Final Takeaway:** For a small model like `granite4:micro-h`, validation must go beyond "deprecated APIs" to include **syntax checking** and **module existence verification** to catch the hallucinations seen in the "successful" benchmark results.
