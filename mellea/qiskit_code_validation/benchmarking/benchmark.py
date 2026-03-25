# pytest: skip
# /// script
# dependencies = [
#   "mellea",
#   "flake8-qiskit-migration",
#   "pyyaml",
#   "packaging",
#   "pyarrow",
# ]
# ///
"""Benchmark runner and analysis tool for the Qiskit code validation example.

Runs prompts against context/strategy combinations and writes results to
run_<timestamp>/benchmark_<timestamp>.json.

Also supports sending benchmark results to a local Ollama model for analysis.

Usage:
    # Run QKT benchmark (all prompts x all context combinations):
    $ uv run benchmarking/benchmark.py

    # Run Phase 2 benchmark (QHE dataset, 5 combinations across two models):
    $ uv run benchmarking/benchmark.py --phase2

    # Resume an interrupted Phase 2 Qiskit model run:
    $ uv run benchmarking/benchmark.py --resume-phase2

    # Run analysis on most recent benchmark results:
    $ uv run benchmarking/benchmark.py --analyze

    # When running from a different location (e.g. toolbox repo), point to the example dir:
    $ uv run benchmark.py --example-dir /path/to/qiskit_code_validation
"""

import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# Allow imports from the example directory (qiskit_code_validation.py, validation_helpers.py).
# Defaults to the parent of this script, which works when benchmarking/ lives inside the example.
# Override with --example-dir <path> when running from a different location (e.g. toolbox repo).
_example_dir = Path(__file__).parent.parent
if "--example-dir" in sys.argv:
    _example_dir = Path(sys.argv[sys.argv.index("--example-dir") + 1])
sys.path.insert(0, str(_example_dir))

from qiskit_code_validation import (
    QISKIT_SYSTEM_PROMPT,
    generate_validated_qiskit_code,
)
from validation_helpers import get_qkt_rules_text, validate_qiskit_migration

from mellea import start_session
from mellea.backends import ModelOption
from mellea.stdlib.context import ChatContext
from mellea.stdlib.sampling import MultiTurnStrategy, RepairTemplateStrategy

_EXAMPLE_DIR = Path(__file__).parent.parent
_BENCHMARK_DIR = Path(__file__).parent

_BENCHMARK_PROMPTS_FILE = _BENCHMARK_DIR / "qkt_benchmark_v1.json"
_QHE_PARQUET_FILE = _BENCHMARK_DIR / "test-00000-of-00001.parquet"

BENCHMARK_PROMPTS: list[dict] = json.loads(_BENCHMARK_PROMPTS_FILE.read_text())

# (context_mode, sys_prompt_name, strategy_name)
# strategy_name: "repair_template" or "multi_turn"
_BENCHMARK_COMBINATIONS: list[tuple[str, str | None, str]] = [
    ("none", None, "repair_template"),
    ("system_prompt", "inline", "repair_template"),
    ("system_prompt", "inline", "multi_turn"),
    ("system_prompt", "qiskit_short", "repair_template"),
    ("system_prompt", "qiskit_short", "multi_turn"),
    ("system_prompt", "qiskit", "repair_template"),
    ("system_prompt", "qiskit", "multi_turn"),
]

# Phase 2 — QHE dataset combinations per model
_PHASE2_MODEL_MICRO_H = "granite4:micro-h"
_PHASE2_MODEL_QISKIT = "hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest"

_PHASE2_COMBINATIONS_MICRO_H: list[tuple[str, str | None, str]] = [
    ("system_prompt", "qiskit_short", "multi_turn"),
]
_PHASE2_COMBINATIONS_QISKIT: list[tuple[str, str | None, str]] = [
    ("none", None, "repair_template"),
    ("none", None, "multi_turn"),
    ("system_prompt", "qiskit_short", "repair_template"),
    ("system_prompt", "qiskit_short", "multi_turn"),
]

_SYS_PROMPTS: dict[str, str] = {
    "inline": QISKIT_SYSTEM_PROMPT,
    "qiskit": (_BENCHMARK_DIR / "prompts" / "system-prompt-qiskit-stripped.md").read_text(),
    "qiskit_short": (_BENCHMARK_DIR / "prompts" / "system-prompt-qiskit-short.md").read_text(),
}


