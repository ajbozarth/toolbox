# pytest: skip
# /// script
# dependencies = [
#   "mellea",
#   "flake8-qiskit-migration",
#   "qiskit",
#   "qiskit-aer",
#   "qiskit-ibm-runtime",
#   "pyarrow",
# ]
# ///
"""Benchmark v3: QHE with QKT + check() as dual IVR validators.

Extends v2 by wiring the per-problem QHE check() function into the IVR repair
loop as a second validator alongside flake8-qiskit-migration QKT rules.

With check() assertion messages (qiskit-human-eval PR #88), the repair loop now
receives actionable feedback when generated code passes QKT but fails the
behavioural test — e.g. "Expected 3 qubits, got 5" rather than a silent failure.

Results record QKT pass and check() outcome separately so v3 can be compared
directly against v2 QHE data (QKT-only) to measure whether the richer signal
actually improves end-to-end correctness.

Strategies tested:
  repair_template  — RepairTemplateStrategy (validation errors appended to instruction)
  multi_turn       — MultiTurnStrategy (validation errors added as new user message)

Usage:
    # Run from the toolbox benchmarking dir (default paths):
    $ uv run benchmark_v3.py

    # Override the mellea example dir (e.g. when paths differ on LSF):
    $ uv run benchmark_v3.py --example-dir /path/to/qiskit_code_validation

    # Run only one strategy:
    $ uv run benchmark_v3.py --repair-template
    $ uv run benchmark_v3.py --multi-turn

    # Resume an interrupted run (picks up the most recent partial JSON):
    $ uv run benchmark_v3.py --resume

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


def make_qhe_check_validator(check_fn: str, entry_point: str):
    def _extract_code(text: str) -> str:
        import re
        matches = re.findall(r"```(?:python|py)?\s*(.*?)```", text, re.DOTALL)
        return matches[0].strip() if matches else text.strip()

    def _validate(md_code: str) -> tuple[bool, str]:
        code = _extract_code(md_code)
        namespace: dict = {}
        try:
            exec(code, namespace)
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

        fn = namespace.get(entry_point)
        if fn is None:
            return False, f"Function '{entry_point}' not defined in generated code"

        try:
            exec(check_fn, namespace)
            namespace["check"](fn)
            return True, ""
        except AssertionError as e:
            msg = str(e)
            return False, msg if msg else "Assertion failed (no message)"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    return _validate
from mellea.backends import ModelOption  # noqa: E402
from mellea.stdlib.context import ChatContext  # noqa: E402
from mellea.stdlib.requirements import req, simple_validate  # noqa: E402
from mellea.stdlib.sampling import MultiTurnStrategy, RepairTemplateStrategy  # noqa: E402

_BENCHMARK_DIR = Path(__file__).parent
_QHE_PARQUET_FILE = _BENCHMARK_DIR / "test-00000-of-00001.parquet"

_MODEL_ID = "hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest"
_MAX_REPAIR_ATTEMPTS = 10


def _build_strategy(strategy_name: str) -> MultiTurnStrategy | RepairTemplateStrategy:
    if strategy_name == "multi_turn":
        return MultiTurnStrategy(loop_budget=_MAX_REPAIR_ATTEMPTS)
    return RepairTemplateStrategy(loop_budget=_MAX_REPAIR_ATTEMPTS)


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


def run_benchmark(
    strategies: list[str],
    prompts: list[dict],
    output_dir: Path,
    resume_path: Path | None = None,
) -> Path:
    """Run all prompts × strategies and write results to a JSON file.

    Each prompt gets two validators in the IVR loop:
      1. QKT (flake8-qiskit-migration) — static, same as v2
      2. QHE check() — per-problem behavioural test from the dataset

    Results record the QKT outcome separately from the overall IVR success so
    this run can be compared directly against v2 data.
    """
    completed_keys: set[tuple[str, str]] = set()
    if resume_path is not None:
        existing = json.loads(resume_path.read_text())
        results: list[dict] = existing["results"]
        timestamp = existing["timestamp"]
        out_path = resume_path
        completed_keys = {(r["prompt_id"], r["strategy_name"]) for r in results}
        print(f"\nResuming from {resume_path.name} ({len(results)} results already recorded)")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir.mkdir(parents=True, exist_ok=True)
        results = []
        out_path = output_dir / f"benchmark_qhe_v3_{timestamp}.json"

    combos = [(s,) for s in strategies]
    total = len(prompts) * len(combos)

    _context = (
        f"Benchmark v3 of Mellea's IVR pattern for Qiskit code generation. "
        f"QHE prompts only. Dual validators: QKT (flake8-qiskit-migration) + "
        f"per-problem QHE check() with assertion messages (PR #88). "
        f"Model: {_MODEL_ID}. No system prompt or grounding context. "
        f"success:true means BOTH QKT and check() passed."
    )

    def _flush() -> None:
        passed = sum(r["success"] for r in results)
        out_path.write_text(
            json.dumps(
                {
                    "version": 3,
                    "phase": "qhe",
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
                },
                indent=2,
            )
        )

    print(f"\n{'=' * 60}")
    print(f"QHE v3: {len(prompts)} prompts × {len(combos)} strategies = {total} runs")
    print(f"Validators: QKT (flake8) + QHE check() [PR #88 assertion messages]")
    print(f"Model: {_MODEL_ID}")
    print(f"Output: {out_path}")
    print(f"{'=' * 60}\n")

    run_start = time.time()

    with start_session(
        model_id=_MODEL_ID,
        backend_name="ollama",
        ctx=ChatContext(),
        model_options={ModelOption.TEMPERATURE: 0.8, ModelOption.MAX_NEW_TOKENS: 2048},
    ) as m:
        run_num = 0
        for prompt_entry in prompts:
            prompt_id = prompt_entry.get("task_id", "")
            prompt = prompt_entry["prompt"]
            entry_point = prompt_entry.get("entry_point", "")
            check_fn = prompt_entry.get("test") or prompt_entry.get("check_fn", "")

            for (strategy_name,) in combos:
                run_num += 1
                if (prompt_id, strategy_name) in completed_keys:
                    continue

                passed_so_far = sum(r["success"] for r in results)
                total_so_far = len(results)
                pass_rate = f"{passed_so_far}/{total_so_far} passed" if total_so_far else "0/0 passed"
                elapsed_total = time.time() - run_start
                elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_total))
                print(
                    f"[{run_num}/{total} | {pass_rate} | {elapsed_str}] "
                    f"{prompt_id} | {strategy_name}"
                )

                strategy = _build_strategy(strategy_name)
                extra = []
                if check_fn and entry_point:
                    extra = [
                        req(
                            "Code must pass QHE check() function",
                            validation_fn=simple_validate(
                                make_qhe_check_validator(check_fn, entry_point)
                            ),
                        )
                    ]

                start = time.time()
                try:
                    code, success, attempts = generate_validated_qiskit_code(
                        m, prompt, strategy, extra_requirements=extra or None
                    )
                    _, qkt_errors = validate_qiskit_migration(code)
                    error = None
                except Exception as e:
                    code, success, attempts, qkt_errors = "", False, 0, ""
                    error = str(e)

                elapsed = time.time() - start
                status = "PASS" if success else "FAIL"
                print(f"  → {status} in {attempts} attempt(s), {elapsed:.1f}s")

                results.append(
                    {
                        "prompt_id": prompt_id,
                        "category": prompt_entry.get("difficulty_scale"),
                        "entry_point": entry_point,
                        "check_fn": check_fn,
                        "strategy_name": strategy_name,
                        "success": success,
                        "attempts": attempts,
                        "elapsed_s": round(elapsed, 1),
                        "qkt_errors": qkt_errors,
                        "error": error,
                        "prompt": prompt,
                        "generated_code": code,
                    }
                )
                _flush()

    passed = sum(r["success"] for r in results)
    print(f"\nQHE v3 complete: {passed}/{total} passed (QKT + check())")
    print(f"Results: {out_path}")
    return out_path


if __name__ == "__main__":
    run_repair_template = "--repair-template" in sys.argv
    run_multi_turn = "--multi-turn" in sys.argv
    if run_repair_template and not run_multi_turn:
        strategies = ["repair_template"]
    elif run_multi_turn and not run_repair_template:
        strategies = ["multi_turn"]
    else:
        strategies = ["repair_template", "multi_turn"]

    resume_path = None
    if "--resume-from" in sys.argv:
        resume_path = Path(sys.argv[sys.argv.index("--resume-from") + 1])
    elif "--resume" in sys.argv:
        resume_path = _find_latest("run_v3_*/benchmark_qhe_v3_*.json")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = _BENCHMARK_DIR / f"run_v3_{timestamp}"

    qhe_prompts = _load_qhe_prompts()
    run_benchmark(
        strategies=strategies,
        prompts=qhe_prompts,
        output_dir=run_dir,
        resume_path=resume_path,
    )
