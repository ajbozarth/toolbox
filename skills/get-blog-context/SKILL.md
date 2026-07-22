---
name: get-blog-context
description: >-
  Gather full context for a new blog post before drafting begins. Pulls the
  tracking issue, finds related prior posts, surveys the source repos the post
  will draw on, then reports back a structured brief and stops. Hands off to a
  drafting skill after the user gives direction. Works in any project — the
  issue's repo, blog path, and source repos are configured or inferred, not
  hardcoded.
argument-hint: "[issue-url-or-number]"
compatibility: "Claude Code, IBM Bob"
metadata:
  version: "2026-07-14"
  capabilities: [bash, read_file, grep, web_fetch]
---

# Get Blog Context

Prep skill for starting a new blog post. It resolves a tracking issue, pulls the
material the post will draw on, surveys the referenced source repos, and reports
a structured brief — then **stops**. The user will follow up with their vision
for the post; do NOT begin drafting until they do.

## Inputs

- `$ARGUMENTS` — a full issue URL (e.g.
  `https://github.com/org/repo/issues/40`) or a bare issue number (e.g. `40`).
  Optional; if empty, ask which issue to pull.

The tracking issue lives in the **current repo** by default. A bare number is an
issue here; only a full URL or the `tracking_repo` config below points elsewhere.

## Configuration resolution

This skill has no hardcoded project. Resolve each setting below in this order,
stopping at the first that succeeds:

1. **AGENTS.md config block** — read the `## get-blog-context` section of the
   repo's `AGENTS.md` (see the format at the bottom of this file). This is the
   authoritative source when present.
2. **Inference** — infer from the repo (directory layout, `AGENTS.md`/`CLAUDE.md`
   prose).
3. **Ask** — if a required value can't be resolved, ask the user rather than
   guessing.

| Setting | Config key | If unconfigured |
|---|---|---|
| Issue repo | `tracking_repo` | The **current** repo (a bare number is an issue here). |
| Blog content path | `blog_content_path` | Read `AGENTS.md`/`CLAUDE.md` prose; else glob `content/blog*`, `src/content/blog*`. |
| Source repos root | `source_repos_root` | Parent of the current working directory (`../`). |
| Handoff skill | `handoff_skill` | `write-technical-blog`. |

---

## Steps

### 1. Resolve the issue

Determine the issue number and its repo from `$ARGUMENTS`:

- **Bare number** → an issue in the current repo (or `tracking_repo`, if configured).
- **Full URL** → parse the owner/repo and issue number from it.
- **Empty** → ask which issue to pull.

Fetch the issue. When it's in the current repo, `gh` resolves the host and auth
from the working directory automatically — no `--repo` needed, whether the repo
is on public GitHub or a GitHub Enterprise (GHE) host:

```bash
gh issue view <number> \
  --json number,title,body,state,labels,assignees,comments,url
```

When the issue is in a **different** repo, add `--repo <owner>/<repo>`. On public
GitHub that's all it needs. On a **GHE** host, `gh` defaults to `github.com`
unless it can tell otherwise, so set the host explicitly — either
`GH_HOST=<ghe-host> gh issue view ... --repo <owner>/<repo>`, or run the command
from inside a local checkout of that host. (`<ghe-host>`, e.g. a self-hosted
`github.<company>.com`, is a neutral placeholder — never hardcode a real host.)

Read the title, body, and all comments carefully. Extract:

- **Blog topic / angle** the issue describes
- **Referenced PRs, commits, issues** (in this repo or others)
- **Referenced features, code paths, file names**
- **Any deadlines, audience, or framing the issue calls out**
- **Whether this post is a follow-up to a prior post** (a common pattern)

### 2. Pull linked items

For every PR, issue, or discussion referenced in the issue body or comments,
fetch it with `gh issue view` / `gh pr view` (add `--repo <owner>/<repo>` for
items in another repo; the same GHE host note from Step 1 applies).

Capture title, status (open/merged/closed), and a one-line summary of each
linked item.

### 3. Find related prior blog posts

Blogs live in the current repo under the resolved blog content path. If the
issue indicates this is a follow-up, find the prior post(s):

- Search the blog content path (verify the directory against the actual repo
  structure) for posts by the same author or on adjacent topics.
- Pull title, slug, date, and a one-line summary of any prior post that looks
  related.

### 4. Survey referenced source repos

For each repo the issue references:

1. Check if it exists under the source repos root (`../<repo-name>` by default).
   If not, note "not checked out locally" and skip the local checks (still fetch
   GitHub-side context).
2. If checked out, gather:
   - Current branch and whether it's clean (`git status -s`)
   - Most recent merged PRs related to the blog topic — search by keyword from
     the issue (`gh pr list --repo <owner>/<repo> --state merged --search "<keyword>" --limit 10`)
   - The specific PRs/commits/files the issue calls out (read the relevant code
     paths if they're named)
3. If the issue points at a specific PR or commit, fetch its title, description,
   and changed files — that's the primary source material for the blog.

Only look at repos under the source repos root — do NOT walk further up the
tree.

### 5. Report back — and STOP

Produce a structured brief. Do not start drafting. Use this shape:

```markdown
# Blog Context Brief: <issue title>

## Tracking issue
- **Repo**: <owner/repo>
- **Issue**: #<n> — <title>
- **State**: <open/closed>
- **Summary**: <2-3 sentence summary of what the issue asks for>
- **Audience / framing called out**: <if any>

## Source material
<List of PRs, commits, files, features the blog will cover. For each,
include repo, identifier, status, and one-line summary.>

## Prior art
- **Follow-up to**: <prior blog post if applicable, with link/path>

## Source repo state
<For each referenced repo: checked out yes/no, branch, any recent
relevant PRs.>

## Open questions for you
<Things the issue does not resolve and that I'd need your direction on
before drafting — angle, depth, target length, code examples to include,
etc.>

## Ready when you are
Share your vision for the post and I'll kick off the drafting skill with
this context loaded.
```

After printing the brief, **stop**. Do not invoke any other skill. Do not begin
drafting. Wait for the user.

---

## Handoff

When the user responds with their direction, naturally invoke the configured
handoff skill (default `/write-technical-blog`), passing along the issue number
/ PR references / topic so it has the full context. Do not require the user to
re-state anything from the brief.

---

## Constraints

- Only look at repos under the source repos root. Do NOT look at directories
  above it.
- Do NOT read large source files exhaustively — pull the specific files the
  issue points at and skim. Save deep reads for the drafting phase.
- Keep the brief scannable. Bullets over prose.
- If a `gh` command fails (auth, rate limit, missing repo), note what was
  unavailable and continue with what you have.

---

## AGENTS.md configuration

A project gets fully-tuned behavior by adding a `## get-blog-context` section to
its `AGENTS.md`. All keys are optional — the skill infers or asks for anything
absent. Example with neutral placeholder values:

```markdown
## get-blog-context

- tracking_repo: org/repo
- blog_content_path: content/blogs/
- source_repos_root: ..
- handoff_skill: write-technical-blog
```

Notes:

- `tracking_repo` is `owner/repo`, only needed when the tracking issue lives in a
  **different** repo than the current one. Omit it when issues are filed in the
  current repo (the default).
- `blog_content_path` is repo-relative. If omitted, the skill reads
  `AGENTS.md`/`CLAUDE.md` prose, then globs `content/blog*` and `src/content/blog*`.
- `source_repos_root` is where sibling source repos are checked out, relative to
  the current repo. Defaults to the parent directory.
- `handoff_skill` is the drafting skill invoked after you give direction.
  Defaults to `write-technical-blog`.
