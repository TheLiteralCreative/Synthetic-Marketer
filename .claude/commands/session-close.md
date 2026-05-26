# /session-close

Run this at the end of every session. Execute all steps automatically — commit, log, and close without asking about each step individually. Only pause for explicit user decisions.

## Steps (execute in order)

1. Run `git log --oneline -5` and `git status`
2. Read `docs/FORWARD_PLAN.md`
3. **Update FORWARD_PLAN.md:**
   - Mark newly completed items `✓` with today's date
   - Add any newly discovered tasks into the correct phase with ownership tag
   - Update `**Last updated:**` and `**Current version:**` at the top
   - Update the phase status table at the bottom
4. **Stage and commit** all modified source files (`.py`, `.md` in docs/) with a descriptive commit message in the established format: `feat:` / `fix:` / `docs:` + phase tag + bullet summary
5. **Write session log** to `docs/session-log/YYYY-MM-DD.md` (append `-EOD` if a same-day log already exists):

---

**SESSION LOG — [YYYY-MM-DD]**

**Version shipped:** [version] · **Commit:** `[hash]`

**Completed:**
- [what was finished — be specific, reference files changed]

**Decisions made:**
- [architectural or product choices locked in — include the reasoning, not just the conclusion]

**Open items / next session (priority order):**
1. [First thing to pick up — specific enough that any dev/agent can start without asking]
2. [Second item]

**Blockers / waiting on:**
- [user decision needed, external dependency, or pending design question]
- "None" if clear

**Where we left off:**
[One paragraph. Specific enough that tomorrow's session-open produces an accurate brief without ambiguity. Name the files touched, the decision pending, and the first action for next session.]

---

6. Commit the FORWARD_PLAN update and session log in a second commit: `docs: session close [date]`
7. Output a 3-sentence plain-English wrap confirming what shipped, what's staged for tomorrow, and any open decision the user needs to have an answer for.

## Rules

- Do not ask "should I commit?" — commit. If the user wants to undo, they can
- Do not write vague log entries ("worked on ingestion") — be specific ("implemented `check_subscriptions()` in `api/app/services/ingestion.py`, RSS path only, YouTube pending")
- If CLAUDE.md is out of date with what was built today, update it as part of this close
- The session log is institutional memory — write it for a dev who wasn't in the room

## Pair with

`/session-open` at the start of each session.
