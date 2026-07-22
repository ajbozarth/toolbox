---
name: review-blogpost-pr
description: >-
  Review a blog post PR before publishing. Checks process compliance, content
  quality, de-llmify score, code correctness, and technical accuracy against the
  relevant source repo. Works in any project — blog path, front-matter schema,
  slug rules, and companion skills are configured or inferred, not hardcoded.
argument-hint: "[pr-url-or-number]"
compatibility: "Claude Code, IBM Bob"
metadata:
  version: "2026-07-14"
  capabilities: [bash, read_file, grep, web_fetch]
---

# Review a Blog PR

A structured pre-publish review for blog post pull requests. Covers process
compliance, editorial quality, LLM-writing tells, code validation, and technical
accuracy.

## Inputs

- `$ARGUMENTS` — a full GitHub PR URL (e.g.
  `https://github.com/org/repo/pull/128`) or a bare PR number (e.g. `128`).
  Optional; if empty, ask which PR to review.

The target PR should be a blog-only change (typically one new `.md` file under
the blog content path). If the PR adds other files, flag it and ask the user how
to proceed.

## Configuration resolution

This skill has no hardcoded project. Resolve each setting below in this order,
stopping at the first that succeeds:

1. **AGENTS.md config block** — read the `## review-blogpost-pr` section of the
   repo's `AGENTS.md` (see the format at the bottom of this file). Authoritative
   when present.
2. **Inference** — infer from the repo (directory layout, existing posts,
   `AGENTS.md`/`CLAUDE.md` prose).
3. **Ask / documented fallback** — use the documented fallback below, or ask.

