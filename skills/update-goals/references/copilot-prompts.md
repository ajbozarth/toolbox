# Microsoft 365 Copilot prompts

Prompt templates for the human-in-the-loop Microsoft 365 step of the `update-goals`
skill. The agent fills in the placeholders and shows the prompt to the user as a
copyable block; the user runs it in Microsoft 365 Copilot and pastes the reply
back into the session.

These templates were tuned against real Copilot output, using a past period
whose activity was already known as ground truth. Edit them here, not inline in
`SKILL.md`.

## How to run them (tell the user)

- Use Copilot's **temporary chat** mode (the incognito icon) for every prompt.
  It does not read or write Copilot's memory, so a run is not shaped by earlier
  conversations and does not change later ones.
- Use a **fresh temporary chat for each monthly prompt**.
- Temporary chats don't last: only the most recent one is kept, and only until
  the user browses away. So any follow-ups for a month are best run straight
  after its monthly reply, in the same chat. Later follow-ups go in a new
  temporary chat; the follow-up template works on its own for that.
- Copy the reply with Copilot's **copy button** and paste it back as-is. The
  copy often collapses line breaks; that is expected, see "Reading the replies"
  below.
- **Confidential-content warnings.** Copilot shows a warning icon next to the
  copy button when a reply contains content labelled confidential. If it
  appears, check what's flagged before pasting, and remove anything the draft
  doesn't need (often it's a reference to an all-hands or similar broadcast,
  which the prompts exclude anyway). Whether the rest is fine to paste is the
  user's call.

## What Copilot is and isn't good for

Learned from testing; use this to decide how far to trust each reply.

| Reliable | Not reliable |
|---|---|
| Calendar timeline: meeting titles, dates, organizer, attendees | Meeting outcomes or decisions (only present when the meeting chat has them) |
| Recognition emails (e.g. peer-recognition awards) | Meeting recordings and transcripts: usually none exist except for large org events |
| Meeting chats the user posted in, quoted exactly | Anything over a window longer than about a month: results are capped and skew recent, with no warning |
| Saying "NONE FOUND" / "NO CONTENT AVAILABLE" when told it may | Its own claims about what it can access, until a reply's "Sources searched" confirms it |

Known blind spots:

- **Deleted past meetings.** When an organizer cancels a recurring series
  incorrectly, Outlook can delete its *past* occurrences too. A calendar-led
  search then misses them; the Teams meeting chat usually survives. The monthly
  prompt asks for chats without a calendar entry for this reason.
- **Email outside the Inbox.** Asked about "email" in general, Copilot tends to
  search only the Inbox, so users who file their mail into folders get little
  or nothing back. The monthly prompt names every folder for this reason.
- **Topic filters lose email.** Asking only for email "about" a list of topics
  quietly drops everything outside the list. The monthly prompt filters email
  by kind (sent by me, addressed to me, recognition, feedback), never by topic.
  Don't add topic filters to it.
- **Long windows.** Never ask for more than one calendar month per prompt.
- **Slack and other non-Microsoft tools** are not covered at all. Ask the user.

## Template 1: monthly activity (broad pass)

One per calendar month in the review period. Clip the first and last month to
the period's start and end dates. Replace `{START}` and `{END}` with dates
written out in full (e.g. `March 1, 2026`).

