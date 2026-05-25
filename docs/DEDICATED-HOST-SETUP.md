# Dedicated Host — SignalRipper's Always-On Machine

This is the spec for Tier 2 in `HOSTING-ROADMAP.md`: moving the SignalRipper tunnel off
your laptop onto a machine that stays on so the tool is reachable while you're away,
working on your laptop elsewhere.

**Why a separate machine and not just "keep the laptop awake":** your laptop travels with
you, sleeps, and gets closed. A tool other people rely on cannot depend on that. A small
machine that sits in one place, plugged in, doing only this one job, is the difference
between "SignalRipper is up" and "SignalRipper is up when Joel's laptop happens to be."

---

## 1. What the machine has to do

It runs exactly two things, continuously:

1. **SignalRipper itself** — `python3 start.py`, serving the GUI on `localhost:8000`.
2. **The Cloudflare tunnel** — `cloudflared`, connecting `localhost:8000` to
   `signalripper.literalcreative.com`.

Both must start automatically on boot and restart themselves if they crash. Neither needs
a monitor, keyboard, or mouse attached once set up — the machine runs "headless," and you
reach it remotely (§4).

## 2. What the machine should be

SignalRipper runs headless Chrome and a parallel-subagent phase, so this is not a
job for the smallest hardware. Sizing guidance:

| Resource | Minimum | Comfortable |
|---|---|---|
| RAM | 8 GB | 16 GB |
| CPU | modern 4-core | 4-core+ |
| Disk | 128 GB SSD | 256 GB+ SSD (audit bins accumulate) |
| Network | wired Ethernet preferred over Wi-Fi for reliability | |

**Recommended: a Mac** — a Mac mini, or a spare/older MacBook or iMac you already own.
The reason is consistency, not preference: your whole environment is macOS, `cloudflared`
installs cleanly via Homebrew, persistence uses `launchd` (§3), and SignalRipper's
`md_to_pdf.py` already has macOS Chrome path detection. A Mac mini is the ideal form
factor — small, quiet, low-power, built to sit on a shelf for years.

**Workable alternative: a mini PC / Intel NUC running Linux.** Cheaper, and SignalRipper's
Chrome detection already covers Linux. The tradeoff is that you'd be running the tool on
an OS you don't develop on, so it needs its own smoke test before you trust it. Choose
this only if cost is the deciding factor.

**Not recommended: a Raspberry Pi.** Even an 8 GB Pi is thin for headless Chrome plus the
parallel phase; audits would be slow and memory-tight. Fine as an experiment, not as the
machine people depend on.

## 3. Setting it up

The tunnel does **not** need to be recreated — the existing tunnel (`signalripper`, UUID
`2e97776b-dacf-403c-97a7-91380488ff3e`) and its DNS route are account-level Cloudflare
objects. You move the *credentials and config* to the new machine; the tunnel itself is
unchanged. The Cloudflare Access gate is likewise unaffected — it lives on the subdomain.

Outline (Claude can do the file-writing steps; you do the installs and the physical
setup):

1. **Prepare the machine.** Install the OS, create a user account, enable automatic login
   so it boots straight into a running session, and disable system sleep (on macOS:
   System Settings → Energy / Lock Screen → never sleep; "Wake for network access" on).
2. **Install the runtimes.** Python 3.11+, then SignalRipper's dependencies
   (`pip install` against the repo's requirements), then `cloudflared`
   (`brew install cloudflared` on macOS).
3. **Copy SignalRipper to the machine.** Clone the repo, restore `data/settings.json`
   (the gitignored file holding the Anthropic API key — or set `ANTHROPIC_API_KEY` as an
   environment variable instead).
4. **Copy the tunnel credentials.** Move `~/.cloudflared/` (the `cert.pem`, the
   tunnel credentials JSON, and `config.yml` with the `localhost:8000` ingress rule) from
   your laptop to the same path on the new machine.
5. **Smoke-test by hand.** Start SignalRipper and `cloudflared tunnel run signalripper`
   manually; confirm `https://signalripper.literalcreative.com` loads through the Access
   gate.
6. **Make both persistent.** Install SignalRipper and the tunnel as services that start
   on boot and restart on crash. On macOS that is two `launchd` agents — this is
   `FORWARD_PLAN.md` priority #3 (`cloudflared service install` can generate the tunnel's
   plist automatically; SignalRipper needs its own). On Linux it is two `systemd` units.
7. **Run the non-skippable SSE smoke test.** With everything persistent, run one real
   audit end-to-end through the public URL and confirm progress events stream live, not
   in a buffered dump — per `REMOTE-HOSTING.md` §3 step 7.
8. **Decommission the laptop tunnel.** Once the dedicated machine is verified, stop
   running `cloudflared` on your laptop so there is exactly one host. Two machines
   answering the same tunnel is a source of confusing behavior.

## 4. Reaching the machine remotely

The machine is headless and may not be in the same place as you. Two complementary tools:

- **Tailscale** — install it on the dedicated machine and on your laptop. Both join your
  private "tailnet," and you can then reach the machine from anywhere by a stable name,
  as if it were on your local network. Free Personal plan. (`REMOTE-HOSTING.md` §4
  already discusses Tailscale — here it is for *your admin access*, not for serving the
  tool; the tool is still served publicly via the Cloudflare tunnel.)
- **Screen Sharing / VNC / Remote Desktop** — over Tailscale, gives you the machine's
  actual desktop when you need to look at it. macOS Screen Sharing is built in.

Day to day you should rarely need to touch the machine — it boots, starts both services,
and serves SignalRipper unattended. Remote access is for the occasional update, restart,
or check.

## 5. What this does and doesn't solve

**Solves:** SignalRipper stays reachable regardless of where your laptop is or whether
it's asleep. Your laptop goes back to being just your laptop.

**Doesn't solve:** the machine still depends on your home power and internet. A blackout
or an ISP outage takes SignalRipper down until it's back. For an interactive tool used by
a small invited group that is an acceptable risk. The point at which it stops being
acceptable is exactly the move to Tier 3 (full cloud) — see `HOSTING-ROADMAP.md` §5.