| Setting | Config key | If unconfigured |
|---|---|---|
| Blog content path | `blog_content_path` | Detect: glob `content/blog*`, `src/content/blog*`; default `content/blogs/`. |
| Front-matter schema | `frontmatter_schema` | Infer from existing posts (the fields their front matter shares); else the documented fallback schema in Step 2. |
| Slug rules | `slug_rules` | Use the documented rules in Step 2. |
| Slug exceptions | `slug_exceptions` | None. (Grandfathered slugs belong in a project's own config, never here.) |
| Source repos root | `source_repos_root` | Parent of the current working directory (`../`). |

---

## Step 1: Gather PR Context

Fetch the PR metadata:

```bash
gh pr view <PR> --repo <owner>/<repo> \
  --json title,headRefName,headRefOid,body,files,author,isDraft,url
```

Record: `headRefName`, `headRefOid`, `files[].path`, `url`, `isDraft`, `author`,
and the PR body.

**Confirm you're reviewing the right artifact — by commit, not by name.** A
worktree or directory named after the PR may be checked out on an unrelated
branch, and a branch *name* can differ from the PR's head ref while the content
is identical. Compare commit OIDs, not names:

```bash
test "$(git rev-parse HEAD)" = "$(gh pr view <PR> --repo <owner>/<repo> --json headRefOid -q .headRefOid)" \
  && echo "on PR head commit" || echo "MISMATCH — investigate before reviewing"
```

A mismatch means HEAD is ahead (unpushed local commits — often fine), behind
(the PR has commits you haven't pulled), or on an unrelated branch. Reconcile
with `git log --oneline -3` against the PR's head OID before reading a single
line. Reviewing the wrong commit wastes a full pass and produces confident,
irrelevant findings.

If the current branch does not match `headRefName` (and the OID check failed),
ask the user to check it out before continuing.

Also scan the PR body and the blog file for author-flagged open questions —
typically `**Reviewer note —**` callouts in the post body, or a numbered "Open
questions for the reviewer" section in the PR description. Note them. The author
already knows about these; they should not appear as your own findings in the
action-item list (acknowledge once if relevant, then move on).

Read the blog file from disk. Identify the file path from `files[].path`.

---

## Step 2: Process Compliance

Read the repository's `AGENTS.md` (or equivalent agent instructions file) for
blog-specific rules, and apply the configuration resolved above. Check every
item:

### File location

- Must be under the resolved blog content path.

### Filename / slug

Apply the slug rules from configuration. If none are configured, use these
common fallback rules:

- No `blog-`, `post-`, `article-`, or `entry-` prefixes — the URL path already
  provides that context.
- Slug is the topic, not a description of the content type.
- Append `-<project>` only if needed to disambiguate a generic topic name.
- Permanent public URL — flag if the slug looks like it would need to change.

Apply any configured `slug_exceptions` (grandfathered slugs that predate the
rules): links to them are fine, and the rules apply to new posts only. If none
are configured, there are no exceptions.

### Front matter

Check all required fields are present and non-empty. Resolve the schema in the
skill's usual order:

1. If a `frontmatter_schema` is configured, use it.
2. Otherwise **infer from existing posts**: read the front matter of a few
   recent posts under the blog content path and treat the fields they all carry
   as required, the ones that vary as optional. This reflects what the project
   actually ships and beats any generic guess. Flag the reviewed post against
   *that* inferred schema.
3. If there are no existing posts to infer from, use this documented fallback
   schema:

| Field | Required | Rule |
|-------|----------|------|
| `title` | Yes | Post title |
| `date` | Yes | `YYYY-MM-DD`, used for listing sort order |
| `author` | Yes | Display name |
| `excerpt` | Yes | One sentence — shown on cards and listing |
| `tags` | No | Array of strings |

Check the date against today's actual date:

```bash
date +%Y-%m-%d
```

Apply these rules — **but only flag stale dates on non-draft PRs**. On a draft,
the front-matter date is a publish-stage concern; the author updates it when
scheduling. Don't list it as an action item.

- **Draft PR**: skip the date-staleness check. Note the date for context only.
- **Past date** (non-draft, even one day ago): ⚠️ flag — may publish with a stale timestamp and sort behind newer posts.
- **Today's date**: ✅ pass.
- **Up to ~2 weeks in the future**: ✅ pass — intended for scheduled publication; note the date informally but do not flag it.
- **More than 2 weeks in the future** (non-draft): ⚠️ flag — likely a placeholder.

### Cross-links

Find all internal links (`[text](/blogs/...)` or the equivalent for the repo's
URL scheme) in the post. For each:
- Confirm the target slug corresponds to an existing file in the blog content path.
- Flag any dead links (target file does not exist).

Do NOT flag existing posts whose slugs predate the naming rules — see any
configured `slug_exceptions`. The rules apply to new posts only.

---

## Step 3: Content Review

Read the full blog post.

The questions below are diagnostic prompts, not a checklist. The absence of "a
runnable example" or "a trade-offs section" is only a finding when the post
would actually be improved by adding one. A short positioning piece that points
at existing capabilities does not need a runnable example. A piece that cites
another post's data does not need to re-explain it.

For each question, ask: "if I added this, would the post be better — or just
longer?" Only flag what would actually improve the post. Do not flag absences
just because the prompt mentions them.

### Structure and flow

- Does the opening get to its point quickly, without restating the topic back to
  the reader?
- Where the post leans on a concrete example, is it close to the top rather than
  buried under theory?
- Does the flow follow the post's own logic, or does it jump?
- Where the post makes a strong claim, does it acknowledge limits or trade-offs
  in places where a thoughtful reader would push back?

### Clarity

- Are new terms defined before use?
- Are diagrams (ASCII or images) accurate and helpful?
- Is the length appropriate for the depth — not padded, not truncated?

### Optional sections

- If a section is optional (requires extra setup, cloud API key, etc.), is it
  clearly flagged?
- Are prerequisites for optional sections listed where they're needed, not all
  upfront?

Flag any usability issues: prerequisites downloaded for sections that are
optional, unclear instructions, steps out of order.

---

## Step 4: de-llmify Check

If `/de-llmify` is available, run it. It edits files in-place. Use the Read and Write tools to handle the restore — no shell commands
needed.

Procedure:

1. Use the Read tool to capture the full file content into memory.

2. Run de-llmify on the file:
   ```
   /de-llmify <path-to-blog.md>
   ```

3. Record the score, the list of flagged sentences verbatim, and the changelog
   that de-llmify produces. This is what you report in the review.

4. Use the Write tool to write the content captured in step 1 back to the same
   path, restoring the original.

If `/de-llmify` is not available, do a manual pass for common LLM-writing tells
(em-dash overuse, "it's not just X, it's Y" constructions, hedging preambles,
listy paragraphs) and note in the review that the automated check was skipped.

Steps 5 and 6 read from the restored original.

---

## Step 5: Code Validation

Find all fenced code blocks in the post. Classify each:

### Executable

Python, shell, Go, JavaScript, TypeScript snippets that are not partial
fragments. A snippet is partial if it contains `...`, `# ...`, `YOUR_`, or
`<your-`.

**Reproduce before critiquing.** Do not infer that a snippet is broken from its
signature — run it and observe. "I ran this and got X" beats "this would raise
X." Every claim that something is broken must be backed by a reproduced error in
a clean environment.

Set up a clean environment rather than testing against whatever happens to be
installed, so you exercise the exact packages the post tells the reader to
install (including any wheel URLs, not substitutes). For example, for a Python
post:

```bash
mkdir /tmp/blog-test-env && cd /tmp/blog-test-env
uv init --bare --python 3.12
# Run EACH install command from the blog verbatim (translating pip→uv where the
# blog recommends uv):
uv add <packages from blog>
uv pip install <any wheel URLs from blog>
```

**Check for sequential dependencies before running.** Some blog posts build
across snippets — snippet 2 imports a file written by snippet 1, or a shell
snippet changes directory for the next one, or module-level state
(`configure(...)`, a session object, shared imports) accumulates across blocks.
Read the post narrative to identify any such chains, and note them in the
report. Run dependent snippets **in order**, preserving state between blocks — an
isolated run can pass while the sequential run a reader actually hits fails. Pass
this context to `/validate-snippets` if it supports it; otherwise run dependent
snippets in order manually.

Run `/validate-snippets <blog-file-path>` (if available) to execute what's
runnable. If a snippet requires packages that aren't installed, install them
first and then run. Do not skip execution just because dependencies are missing.

For snippets that make LLM calls (Ollama, OpenAI, etc.), check whether the
service is reachable before skipping — try `ollama list` or a quick API ping. If
the service is up, run the snippet. If it is genuinely unavailable, report it
explicitly as "skipped: <reason>" in the validation table and do a **static
check** instead. Do not silently fall back to static analysis.

1. Python syntax: `python3 -c "import ast; ast.parse(open('tmp.py').read())"`
2. API accuracy: grep the source repo for the function/class names used. Confirm
   they exist and match the documented signature.

### API accuracy checklist

For each class or function called in the code examples:
- Does it exist in the source repo at the path implied?
- Do the constructor arguments match the source?
- Do the attribute names on return values match the source?
- Are enum/literal values in the allowed set?

Flag any mismatch between blog code and source.

### Expected output blocks

If the blog includes a "you should see output like this" block, verify it is
consistent with what the code would actually produce given the logic.

---

## Step 6: Technical Accuracy

Identify the main technical claims in the post. For each non-trivial claim, check
it against:

1. The source code in the related project repo. Look for sibling repos under the
   source repos root (parent of the current working directory by default) — do
   not search the home directory.
2. Any official documentation linked from the post.

Common claims to verify:
- Parameter names, defaults, and allowed values
- Behavioral descriptions of how a feature works
- Constraints and prerequisites
- Feature availability and optional vs. required arguments

### Citations to other posts on this site

If the post cites a stat, claim, or example from another already-published post
in the blog content path, the only check is that the citation accurately
represents what the linked post says — NOT a re-verification of the linked
post's underlying numbers or claims. Those were reviewed when that post shipped;
re-checking them is out of scope and pads the review with noise.

Concretely: if this post says "the X case study lifted Y from 27% to 50% [link
to /blogs/x-case-study]", check that the linked post does claim 27% to 50%. Do
not go grep the original source repo for the experimental data.

Do NOT verify external claims about competitors, benchmarks, or third-party
tooling unless the post makes a specific numerical claim — flag those for the
author to verify.

When you do report a verified claim in the review, name the source clearly
("citation to /blogs/x-case-study verified") so the reader can tell whether you
checked the cite or the underlying fact.

---

## Step 7: Existing Review Reconciliation

Before compiling, check whether this PR already has reviews or comments from
humans (or prior agent runs). Fetch them — note that `gh pr view --comments`
only returns issue-level comments and review summary bodies; it does NOT return
inline review comments. Use the API directly to get everything:

```bash
# Top-level review bodies
gh pr view <PR> --repo <owner>/<repo> --json reviews \
  | jq '.reviews[] | {author: .author.login, state: .state, body: .body, submitted: .submittedAt}'

# Inline review comments (the ones attached to specific lines)
gh api repos/<owner>/<repo>/pulls/<PR>/comments \
  --jq '.[] | {user: .user.login, path: .path, line: .line, body: .body}'
```

Combine both before proceeding.

For each finding in the existing review(s), determine its status:

| Status | Meaning |
|--------|---------|
| **Addressed** | The code or file has been updated to fix it since the review was posted |
| **Still open** | The finding is unresolved and should appear in the Summary |
| **Superseded** | The skill's review found a more precise version of the same issue |

To check whether a finding was addressed, look at the current state of the file
— not the diff. If the reviewer said "add an import for X" and the import is
present now, it is addressed. If the file is unchanged from the commit the
review was posted against, assume nothing has been addressed.

Then identify any **gaps**: findings in the existing review that the skill's own
checks did not surface. Flag them explicitly — they are missed coverage, not
already-addressed items. Common gap: undefined variables used across snippets
that static syntax checks won't catch.

Report this reconciliation in the compiled review as a new section:

```markdown
### 6. Existing Review Reconciliation

| Finding | Source | Status |
|---------|--------|--------|
| <summary of finding> | @reviewer, <date> | Addressed / Still open / Superseded by #N |

**Gaps in skill coverage:** <findings the existing review caught that the
skill's checks did not surface, with a note on what check would catch them>
```

If there are no prior reviews or comments, skip this section and note "No prior
reviews found."

---

## Step 8: Compile the Review

Write the review as a structured markdown report. Format:

```markdown
## Blog PR Review: <title> (#<PR>)

**Branch:** <headRefName>
**File:** <path>
**Reviewed:** YYYY-MM-DD

---

### 1. Process Compliance

<table: check, result (✅/⚠️/❌), notes>

---

### 2. Content Review

**Strengths:**
<bullet list>

**Issues:**
<numbered list, must-fix vs. consider>

---

### 3. de-llmify Score: <Clean/Minor/Moderate/Heavy>

<findings, or "No significant LLM-writing patterns found.">

---

### 4. Code Validation

<table: snippet, type, result, notes>
<API accuracy findings>

---

### 5. Technical Accuracy

<findings, or "All technical claims verified against source.">

---

### Summary

**Status:** <Ready to publish / Ready with minor fixes / Needs revision>

<numbered action items>
```

Label each action item as:
- **Must fix** — blocks publish (dead link, broken code, wrong API)
- **Should fix** — strong recommendation (UX friction, misleading claim)
- **Consider** — optional improvement (wording, structure)
- **(Pre-existing)** — issue exists in the repo but was not introduced by this PR

The Summary must include every actionable finding from sections 1–5 — including
any de-llmify suggestions — even if they would be "Consider" level. Nothing found
in the body of the review should be absent from the Summary.

**Exclusions from the action-item list:**
- **Author-flagged open questions** (from PR body or in-post `**Reviewer note —**`
  callouts). The author already knows. If you have a non-trivial opinion on one,
  fold it into the relevant section's prose; do not enumerate it as a Must-fix or
  Should-fix item.

  **Verify before excluding.** "Author-flagged" means the *PR author* flagged it
  — not any commenter on the PR. Before treating a PR-body question or an inline
  comment as author-flagged, compare the comment's `user.login` to the PR's
  `author.login` (both fetched in Step 1 / Step 7). If they differ, it's a
  reviewer comment, not an author-flagged question: evaluate the underlying issue
  independently and report what you find, rather than echoing the reviewer's
  question back to them as "the author already knows."
- **Verify-X items you can resolve yourself.** "Verify the `foo[bar]` extras
  exists" is a one-grep check against a sibling repo's `pyproject.toml`. Do the
  check; report the result. Only escalate to a finding if you can't resolve it
  locally.
- **Process items on draft PRs** (front-matter date staleness) — see Step 2.
  These belong to publish-stage scheduling, not content review.

---

## Public-content scrubbing

PR bodies, review comments, and issue text posted to public GitHub are public.
Before posting anything, scrub it: **never let internal repository, host,
infrastructure, or tooling names leak into public-facing content.**

- Internal repo and host names (e.g. an internal tracker, a self-hosted
  `github.<company>.com` link) must never appear in a public comment. If an
  internal-tracker issue is the upstream source, omit the reference entirely —
  do not write "Closes #N in <internal-repo>" or link to the internal host.
- Internal infrastructure and tooling names — compute schedulers, internal CLIs,
  host clusters — leak just as readily through "we validated this on X" asides.
  Rephrase "validated on <internal cluster> via <internal CLI>" to "validated in
  our internal environment."
- This bites hardest when **moving inline draft notes into a public comment** —
  scrub them first.
- Keep suggested-fix code at reader grade: no internal function-routing comments
  (`# routes to _internal_helper`) that are for reviewer explanation, not
  readers. Explanatory mechanism goes in the comment body, not the pasted fix.

This applies to everything this skill might post or hand back for posting.

---

## Step 9: Self-Review Checklist

Before finalizing, verify each item:

| # | Check |
|---|-------|
| 1 | Was the right artifact confirmed by **commit OID** (not branch name) before reading the file? |
| 2 | Were ALL required front matter fields checked (against the configured, inferred, or fallback schema)? |
| 3 | Were ALL internal cross-links checked against actual files? |
| 4 | Was `/de-llmify` run (or a manual pass done and the skip noted) and its exact score and findings included? |
| 5 | Were executable snippets actually run in a clean env? (Static check is only acceptable for snippets that require a live external service — missing packages are not an excuse to skip.) |
| 6 | Were API names and signatures verified against the actual source, not just documentation? |
| 7 | Are pre-existing violations labeled as such, not counted against this PR? |
| 8 | Were existing PR reviews fetched and reconciled (Step 7)? |
| 9 | Does the Summary state a clear ship/hold recommendation? |
| 10 | Was all posted/handed-back content scrubbed of internal repo/host/infra names? |

---

## Common Issues to Watch For

- **Ghost links**: cross-links to posts that don't exist yet
- **API drift**: blog was written against a dev branch; verify the API ships in the released version
- **Output examples**: expected output blocks that don't match what the code would produce
- **Setup ordering**: prerequisites for optional sections downloaded or installed upfront, before the reader knows whether they need them
- **Inferred-state heuristics**: code that infers internal state from observable side effects (which model ran, which path was taken) is often fragile — check for documented assumptions
- **Code-path asymmetries**: frameworks often have multiple validation/execution paths (LLM-driven vs rule-based, streaming vs batch, sync vs async) that look identical but behave differently for the same input. If the post exercises both without naming the distinction, readers adapting the examples will hit silent surprises.

---

## Related Skills

- `/validate-snippets` — run as part of Step 5 for runnable snippets (if present)
- `/de-llmify` — run as part of Step 4 (if present)
- `/get-blog-context` — gather context before a post is written
- `/write-technical-blog` — use when authoring a new post (before this review)

---

## AGENTS.md configuration

A project gets fully-tuned behavior by adding a `## review-blogpost-pr` section
to its `AGENTS.md`. All keys are optional — the skill infers, uses the documented
fallback, or asks for anything absent. Example with neutral placeholder values:

```markdown
## review-blogpost-pr

- blog_content_path: content/blogs/
- source_repos_root: ..
- slug_rules: |
    No blog-/post-/article- prefixes; slug is the topic; append -<project> only
    to disambiguate a generic name; slug is a permanent public URL.
- slug_exceptions: [some-grandfathered-slug.md]
- frontmatter_schema: |
    title (required), date (required, YYYY-MM-DD), author (required),
    excerpt (required, one sentence), tags (optional, array)
```

Notes:

- `blog_content_path` is repo-relative. If omitted, the skill globs
  `content/blog*` / `src/content/blog*` and defaults to `content/blogs/`.
- `source_repos_root` is where sibling source repos are checked out, relative to
  the current repo. Defaults to the parent directory.
- `slug_rules` / `slug_exceptions` override the fallback rules in Step 2.
  Grandfathered slugs go in `slug_exceptions` here — never hardcoded in the
  skill.
- `frontmatter_schema` overrides the fallback schema in Step 2.
