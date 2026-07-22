# Toolbox
A personal collection of scripts, tools, data, and miscellaneous projects.

## scripts/

Standalone command-line scripts, usable from any repo.

| Script | What it does |
|---|---|
| `pr-review-council.sh` | Fans out a single PR-review prompt to several AI CLIs (claude, codex, opencode) headlessly and in parallel, each writing its own `scratchpad/pr-review-<suffix>.md`. Run it from inside the repo you want reviewed, with a draft PR body in that repo's `scratchpad/`. See `--help`. |

To run these by name from anywhere, add `scripts/` to your `PATH`. Append it to the
**end** so your system commands always take precedence:

```bash
export PATH="$PATH:/path/to/toolbox/scripts"
```

## skills/

Agent skills in the [agentskills.io](https://agentskills.io) `SKILL.md` format, usable
in any repo. Register the directory in your Claude Code `~/.claude/settings.json`:

```json
{
  "skillLocations": [
    "/path/to/toolbox/skills"
  ]
}
```

| Skill | What it does |
|---|---|
| `pr-review-council` | Convene the AI Review Council on the current branch before opening a PR: runs `pr-review-council.sh`, then consolidates every reviewer's findings into one attributed action-item file and hands off to interactive triage. |
| `get-blog-context` | Gather full context for a new blog post before drafting: pull the tracking issue, find related prior posts, survey source repos, report a brief. |
| `review-blogpost-pr` | Pre-publish review of a blog post PR: process compliance, content quality, de-llmify score, code correctness, technical accuracy. |

## mellea/qiskit_code_validation/

Benchmarking research for the [`qiskit_code_validation`](https://github.com/generative-computing/mellea/tree/main/docs/examples/instruct_validate_repair/qiskit_code_validation) Mellea example. Contains benchmark scripts, all run data, system prompt variants, and analysis docs from a multi-phase study of the Mellea Instruct-Validate-Repair (IVR) pattern applied to Qiskit code generation.

See [`mellea/qiskit_code_validation/benchmarking/README.md`](mellea/qiskit_code_validation/benchmarking/README.md) for full details and [`RESEARCH_SUMMARY.md`](mellea/qiskit_code_validation/benchmarking/RESEARCH_SUMMARY.md) for findings.
