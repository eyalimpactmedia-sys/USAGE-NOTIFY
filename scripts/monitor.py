"""
Claude Usage Monitor — portable, runs as a Stop hook after each Claude response.
Sends a system notification when 5-hour or weekly output-token usage crosses 70%.

Auto-detects: home directory, OS, Claude projects path.
Notification backends: winotify (Windows), osascript (macOS), notify-send (Linux).
"""
import json
import sys
import time
import platform
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths (all derived from home directory, fully portable) ──────────────────
HOME         = Path.home()
CLAUDE_DIR   = HOME / ".claude"
MONITOR_DIR  = CLAUDE_DIR / "usage_monitor"
PROJECTS_DIR = CLAUDE_DIR / "projects"
CONFIG_FILE  = MONITOR_DIR / "config.json"
STATE_FILE   = MONITOR_DIR / "state.json"
LOG_FILE     = MONITOR_DIR / "usage.log"

# Skip full scan if another check ran less than this many seconds ago
SCAN_COOLDOWN_SECONDS = 90


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_output_tokens(start_dt, end_dt):
    """
    Sum output tokens from all .jsonl files in the relevant time window.
    Uses file mtime as a pre-filter for speed. Deduplicates by requestId.
    """
    seen = set()
    total_output = 0
    start_ts = start_dt.timestamp()

    for jsonl_file in PROJECTS_DIR.rglob("*.jsonl"):
        try:
            if jsonl_file.stat().st_mtime < start_ts - 3600:
                continue
            with open(jsonl_file, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("type") != "assistant":
                            continue
                        ts_str = data.get("timestamp", "")
                        if not ts_str:
                            continue
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if not (start_dt <= ts <= end_dt):
                            continue
                        req_id = data.get("requestId") or data.get("uuid", "")
                        if req_id:
                            if req_id in seen:
                                continue
                            seen.add(req_id)
                        usage = (data.get("message") or {}).get("usage") or {}
                        output = usage.get("output_tokens", 0)
                        if output > 0:
                            total_output += output
                    except Exception:
                        pass
        except Exception:
            pass

    return total_output


def send_notification(title, message):
    os_name = platform.system()
    try:
        if os_name == "Windows":
            from winotify import Notification, audio
            toast = Notification(
                app_id="Claude Usage Monitor",
                title=title,
                msg=message,
                duration="long",
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()

        elif os_name == "Darwin":
            import subprocess
            escaped = message.replace('"', '\\"').replace('\n', ' ')
            subprocess.run(
                ["osascript", "-e",
                 f'display notification "{escaped}" with title "{title}"'],
                capture_output=True
            )

        else:  # Linux
            import subprocess
            subprocess.run(
                ["notify-send", "--urgency=normal", "--expire-time=8000", title, message],
                capture_output=True
            )
    except Exception as e:
        log(f"Notification error ({os_name}): {e}")


def log(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def run():
    if not PROJECTS_DIR.exists():
        return  # Claude projects not found — nothing to monitor

    cfg   = load_json(CONFIG_FILE, {})
    state = load_json(STATE_FILE, {})

    # Cooldown: skip if checked very recently
    if time.time() - state.get("last_check_ts", 0) < SCAN_COOLDOWN_SECONDS:
        return

    fiveh_limit  = cfg.get("fivehour_limit_output_tokens", 0)
    weekly_limit = cfg.get("weekly_limit_output_tokens", 0)
    threshold    = cfg.get("alert_threshold", 0.70)

    if not fiveh_limit or not weekly_limit:
        return  # Not calibrated yet — run setup first

    now = datetime.now(timezone.utc)

    fiveh_output  = get_output_tokens(now - timedelta(hours=5), now)
    week_output   = get_output_tokens(now - timedelta(days=7), now)

    fiveh_pct = fiveh_output / fiveh_limit
    week_pct  = week_output  / weekly_limit

    state["last_check_ts"] = time.time()

    fiveh_key = now.strftime("%Y-%m-%d-%H")
    week_key  = now.strftime("%Y-W%W")

    if fiveh_pct >= threshold and state.get("last_fiveh_alert") != fiveh_key:
        remaining = f"{(1 - fiveh_pct):.0%}"
        send_notification(
            f"Claude — {fiveh_pct:.0%} of 5-hour window",
            f"{remaining} remaining until reset\nBe mindful before starting another project"
        )
        log(f"ALERT 5h: {fiveh_pct:.0%} ({fiveh_output:,} / {fiveh_limit:,})")
        state["last_fiveh_alert"] = fiveh_key

    if week_pct >= threshold and state.get("last_weekly_alert") != week_key:
        remaining = f"{(1 - week_pct):.0%}"
        send_notification(
            f"Claude — {week_pct:.0%} of weekly quota",
            f"{remaining} of weekly quota remaining\nBe mindful before starting another project"
        )
        log(f"ALERT weekly: {week_pct:.0%} ({week_output:,} / {weekly_limit:,})")
        state["last_weekly_alert"] = week_key

    save_json(STATE_FILE, state)


if __name__ == "__main__":
    run()
