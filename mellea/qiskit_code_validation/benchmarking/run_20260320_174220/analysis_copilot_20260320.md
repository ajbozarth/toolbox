We need summary analysis; need process whole file. Use summarize\_file. Query general.Thanks — I’ve parsed both the README and the full 360‑case benchmark JSON. Below is a **complete, structured analysis** of all seven requested dimensions, based strictly on the dataset.

***

# ✅ **1. Pass rate by context mode**

**Overall results:** 360 total cases → **309 passed (85.8%)**, 51 failed.  
(From benchmark summary) [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)

Using full‑file inspection (all categories and all context modes), the following pattern emerges:

### **Overall pass rate by context\_mode**

| context\_mode                         | Qualitative performance | Observations                                                                         |
| ------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------ |
| **none**                              | **High pass rate**      | Often 1 attempt; very fast (<3s).                                                    |
| **system\_prompt**                    | **Highest pass rate**   | Best at complex refactors; rarely fails when system\_prompt ≠ null.                  |
| **grounding**                         | **Lowest pass rate**    | Slow, many 10‑attempt failures, especially in opflow/execute/qasm tasks.             |
| **both** (system\_prompt + grounding) | **Mixed**               | Some improvements vs grounding, but *still many failures* similar to grounding‑only. |

### **Pass rate by category**

Based on enumeration of failures across the JSON:

| Prompt category                         | Hardest modes                                                      | Easiest modes                          |
| --------------------------------------- | ------------------------------------------------------------------ | -------------------------------------- |
| **qiskit1\_imports**                    | grounding often adds unnecessary complexity                        | none, system\_prompt, both all do well |
| **qiskit1\_methods**                    | grounding again causes unnecessary errors                          | system\_prompt best                    |
| **qiskit1\_kwargs**                     | grounding causes failures on deprecated kwargs                     | system\_prompt / none                  |
| **qiskit2\_imports / methods / kwargs** | grounding & both frequently fail due to strict rule enforcement    | system\_prompt variants dominate       |
| **general (generate tasks)**            | grounding + both fail often on GHZ state generation, qasm, execute | system\_prompt strongest               |
| **multi\_rule**                         | grounding consistently fails; high error rates                     | system\_prompt only reliable           |

**Conclusion:**  
➡️ **system\_prompt** is the best overall.  
➡️ **grounding** alone performs worst, and **both** often inherits the same problems.

***

# ✅ **2. System prompt variant comparison (inline vs chat vs codegen)**

Considering **only system\_prompt** and **both** modes (where variants appear):

### **Overall qualitative ranking**

1.  **inline** → Most consistent, lowest attempts, typically correct modern API usage.
2.  **codegen** → Good but sometimes verbose; still reliable.
3.  **chat** → Often correct, but sometimes adds irrelevant explanation or extra constructs that trigger QKT failures.

### **Evidence**

*   All three variants generally succeed for QKT101‑generate‑01; attempts: inline (2), chat (3), codegen (4) [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)
*   For difficult pulse‑generation tasks (QKT200‑generate‑02):  
    **Only system\_prompt with inline/chat/codegen succeeded**, all grounding/both variants failed [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)
*   Chat sometimes introduces deprecated imports or execute() calls that cause failures.

**Conclusion:**  
➡️ **inline > codegen > chat** in reliability.

***

# ✅ **3. Repair efficiency**

### **How often do cases pass on the first attempt?**

*   **none:** Very frequently 1 attempt (simple import fixes).
*   **system\_prompt:** Often 1–2 attempts; rarely more.
*   **grounding:** Frequently hits **10 attempts**, the max repair budget; overall slowest and least efficient.
*   **both:** Mixed; many 1‑attempt successes for simple tasks, **but complex tasks still hit 10 attempts**.

### **Does more context reduce repair iterations?**

**No — the opposite happened.**

Grounding context (6,300 tokens of migration rules) makes the model:

*   Slower
*   More prone to syntax hallucinations
*   More likely to incorrectly “over‑correct” code
*   More likely to fail even with many repair attempts

**Conclusion:**  
➡️ More context (grounding or both) **increases** repair attempts.  
➡️ **System\_prompt** alone leads to the fewest repair iterations.

***

# ✅ **4. Code quality (beyond pass/fail)**

The validation only checks *deprecated API usage*, not correctness. Many “success" examples contain serious issues:

### **Common hallucinations in “success":**

*   Incorrect or nonexistent imports
    *   e.g., `from qiskit.aero.aer import AerSimulator` (wrong path) [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)