def _build_context(
    context_mode: str, sys_prompt_name: str | None, qkt_rules: str
) -> tuple[str | None, dict[str, str] | None]:
    """Return (system_prompt, grounding_context) for a given combination."""
    sys_prompt = _SYS_PROMPTS[sys_prompt_name] if sys_prompt_name else None
    if context_mode == "none":
        return None, None
    elif context_mode == "grounding":
        return None, {"qkt_migration_rules": qkt_rules}
    elif context_mode == "system_prompt":
        return sys_prompt, None
    else:  # both
        return sys_prompt, {"qkt_migration_rules": qkt_rules}


def _build_strategy(
    strategy_name: str, loop_budget: int
) -> MultiTurnStrategy | RepairTemplateStrategy:
    """Return a strategy instance for the given strategy name."""
    if strategy_name == "multi_turn":
        return MultiTurnStrategy(loop_budget=loop_budget)
    return RepairTemplateStrategy(loop_budget=loop_budget)


def run_benchmark(
    model_id: str = "granite4:micro-h",
    max_repair_attempts: int = 10,
    output_dir: Path | None = None,
    resume_path: Path | None = None,
    combinations: list[tuple[str, str | None, str]] | None = None,
    prompts: list[dict] | None = None,
) -> Path:
    """Run all prompts x all context combinations and write results to JSON.

    Args:
        model_id: Ollama model to benchmark.
        max_repair_attempts: Repair loop budget per run.
        output_dir: Directory to write results (defaults to benchmarking/).
        resume_path: Path to a partial benchmark JSON to resume from.
        combinations: Subset of _BENCHMARK_COMBINATIONS to run. Defaults to all.
        prompts: Prompt list to run. Defaults to BENCHMARK_PROMPTS (QKT).

    Returns:
        Path to the written JSON file.
    """
    active_combinations = combinations or _BENCHMARK_COMBINATIONS
    active_prompts = prompts or BENCHMARK_PROMPTS
    qkt_rules = get_qkt_rules_text()

    # Resume from existing partial run, or start fresh
    completed_keys: set[tuple[str, str, str | None]] = set()
    if resume_path is not None:
        existing = json.loads(resume_path.read_text())
        results: list[dict] = existing["results"]
        timestamp = existing["timestamp"]
        run_dir = resume_path.parent
        out_path = resume_path
        completed_keys = {
            (r["prompt_id"], r["context_mode"], r["sys_prompt_name"], r["strategy_name"]) for r in results
        }
        print(f"\nResuming from {resume_path.name} ({len(results)} results already recorded)")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = (output_dir or _BENCHMARK_DIR) / f"run_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        results = []
        out_path = run_dir / f"benchmark_{timestamp}.json"

    total = len(active_prompts) * len(active_combinations)

    _context = (
        "Benchmark of Mellea's Instruct-Validate-Repair (IVR) pattern for Qiskit code generation. "
        "A small LLM is asked to generate or fix Qiskit code; output is validated against "
        "flake8-qiskit-migration (QKT) rules and repaired automatically on failure. "
        "The benchmark isolates three variables: (1) system prompt variant — none, inline "
        "(condensed Qiskit expertise), qiskit_short (stripped production prompt, short), or "
        "qiskit (stripped production prompt, full); (2) context_mode — none or system_prompt; "
        "(3) strategy — repair_template (validation failures appended to instruction) or "
        "multi_turn (validation failures added as new user message). "
        "WARNING: success:true means QKT rules passed, NOT that the code is runnable — "
        "hallucinated but non-deprecated APIs pass validation. Inspect generated_code directly. "
        "See BENCHMARK_README.md for full field descriptions and limitations."
    )

    def _flush() -> None:
        passed = sum(r["success"] for r in results)
        out_path.write_text(json.dumps({
            "model": model_id,
            "timestamp": timestamp,
            "max_repair_attempts": max_repair_attempts,
            "summary": {"total": total, "completed": len(results), "passed": passed, "failed": len(results) - passed},
            "context": _context,
            "results": results,
        }, indent=2))

    print(f"\nBenchmark: {len(active_prompts)} prompts × {len(active_combinations)} combinations = {total} runs")
    print(f"Model: {model_id}\n")

    run_start = time.time()

    # MultiTurnStrategy requires ChatContext; RepairTemplateStrategy works with SimpleContext.
    # Use ChatContext for all runs since it is a superset — RepairTemplate ignores multi-turn history.
    with start_session(
        model_id=model_id,
        backend_name="ollama",
        ctx=ChatContext(),
        model_options={ModelOption.TEMPERATURE: 0.8, ModelOption.MAX_NEW_TOKENS: 2048},
    ) as m:
        run_num = 0
        for prompt_entry in active_prompts:
            prompt_id = prompt_entry.get("id") or prompt_entry.get("task_id", "")
            prompt = prompt_entry["prompt"]
            for context_mode, sys_prompt_name, strategy_name in active_combinations:
                run_num += 1
                if (prompt_id, context_mode, sys_prompt_name, strategy_name) in completed_keys:
                    continue

                passed_so_far = sum(r["success"] for r in results)
                total_so_far = len(results)
                pass_rate = f"{passed_so_far}/{total_so_far} passed" if total_so_far else "0/0 passed"
                elapsed_total = time.time() - run_start
                elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_total))
                combo_label = f"{context_mode}/{sys_prompt_name or 'none'}/{strategy_name}"
                print(f"[{run_num}/{total} | {pass_rate} | {elapsed_str}] {prompt_id} | {combo_label}")

                system_prompt, grounding_context = _build_context(
                    context_mode, sys_prompt_name, qkt_rules
                )
                strategy = _build_strategy(strategy_name, max_repair_attempts)

                start = time.time()
                try:
                    code, success, attempts = generate_validated_qiskit_code(
                        m,
                        prompt,
                        strategy,
                        system_prompt=system_prompt,
                        grounding_context=grounding_context,
                    )
                    _, validation_errors = validate_qiskit_migration(code)
                    error = None
                except Exception as e:
                    code, success, attempts, validation_errors = "", False, 0, ""
                    error = str(e)

                elapsed = time.time() - start
                status = "PASS" if success else "FAIL"
                print(f"  → {status} in {attempts} attempt(s), {elapsed:.1f}s")

                results.append({
                    "prompt_id": prompt_id,
                    "rule": prompt_entry.get("rule"),
                    "category": prompt_entry.get("category") or prompt_entry.get("difficulty_scale"),
                    "prompt_type": prompt_entry.get("prompt_type", "generate"),
                    "entry_point": prompt_entry.get("entry_point"),
                    "check_fn": prompt_entry.get("test"),
                    "context_mode": context_mode,
                    "sys_prompt_name": sys_prompt_name,
                    "strategy_name": strategy_name,
                    "success": success,
                    "attempts": attempts,
                    "elapsed_s": round(elapsed, 1),
                    "validation_errors": validation_errors,
                    "error": error,
                    "prompt": prompt,
                    "generated_code": code,
                })
                _flush()

    passed = sum(r["success"] for r in results)
    print(f"\nResults written to: {out_path}")
    print(f"Summary: {passed}/{total} passed")
    return out_path


