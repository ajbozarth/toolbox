# pytest: skip
# /// script
# dependencies = [
#   "mellea",
#   "flake8-qiskit-migration",
#   "pyarrow",
# ]
# ///
"""Benchmark v2: pure IVR benchmark for the Qiskit code validation example.

Re-runs the benchmark after removing the pre-IVR input validation from the example,
so the IVR loop now does all the work end-to-end. Tests only the Qiskit-specialized
model with no system prompt or grounding context — the intended default configuration.

Two phases run sequentially:
  Phase 1 — QKT prompts (45 × 2 combos = 90 runs)
  Phase 2 — QHE prompts (151 × 2 combos = 302 runs)

Strategies tested:
  repair_template  — RepairTemplateStrategy (validation errors appended to instruction)
  multi_turn       — MultiTurnStrategy (validation errors added as new user message)

Usage:
    # Run from the toolbox benchmarking dir (default paths):
    $ uv run benchmark_v2.py

    # Override the mellea example dir (e.g. when paths differ on LSF):
    $ uv run benchmark_v2.py --example-dir /path/to/qiskit_code_validation

    # Run only one phase:
    $ uv run benchmark_v2.py --phase1
    $ uv run benchmark_v2.py --phase2

    # Resume an interrupted run (picks up the most recent partial JSON):
    $ uv run benchmark_v2.py --resume --phase1
    $ uv run benchmark_v2.py --resume --phase2

LSF example:
    bsub -n 1 -G grp_preemptable -q preemptable \\
      -gpu "num=1/task:mode=shared:j_exclusive=yes" \\
      "bash run_benchmark_with_ollama.sh"
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Allow imports from the example directory.
# Defaults to the parent of this script when benchmarking/ lives inside the example.
# Override with --example-dir <path> when running from a different location (e.g. toolbox repo).
_example_dir = Path(__file__).parent.parent
if "--example-dir" in sys.argv:
    _example_dir = Path(sys.argv[sys.argv.index("--example-dir") + 1])
sys.path.insert(0, str(_example_dir))

from qiskit_code_validation import generate_validated_qiskit_code  # noqa: E402
from validation_helpers import validate_qiskit_migration  # noqa: E402

from mellea import start_session  # noqa: E402
from mellea.backends import ModelOption  # noqa: E402
from mellea.stdlib.context import ChatContext  # noqa: E402
from mellea.stdlib.sampling import MultiTurnStrategy, RepairTemplateStrategy  # noqa: E402

_BENCHMARK_DIR = Path(__file__).parent
_QKT_PROMPTS_FILE = _BENCHMARK_DIR / "qkt_benchmark_v1.json"
_QHE_PARQUET_FILE = _BENCHMARK_DIR / "test-00000-of-00001.parquet"

_MODEL_ID = "hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest"
_MAX_REPAIR_ATTEMPTS = 10

# (strategy_name,) — no system prompt, no grounding context
_COMBINATIONS: list[tuple[str]] = [
    ("repair_template",),
    ("multi_turn",),
]


def _build_strategy(strategy_name: str) -> MultiTurnStrategy | RepairTemplateStrategy:
    if strategy_name == "multi_turn":
        return MultiTurnStrategy(loop_budget=_MAX_REPAIR_ATTEMPTS)
    return RepairTemplateStrategy(loop_budget=_MAX_REPAIR_ATTEMPTS)


def run_benchmark(
    phase: str,
    prompts: list[dict],
    output_dir: Path,
    resume_path: Path | None = None,
) -> Path:
    """Run all prompts × combinations and write results to a JSON file.

    Args:
        phase: Label for this phase (e.g. "qkt", "qhe"). Used in filename.
        prompts: List of prompt dicts with at minimum "prompt" and an id field.
        output_dir: Directory to write the result JSON.
        resume_path: Path to a partial benchmark JSON to resume from.

    Returns:
        Path to the written JSON file.
    """
    completed_keys: set[tuple[str, str]] = set()
    if resume_path is not None:
        existing = json.loads(resume_path.read_text())
        results: list[dict] = existing["results"]
        timestamp = existing["timestamp"]
        out_path = resume_path
        completed_keys = {(r["prompt_id"], r["strategy_name"]) for r in results}
        print(f"\nResuming {phase} from {resume_path.name} ({len(results)} results already recorded)")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir.mkdir(parents=True, exist_ok=True)
        results = []
        out_path = output_dir / f"benchmark_{phase}_{timestamp}.json"

    total = len(prompts) * len(_COMBINATIONS)

    _context = (
        f"Benchmark v2 of Mellea's Instruct-Validate-Repair (IVR) pattern for Qiskit code generation. "
        f"Phase: {phase.upper()}. "
        f"The example was updated to remove pre-IVR input validation; the IVR loop now handles all "
        f"validation end-to-end. Model: {_MODEL_ID}. No system prompt or grounding context — "
        f"the model's built-in Qiskit knowledge is used directly. "
        f"Two strategies compared: repair_template (validation errors appended to instruction) "
        f"and multi_turn (validation errors added as new user message). "
        f"WARNING: success:true means QKT rules passed, NOT that the code is runnable."
    )

    def _flush() -> None:
        passed = sum(r["success"] for r in results)
        out_path.write_text(json.dumps({
            "version": 2,
            "phase": phase,
            "model": _MODEL_ID,
            "timestamp": timestamp,
            "max_repair_attempts": _MAX_REPAIR_ATTEMPTS,
            "summary": {
                "total": total,
                "completed": len(results),
                "passed": passed,
                "failed": len(results) - passed,
            },
            "context": _context,
            "results": results,
        }, indent=2))

    print(f"\n{'=' * 60}")
    print(f"Phase {phase.upper()}: {len(prompts)} prompts × {len(_COMBINATIONS)} combos = {total} runs")
    print(f"Model: {_MODEL_ID}")
    print(f"Output: {out_path}")
    print(f"{'=' * 60}\n")

    run_start = time.time()

    # ChatContext is a superset: works for both strategies.
    with start_session(
        model_id=_MODEL_ID,
        backend_name="ollama",
        ctx=ChatContext(),
        model_options={ModelOption.TEMPERATURE: 0.8, ModelOption.MAX_NEW_TOKENS: 2048},
    ) as m:
        run_num = 0
        for prompt_entry in prompts:
            prompt_id = prompt_entry.get("id") or prompt_entry.get("task_id", "")
            prompt = prompt_entry["prompt"]
            for (strategy_name,) in _COMBINATIONS:
                run_num += 1
                if (prompt_id, strategy_name) in completed_keys:
                    continue

                passed_so_far = sum(r["success"] for r in results)
                total_so_far = len(results)
                pass_rate = f"{passed_so_far}/{total_so_far} passed" if total_so_far else "0/0 passed"
                elapsed_total = time.time() - run_start
                elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_total))
                print(f"[{run_num}/{total} | {pass_rate} | {elapsed_str}] {prompt_id} | {strategy_name}")

                strategy = _build_strategy(strategy_name)

                start = time.time()
                try:
                    code, success, attempts = generate_validated_qiskit_code(
                        m, prompt, strategy
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
                    "check_fn": prompt_entry.get("test") or prompt_entry.get("check_fn"),
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
    print(f"\nPhase {phase.upper()} complete: {passed}/{total} passed")
    print(f"Results: {out_path}")
    return out_path



def _load_qhe_prompts() -> list[dict]:
    import pyarrow.parquet as pq
    if not _QHE_PARQUET_FILE.exists():
        raise FileNotFoundError(f"QHE parquet file not found: {_QHE_PARQUET_FILE}")
    prompts = pq.read_table(_QHE_PARQUET_FILE).to_pylist()
    print(f"Loaded {len(prompts)} QHE prompts from {_QHE_PARQUET_FILE.name}")
    return prompts


def _find_latest(pattern: str) -> Path:
    candidates = sorted(_BENCHMARK_DIR.glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No file matching {pattern} found in {_BENCHMARK_DIR}")
    return candidates[-1]


if __name__ == "__main__":
    run_phase1 = "--phase1" in sys.argv
    run_phase2 = "--phase2" in sys.argv
    run_both = not run_phase1 and not run_phase2  # default: run both

    resume = "--resume" in sys.argv

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = _BENCHMARK_DIR / f"run_ivr_{timestamp}"

    qkt_prompts: list[dict] = json.loads(_QKT_PROMPTS_FILE.read_text())

    if run_phase1 or run_both:
        resume_path = None
        if resume:
            resume_path = _find_latest("run_ivr_*/benchmark_qkt_*.json")
        run_benchmark(phase="qkt", prompts=qkt_prompts, output_dir=run_dir, resume_path=resume_path)

    if run_phase2 or run_both:
        qhe_prompts = _load_qhe_prompts()
        resume_path = None
        if resume:
            resume_path = _find_latest("run_ivr_*/benchmark_qhe_*.json")
        run_benchmark(phase="qhe", prompts=qhe_prompts, output_dir=run_dir, resume_path=resume_path)
