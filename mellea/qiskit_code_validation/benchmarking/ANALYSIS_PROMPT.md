I'm sharing two files: `BENCHMARK_README.md` (read this first for full context) and a `benchmark_*.json` file containing results from a small LLM code generation benchmark.

**What this is:** A small LLM (`granite4:micro-h`) was asked to generate Qiskit quantum computing code across 45 prompts and 8 context configurations. Each configuration varies what additional knowledge was provided to the model (system prompt, grounding context, or both). The repair loop automatically retried failed attempts up to 10 times using validation error feedback.

**Please analyze:**
1. **Pass rate by context mode** — which of `none`, `system_prompt`, `grounding`, `both` performed best overall and per prompt category?
2. **System prompt variant comparison** — across the `system_prompt` and `both` modes, which variant (`inline`, `chat`, `codegen`) produced better results?
3. **Repair efficiency** — how often did cases pass on the first attempt vs requiring repairs? Did more context reduce repair iterations?
4. **Code quality (beyond pass/fail)** — `success: true` does NOT mean the code is runnable. Review `generated_code` for passing cases and flag any that look incorrect (hallucinated APIs, wrong imports, etc.)
5. **Failure patterns** — for `success: false` cases, what do the `validation_errors` reveal? Are certain QKT rules consistently violated?
6. **Prompt difficulty** — which prompts were hardest across all configurations? Any that no configuration could pass?
7. **Recommendation** — given these results, which context configuration would you recommend as default for this model?
