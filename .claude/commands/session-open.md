# /session-open

Run this at the start of every session. Execute all steps automatically — output the Session Brief without asking first.

## Steps (execute in order, no pausing)

1. Run `git log --oneline -8` — note branch, last commit hash + message
2. Run `git status` — flag any uncommitted changes
3. Read `docs/FORWARD_PLAN.md` — current version, completed items, UP NEXT list
4. Read the most recent file in `docs/session-log/` — last session context
5. Read `CLAUDE.md` if it exists — confirm no stale flags need immediate attention

## Output — Session Brief (write this exactly)

---

**SESSION BRIEF — [YYYY-MM-DD]**

**Branch:** `[branch]` · **Version:** [version] · **Last commit:** `[hash]` [message]

**Where we left off:**
[2–3 sentences max. What was last built, what was unresolved, any open decisions from session log.]

**Today's priority (in order):**
1. [First UP NEXT task from FORWARD_PLAN — include `[CLAUDE]` / `[YOU]` / `[TOGETHER]` tag]
2. [Second task]
3. [Third task if clear]

**Decisions needed before building:**
- [Any `[TOGETHER]` or `[YOU]` items that block item 1 or 2]
- "None" if clear to proceed

**Flags:**
- [Uncommitted changes / stale docs / anything that needs a quick fix before building]
- "None" if clean

---

Confirm focus or redirect?

## Rules

- Do not ask the user questions before outputting the brief — produce it first
- Do not summarise yesterday's summary — pull the specific unresolved thread
- If FORWARD_PLAN says "Pending decision", surface that as the first decision item
- If git status is clean and brief is confirmed, proceed directly to the first task
- After user confirms, update `FORWARD_PLAN.md` `**Last updated:**` line to today's date

## Pair with

`/session-close` at end of session.
