#!/usr/bin/env bash
#
# gather_github.sh — fixed, metadata-only GitHub activity gather for the update-goals skill.
#
# Runs the same set of `gh search` queries against every GitHub host you are logged in to
# (github.com plus any GitHub Enterprise hosts) and prints a markdown report. Only metadata
# is requested (number, title, state, repo, dates, URL) — never bodies or comments.
#
# Usage:
#   gather_github.sh <start-date> [end-date] [--host <host>]... [--limit <n>]
#
#   <start-date>, [end-date]  YYYY-MM-DD, inclusive. end-date defaults to today.
#   --host <host>             Query only this host (repeatable). Default: every host in
#                             `gh auth status`.
#   --limit <n>               Max results per query (default 200). gh's own default is 30,
#                             which silently truncates long periods.
#
# Every host is reported, including failures: a host whose login is broken or unreachable
# prints a HOST UNAVAILABLE line instead of an empty section, so "no activity" and "could
# not look" are never confused.

set -uo pipefail

usage() { sed -n '3,21p' "$0" | sed 's/^# \{0,1\}//'; }

START=""
END=""
LIMIT=200
HOSTS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --host) HOSTS+=("$2"); shift 2 ;;
    --limit) LIMIT="$2"; shift 2 ;;
    -*) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    *)
      if [[ -z "$START" ]]; then START="$1"
      elif [[ -z "$END" ]]; then END="$1"
      else echo "Too many arguments" >&2; exit 2
      fi
      shift ;;
  esac
done

date_re='^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
if [[ ! "$START" =~ $date_re ]]; then
  echo "start-date is required, as YYYY-MM-DD" >&2; usage >&2; exit 2
fi
END="${END:-$(date +%Y-%m-%d)}"
if [[ ! "$END" =~ $date_re ]]; then
  echo "end-date must be YYYY-MM-DD" >&2; exit 2
fi
RANGE="${START}..${END}"

if [[ ${#HOSTS[@]} -eq 0 ]]; then
  while IFS= read -r h; do [[ -n "$h" ]] && HOSTS+=("$h"); done \
    < <(gh auth status --json hosts --jq '.hosts | keys[]' 2>/dev/null)
fi
if [[ ${#HOSTS[@]} -eq 0 ]]; then
  echo "No GitHub hosts found in 'gh auth status'. Log in with 'gh auth login'." >&2
  exit 1
fi

FIELDS="number,title,state,repository,createdAt,closedAt,url"
# One line per item: repo#num — title (state; created, closed) url
LINE_JQ='.[] | "- \(.repository.nameWithOwner)#\(.number) — \(.title) (\(.state); created \(.createdAt[:10])\(if (.closedAt // "" | startswith("20")) then ", closed " + .closedAt[:10] else "" end)) \(.url)"'

# run_query <host> <heading> <prs|issues> <gh search args...>
# Shared flags go right after the subcommand so a trailing `-- <query terms>` stays last.
run_query() {
  local host="$1" heading="$2" kind="$3"; shift 3
  local out count
  echo
  echo "### ${heading}"
  if ! out=$(GH_HOST="$host" gh search "$kind" --limit "$LIMIT" --json "$FIELDS" --jq "$LINE_JQ" "$@" 2>&1); then
    echo "QUERY FAILED: ${out}"
    return
  fi
  if [[ -z "$out" ]]; then
    echo "NONE FOUND"
    return
  fi
  echo "$out"
  count=$(printf '%s\n' "$out" | grep -c '^- ')
  if [[ "$count" -ge "$LIMIT" ]]; then
    echo
    echo "WARNING: hit the ${LIMIT}-result limit; results are truncated. Re-run with a larger --limit or a shorter date range."
  fi
}

echo "# GitHub activity ${START} to ${END}"
echo
echo "Hosts: ${HOSTS[*]}"
echo "Notes: 'Reviewed' uses each PR's last-updated date (GitHub search has no review-date"
echo "filter), so a PR reviewed before the period but updated during it can appear."

for host in "${HOSTS[@]}"; do
  echo
  echo "## ${host}"
  if ! auth_err=$(gh auth status --active -h "$host" 2>&1); then
    reason=$(printf '%s\n' "$auth_err" | grep -E -i 'error|invalid|timeout|failed' | head -1 | sed -E 's/^[[:space:]X-]*//')
    echo
    echo "HOST UNAVAILABLE: ${reason:-login check failed}"
    echo "If the host is up, re-authenticate with: gh auth refresh -h ${host}"
    continue
  fi
  run_query "$host" "PRs I authored, merged in period" \
    prs --author @me --merged-at "$RANGE"
  run_query "$host" "PRs I authored, still open, updated in period" \
    prs --author @me --state open --updated "$RANGE"
  run_query "$host" "PRs by others I reviewed, updated in period" \
    prs --reviewed-by @me --updated "$RANGE" -- -author:@me
  run_query "$host" "Issues I opened, updated in period" \
    issues --author @me --updated "$RANGE"
done
