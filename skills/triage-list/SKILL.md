---
name: triage-list
description: >-
  Work through a list of items with the user one at a time — research, propose,
  discuss, and resolve each before moving to the next, at the user's pace. Use when
  triaging a list of candidate changes, review feedback, or action items with the
  user. The user drives every advance, edit, and commit.
---

# Triage List

Work through a list of items with the user, one at a time: research each item,
present the problem and a proposed resolution, discuss, resolve, and only then move
on. The user sets the pace throughout.

**Governing principle: the user drives the pace. Never advance to the next item,
make an edit, or commit without the user's explicit go-ahead.**

## When to use

A list of candidate changes or action items is being worked through with the user:

- Review feedback to work through (e.g. a review-council action file or a batch of
  comments).
- A set of action items or TODOs from a working session.
- Any other "here is a list, let's go through it together" moment.

Stay off until the user asks. Do not auto-start triage on a stray list.

## The triage document

Triage is driven by a markdown document on disk — not from session context. The
document is the source of truth for what the items are and where each one stands, so
progress survives interruptions and is never held only in the conversation.

Use whatever document the user points to, in whatever format it arrives — a
review-council action file, an exported set of comments, a plain bullet list — and
do not force it into a different shape. If the user asks to triage a list that is not
yet a file, create the document first, then drive triage from it.

A workable shape when creating one:

```markdown
### N. <one-line statement of the item>
- **Source:** <who/what raised it>
- **Where:** <file:line or area, if there is one>
- **Detail:** <the substance — what is at issue>
- **Resolution:** pending
```

`Resolution` starts at `pending` and changes only when the user says the item is
done (see step 5). If the document arrived without a resolution field, add one so
state stays in the file. Typical terminal values:

- `addressed — <short note of what changed>`
- `skipped — <why it is not actually an issue>`
- `deferred — drafted to a working file, to post/apply at end of triage`
- `external — <PR #, issue #, or "comment posted">`

## The per-item loop

Go through the list one item at a time.

1. **Investigate and present.** Read the item and do whatever research is needed to
   understand it. Present it clearly: explain the problem — what it is and why it
   matters — so the user has the context to judge the fix, then propose a solution,
   or several options, to weigh. Bring an informed proposal, not a restatement.

2. **Discuss.** Iterate with the user: whether the item is real, which fix to apply,
   or whether to skip it. Treat the user's questions and comments during this
   discussion as design input, not instructions to edit. Do not start code changes
   off the back of a question. Wait until the user explicitly asks for the edit.

3. **Resolve.** An item resolves one of these ways, and only once the user has
   chosen:
   - an **edit** — the proposed fix, or whatever was settled in discussion;
   - **skip** — not something to change;
   - an **external action** — open or update a PR, open an issue, or post a comment.
     Draft external actions into a working file to post or apply at the end of triage
     rather than firing them immediately, in case later items revise them. The user
     decides immediate versus deferred.

4. **Let the user review the work.** After an edit, the user reviews it and usually
   gives feedback. That feedback is not permission to edit again — it is often
   further discussion. Resume editing only when the user explicitly asks to address
   it.

5. **Mark complete only on the user's explicit say-so.** Record the item as resolved
   only when the user says it is done. If it is unclear whether an item is finished,
   ask; do not assume.

6. **Move on only after step 5.** Advancing to the next item starts its
   investigation, so moving early means researching the next item while the current
   one is still open. Do not advance without the user's go-ahead. This is the single
   most important rule.

## Commits

Do not commit as triage proceeds. Commits happen at the end, driven by the user.

## Never

- Advance to the next item without the user's explicit go-ahead.
- Treat a discussion question or comment as a directive to start editing.
- Treat the user's review of an edit as permission to edit again.
- Commit mid-triage.
- Work several items at once from the start, or defer all edits until a batch of
  items has been designed.
- Mark an item complete because it was discussed.
