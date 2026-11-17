---
name: update-goals
description: >-
  Draft updates for work goals tracked in SAP SuccessFactors, with the user in
  the loop. Reads the goals from a PDF the user exports, gathers GitHub activity
  across every logged-in host, walks the user through Microsoft 365 Copilot
  prompts for email/calendar/Teams evidence, then drafts an overview of what the
  user did in the period followed by one paste-ready comment per goal,
  suggested status changes, work that fits no goal, and suggested new goals.
  Refines in chat. Never writes to SuccessFactors; the user pastes
  the final comments in. Use for goal updates, goal check-ins, or year-end
  review prep.
argument-hint: "[period, e.g. 'since 2026-08-01' or 'Q3'] (optional)"
compatibility: "Claude Code, IBM Bob"
metadata:
  version: "2026-11-16"
  capabilities: [bash, read_file]
---

# Update Goals

Draft goal updates for SAP SuccessFactors (SF) from the user's real activity.
The output has two parts: an overview of everything the user did in the
period, and the goal updates drawn from it. The agent gathers what it can reach directly (GitHub); the user brings in what
it can't (the goals themselves, Microsoft 365 evidence via Copilot, anything
else they remember). Everything happens in the chat. The user stays in control
of every step and does all writing to SF themselves.

## Inputs

- `$ARGUMENTS`: optional review period that overrides the default (see step 2).
  Accept anything a person would say: `since 2026-08-01`, `Q3`,
  `Jul 1 - Sep 30`. If empty, use the default period.
- The SF goals PDF, requested in step 1.

## Rules for every step

- **Report only what a source shows.** Never invent PRs, meetings, emails,
  people, numbers, or outcomes. If something is unclear, ask.
- **Don't force work into goals.** Map an item to a goal only when it clearly
  fits. Notable work that fits no goal goes in "Not covered by current goals".
- **Status changes are separate.** Never fold a status change into a comment.
  List each one with its reason, so the user can decide.
- **Chat first.** Don't write files unless the user asks. If they do, write to
  `./scratchpad/` only after confirming it is gitignored (`git check-ignore
  scratchpad`); otherwise ask where.
- **Metadata by default.** Don't open the bodies of issues or PRs, or the
  contents of repos, unless the user asks for a specific one.
- **The user drives.** Pause where a step says to wait. Never move on from a
  Copilot prompt until the user pastes the reply or says to skip it.

---

## Steps

### 1. Load the goals

Ask the user for their goals as a PDF, if they haven't already given a path:

> In SuccessFactors, open your goal plan's goal list, use its print option, and
> save as PDF. Then give me the file path.

Read the PDF and build a goals table: title, category, status, due date,
description, and every comment with its date. Some tools return the PDF as
extracted text rather than page images. That text has known quirks; correct
for them:

- A goal title may repeat several times, run together
  (`...outsideTake initiative...outside my comfort zonemy comfort zone`).
  Use the single clean title.
- Comment author names can come loose from their comments, appearing as a
  separate run of names. Match comments to dates, not to names.
- URLs that wrapped at a hyphen may have lost it
  (`generativecomputing` for `generative-computing`). Check URLs that look
  wrong against the gathered GitHub data.

Show the user a short table, one row per goal: title, category, status, due
date, date of the latest comment. Ask them to confirm it's right before going on.

### 2. Set the period

There is one period for all goals.

- **Default:** from the **most recent** comment date across all goals to today.
  That date marks the user's last update session. A goal with an older latest
  comment wasn't skipped; it had nothing new to report then, so its older date
  is not a starting point.
- **Override:** if `$ARGUMENTS` (or the user) gives a period, use it instead.
  If it starts before the last update session, compare it with the existing
  comments and flag any overlap, so the draft doesn't repeat what's already
  posted.

Tell the user the period and how it was chosen, then continue.

### 3. Gather GitHub activity

Run the bundled [gather script](scripts/gather_github.sh) for the period:

```bash
<this skill's directory>/scripts/gather_github.sh <start> <end>
```

It queries every host in `gh auth status` (github.com and any GitHub
Enterprise hosts) with the same fixed, metadata-only searches: PRs authored and
merged, PRs authored and still open, others' PRs reviewed, and issues opened.

- If a host reports **HOST UNAVAILABLE**, tell the user, with the
  re-authentication command the script prints. Offer to re-run once they've
  fixed it, or to continue without that host. Never treat an unavailable host
  as "no activity".
- If a section reports the **result limit was hit**, re-run that period in
  shorter pieces or with a larger `--limit`.
- For extra lookups the user asks for ("what about repo X?"), run `gh` directly,
  reusing the script's flags and metadata-only fields.

Summarize the results for the user by repo or theme in a few lines; keep the
full list for drafting.

### 4. Gather Microsoft 365 evidence through Copilot

The agent can't reach Microsoft 365, so the user runs prompts in Microsoft 365
Copilot and pastes the replies back. Read
[the Copilot prompts reference](references/copilot-prompts.md) now. It has the
templates, how the user should run them, and what Copilot output can and
can't be trusted for.

1. Explain the routine once: temporary chat, a fresh chat per month, paste the
   reply back with Copilot's copy button. Mention that a temporary chat is
   gone once they start the next one or browse away, and what to do if Copilot
   shows its confidential-content warning.
