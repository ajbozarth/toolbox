#!/usr/bin/env bash
#
# AI Review Council — fan out a single PR-review prompt to multiple AI CLIs headlessly.
#
# Runs each configured harness in parallel against the current branch + a draft PR body,
# each writing to its own scratchpad/pr-review-<suffix>.md so they don't overwrite each
# other. You analyze and act on the reviews manually afterward.
#
# Usage:
#   pr-review-council.sh [--pr-body <path>] [--dry-run] [-h|--help]

set -uo pipefail

# --- harness lineup -----------------------------------------------------------
# Format: "harness|model|suffix"   (model may be empty to use the harness default)
# Output goes to scratchpad/pr-review-<suffix>.md
# Suffixes are stable (not model-derived) so you can swap models without renaming files.
COUNCIL=(
  "claude|opus|claude"
  "codex||codex"
  "opencode|openai/azure/gpt-5.5|opencode-gpt"
  "opencode|litellm/gcp/gemini-3.1-pro-preview|opencode-gemini"
  "opencode|anthropic/aws/claude-opus-4-8|opencode-opus"
  # gemini-cli: re-enable once the litellm instance picks up the fix.
  # "gemini||gemini"
)

# --- args ---------------------------------------------------------------------
PR_BODY=""
DRY_RUN=0

usage() {
  cat <<EOF
AI Review Council — fan out a PR-review prompt to multiple AI CLIs headlessly.

Usage: $(basename "$0") [options]

Options:
  --pr-body <path>   Path to the draft PR body markdown. If omitted, the script
                     auto-detects a single *.md in scratchpad/ (excluding the
                     pr-review-*.md outputs).
  --dry-run          Print the command that would run for each harness, then exit.
  -h, --help         Show this help.

Council (edit the COUNCIL array in this script to change models/harnesses):
EOF
  local entry harness model suffix
  for entry in "${COUNCIL[@]}"; do
    IFS='|' read -r harness model suffix <<< "$entry"
    printf '  %-9s %-38s -> scratchpad/pr-review-%s.md\n' "$harness" "${model:-(default)}" "$suffix"
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pr-body) PR_BODY="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; echo "Try --help." >&2; exit 2 ;;
  esac
done

# --- resolve repo root from the current working directory ---------------------
# Resolved from where you invoke the script (the repo you're cd'd into), NOT from
# where the script lives — so it works when installed on PATH from any repo.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: not inside a git repository (run this from within the repo you want reviewed)." >&2
  exit 1
}
SCRATCH="$REPO_ROOT/scratchpad"
LOG_DIR="$SCRATCH/pr-review-logs"

# --- resolve PR body ----------------------------------------------------------
if [[ -n "$PR_BODY" ]]; then
  if [[ ! -f "$PR_BODY" ]]; then
    echo "Error: --pr-body path not found: $PR_BODY" >&2
    exit 1
  fi
