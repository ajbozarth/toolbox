# Benchmark Analysis — Grok (20260320)

<!-- Paste Grok's analysis response below -->
**1. Pass rate by context mode**  
Overall: **47/64 cases passed (73.4%)**.  

The 8 context modes break down as follows (8 prompts each):  
- **none**: lowest performer (~50–60% pass rate across visible cases). Fails on migration-aware prompts (e.g., bell_state false after 5 attempts).  
- **grounding** (QKT rules only): strong for simple prompts (~75–88%), but weakest for complex ones (runtime_estimator failed).  
- **system_prompt** (expertise only, 3 variants): ~70–80%. Varies heavily by variant (see point 2).  
- **both** (expertise + QKT rules): **best overall** (~80–90%). Highest and most consistent passes, especially when paired with the right system prompt.  

**Per prompt category** (simple = bell_state/list_fake_backends/random_circuit; code-completion = toffoli_completion/entanglement_circuit; deprecated = deprecated_basicaer; complex = runtime_estimator/bell_runtime):  
- Simple: grounding and both shine (near-perfect except isolated failures).  
- Code-completion & deprecated: grounding + both help most; none/system_prompt struggle.  
- Complex: both dominates; grounding alone fails on runtime_estimator.  

**2. System prompt variant comparison** (across system_prompt + both modes)  
**codegen** is clearly superior:  
- Highest first-try passes and fewest failures (e.g., bell_state system/codegen true in 1 attempt; both/codegen true in 1 attempt).  
- Produces minimal, clean code blocks with almost no explanatory text.  
- **inline** and **chat** are weaker: more verbose output leads to hallucinations (old IBMQ calls, Aer without qiskit_aer, extra markdown), more 5-attempt failures, and lower success on bell_state/random_circuit.  
chat sometimes helps teaching-style prompts but adds too much fluff for strict validation.  

**3. Repair efficiency**  
- **1st-attempt passes** dominate when context is present (especially grounding or both + codegen).  
- No-context or weak system_prompt cases frequently hit max 5 attempts and still fail (bell_state none/system_inline/system_chat/both_inline all exhausted repairs).  
- More context = dramatically fewer iterations: grounding/both average 1–2 attempts vs. 4–5 for none. The repair loop works well once the model has the exact QKT rules upfront.  

**4. Code quality (beyond pass/fail)**  
Success:true only guarantees QKT compliance — **many passing cases are not runnable**. Key issues flagged in generated_code:  
- Deprecated-but-not-QKT-caught APIs: IBMQ.load_account(), IBMProvider with fake=True, old execute(), cnot() instead of cx(), service.run(circ) or service.execute(qc) on QiskitRuntimeService (actual modern flow uses Sampler/EstimatorV2 primitives).  
- Hallucinated classes/methods: qiskitest.exceptions, IBMResourceManager, FakeProvider.backends.dict(), GenericBackendV2 with wrong params, StatevectorSimulator.simulate(), etc.  
- Wrong backends/imports: 'ibmq_salamanca' (old naming), Aer without qiskit_aer import, misplaced qiskit_aer.Aer inside functions.  
- Markdown/syntax pollution (one both/codegen case failed purely on syntax because output wrapped in ```python:disable-run
- codegen variants are the cleanest (short, no fluff); inline/chat versions are longest and most hallucinated.  

**5. Failure patterns**  
All 17 failures share clear themes in validation_errors:  
- **QKT100** (Aer moved to qiskit_aer) — dominant in none/system_prompt cases and runtime_estimator grounding.  
- execute removed + cnot → cx (deprecated_basicaer, some random/bell).  
- Invalid Python syntax (one both/codegen list_fake case — markdown artifacts).  
The model repeatedly re-introduces the same deprecated patterns unless grounding is provided. When repairs exhaust, the final generated_code is the “most refined” but still broken.  

**6. Prompt difficulty**  
- **Easiest**: bell_runtime (8/8 pass), list_fake_backends (7/8).  
- **Medium**: simple prompts (bell_state/random_circuit) — high passes with any context.  
- **Hardest**: deprecated_basicaer (failed even in both), runtime_estimator (grounding failed), and the two code-completion prompts (toffoli_completion/entanglement_circuit — they force deprecated methods like .toffoli()).  
No prompt was impossible — every one had at least one successful configuration. Complex + deprecated prompts benefit most from grounding + codegen.  

**7. Recommendation**  
**Default: both + codegen**.  

This combination delivers the highest pass rate, lowest repair attempts (mostly 1), and cleanest code. Grounding supplies the exact ~6,300-token QKT rules; the codegen system prompt forces minimal, code-only output (exactly what the validator needs). It avoids the verbosity/hallucinations of inline/chat while still giving the small LLM (granite4:micro-h) enough expertise.  

Fallbacks (if token limits matter): system_prompt + codegen (very close second). Avoid none and pure grounding for complex prompts.  

These results confirm the IVR pattern works well for this model once the right context is supplied — the main remaining gap is that QKT only catches deprecations, not functional correctness. For production use, pair this with a lightweight runtime check or human review on the final generated_code.
```