```text
I am preparing a retrospective work-goals update. Act as a retrieval layer for another AI system: report facts, not prose.

Using my Microsoft 365 data (Outlook email, calendar, Teams chats, Teams channel posts and replies, meeting recordings/transcripts, OneDrive and SharePoint files), report my work activity between {START} and {END} inclusive. Exclude anything outside that range.

For email, search ALL of my Outlook mail folders, including Archive, Sent Items, subfolders, and any folders where rules or I file mail, not just the Inbox. Do NOT search Deleted Items, Trash, Junk Email, or Spam.

Group items under these headings, in this order:
1. Work streams / projects (one sub-heading per project)
2. Presentations, talks, demos I gave (only if I presented: a transcript, slide file, or my name as presenter shows it)
3. Learning: talks, tech forums, courses, and sessions I attended
4. Mentoring and coaching (given or received)
5. Recognition and feedback I received (for example awards, peer recognition, kudos, thank-you notes, feedback on my work), from any source
6. Community and cross-team activity, including Teams channel posts I authored or replied to and things I shared with other teams or communities
7. Other email: emails I sent, and emails addressed directly to me (in To, not only CC), that aren't already listed above
8. Meeting chats with my messages whose calendar entry no longer exists (for example, because the series was cancelled)

For every item give one bullet in this format:
- DATE | TYPE (meeting / recording / email / chat / channel post / file) | EXACT TITLE, SUBJECT, OR FILE NAME | MY ROLE (organizer, presenter, attendee, author, sender, recipient) | one-line factual outcome | link if available
For emails, write the TYPE as "email (FOLDER)", naming the mail folder it was found in.

Rules:
- Only include items you can tie to a specific dated source. If you cannot name the source, leave the item out.
- If all you have is the calendar entry, write "calendar only" as the outcome instead of describing it from the title.
- Recurring meetings: list once as "TITLE | recurring | N occurrences | dates". Only list a single occurrence separately if it has a transcript, meeting chat, or notes with content.
- Do not estimate percentages, confidence scores, or time spent.
- Ignore company-wide announcements and broadcasts, newsletters, automated notifications (for example from GitHub), calendar invitations, mandatory compliance training, office/facilities logistics, and vacation entries. Do NOT ignore technical talks or forums I attended; those go under Learning.
- If a heading has nothing, write NONE FOUND under it.

End with a section "Sources searched" listing which of the sources above you were actually able to search for this request, and any you could not. For email, list the mail folders you searched.
```

## Template 2: targeted follow-up

Optional, for specific items worth a closer look: meetings the user organized,
meetings on a goal's topic, chats where the user contributed, or a goal with
thin evidence. Replace `{MONTH}` (e.g. `August 2026`) and write one numbered
question per item in `{QUESTIONS}`.

The prompt doesn't rely on the earlier chat, so it works in the monthly chat
(best, while it's still open) or in a new temporary chat later. That only holds
if each question names its item by **exact title and date**, as given in the
monthly reply; never write "the meeting above" or similar.

Good questions ask what the source *contains*, e.g.:

- `"<meeting title>" on <date>: what did I propose or argue for, what was decided, and what action items came out of it?`
- `The <date> "<meeting title>" chat that mentions "<topic>": quote my message exactly and summarize the surrounding discussion.`
- `Teams channel posts I authored, or threads I replied to, about <topic> in <month>.`

```text
I am preparing a retrospective work-goals update and need detail on specific items of my Microsoft 365 activity from {MONTH}. For each one, use the meeting recording or transcript, the meeting chat, or a meeting recap if one exists.

{QUESTIONS}

For every item give one bullet in this format:
- DATE | SOURCE USED (transcript / meeting chat / recap / calendar only) | EXACT TITLE | what I contributed or what was decided | link if available

Rules:
- If an item has no transcript, chat, or recap available to you, write "NO CONTENT AVAILABLE (calendar only)" for it instead of summarizing from the title.
- Do not infer or guess what was said. Only report what the source contains.
- Do not estimate percentages, confidence scores, or time spent.

End with a section "Sources searched" saying whether you were able to open any recordings or transcripts for this request, and if not, why not.
```

## Reading the replies

- **Collapsed formatting.** Copilot's copy button often removes line breaks, so
  headings, bullets, and tables run together on one line. Split on the
  numbered headings, ` - ` bullet separators, and `|` field separators. Don't
  ask the user to reformat.
- **Check every reply** before using it:
  - Dates outside the requested range: drop those items and mention it.
  - A missing "Sources searched" section, or a source listed as not
    searchable: note which sources weren't covered for that month.
  - Items without a named, dated source: treat as unverified.
  - Outcomes that look inferred from a meeting title rather than from content:
    treat as "calendar only".
  - Email: if "Sources searched" (or the folders on the email items) shows
    only the Inbox, the all-folders search didn't happen. Tell the user, so
    they can decide whether to re-run that month.
  - If the user mentions Copilot's confidential-content warning, don't carry
    the flagged items into the draft unless the user says they're needed.
- **Copilot-only items.** Anything only Copilot reported (no GitHub or user
  confirmation) is still used, weighed by how specific it is (see step 7 of
  `SKILL.md`), and marked "Copilot only" in the draft's evidence list so the
  user can check it.
