# Phase 1b — Complete

**As of:** 2026-05-25 (Phase 1b completion session)
**Status:** Phase 1b is **COMPLETE**. SignalRipper runs on LC-NODE-01 as a persistent,
unattended service — it starts on boot, restarts on crash, and serves through the
Cloudflare tunnel with no Terminal windows open. Verified across a full reboot.

This note records the finished state so the next session resumes with an accurate picture.

---

## What was accomplished this session

Building on the overnight host setup (see "Foundation" below), the four remaining
Phase 1b tasks were completed:

1. **Anthropic API key + output folder set.** Entered via the GUI Settings page; saved
   to `~/srv/apps/signalripper/data/settings.json`. The output folder for this machine
   is `/Users/literalcreative/srv/apps/signalripper`.
2. **Real audit run end-to-end.** A full audit ran through
   `https://signalripper.literalcreative.com` and completed successfully, writing all
   deliverables to the output folder. The In-Progress view updated **gradually, phase by
   phase** — confirming SSE streams live through the named tunnel rather than buffering.
   The non-skippable SSE check (`REMOTE-HOSTING.md` §3 step 7) is **passed**.
3. **`launchd` persistence installed.** Two user LaunchAgents now run and supervise the
   tool (details below). Verified by a full reboot: after a cold boot, both services
   auto-started with fresh low PIDs and the public URL served the GUI with no manual
   intervention.
4. **Laptop tunnel decommissioned.** Confirmed no `cloudflared` process and no `launchd`
   service for it on the laptop. The iMac is the sole host answering the tunnel.

---

## How SignalRipper runs now (launchd — replaces the old two-Terminal method)

The tool is no longer started by hand. Two **user LaunchAgents** own it:

| Service | Plist (deployed copy) | Runs |
|---|---|---|
| SignalRipper | `~/Library/LaunchAgents/com.literalcreative.signalripper.plist` | `.venv/bin/python3 start.py --no-open` |
| Tunnel | `~/Library/LaunchAgents/com.literalcreative.cloudflared.plist` | `cloudflared --config ~/.cloudflared/config.yml tunnel run signalripper` |

Both use `RunAtLoad` (start at login/boot) and `KeepAlive` (restart on exit or crash),
with `ThrottleInterval` 10 (at least 10s between restart attempts). Automatic login is
enabled, so a login — and therefore an agent load — happens on every boot.

Version-controlled copies of both plist files live in the repo at `deploy/launchd/`.
Those are the source of truth; the files in `~/Library/LaunchAgents/` are the deployed
copies.

Because a launchd-managed process has no controlling Terminal, process output is
redirected to log files:

- `~/srv/logs/signalripper.out.log` and `.err.log`
- `~/srv/logs/cloudflared.out.log` and `.err.log`

---

## Operating reference

Check both services (real PID + `0` = healthy; `-` + non-zero = failed):
```
launchctl list | grep literalcreative
```

Watch live activity — the launchd-era replacement for watching the Terminal:
```
tail -f ~/srv/logs/signalripper.out.log
```

Restart a service. Note that `kill` alone will NOT stop it — `KeepAlive` immediately
respawns the process. To actually stop or restart, unload then load:
```
launchctl unload ~/Library/LaunchAgents/com.literalcreative.signalripper.plist
```
```
launchctl load -w ~/Library/LaunchAgents/com.literalcreative.signalripper.plist
```

To deploy updated code (`git pull`): unload the SignalRipper agent, pull, load again.

---

## Foundation (overnight setup session — unchanged)

LC-NODE-01 is the repurposed Late-2015 27" iMac. macOS Monterey 12.7.6; sleep disabled;
automatic login and restart-after-power-failure enabled. Installed: Homebrew, Python
3.11.15, `cloudflared` 2026.5.0, GitHub CLI, Node.js 24, Chrome. SignalRipper cloned to
`~/srv/apps/signalripper`; `.venv` created with `pip install -e ".[pipeline]"`. Tunnel
credentials in `~/.cloudflared/`. The Cloudflare Access gate is live on the subdomain.

---

## Reference docs

- `DEDICATED-HOST-SETUP.md` — the 8-step host build. **All 8 steps are now done** (the
  doc still reads "6–8 remain" — worth correcting).
- `REMOTE-HOSTING.md` — the hosting decision; §3 holds the SSE buffering fixes if that
  problem ever appears later.
- `LC-NODE-01_Infrastructure-Strategy.md` — the node's organizational SSOT.
- `HOSTING-ROADMAP.md` — the three-tier hosting plan and runtime-shape rule.
- `CLOUDFLARE-ACCESS-SETUP.md` — the auth gate (live).

---

## Open breadcrumbs (carried forward — not part of Phase 1b)

- **Commit & push the new files** from the laptop: this doc,
  `LC-NODE-01_Infrastructure-Strategy.md`, and the new `deploy/launchd/` plist files are
  all untracked.
- **Rotate the two exposed credentials** — the Stripe test key and the GitHub PAT.
- **Update `MEDIA_RIPPERS_PROGRAM_PLAN.md`** per `HOSTING-ROADMAP.md` §1.
- **Hand `PHASE-1-BRIEF.md` to Claude Code** pointed at the `Synthetic-Marketer` folder.
- **Mark `DEDICATED-HOST-SETUP.md` steps 6–8 complete.**

---

## Known issues

- **Universal Clipboard, iMac → laptop, is unreliable.** During this session, copy
  worked laptop → iMac but not the reverse; `killall pboard` and re-toggling Handoff did
  not fix it. Apple Notes (iCloud sync) was used as a reliable bridge instead. A full
  restart is the standard heavy fix — verify whether the Phase 1b reboot resolved it.
- A **stray copy of this file** exists at the `VSCode_Projects/` root, outside the repo.
  The canonical copy is `Synthetic-Marketer/docs/PHASE-1B-STATE.md`; remove the stray to
  avoid the two drifting apart.
