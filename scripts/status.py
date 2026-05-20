"""
Claude Usage Monitor — status check (portable).
Usage:
  python status.py
  python status.py --calibrate --5h 89 --weekly 28
  python status.py --test-notify
"""
import json
import sys
import platform
from datetime import datetime, timezone, timedelta
from pathlib import Path

HOME         = Path.home()
CLAUDE_DIR   = HOME / ".claude"
MONITOR_DIR  = CLAUDE_DIR / "usage_monitor"
CONFIG_FILE  = MONITOR_DIR / "config.json"

# Import shared helpers from monitor.py in the same directory
sys.path.insert(0, str(Path(__file__).parent))
from monitor import get_output_tokens, load_json, save_json, send_notification


def bar(pct, width=28):
    filled = int(min(pct, 1.0) * width)
    char = "#" if pct < 0.70 else ("!" if pct < 0.90 else "X")
    return "[" + char * filled + "-" * (width - filled) + "]"


def run():
    args = sys.argv[1:]

    if "--test-notify" in args:
        send_notification("USAGE NOTIFY — Test", "Notifications are working!")
        print("Test notification sent.")
        return

    if "--calibrate" in args:
        pct_5h = pct_week = None
        for i, a in enumerate(args):
            if a == "--5h"     and i + 1 < len(args): pct_5h   = float(args[i + 1])
            if a == "--weekly" and i + 1 < len(args): pct_week = float(args[i + 1])

        now = datetime.now(timezone.utc)
        cfg = load_json(CONFIG_FILE, {})

        if pct_5h:
            tokens = get_output_tokens(now - timedelta(hours=5), now)
            limit  = round(tokens / (pct_5h / 100))
            cfg["fivehour_limit_output_tokens"] = limit
            print(f"5h tokens used: {tokens:,}  =>  5h limit set to: {limit:,}")

        if pct_week:
            tokens = get_output_tokens(now - timedelta(days=7), now)
            limit  = round(tokens / (pct_week / 100))
            cfg["weekly_limit_output_tokens"] = limit
            print(f"Weekly tokens used: {tokens:,}  =>  weekly limit set to: {limit:,}")

        if pct_5h or pct_week:
            save_json(CONFIG_FILE, cfg)
            print(f"Config saved: {CONFIG_FILE}")
        else:
            print("Usage: python status.py --calibrate --5h <pct> --weekly <pct>")
        return

    # ── Normal status display ──────────────────────────────────────────────────
    cfg = load_json(CONFIG_FILE, {})
    fiveh_limit  = cfg.get("fivehour_limit_output_tokens", 0)
    weekly_limit = cfg.get("weekly_limit_output_tokens", 0)
    threshold    = cfg.get("alert_threshold", 0.70)

    if not fiveh_limit or not weekly_limit:
        print("\n  Not calibrated yet. Run:")
        print("  python status.py --calibrate --5h <X> --weekly <Y>")
        print("  (X and Y = the percentages shown in the Claude.ai UI)")
        return

    now = datetime.now(timezone.utc)
    fiveh_output = get_output_tokens(now - timedelta(hours=5), now)
    week_output  = get_output_tokens(now - timedelta(days=7), now)
    fiveh_pct    = fiveh_output / fiveh_limit
    week_pct     = week_output  / weekly_limit

    print(f"\nClaude Usage — {datetime.now().strftime('%Y-%m-%d %H:%M')}  [{platform.system()}]")
    print("=" * 52)
    print(f"  5-hour  {bar(fiveh_pct)} {fiveh_pct:5.1%}")
    print(f"          {fiveh_output:>7,} / {fiveh_limit:,} output tokens")
    print(f"          alert at {threshold:.0%}  |  rolling window")
    print()
    print(f"  Weekly  {bar(week_pct)} {week_pct:5.1%}")
    print(f"          {week_output:>7,} / {weekly_limit:,} output tokens")
    print(f"          alert at {threshold:.0%}  |  rolling window")
    print()
    print(f"  Config: {CONFIG_FILE}")


if __name__ == "__main__":
    run()
