# /// script
# dependencies = [
#   "datasets",
#   "pyarrow",
# ]
# ///
"""Download the Qiskit Human Eval dataset to a local parquet file.

Two sources are supported:

  HuggingFace (default):
    Downloads "Qiskit/qiskit_humaneval" from HuggingFace. Use --revision to
    pin a specific branch or commit SHA (e.g. after the dataset is regenerated
    from a merged PR).

  GitHub PR branch (--from-pr):
    Fetches the raw JSON dataset files from an open GitHub PR branch and
    converts them to parquet. Use this before the HuggingFace dataset has been
    regenerated from the PR (e.g. qiskit-community/qiskit-human-eval PR #88
    which adds assertion messages to check() functions).

Usage:
    uv run fetch_dataset.py                       # HuggingFace main
    uv run fetch_dataset.py --revision <sha/ref>  # HuggingFace specific revision
    uv run fetch_dataset.py --from-pr 88          # GitHub PR #88 branch
    uv run fetch_dataset.py --out /path/to/custom.parquet
"""

import json
import sys
import urllib.request
from pathlib import Path

_BENCHMARK_DIR = Path(__file__).parent
_DEFAULT_OUT = _BENCHMARK_DIR / "test-00000-of-00001.parquet"

_HF_REPO = "Qiskit/qiskit_humaneval"
_GH_RAW_TEMPLATE = (
    "https://raw.githubusercontent.com/qiskit-community/qiskit-human-eval"
    "/refs/pull/{pr}/head/dataset/dataset_qiskit_test_human_eval.json"
)


def _fetch_from_hf(revision: str, out_path: Path) -> None:
    from datasets import load_dataset

    print(f"Downloading {_HF_REPO} (revision={revision!r}) from HuggingFace...")
    ds = load_dataset(_HF_REPO, split="test", revision=revision)
    ds.to_parquet(str(out_path))
    print(f"Saved {len(ds)} rows → {out_path}")


def _fetch_from_pr(pr: int, out_path: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    url = _GH_RAW_TEMPLATE.format(pr=pr)
    print(f"Fetching PR #{pr} dataset from:\n  {url}")
    try:
        with urllib.request.urlopen(url) as resp:  # noqa: S310
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} fetching {url} — is the PR number correct and still open?")

    if not isinstance(data, list) or not data:
        sys.exit(f"Unexpected response format from {url}")

    table = pa.Table.from_pylist(data)
    pq.write_table(table, out_path)
    print(f"Saved {len(data)} rows → {out_path}")


if __name__ == "__main__":
    args = sys.argv[1:]

    out_path = _DEFAULT_OUT
    if "--out" in args:
        out_path = Path(args[args.index("--out") + 1])

    if "--from-pr" in args:
        pr = int(args[args.index("--from-pr") + 1])
        _fetch_from_pr(pr, out_path)
    else:
        revision = "main"
        if "--revision" in args:
            revision = args[args.index("--revision") + 1]
        _fetch_from_hf(revision, out_path)
