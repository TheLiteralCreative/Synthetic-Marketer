# Cloudflare Access — Auth Gate for SignalRipper

This is the one step between SignalRipper and being safely shareable. The tunnel at
`signalripper.literalcreative.com` already works; right now it is just switched off,
because anyone with the URL could use it. Cloudflare Access puts a login screen in front
of it so only you and people you invite get through.

**Who does this:** you, in the Cloudflare dashboard. No code, no terminal. ~15 minutes.
**Cost:** $0 — Cloudflare Access free tier covers 50 users.

---

## How it works (the 30-second model)

Cloudflare Access sits *in front of* the subdomain. Every request to
`signalripper.literalcreative.com` hits Cloudflare first. If the visitor hasn't proven
who they are, Cloudflare shows a login screen. If their email is on your allowlist, they
get a session cookie and Cloudflare passes them through to the tunnel. If not, they never
reach SignalRipper at all — the request stops at Cloudflare's edge.

The important consequence: **the gate is on the subdomain, not on any machine.** It does
not matter whether the tunnel runs on your laptop today or a dedicated box later — the
Access policy is unchanged. That is why we can do this now and migrate the host later.

---

## Step 1 — Open Zero Trust

1. Go to the Cloudflare dashboard (`dash.cloudflare.com`) and log in.
2. In the left sidebar, click **Zero Trust**. (It may open a new tab at
   `one.dash.cloudflare.com`.)
3. If this is the first time, Cloudflare asks you to name your "team" and pick a plan —
   choose the **Free** plan. A team name becomes part of your login URL; something like
   `literalcreative` is fine.

## Step 2 — Choose a login method

Before creating the application, decide how invited people prove who they are. Two
options — pick one:

**Option A — Email one-time PIN (recommended for a 2–4 person tool).**
Cloudflare emails the visitor a 6-digit code; they type it in. Nothing to configure — it
is built in. Lowest friction to set up, slightly more friction per login.

**Option B — Google sign-in.**
Visitors click "Sign in with Google." One-click logins, but it requires creating a Google
OAuth app in Google Cloud Console and pasting its client ID/secret into Zero Trust under
**Settings → Authentication → Login methods → Add new → Google**. Worth it later if the
collaborator group grows; overkill for the first handful of people.

This guide assumes **Option A**. Email OTP is on by default, so there is nothing to do in
this step — it is just the decision.

## Step 3 — Create the Access application

1. In Zero Trust, go to **Access → Applications**.
2. Click **Add an application**.
3. Choose **Self-hosted**.
4. Fill in:
   - **Application name:** `SignalRipper`
   - **Session duration:** `24 hours` (how long a login lasts before re-auth — a day is
     a reasonable default; a week is fine too)
   - **Application domain:** subdomain `signalripper`, domain `literalcreative.com`,
     path left blank. (`literalcreative.com` should already appear in the domain
     dropdown since it is on Cloudflare.)
5. Leave the rest at defaults and continue to the policy step.

## Step 4 — Create the allowlist policy

This is the rule that says *who* gets in.

1. **Policy name:** `Allowed users`
2. **Action:** `Allow`
3. Under **Configure rules**, add an **Include** rule:
   - Selector: **Emails**
   - Value: add each address that should have access — start with your own
     (`theliteralcreative@gmail.com`) and add invited collaborators.
   - (If you'd rather allow a whole domain later, the selector **Emails ending in**
     accepts something like `@literalcreative.com`.)
4. Save the policy, then save the application.

## Step 5 — Turn the tunnel on and verify

The gate is now live, but SignalRipper only answers when the tunnel is running.

1. On the machine that hosts the tunnel, start SignalRipper (`python3 start.py`) and the
   tunnel (`cloudflared tunnel run signalripper`).
2. Open `https://signalripper.literalcreative.com` in a **private/incognito window** (so
   you're not already logged in).
3. You should see Cloudflare's login screen. Enter an allowlisted email, receive the
   6-digit code by email, enter it.
4. You should land on the SignalRipper GUI.
5. Sanity check the gate actually blocks: try an email that is *not* on the list — it
   should be refused.

If you see the SignalRipper GUI **without** a login prompt, the application domain in
Step 3 doesn't match the subdomain — recheck it. Until the login screen appears for an
incognito visitor, treat the tool as unprotected and keep the tunnel down.

---

## After this

SignalRipper is now safely shareable. The next deployment milestone is moving the tunnel
off your laptop onto an always-on machine so it stays up while you're away — see
`DEDICATED-HOST-SETUP.md`. The Access policy created here carries over to that machine
unchanged; you will not redo this step.
