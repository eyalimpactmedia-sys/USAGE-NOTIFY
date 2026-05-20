# USAGE NOTIFY

A Claude Code skill that silently monitors your token usage and sends a system notification when you hit **70%** of your 5-hour or weekly limits — only while Claude is actively working.

**No background process. Zero CPU when Claude is idle.**

## How it works

- Hooks into Claude Code's `Stop` event (fires after every response)
- Reads token data from `~/.claude/projects/**/*.jsonl`
- Sends a native OS notification when usage crosses 70%
- Cooldown of 90 seconds between scans — no performance impact

## Supported platforms

| OS | Notifications |
|----|---------------|
| Windows | winotify (Toast) |
| macOS | osascript (Notification Center) |
| Linux | notify-send (libnotify) |

## Installation

### 1. Install the skill into Claude Code

In Claude Code, type:
```
/install-skill https://github.com/eyalimpactmedia-sys/USAGE-NOTIFY
```

### 2. Run one-time setup

```bash
python ~/.claude/skills/usage-notify/scripts/setup.py
```

Setup will:
1. Install the right notification package for your OS
2. Copy scripts to `~/.claude/usage_monitor/`
3. Add the Stop hook to `~/.claude/settings.json`
4. Ask for current % from Claude.ai UI to calibrate your limits

## Usage

| Command | Action |
|---------|--------|
| `/usage` | Show current 5-hour and weekly usage |
| `/usage setup` | First-time setup instructions |
| `/usage calibrate` | Recalibrate limits from Claude.ai UI |

### Manual calibration

Open Claude.ai, check your usage panel, then run:
```bash
python ~/.claude/usage_monitor/status.py --calibrate --5h 89 --weekly 28
```

### Test notifications

```bash
python ~/.claude/usage_monitor/status.py --test-notify
```

### Uninstall

```bash
python ~/.claude/skills/usage-notify/scripts/setup.py --uninstall
```

## Files

```
usage-notify/
├── SKILL.md              # Claude Code skill definition
└── scripts/
    ├── setup.py          # One-time installer
    ├── monitor.py        # Silent hook monitor
    └── status.py         # Status check + calibration
```
