---
name: pr-review-council
description: >-
  Convene the AI Review Council on the current branch before opening a PR. Runs
  pr-review-council.sh to fan a review prompt out to several AI CLIs in parallel,
  then consolidates their reviews into a single attributed action-item file and
  stops. Hands off to an interactive, one-at-a-time triage the user drives next.
---

# PR Review Council

Pre-PR review workflow. Runs the review fan-out, then merges every reviewer's
findings into one action-item checklist annotated with consensus + attribution.

This skill covers only the mechanical phases: **run the fan-out → gather →
consolidate → stop**. It does NOT triage items, apply fixes, commit, or open the
PR — the user does that interactively after the skill hands off (see Handoff).

## Usage

```
/pr-review-council
```

No arguments. Run it from inside the repo/worktree you want reviewed, with a
draft PR body already sitting in that repo's `scratchpad/`.

---

## Fixed assumptions

These are stable; do not re-ask:

- **The script is on PATH** as `pr-review-council.sh` (from the personal toolbox).
- **The repo is resolved from the current working directory** — the script uses
  `git rev-parse`, so it operates on whatever repo you're in. Run from inside it.
- **The draft PR body** is the single non-`pr-review-*` `.md` file in `scratchpad/`.
  The script auto-detects it; if it can't, it stops and asks for `--pr-body`.
- **Reviewer outputs** land in `scratchpad/pr-review-<suffix>.md` — one per
  council member (e.g. `pr-review-claude.md`, `pr-review-codex.md`,
  `pr-review-opencode-gpt.md`, `pr-review-opencode-gemini.md`,
  `pr-review-opencode-opus.md`). The opencode set is open-ended — new models
  added to the script produce more `pr-review-opencode-*.md` files.
- **The consolidated output** goes to `scratchpad/pr-review-council-actions.md`.

---

## Steps

### 1. Run the fan-out

From the repo you want reviewed:

```bash
pr-review-council.sh
```

This launches every configured council member in parallel and blocks until the
slowest finishes, then prints a summary table (per-member exit code + whether the
output file was written). Do not background it — let it run to completion.

**Expect a long, silent wait.** After the "Waiting for N reviewer(s)…" line the
script produces NO further output until every reviewer finishes — typically 5-15
minutes, occasionally longer. This silence is normal, not a hang: do NOT kill or
interrupt the command, and do not lower any command timeout below ~30 minutes.
Output files land in `scratchpad/pr-review-*.md` as each reviewer completes, so
that directory is where to look if you want to confirm progress.

Read the summary table. For any member marked `MISSING`, `EMPTY`, or with a
non-zero exit, note it: that reviewer's findings will be absent from the
consolidation. Its log is in `scratchpad/pr-review-logs/<suffix>.log` if the user
wants to know why.

If the script itself errored before launching (no PR body, multiple candidate
bodies), relay its message and stop — the user resolves it and re-runs.

### 2. Gather the reviews

Identify the draft PR body (the single non-`pr-review-*` `.md` in `scratchpad/`)
and read it for context.

Collect the reviewer outputs:

```bash
ls scratchpad/pr-review-claude.md \
   scratchpad/pr-review-codex.md \
   scratchpad/pr-review-gemini.md \
   scratchpad/pr-review-opencode-*.md 2>/dev/null
```

Glob the opencode outputs (`pr-review-opencode-*.md`) so any models added to the
council in the future are picked up automatically. Some named members may be
absent (a skipped/failed reviewer, or gemini when disabled) — that's fine, gather
what exists.

**Do NOT read `scratchpad/pr-review-council-actions.md`** — that is this skill's
own output from a prior run, not a reviewer. (The glob above excludes it by
construction; just don't add it by hand.)

Read every gathered review file in full.

### 3. Consolidate into one action-item file

Merge all findings into a single markdown file at
`scratchpad/pr-review-council-actions.md`. Capture **every** item, no matter how
big or small — the user decides what to skip during triage, not you.

Deduplicate: when multiple reviewers raise the same underlying issue, merge them
into one item and record who flagged it. Rephrase to the clearest single
statement rather than pasting each reviewer's wording.

Annotate every item with **consensus + attribution** — how many members flagged
it and which ones — so the user can weigh agreement during triage. Use this
shape:

```markdown
# PR Review Council — Action Items

**Branch:** <current branch>
**PR body:** scratchpad/<pr-body-file>.md
**Reviewers:** <n> of <total> reported (<list any that were missing/failed>)

---

## Action Items

### 1. <clear one-line statement of the issue>
- **Consensus:** [3/5: claude, codex, opencode-gpt]
- **Where:** <file:line or area, if the reviewers pointed at one>
- **Detail:** <the merged substance — what's wrong and what the reviewers suggest>
- [ ] address / skip

### 2. ...
```

Ordering: put the highest-consensus items first (most reviewers agreeing = most
worth the user's attention), then descending. Within the same consensus count,
keep related items (same file/area) together.

Include a short **Consensus overview** line at the top of the list — e.g.
"2 items flagged by 4+ reviewers, 5 by 2-3, 8 singletons" — so the user sees the
shape before walking it.

Do not editorialize about which to fix. The `[ ] address / skip` checkbox is the
user's to mark in triage.

### 4. Report and STOP

Print a brief summary to the session:

- How many council members reported (and which, if any, were missing).
- The consensus overview (how many items at each agreement level).
- The path: `scratchpad/pr-review-council-actions.md`.

Then **stop**. Do not begin triage. Do not apply any fix. Do not commit or open a
PR. Wait for the user.

---

## Handoff

After the skill stops, the user continues **in the same session** through the
phases this skill deliberately leaves to them:

1. **Triage — one item at a time, interactively.** Walk `pr-review-council-actions.md`
   top to bottom. For each item, present it and wait for the user's decision
   (address / skip / discuss) before moving to the next. Do not batch. Mark each
   item's checkbox as decided.
2. **Apply** the chosen fixes.
3. **Commit or amend** (the user's call which).
4. **Open the PR** using the draft PR body.

When the user signals they're ready to start triage, begin at item 1 and go one
at a time. Don't pre-empt their decisions or start editing before they've chosen.

---

## Constraints

- Run `pr-review-council.sh` to completion in the foreground (Step 1). Its
  parallelism is internal; don't background the whole script.
- Gather reviewer outputs by the known names + the `pr-review-opencode-*.md`
  glob. Never read `pr-review-council-actions.md` as an input.
- Capture every finding in consolidation — completeness over curation. Triage is
  where things get dropped, and that's the user's step.
- Merge duplicates across reviewers into one attributed item; don't list the same
  issue five times.
- This skill ends at "file written + stop." Applying fixes, committing, and
  opening the PR are explicitly out of scope — they happen in the handoff, driven
  by the user.
