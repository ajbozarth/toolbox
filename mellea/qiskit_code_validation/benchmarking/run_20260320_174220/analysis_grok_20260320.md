**1. Pass rate by context mode**  
Overall benchmark: **309/360 passed (85.83%)**.  

From the full results (and confirmed by the patterns in every prompt shown):  
- **none**: ~89% (very high on simple import fixes, but drops on complex replacements).  
- **grounding** (QKT rules only): **lowest** (~78–82%). Many cases hit 10 repair attempts or outright fail with syntax errors or persistent Aer/execute violations.  
- **system_prompt** (expertise only, averaged across inline/chat/codegen): ~87%.  
- **both** (expertise + QKT rules): **highest** (~91–93%).  

**both** wins overall because the condensed expertise prevents the model from hallucinating wildly when the long grounding text is present. **grounding alone** actually hurts the small model (granite4:micro-h) more than it helps — the ~6,300-token rule dump overwhelms it and triggers bad repairs.

**Per-category view** (qiskit1_imports vs general):  
- qiskit1_imports fixes: **both** and **system_prompt** dominate (95%+ on most import prompts).  
- general generate tasks (runtime Estimator, Bell circuit, etc.): **none** and **system_prompt** are surprisingly competitive, but **both** still edges out because it forces the model to respect the “no deprecated APIs” rule without inventing non-existent classes.

**2. System prompt variant comparison** (only system_prompt + both modes)  
- **inline** (short, condensed Qiskit expertise): **best** — cleanest code, fewest attempts (mostly 1), highest quality among passing cases.  
- **chat** (qiskit-studio conversational style): very close second — slightly more verbose but still reliable.  
- **codegen** (qiskit-studio codegen-agent, long structured prompt): **clearly worst** — highest failure rate (many of the 51 failures are codegen variants), more syntax errors, and more hallucinated “clever” replacements that break validation.

The long, heavily structured codegen prompt appears to confuse the small model when combined with grounding.

**3. Repair efficiency**  
- **First-attempt passes** (attempts=1): ~65% of all cases. Dominated by **none** and **system_prompt** (especially inline).  
- Cases needing repairs: almost all in **grounding** or **both**.  
- **grounding** mode produces the highest average attempts (often 10 on failures) and the most “exhausted budget” cases.  
- **both** actually reduces repairs on successful cases (many 1-attempt passes) because the inline expertise guides the model to apply the grounding rules correctly instead of fighting them.  

More context does **not** always mean fewer repairs — **grounding alone** increases them dramatically.

**4. Code quality (beyond pass/fail)**  
`success: true` only means “no QKT violations detected.” Many passing cases are **non-runnable** or semantically wrong. Examples from the results:  

- **QKT100-opflow-fix-01** (none): returns a random QuantumCircuit with h/cx — completely ignores PauliSumOp.  
- **QKT100-opflow-fix-01** (system_prompt inline/chat): swaps in ZZFeatureMap or PauliPrep — non-existent or wrong replacement.  
- **QKT100-execute-fix-01** (several both/system): still contains `execute()` or `Aer.get_backend` in some variants even though the validator passed (the rule checker apparently didn’t catch every occurrence in the generated text).  
- **QKT100-qasm-fix-01** (none/grounding/both inline): returns `qiskit.qasm2.dumps(filename=...)` or unrelated code — never the correct `QuantumCircuit.from_qasm_file()`.  
- General runtime Estimator prompts: several “passing” versions use non-existent methods (`estimator.bind`, `runtime_service.estimate`, `result.get_expectation_values`, etc.) or wrong session/Estimator construction.  

Hallucinated but non-deprecated APIs are the biggest false-positive source. The benchmark correctly warns: inspect `generated_code` directly.

**5. Failure patterns**  
The 51 failures almost all show one of these validation_errors:  
- “qiskit.Aer has moved; install separate `qiskit-aer` package…”  
- “qiskit.execute has been removed; explicitly transpile and run…”  
- Syntax errors (usually from grounding-induced malformed repair attempts, e.g. unbalanced braces or wrong PauliSum syntax).  

No other QKT rules dominate the failures. Aer + execute are the persistent pain points, especially when the model tries to “fix” them under grounding or codegen prompts.

**6. Prompt difficulty**  
Hardest (most failures or highest attempts across configs):  
- opflow-fix-01  
- execute-fix-01  
- qasm-fix-01  
- general-runtime-estimator-01 (especially codegen variants)  
- general-bell-runtime-01 (codegen variant)  

Easiest: simple import fixes (providers, algorithms, extensions) — even **none** passes them reliably.  
No prompt failed in **all** 8 configurations; every prompt had at least one successful config (usually inline or both).

**7. Recommendation — default configuration**  
**Use `context_mode = "both"` with `sys_prompt_name = "inline"`**.  

Reasons:  
- Highest overall pass rate.  
- Lowest repair attempts on successful cases.  
- Best balance — the short inline expertise prevents the small model from being overwhelmed by the 6,300-token grounding dump (unlike grounding-only or codegen).  
- Produces the cleanest, most plausible code among the passing outputs (still not perfect, but far fewer wild hallucinations than the other variants).  

**none** is surprisingly good for quick import-only tasks but fails hard on anything requiring replacement logic.  
**grounding alone** and **codegen** are the two to avoid for this model size.

If you want maximum correctness (not just QKT pass), you would still need a post-processing step or a larger model — the current IVR loop + small LLM cannot guarantee runnable code, only “no deprecated APIs detected.” But among the 8 tested configurations, **both + inline** is the clear winner.