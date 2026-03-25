# /// script
# dependencies = [
#   "qiskit",
#   "qiskit-aer",
#   "qiskit-ibm-runtime",
# ]
# ///
"""Run QHE check() functions against generated code from a benchmark JSON.

For each result where QKT validation passed and a check_fn is stored, executes
the generated code and runs check(entry_point) to measure actual correctness.

Usage:
    $ uv run benchmarking/check_analysis.py                        # most recent run
    $ uv run benchmarking/check_analysis.py <path/to/benchmark.json>

Output:
    Prints a summary and writes check_results_<timestamp>.json to the same dir.
"""

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

_BENCHMARK_DIR = Path(__file__).parent


def _strip_markdown_fences(code: str) -> str:
    """Extract code from the first markdown code fence block if present."""
    lines = code.strip().splitlines()
    if not lines or not lines[0].startswith("```"):
        return code
    # Find the closing fence
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "```":
            return "\n".join(lines[1:i])
    # No closing fence found — drop only the opening line
    return "\n".join(lines[1:])


def run_check(generated_code: str, check_fn: str, entry_point: str) -> tuple[str, str]:
    """Execute generated_code then run check(entry_point_fn).

    Returns:
        (status, detail) where status is "pass", "fail_assertion", or "fail_runtime"
    """
    generated_code = _strip_markdown_fences(generated_code)
    namespace: dict = {}
    try:
        exec(generated_code, namespace)  # noqa: S102
    except Exception as e:
        return "fail_runtime", f"{type(e).__name__}: {e}"

    fn = namespace.get(entry_point)
    if fn is None:
        return "fail_runtime", f"entry_point '{entry_point}' not defined after exec"

    try:
        exec(check_fn, namespace)  # noqa: S102
        namespace["check"](fn)
        return "pass", ""
    except AssertionError as e:
        return "fail_assertion", f"AssertionError: {e}"
    except Exception as e:
        return "fail_runtime", f"{type(e).__name__}: {e}"


def analyze(benchmark_path: Path) -> Path:
    benchmark = json.loads(benchmark_path.read_text())
    results = benchmark["results"]

    check_results = []
    counts = {"pass": 0, "fail_assertion": 0, "fail_runtime": 0, "skipped": 0}

    total = len(results)
    for i, r in enumerate(results):
        prompt_id = r["prompt_id"]
        print(f"[{i+1}/{total}] {prompt_id}", end=" ... ", flush=True)

        if not r["success"]:
            print("skipped (QKT failed)")
            counts["skipped"] += 1
            check_results.append({**r, "check_status": "skipped", "check_detail": "QKT validation failed"})
            continue

        if not r.get("check_fn") or not r.get("entry_point"):
            print("skipped (no check_fn)")
            counts["skipped"] += 1
            check_results.append({**r, "check_status": "skipped", "check_detail": "no check_fn"})
            continue

        status, detail = run_check(r["generated_code"], r["check_fn"], r["entry_point"])
        counts[status] += 1
        print(status + (f" — {detail}" if detail else ""))
        check_results.append({**r, "check_status": status, "check_detail": detail})

    qkt_passed = sum(1 for r in results if r["success"])
    check_passed = counts["pass"]
    print(f"\n{'='*60}")
    print(f"QKT passed:       {qkt_passed}/{total} ({100*qkt_passed/total:.1f}%)")
    print(f"check() passed:   {check_passed}/{qkt_passed} of QKT passes ({100*check_passed/qkt_passed:.1f}%)")
    print(f"  fail_assertion: {counts['fail_assertion']}")
    print(f"  fail_runtime:   {counts['fail_runtime']}")
    print(f"  skipped (QKT):  {counts['skipped']}")

    # Break down by difficulty if available
    cats = set(r.get("category") for r in results if r.get("category"))
    if cats:
        print()
        for cat in sorted(cats):
            cat_results = [r for r in check_results if r.get("category") == cat and r["success"]]
            cat_pass = sum(1 for r in cat_results if r["check_status"] == "pass")
            if cat_results:
                print(f"  {cat}: {cat_pass}/{len(cat_results)} check() passed ({100*cat_pass/len(cat_results):.1f}%)")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = benchmark_path.parent / f"check_results_{timestamp}.json"
    out_path.write_text(json.dumps({
        "source_benchmark": benchmark_path.name,
        "model": benchmark.get("model"),
        "summary": {
            "total": total,
            "qkt_passed": qkt_passed,
            "check_passed": check_passed,
            "fail_assertion": counts["fail_assertion"],
            "fail_runtime": counts["fail_runtime"],
            "skipped": counts["skipped"],
        },
        "results": check_results,
    }, indent=2))
    print(f"\nResults written to: {out_path}")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        candidates = sorted(_BENCHMARK_DIR.glob("run_*/benchmark_*.json"))
        if not candidates:
            raise FileNotFoundError("No benchmark JSON found")
        path = candidates[-1]

    print(f"Analyzing: {path.name}\n")
    analyze(path)
