# Qiskit Code Validation — Benchmarking Research

This directory contains all benchmarking scripts, data, and analysis from the research that informed the `qiskit_code_validation` example's default configuration. It is not part of the example itself — it lives here as reference material for the accompanying blog post and video.

---

## Top-level files

| File | Description |
|---|---|
| `benchmark.py` | Main benchmark runner. Runs the IVR pipeline across combinations of models, system prompts, and strategies. See usage below. |
| `check_analysis.py` | Post-run correctness checker. Runs the QHE `check()` unit tests against stored `generated_code` to measure actual correctness beyond QKT pass rate. |
| `qkt_benchmark_v1.json` | 45-prompt benchmark corpus covering QKT100–QKT202 rules + 6 general Qiskit generation tasks. Used for all Phase 0/1 QKT runs. |
| `test-00000-of-00001.parquet` | [Qiskit Human Eval](https://huggingface.co/datasets/Qiskit/qiskit_humaneval) dataset — 151 Qiskit code generation problems with canonical solutions and `check()` unit tests. Used for Phase 2 runs. |
| `BENCHMARK_README.md` | Older doc describing the Phase 0 benchmark output format and field definitions. Still accurate for the `benchmark_*.json` schema. |
| `RESEARCH_SUMMARY.md` | High-level summary of all research phases, findings, and the pre-PR cleanup plan. Start here for context. |
| `ANALYSIS_PROMPT.md` | Prompt used to feed benchmark JSON files to an AI assistant for analysis during Phase 0. Kept for reference. |

---

## `prompts/` — system prompt variants tested

| File | Lines | Description |
|---|---|---|
| `system-prompt-inline.md` | ~22 | Condensed Qiskit expertise prompt written for this example. Baseline for Phase 0. |
| `system-prompt.md` | ~83 | Full qiskit-studio chat-agent prompt. Conversational teaching style. |
| `system-prompt-codegen.md` | ~227 | qiskit-studio codegen-agent prompt. Code-output-only, structured around Qiskit Pattern steps. |
| `system-prompt-qiskit-stripped.md` | ~90 | Production qiskit-studio prompt stripped of safety/non-technical content. |
| `system-prompt-qiskit-short.md` | ~30 | Further-shortened version of the stripped prompt. **Phase 1 winner** for micro-h. Also inlined into `qiskit_code_validation.py` as `QISKIT_SYSTEM_PROMPT`. |
| `system-prompt-qiskit.md` | ~130 | Full stripped prompt with all technical sections. Slightly underperforms `qiskit_short`. |

---

## Benchmark runs

### Phase 0 — Context mode and system prompt sweep (micro-h)

| Run | Model | Config | Prompts | Results |
|---|---|---|---|---|
| `run_20260320_125818/` | granite4:micro-h | Early exploratory run | 45 | Initial analysis; superseded by `run_20260320_174220` |
| `run_20260320_174220/` | granite4:micro-h | All 8 context combinations × 3 system prompts | 45 | 360 cases, 309/360 passed |
| `run_20260321_103850/` | Qiskit model | none/none | 45 | 45 cases, 44/45 passed — quality ceiling baseline |
| `run_20260321_112157/` | granite4:small-h | none/none | 45 | 45 cases, 37/45 passed |

Each `run_*/` dir contains `benchmark_*.json` (raw results) and `analysis_*.md` files written during review.

### Phase 1 — Strategy and system prompt benchmark (micro-h)

| Run | Model | Config | Prompts | Results |
|---|---|---|---|---|
| `run_20260323_134320/` | granite4:micro-h | 7 combos: 3 system prompts × 2 strategies + no-context baseline | 45 | 315 cases, 296/315 passed |
| `run_20260324_145820/` | Qiskit model | 3 combos: none/none + system_prompt/qiskit_short × 2 strategies | 45 | 135 cases, 134/135 passed |

See `run_20260323_134320/analysis_phase1.md` for the full Phase 1 analysis and winner selection.
See `run_20260324_145820/analysis_phase2_qiskit_model_qkt.md` for Qiskit model QKT comparison.

**Phase 1 winner (micro-h):** `system_prompt/qiskit_short/multi_turn` — 97.8% pass, 91.1% first-attempt, 40.6s avg.
**Qiskit model finding:** all configs reach 100% QKT pass; strategy and system prompt are negligible.

### Phase 2 — Qiskit Human Eval dataset (QHE)

Phase 2 runs the same IVR pipeline against the 151-problem QHE corpus and uses `check_analysis.py` to measure actual correctness (not just QKT pass rate).

The phase 2 runs live under a single parent directory `run_phase2_20260323_220911/` which contains separate `run_*/` subdirectories for each model's run (the runner creates a new subdirectory on each invocation).

```
run_phase2_20260323_220911/
  analysis_phase2_micro_h.md          ← micro-h QHE analysis
  analysis_phase2_qiskit_model.md     ← Qiskit model QHE analysis (partial — benchmark still running)
  run_20260323_220911/                ← micro-h run (complete: 151/151)
    benchmark_20260323_220911.json
    check_results_20260324_150030.json
  run_20260324_001943/                ← Qiskit model run (partial: 90/151 as of 2026-03-25)
    benchmark_20260324_001943.json
    check_results_20260325_110918.json
```

| Model | Prompts complete | QKT pass | check() pass |
|---|---|---|---|
| granite4:micro-h | 151/151 | 94.0% | 4.2% |
| Qiskit model | 90/151 (partial) | 100.0% | 40.6% |

**Key finding:** QKT pass rate is a weak signal for general code generation. The Qiskit model passes QKT at 100% but only 40% of outputs are actually correct by `check()`. micro-h passes QKT at 94% but only 4.2% are correct — the repair loop is recovering from deprecated-API mistakes, not knowledge gaps.

---

## Running the benchmark

Requires `uv`. Run from the `qiskit_code_validation/` directory (one level up from `benchmarking/`).

**Note:** When running from the toolbox repo (after the benchmarking dir is moved), `benchmark.py` needs to find `qiskit_code_validation.py` and `validation_helpers.py` from the mellea repo. Use `--example-dir` to point at the example:

```bash
uv run benchmark.py --example-dir /path/to/mellea/docs/examples/instruct_validate_repair/qiskit_code_validation
```

---

```bash
# Full QKT benchmark run (default model and combinations)
uv run benchmarking/benchmark.py

# Run with a specific model and combinations
uv run benchmarking/benchmark.py --model "granite4:micro-h" --combinations "system_prompt/qiskit_short/multi_turn"

# Resume the most recent QKT run
uv run benchmarking/benchmark.py --resume --model "hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest" --combinations "none/none/multi_turn,system_prompt/qiskit_short/multi_turn,system_prompt/qiskit_short/repair_template"

# Run Phase 2 QHE benchmark (all 4 combos, both models)
uv run benchmarking/benchmark.py --phase2

# Resume Phase 2 Qiskit model run
uv run benchmarking/benchmark.py --resume-phase2

# Analyze results (QKT pass rate summary)
uv run benchmarking/benchmark.py --analyze
```

### Combinations format

`--combinations` takes a comma-separated list of `context_mode/sys_prompt_name/strategy` triples:

- `context_mode`: `none` or `system_prompt`
- `sys_prompt_name`: `none`, `inline`, `qiskit_short`, `qiskit`
- `strategy`: `repair_template` or `multi_turn`

Example: `"none/none/repair_template,system_prompt/qiskit_short/multi_turn"`

---

## Running check() analysis

`check_analysis.py` runs the QHE `check()` unit tests against `generated_code` stored in a benchmark JSON. It strips markdown fences before `exec()` to handle models that wrap responses in code blocks.

```bash
# Run from qiskit_code_validation/ directory
uv run benchmarking/check_analysis.py benchmarking/run_phase2_20260323_220911/run_20260324_001943/benchmark_20260324_001943.json
```

Outputs a summary to stdout and writes a `check_results_<timestamp>.json` alongside the benchmark file.

**Note:** `check_analysis.py` requires `qiskit`, `qiskit-aer`, and `qiskit-ibm-runtime` — it uses `uv run` inline script dependencies so no manual install is needed.

---

## Known issues / notes

- **`success: true` ≠ runnable code.** QKT validation only checks for deprecated API patterns. Passing results can still contain hallucinated imports, wrong method signatures, or logic errors. See `BENCHMARK_README.md` for the full list of what QKT cannot catch.
- **Qiskit model wraps responses in markdown fences.** The stored `generated_code` for the Qiskit model includes ` ```python ... ``` ` fence markers and trailing explanation text. QKT validation ignores these (flake8 treats them as syntax errors and skips the file), but `exec()` in `check_analysis.py` needs to strip them first — which it does via `_strip_markdown_fences()`.
- **`run_num` display bug on resume.** When resuming with `--resume` or `--resume-phase2`, the progress counter shows an inflated total (e.g. `[213/135]`) because `run_num` is initialized to the already-completed count and then also incremented for each skipped entry. Does not affect results.
- **Thermal throttling.** The Qiskit model (24B parameters) runs via Ollama on a MacBook without dedicated GPU. Sustained overnight runs can trigger CPU thermal throttling, increasing per-run time from ~2.75 min to ~7 min. A reboot before long runs helps reset thermal state.