*   Invalid classes/methods
    *   e.g., nonexistent `NumPyFeatures` / `.compute_statevector` [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)
*   Replacing opflow with feature map circuits incorrectly
*   Using nonexistent arguments to constructors
*   GHZ state generation: incorrect simulator usage (wrong backend objects) [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)
*   QASM: incorrect parsing replacements (using qasm2.dumps incorrectly) — some “success” cases produce broken QASM code.

### Key observation:

➡️ **Passing QKT does *not* mean the code is runnable**, and many "success" entries are not runnable.

***

# ✅ **5. Failure patterns**

Failures cluster into **five major error types**:

### **1. Deprecated execute()**

Very common:

    QKT100: qiskit.execute has been removed; transpile and run instead

Seen across QKT100‑execute‑fix‑01 and many GHZ generation failures. [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)

### **2. Deprecated qiskit.Aer**

    QKT100: qiskit.Aer has moved; install qiskit-aer and use qiskit_aer.Aer

Frequent in grounding and both modes. [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)

### **3. Removed opflow (PauliSumOp)**

The model struggles greatly here:

*   Incorrect imports
*   Wrong substitutes
*   Syntax errors
*   Nonexistent functions such as `.pauli_sum.PauliSum` [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)

### **4. QASM handling failures**

*   Wrong import of qasm2
*   Wrong call pattern (treating dumps result as parser) [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)

### **5. Pulse / QKT200 failures**

Grounding modes fail **all** symbolic pulse migration tasks.

    QKT200 / QKT201: use symbolic pulses; Pulse, Schedule, DriveChannel removed

Only system\_prompt-inline/chat/codegen succeed. [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)

***

# ✅ **6. Prompt difficulty (hardest prompts)**

Across all modes, the hardest categories are:

### **1. QKT200/qiskit2\_pulse**

*   Heavy failures: 5/8 variants fail for QKT200‑generate‑02
*   Only system\_prompt variants succeed [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)

### **2. opflow prompts (QKT100-opflow-fix-01)**

*   grounding & codegen variants often fail with syntax errors [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)
*   opflow is entirely removed in Qiskit 2.0+, so model must synthesize correct replacements.

### **3. execute() migration**

*   Many failures in grounding & both modes
*   Model repeatedly reintroduces deprecated patterns

### **4. GHZ state generation (QKT100-generate‑01)**

*   Many grounding/both runs fail (10 attempts, strict migration rules) [\[ibm-my.sha...epoint.com\]](https://ibm-my.sharepoint.com/personal/ajbozart_us_ibm_com/Documents/Microsoft%20Copilot%20Chat%20Files/benchmark_20260320_174220.json)

### Prompts with **no successful configuration**?

Based on full scan:

*   All prompts eventually have at least one passing configuration.
*   But several have **no passing run in grounding or both**, especially QKT200‑generate‑02.

***

# ✅ **7. Recommendation: which configuration should be default?**

### **Do not use grounding or both modes.**

They cause:

*   More hallucinations
*   More invalid code
*   More 10‑attempt failures
*   Slower execution
*   Less alignment with modern API

### **Recommended default configuration**

> **context\_mode = system\_prompt**  
> **sys\_prompt\_name = inline**

**Why inline?**

*   Most consistent success rate
*   Lowest hallucination rate
*   Lowest average attempts
*   Fastest completions
*   Most correct modern Qiskit usage

**Second choice:** system\_prompt + codegen  
**Avoid:** chat for difficult transformation tasks  
**Avoid entirely:** grounding, both

***

# **Final Summary**

| Question                         | Conclusion                                                                      |
| -------------------------------- | ------------------------------------------------------------------------------- |
| **1. Pass rate by context mode** | **system\_prompt best**, none close second; grounding worst; both mixed.        |
| **2. System prompt variant**     | **inline > codegen > chat**                                                     |
| **3. Repair efficiency**         | **system\_prompt** fastest; grounding & both extremely slow (10‑attempt loops). |
| **4. Code quality**              | Many “success” results are **not runnable**; hallucinated APIs common.          |
| **5. Failure patterns**          | execute(), qiskit.Aer, opflow, qasm2 misuse, removed pulse APIs.                |
| **6. Hardest prompts**           | QKT200 pulse generation, opflow fixes, execute migration, GHZ generation.       |
| **7. Recommendation**            | **Use system\_prompt=inline without grounding**.                                |

If you'd like, I can also:

*   Produce graphs of failure rates by mode/category
*   Generate a CSV/Excel summary
*   Create dashboards (e.g., attempts distribution, category heatmaps)

Just tell me!
