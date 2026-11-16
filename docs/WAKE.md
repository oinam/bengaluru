# Waking the Mac for scheduled work

Written 2026-11-16. One permission, set once on this Mac, that any project's scheduled
job can use to wake the Mac when its work is due. No project needs its own. This project
is the first to use it.

It is meant to live in the Oinam vault as well, since it is not about Bengaluru; see
"Where this note lives" at the end.

## What it is

Waking a sleeping Mac at a set time takes `pmset schedule wake`, and `pmset schedule`
needs root. A job that runs at night has no one to type a password. So one line in
`/etc/sudoers.d/claude-wake` lets the `brajeshwar` account run exactly two commands
without a password:

```
brajeshwar ALL=(root) NOPASSWD: /usr/bin/pmset schedule wake *, /usr/bin/pmset schedule cancel wake *
```

- `pmset schedule wake "MM/DD/YY HH:MM:SS"` sets one wake.
- `pmset schedule cancel wake "MM/DD/YY HH:MM:SS"` removes one.

Nothing else: no other `pmset` command (sleep settings, `sleepnow`, `repeat`,
`cancelall`), and no other use of `sudo`.

## Is it safe?

Safe enough to be global, as long as it stays this narrow.

- The rule belongs to the account, not to a project. A per-project file would give every
  program running as `brajeshwar` the same power; the global name only says so honestly.
- The worst a program can do with it is wake the Mac at odd times, which costs battery
  and nothing else, or cancel a wake another job was counting on.
- Do not widen it. `pmset *` would let any program change sleep settings or put the Mac
  to sleep, and a general passwordless `sudo` for Claude Code would hand over the Mac.
  A new need gets its own exact line, added by hand, after reading what it allows.

## Install, once

In Terminal. It writes the line to a temporary file, checks its syntax, installs it
owned by root, and checks the whole sudoers setup:

```
printf '%s\n' 'brajeshwar ALL=(root) NOPASSWD: /usr/bin/pmset schedule wake *, /usr/bin/pmset schedule cancel wake *' > /tmp/claude-wake
visudo -cf /tmp/claude-wake && sudo install -m 440 -o root -g wheel /tmp/claude-wake /etc/sudoers.d/claude-wake && sudo visudo -c
rm /tmp/claude-wake
```

Check it works, with a time a few minutes ahead, then remove the test wake:

```
sudo -n /usr/bin/pmset schedule wake "11/16/26 23:00:00"
pmset -g sched
sudo -n /usr/bin/pmset schedule cancel wake "11/16/26 23:00:00"
```

`sudo -n` never asks for a password: it works, or it fails at once. Scheduled jobs must
use it, and must use the full path `/usr/bin/pmset`, which is what the rule names.

Remove the permission: `sudo rm /etc/sudoers.d/claude-wake`.

## How a project uses it

1. Check the permission is there, and carry on without a wake if it is not:
   `test -e /etc/sudoers.d/claude-wake`.
2. Check the wake is not already set: `pmset -g sched` lists it as
   `wake at MM/DD/YYYY HH:MM:SS`.
3. Set it: `sudo -n /usr/bin/pmset schedule wake "MM/DD/YY HH:MM:SS"`.

`schedule_wake` in `src/bengaluru/night.py` is those three steps.

What this Mac taught us:

- **Wake at the job's start time, not before.** This Mac sleeps again after one idle
  minute. launchd starts a job it slept through the moment the Mac wakes, so a wake at
  23:00:00 starts a 23:00 job at once.
- **Hold the Mac awake with `caffeinate -is`** from the job's first second, as the
  launchd agent's own program: `/usr/bin/caffeinate -is <the job>`. `-s` keeps the Mac
  up on AC power where `-i` alone might not. caffeinate cannot wake a sleeping Mac; that
  is what the wake is for.
- **Each run sets the next wake.** A job that sets the wake for its next start keeps the
  chain going, and since launchd also runs a missed job at the next wake, one missed
  night costs one night.
- **Do not use `pmset repeat`.** It holds a single repeating wake, and this Mac's is
  taken: 05:58 every day.
- **Run launchd agents as `ProcessType` Standard** if they read the external drive. A
  Background agent's reads wait behind everyone else's and can stall for hours.
- **Lid closed is unproven**, and scheduled wakes are only dependable on AC power.
  Plugged in with the lid open is the known-good setup.

None of the above has run for real yet: the permission is not installed, so no wake has
been set through it. The first night after installing it is the test.

## Telling every Claude Code session

Not done. For every project's session to know this exists, add a short section to
`~/.claude/CLAUDE.md`, for example:

```markdown
## Waking the Mac
- Scheduled jobs may wake this Mac with `sudo -n /usr/bin/pmset schedule wake "MM/DD/YY HH:MM:SS"`,
  and cancel with `schedule cancel wake`. `/etc/sudoers.d/claude-wake` allows exactly those two.
  Never ask for, or add, any other passwordless `sudo`.
- How to use it, and what this Mac needs: <where this note lives in the vault>.
```

## Who uses it

- **Bengaluru map** (`~/dev/bengaluru`): `bengaluru night` sets a wake for the next
  23:00 on every run; its launchd agent is `com.oinam.bengaluru.night`.

## Where this note lives

Brajeshwar asked for it in the Oinam vault. The session that wrote it was not allowed to
create a file there, so it is here until he copies it over or says where it goes. Once
the vault has it, cut this file down to a pointer and the "Who uses it" line.
