---
name: usage-notify
description: "USAGE NOTIFY — monitors Claude Code token usage and sends a silent system notification when 5-hour or weekly output-token usage crosses 70%. Runs only while Claude is actively working (Stop hook). Supports /usage, /usage setup, and /usage calibrate."
triggers:
  - "usage"
  - "usage notify"
  - "usage monitor"
  - "claude usage"
---

# USAGE NOTIFY

This skill has three modes depending on what the user asks:

---

## Mode 1: `/usage` — Status check

Run the status script and display the result:

```bash
python "$HOME/.claude/usage_monitor/status.py"
```

On Windows use:
```
python "C:/Users/<USERNAME>/.claude/usage_monitor/status.py"
```

To find the correct path dynamically, run:
```python
import pathlib; print(pathlib.Path.home() / ".claude" / "usage_monitor" / "status.py")
```

Show the output clearly. Then add a one-line summary:
- If 5-hour > 70%: warn that Claude is close to the rate limit and will slow down
- If weekly > 70%: warn that most of the weekly quota is used
- Otherwise: confirm everything looks fine

---

## Mode 2: `/usage setup` — First-time installation on a new machine

Tell the user to run:

```bash
python "$HOME/.claude/skills/usage-notify/scripts/setup.py"
```

The setup script will:
1. Install the right notification package for their OS (winotify / osascript / notify-send)
2. Copy monitor.py and status.py to `~/.claude/usage_monitor/`
3. Add the Stop hook to `~/.claude/settings.json` automatically
4. Ask for the current % shown in Claude.ai to calibrate the limits

After setup completes, the monitor is active — no background process needed.
It runs silently after each Claude response (Stop hook) and sends a notification only when usage crosses 70%.

---

## Mode 3: `/usage calibrate` — Recalibrate limits

When the user says their limits have changed, or they want to recalibrate:

Ask them to:
1. Open Claude.ai and look at the usage panel (click the token counter at the bottom of Claude Code)
2. Note the current **5-hour %** and **weekly %**

Then run:
```bash
python "$HOME/.claude/usage_monitor/status.py" --calibrate --5h <X> --weekly <Y>
```

---

## How the monitor works (for reference)

- **Trigger**: Claude Code `Stop` hook — runs after every response, only while Claude is active
- **Cooldown**: skips scan if checked less than 90 seconds ago (no performance impact)
- **Data source**: parses `~/.claude/projects/**/*.jsonl` — all conversation files
- **Metric**: output tokens only, deduplicated by requestId
- **Alert**: system Toast/notification once per hour (5h) or once per week (weekly)
- **No background process**: zero CPU when Claude Code is not running

## Supported platforms

| OS | Notifications |
|----|---------------|
| Windows | winotify (Windows Toast) |
| macOS | osascript (Notification Center) |
| Linux | notify-send (libnotify) |