2. For each calendar month in the period, clipped to the period's start and
   end, fill in the monthly template and show it as one copyable
   block. Wait for the reply.
3. Check each reply as the reference describes. Briefly tell the user what it
   found and any problems (out-of-range dates, unsearched sources).
4. **Follow-ups for that month, now.** While its chat is still open, suggest
   follow-up questions about the month's items worth a closer look: meetings
   the user organized, meetings or chats on a goal's topic (you already have
   the goals and the GitHub activity), and chats where the user contributed.
   Show the filled-in follow-up template. The user can skip it. Focusing on
   goal topics is for follow-ups only: never narrow the monthly prompt to
   topics, or write new broad prompts that do, since anything outside the
   topics is silently lost.
5. Then give the next month's prompt. The user may skip a month or stop early;
   note which months have no Microsoft 365 evidence.

### 5. Ask for anything else

Ask the user what's missing that no source covered: Slack, conferences,
external talks, offline work, things they know happened that didn't show up.
Treat their answers as evidence with the source "user".

### 6. Map evidence and find gaps

Match each evidence item in the period to the goal it clearly supports. Then:

- For goals that still have thin or no evidence across all months, offer more
  follow-up prompts from the reference's follow-up template. These run in a
  **new temporary chat**, since the monthly chats are gone by now. The user can
  skip this.
- Collect notable items that fit no goal for "Not covered by current goals".
- If several of those share a theme, sketch a possible new goal for each theme.

### 7. Draft

Present the draft in the chat using the format below. Show each goal's comment
as a markdown blockquote, not a code block. Some chat interfaces (e.g. the
Claude Code VS Code extension) don't wrap lines in code blocks, which makes a
long comment unreadable and so impossible to review. Copyable blocks come at
the end, in step 9.

Writing "What I did", the activity overview:

- Cover everything notable from every source in the period, whether or not it
  fits a goal. It's a record of the period in its own right, and it's what the
  goal updates are drawn from.
- Organize it by project or area of work, not by source and not by goal.
- Cite specific items: PR and issue links, meeting titles with dates, blog
  posts. Keep authored work and reviews of others' work clearly apart.
- Keep it factual and scannable: short bullets, no goal language.

Writing the goal comments:

- One comment per goal, covering the period. Short sections or bullets
  inside a comment are fine when there's a lot to cover.
- Match the voice of the user's earlier comments in the PDF.
- Name the concrete work and include links (PR, issue, blog post) where they
  exist.
- Include Microsoft 365 work even when no other source backs it up; plenty of
  real work never touches GitHub. Weigh it by how specific it is:
  - An item with a named, dated source and real content (a chat you quoted, a
    recognition email, a talk you gave) is as good as any other evidence.
  - A "calendar only" item shows a meeting happened, not what came of it.
    Include it when attending is itself the point (a forum or course for a
    learning goal, mentoring sessions), and keep it to a brief mention. Leave
    routine syncs and status meetings out.
  - In the goal's evidence list, mark items that came only from Copilot as
    "Copilot only", so the user can check them before posting.
- No attribution line or signature; the user is posting it themselves.
- Goals that are completed or on hold get a comment only if new evidence
  clearly belongs to them. Don't suggest reopening them.

Draft format:

````markdown
# Goal update draft: <period>

## What I did

### <Project or area>
- <item, with link or date>

<repeat for each project or area>

## Proposed goal updates

### <Goal title>
Status: <current status> (no change) | Suggested change: <current> → <new>, because <reason>

> <comment, exactly as it would be posted>
> <every line of it prefixed with "> ", including blank lines and bullets>

Evidence: <short list of sources used: links, meeting titles and dates,
"user"; items that came only from Copilot are marked "Copilot only">

<repeat for each goal with an update>

## No update proposed
- <Goal title>: <one line on why: no evidence in period, completed, on hold>

## Not covered by current goals
- <item>: <evidence>

## Suggested new goals
- **<Possible goal title>**: <one-line description>. Based on: <items above>

## Status changes to review
- <Goal title>: <current> → <suggested>, because <reason>
````

Leave out any section that would be empty.

### 8. Refine

Iterate in the chat until the user is happy: edit wording, add or drop items,
run extra GitHub lookups or more Copilot follow-ups when asked. After each
change, show only what changed, not the whole draft:

- Name where each change is (goal title, or the overview's project/area).
- Show the changed part as readable text in the same blockquote form, with
  enough around it to read in context: the changed sentence, bullet, or
  paragraph, not the whole comment. Show a whole comment only when most of it
  changed.
- Unchanged goals and overview sections aren't repeated. The full final text
  comes once, in step 9. Show the full current draft, or any part of it,
  whenever the user asks.

Write the draft to a file only if the user asks (see the chat-first rule).

### 9. Hand off for posting

When the user says the draft is done (or that a particular goal is final),
print each final comment once more, this time in a plain `text` code block,
one block per goal under its goal title. Code blocks have a copy button in
most chat interfaces and keep the exact text, including bullet markers, that
copying rendered markdown can lose. The user has already reviewed the
readable version, so a block that doesn't wrap is fine here. The text must
match the reviewed blockquote exactly, minus the `> ` prefixes. List any
status changes the user accepted beneath the blocks.

The user posts the comments and makes any status changes in SF themselves.
Remind them that next time, a fresh PDF export lets the default period pick up
from these new comments.