else
  # Auto-detect: *.md in scratchpad/, excluding the pr-review-*.md outputs.
  candidates=()
  while IFS= read -r f; do
    candidates+=("$f")
  done < <(find "$SCRATCH" -maxdepth 1 -name '*.md' ! -name 'pr-review-*.md' 2>/dev/null | sort)

  if [[ ${#candidates[@]} -eq 0 ]]; then
    echo "Error: no PR body found in $SCRATCH (looked for *.md excluding pr-review-*.md)." >&2
    echo "Create your draft PR body there, or pass --pr-body <path>." >&2
    exit 1
  elif [[ ${#candidates[@]} -gt 1 ]]; then
    echo "Error: multiple candidate PR bodies in $SCRATCH — pass --pr-body <path> to pick one:" >&2
    printf '  %s\n' "${candidates[@]}" >&2
    exit 1
  fi
  PR_BODY="${candidates[0]}"
fi

# Path passed into the prompt, relative to repo root when possible (harnesses run there).
PR_BODY_REL="${PR_BODY#$REPO_ROOT/}"

echo "PR body: $PR_BODY_REL"

# --- prompt template ----------------------------------------------------------
# <PR_BODY> and <SUFFIX> are substituted per harness.
build_prompt() {
  local pr_body="$1" suffix="$2"
  cat <<EOF
Before opening a PR for my current branch, do a PR review.
The planned PR body is at $pr_body for reference.
After completing your review, save the results to a new file scratchpad/pr-review-$suffix.md.
Only review — do not modify any existing files; the only file you may create is your review output file.
EOF
}

# --- build the command for a given harness ------------------------------------
# Builds the argv into the global CMD array.
# Args: harness, model, prompt, suffix, xdg_base
#   xdg_base — parent dir under which opencode instances get an isolated
#   XDG_DATA_HOME (see the opencode branch); ignored by other harnesses.
CMD=()
build_cmd() {
  local harness="$1" model="$2" prompt="$3" suffix="$4" xdg_base="$5"
  CMD=()
  case "$harness" in
    claude)
      CMD=(claude -p "$prompt" --permission-mode bypassPermissions)
      [[ -n "$model" ]] && CMD+=(--model "$model")
      ;;
    codex)
      # network_access=true is required: workspace-write blocks network by default, so a
      # review skill that reads a referenced issue (gh) would hang. Both settings use -c
      # (exec rejects the --ask-for-approval flag). Prompt must come last.
      CMD=(codex exec --sandbox workspace-write \
        -c approval_policy="never" \
        -c 'sandbox_workspace_write.network_access=true')
      [[ -n "$model" ]] && CMD+=(-m "$model")
      CMD+=("$prompt")
      ;;
    opencode)
      # All opencode instances share one SQLite db (~/.local/share/opencode/opencode.db);
      # running them in parallel triggers "database is locked" and a reviewer silently
      # drops out. Give each its own XDG_DATA_HOME so it uses an isolated db. opencode
      # creates the dir itself, so no mkdir needed.
      CMD=(env "XDG_DATA_HOME=$xdg_base/$suffix" opencode run "$prompt" --dangerously-skip-permissions)
      [[ -n "$model" ]] && CMD+=(-m "$model")
      ;;
    gemini)
      CMD=(gemini -p "$prompt" --yolo --skip-trust)
      [[ -n "$model" ]] && CMD+=(-m "$model")
      ;;
    *)
      return 1 ;;
  esac
  return 0
}

# Per-run base dir for opencode's isolated XDG_DATA_HOME (see build_cmd).
XDG_BASE="${TMPDIR:-/tmp}/pr-review-council.$$"

# --- dry run ------------------------------------------------------------------
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "== DRY RUN =="
  for entry in "${COUNCIL[@]}"; do
    IFS='|' read -r harness model suffix <<< "$entry"
    prompt="$(build_prompt "$PR_BODY_REL" "$suffix")"
    if ! build_cmd "$harness" "$model" "$prompt" "$suffix" "$XDG_BASE"; then
      echo "  [skip] unknown harness: $harness"; continue
    fi
    if ! command -v "$harness" >/dev/null 2>&1; then
      echo "  [skip] $harness not found on PATH -> would write pr-review-$suffix.md"; continue
    fi
    printf '  [%s] -> scratchpad/pr-review-%s.md\n' "$harness" "$suffix"
    printf '        %q ' "${CMD[@]}"; echo
  done
  exit 0
fi

# --- run in parallel ----------------------------------------------------------
mkdir -p "$LOG_DIR"
cd "$REPO_ROOT" || { echo "Error: cannot cd to repo root $REPO_ROOT" >&2; exit 1; }

declare -a PIDS SUFFIXES HARNESSES
SKIPPED=()

for entry in "${COUNCIL[@]}"; do
  IFS='|' read -r harness model suffix <<< "$entry"

  if ! command -v "$harness" >/dev/null 2>&1; then
    SKIPPED+=("$harness ($suffix): binary not on PATH")
    continue
  fi

  prompt="$(build_prompt "$PR_BODY_REL" "$suffix")"
  if ! build_cmd "$harness" "$model" "$prompt" "$suffix" "$XDG_BASE"; then
    SKIPPED+=("$harness ($suffix): unknown harness type")
    continue
  fi

  log="$LOG_DIR/$suffix.log"
  echo "Launching $harness (${model:-default}) -> pr-review-$suffix.md  (log: ${log#$REPO_ROOT/})"
  ( "${CMD[@]}" ) >"$log" 2>&1 &
  PIDS+=("$!")
  SUFFIXES+=("$suffix")
  HARNESSES+=("$harness")
done

if [[ ${#PIDS[@]} -eq 0 ]]; then
  echo "No harnesses launched." >&2
  [[ ${#SKIPPED[@]} -gt 0 ]] && printf 'Skipped: %s\n' "${SKIPPED[@]}" >&2
  exit 1
fi

echo
echo "Waiting for ${#PIDS[@]} reviewer(s) to finish..."
echo "This runs headless (no approval prompts) and blocks with no per-reviewer output"
echo "until all finish — typically 5-15 minutes, occasionally longer for a large diff."
echo "Output files appear in scratchpad/ as each reviewer completes if you want to watch."

declare -a EXITS
for i in "${!PIDS[@]}"; do
  wait "${PIDS[$i]}"
  EXITS[$i]=$?
done

# Remove the per-run opencode XDG_DATA_HOME dirs (safe: $$-scoped, our own path).
[[ -n "$XDG_BASE" && -d "$XDG_BASE" ]] && rm -rf "$XDG_BASE"

# --- summary ------------------------------------------------------------------
echo
echo "==================== AI Review Council — summary ===================="
printf '%-24s %-8s %-6s %s\n' "HARNESS/SUFFIX" "EXIT" "OUTPUT" "FILE"
for i in "${!SUFFIXES[@]}"; do
  suffix="${SUFFIXES[$i]}"
  harness="${HARNESSES[$i]}"
  exit_code="${EXITS[$i]}"
  outfile="$SCRATCH/pr-review-$suffix.md"
  if [[ -s "$outfile" ]]; then
    out_status="ok"
  elif [[ -f "$outfile" ]]; then
    out_status="EMPTY"
  else
    out_status="MISSING"
  fi
  printf '%-24s %-8s %-6s %s\n' "$harness/$suffix" "$exit_code" "$out_status" "scratchpad/pr-review-$suffix.md"
done

if [[ ${#SKIPPED[@]} -gt 0 ]]; then
  echo
  echo "Skipped:"
  printf '  - %s\n' "${SKIPPED[@]}"
fi

echo
echo "Logs: ${LOG_DIR#$REPO_ROOT/}/<suffix>.log"
echo "Review outputs written to scratchpad/pr-review-*.md — inspect and act on them manually."
