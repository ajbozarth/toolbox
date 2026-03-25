# Qiskit Code Validation — Benchmark Results

This directory contains benchmark output files (`benchmark_YYYYMMDD_HHMMSS.json`) from
the `run_benchmark()` function in `qiskit_code_validation.py`.

Each file is one benchmark run: all 45 prompts × 8 context combinations = 360 cases.

---

## What is being tested

The example uses Mellea's **Instruct-Validate-Repair (IVR)** pattern to have a small LLM
generate Qiskit quantum computing code that passes `flake8-qiskit-migration` (QKT) validation.

The benchmark isolates two variables:

| Variable | Values |
|---|---|
| **System prompt** | none, `inline` (condensed baseline), `chat` (qiskit-studio chat-agent), `codegen` (qiskit-studio codegen-agent) |
| **Grounding context** | absent or QKT migration rules extracted live from the flake8 plugin |

### Context mode combinations (2×2 matrix)

| `context_mode` | System prompt | Grounding context (QKT rules) |
|---|:---:|:---:|
| `none` | — | — |
| `system_prompt` | ✓ | — |
| `grounding` | — | ✓ |
| `both` | ✓ | ✓ |

For modes with a system prompt, the benchmark tests all three system prompt variants
(`inline`, `chat`, `codegen`), giving 8 combinations total per prompt.

### System prompt variants

- **`inline`** — Condensed Qiskit expertise prompt written for this example (~22 lines).
  Emphasises modern API usage and code quality.
- **`chat`** — Full qiskit-studio chat-agent prompt (~83 lines). Conversational teaching
  style; covers algorithms, circuit design, error mitigation, progressive learning.
- **`codegen`** — qiskit-studio codegen-agent prompt (~227 lines). Code-output-only focus;
  structured around Qiskit Pattern steps (Map, Optimize, Execute, Post-process).

### Grounding context

~6,300 tokens of structured migration rules extracted directly from the
`flake8-qiskit-migration` plugin's internal data (the same rules used for validation).
Covers deprecated import paths, methods, and kwargs for Qiskit 1.0 and 2.0.

---

## Prompts

45 prompts from `qkt_benchmark_v1.json`, organized by category:

| Category | Count | Description |
|---|---|---|
| `general` | 6 | Open-ended generation tasks (bell state, random circuit, estimator workflows, etc.) |
| `qiskit1_imports` | 8 | Fix deprecated Qiskit 1.x import paths (QKT100–QKT109) |
| `qiskit1_methods` | 6 | Fix deprecated Qiskit 1.x method calls (QKT110–QKT119) |
| `qiskit1_kwargs` | 3 | Fix deprecated Qiskit 1.x keyword arguments (QKT120–QKT129) |
| `qiskit2_imports` | 8 | Fix deprecated Qiskit 2.x import paths (QKT200–QKT209) |
| `qiskit2_methods` | 6 | Fix deprecated Qiskit 2.x method calls (QKT210–QKT219) |
| `qiskit2_kwargs` | 6 | Fix deprecated Qiskit 2.x keyword arguments (QKT220–QKT229) |
| `multi_rule` | 2 | Prompts requiring simultaneous fixes across multiple QKT rules |

Each prompt entry has an `id` (e.g. `qkt100-fix-basic-aer-01`), a `rule` (e.g. `QKT100` or `null` for general), a `prompt_type` (`fix` or `generate`), and the prompt text.

---

## Output fields

```json
{
  "model": "granite4:micro-h",
  "timestamp": "20260320_123456",
  "max_repair_attempts": 10,
  "summary": { "total": 360, "passed": 309, "failed": 51 },
  "context": "...",
  "results": [
    {
      "prompt_id":          "general-bell-state-01",
      "rule":               null,
      "category":           "general",
      "prompt_type":        "generate",
      "context_mode":       "both",
      "sys_prompt_name":    "inline",
      "success":            true,
      "attempts":           2,
      "elapsed_s":          31.4,
      "validation_errors":  "",
      "error":              null,
      "prompt":             "create a bell state circuit",
      "generated_code":     "..."
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `prompt_id` | Unique prompt identifier (e.g. `qkt100-fix-basic-aer-01`) |
| `rule` | QKT rule being tested (e.g. `QKT100`), or `null` for general/multi-rule prompts |
| `category` | Prompt category (e.g. `qiskit1_imports`, `general`) |
| `prompt_type` | `fix` (repair deprecated code) or `generate` (write new code) |
| `success` | `true` if generated code passed all QKT validation rules within the repair budget |
| `attempts` | Number of generate-validate-repair iterations used (1 = passed first try) |
| `elapsed_s` | Wall-clock seconds for the full IVR loop |
| `validation_errors` | QKT rule violations in the final output (empty string if `success: true`) |
| `error` | Python exception string if the run crashed (rare); `null` otherwise |
| `generated_code` | Raw LLM output (may include markdown, explanation text, etc.) |

---

## Known limitations / false positives

**`success: true` does not mean the code is runnable.** The QKT validator only checks for
deprecated API usage — it cannot detect:

- Incorrect but non-deprecated imports (e.g. importing a class that doesn't exist)
- Wrong constructor arguments or method signatures
- Unused imports
- Logic errors

Models that avoid all deprecated patterns but hallucinate incorrect APIs will show
`success: true`. When reviewing results, inspect `generated_code` for plausibility, not
just the `success` flag.

---

## Repair loop

The IVR pattern allows up to `max_repair_attempts` attempts (default 5). On each failure,
the validation error messages (QKT rule codes + descriptions) are fed back to the model
as repair context. The `attempts` field records how many iterations were needed.

A case that exhausts all attempts without passing returns `success: false` and the **last**
generated attempt in `generated_code` (the most refined, since each repair iteration feeds
the previous validation errors back to the model).