def run_phase2_benchmark(output_dir: Path | None = None) -> None:
    """Run Phase 2 benchmark: QHE dataset across micro-h and Qiskit model.

    Runs 5 combinations total (1 for micro-h, 4 for Qiskit model) and writes
    two benchmark JSON files into a shared run_phase2_<timestamp>/ directory.
    """
    import pyarrow.parquet as pq

    if not _QHE_PARQUET_FILE.exists():
        raise FileNotFoundError(f"QHE parquet file not found: {_QHE_PARQUET_FILE}")

    qhe_prompts = pq.read_table(_QHE_PARQUET_FILE).to_pylist()
    print(f"Loaded {len(qhe_prompts)} QHE prompts from {_QHE_PARQUET_FILE.name}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = (output_dir or _BENCHMARK_DIR) / f"run_phase2_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Phase 2 output dir: {run_dir}\n")

    run_benchmark(
        model_id=_PHASE2_MODEL_MICRO_H,
        prompts=qhe_prompts,
        combinations=_PHASE2_COMBINATIONS_MICRO_H,
        output_dir=run_dir,
    )
    run_benchmark(
        model_id=_PHASE2_MODEL_QISKIT,
        prompts=qhe_prompts,
        combinations=_PHASE2_COMBINATIONS_QISKIT,
        output_dir=run_dir,
    )


def run_analysis(
    benchmark_path: Path | None = None,
    model_id: str = "hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest",
    output_dir: Path | None = None,
) -> Path:
    """Send benchmark results to the Qiskit model for analysis via Ollama.

    Strips generated_code from results to keep the prompt within the model's
    context window, then writes the response to analysis_qiskit_<timestamp>.md.

    Args:
        benchmark_path: Path to benchmark JSON. Defaults to most recent run.
        model_id: Ollama model to use for analysis.
        output_dir: Directory to write analysis (defaults to the run dir).

    Returns:
        Path to the written analysis file.
    """
    if benchmark_path is None:
        candidates = sorted(_BENCHMARK_DIR.glob("run_*/benchmark_*.json"))
        if not candidates:
            raise FileNotFoundError("No benchmark JSON found in benchmarking run subdirectories")
        benchmark_path = candidates[-1]

    output_dir = output_dir or benchmark_path.parent

    print(f"Analyzing: {benchmark_path.name}")
    print(f"Model: {model_id}\n")

    benchmark = json.loads(benchmark_path.read_text())
    # Strip generated_code to keep the prompt within the model's context window
    stripped = {
        **benchmark,
        "results": [{k: v for k, v in r.items() if k != "generated_code"} for r in benchmark["results"]],
    }
    analysis_prompt = (_BENCHMARK_DIR / "ANALYSIS_PROMPT.md").read_text()
    benchmark_readme = (_BENCHMARK_DIR / "BENCHMARK_README.md").read_text()

    prompt = (
        f"{analysis_prompt}\n\n"
        f"---\n\n"
        f"## BENCHMARK_README.md\n\n{benchmark_readme}\n\n"
        f"---\n\n"
        f"## Benchmark Results\n\n"
        f"```json\n{json.dumps(stripped, indent=2)}\n```"
    )

    payload = json.dumps({
        "model": model_id,
        "prompt": prompt,
        "stream": True,
        "options": {"num_predict": 4096},
    }).encode()

    prompt_tokens_est = len(prompt) // 4
    print(f"Sending to Ollama... (~{prompt_tokens_est:,} tokens estimated, this may take a while)")
    print("Streaming response: ", end="", flush=True)
    ollama_req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    chunks = []
    with urllib.request.urlopen(ollama_req, timeout=120) as resp:
        for line in resp:
            chunk = json.loads(line.decode())
            token = chunk.get("response", "")
            chunks.append(token)
            print(token, end="", flush=True)
            if chunk.get("done"):
                break
    print()  # newline after streaming

    analysis_text = "".join(chunks)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"analysis_qiskit_{timestamp}.md"
    out_path.write_text(f"# Benchmark Analysis — Qiskit Model ({timestamp})\n\n{analysis_text}")

    print(f"Analysis written to: {out_path}")
    return out_path


if __name__ == "__main__":
    # Parse --model <model_id>
    _model_id = "granite4:micro-h"
    if "--model" in sys.argv:
        _model_id = sys.argv[sys.argv.index("--model") + 1]

    # Parse --combinations <mode/variant/strategy,...>  e.g. "none/none/repair_template,system_prompt/inline/multi_turn"
    _combinations: list[tuple[str, str | None, str]] | None = None
    if "--combinations" in sys.argv:
        raw = sys.argv[sys.argv.index("--combinations") + 1]
        _combinations = []
        for entry in raw.split(","):
            mode, variant, strategy = entry.strip().split("/")
            _combinations.append((mode, None if variant == "none" else variant, strategy))

    if "--phase2" in sys.argv:
        run_phase2_benchmark()
    elif "--resume-phase2" in sys.argv:
        import pyarrow.parquet as pq
        qhe_prompts = pq.read_table(_QHE_PARQUET_FILE).to_pylist()
        candidates = sorted(_BENCHMARK_DIR.glob("run_phase2_*/run_*/benchmark_*.json"))
        if not candidates:
            raise FileNotFoundError("No phase2 benchmark JSON found to resume")
        run_benchmark(
            model_id=_PHASE2_MODEL_QISKIT,
            prompts=qhe_prompts,
            combinations=_PHASE2_COMBINATIONS_QISKIT,
            resume_path=candidates[-1],
        )
    elif "--analyze" in sys.argv:
        run_analysis()
    elif "--resume" in sys.argv:
        candidates = sorted(_BENCHMARK_DIR.glob("run_*/benchmark_*.json"))
        if not candidates:
            raise FileNotFoundError("No benchmark JSON found to resume")
        run_benchmark(model_id=_model_id, resume_path=candidates[-1], combinations=_combinations)
    else:
        run_benchmark(model_id=_model_id, combinations=_combinations)
