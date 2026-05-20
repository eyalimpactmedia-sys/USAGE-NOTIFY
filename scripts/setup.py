"""
USAGE NOTIFY — one-time setup script (portable).
Run this once on any machine to install the monitor.

What it does:
  1. Detects OS and home directory
  2. Installs the right notification package
  3. Copies scripts to ~/.claude/usage_monitor/
  4. Adds the Stop hook to ~/.claude/settings.json
  5. Guides through calibration

Usage:
  python setup.py
  python setup.py --uninstall
"""
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HOME         = Path.home()
CLAUDE_DIR   = HOME / ".claude"
MONITOR_DIR  = CLAUDE_DIR / "usage_monitor"
SETTINGS     = CLAUDE_DIR / "settings.json"
SKILLS_DIR   = CLAUDE_DIR / "skills" / "usage-notify" / "scripts"

OS = platform.system()


def run_cmd(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=isinstance(cmd, str))
    if check and result.returncode != 0:
        print(f"  Warning: {result.stderr.strip()}")
    return result.returncode == 0


def install_deps():
    print(f"\n[1/4] Installing notification package for {OS}...")
    if OS == "Windows":
        ok = run_cmd([sys.executable, "-m", "pip", "install", "winotify", "--quiet"], check=False)
        if ok:
            print("  + winotify installed")
        else:
            print("  ! Could not install winotify — notifications may not work")
    elif OS == "Darwin":
        print("  + macOS — using built-in osascript (no install needed)")
    else:
        if shutil.which("notify-send"):
            print("  + notify-send found")
        else:
            print("  notify-send not found. Install with:")
            print("    Ubuntu/Debian: sudo apt install libnotify-bin")
            print("    Fedora:        sudo dnf install libnotify")


def copy_scripts():
    print("\n[2/4] Copying scripts to ~/.claude/usage_monitor/ ...")
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)

    for script in ["monitor.py", "status.py"]:
        src = SKILLS_DIR / script
        dst = MONITOR_DIR / script
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  + {script}")
        else:
            print(f"  ! {script} not found in {SKILLS_DIR}")

    config_file = MONITOR_DIR / "config.json"
    if not config_file.exists():
        config = {
            "_comment": "USAGE NOTIFY config. Run calibration after setup.",
            "fivehour_limit_output_tokens": 0,
            "weekly_limit_output_tokens": 0,
            "alert_threshold": 0.70
        }
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
        print("  + config.json created (uncalibrated)")
    else:
        print("  + config.json already exists — keeping your limits")


def add_hook():
    print("\n[3/4] Adding Stop hook to settings.json ...")
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)

    settings = {}
    if SETTINGS.exists():
        try:
            settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
        except Exception:
            settings = {}

    monitor_script = str(MONITOR_DIR / "monitor.py").replace("\\", "/")

    if OS == "Windows":
        hook_cmd = f'python "{monitor_script}"'
    else:
        hook_cmd = f'python3 "{monitor_script}"'

    new_hook = {"type": "command", "command": hook_cmd, "timeout": 10}

    hooks = settings.setdefault("hooks", {})
    stop_hooks = hooks.setdefault("Stop", [])

    target = None
    for entry in stop_hooks:
        if entry.get("matcher", "") == "":
            target = entry
            break
    if target is None:
        target = {"matcher": "", "hooks": []}
        stop_hooks.append(target)

    existing_cmds = [h.get("command", "") for h in target.get("hooks", [])]
    if any("usage_monitor" in cmd for cmd in existing_cmds):
        print("  + Hook already present in settings.json")
    else:
        target.setdefault("hooks", []).append(new_hook)
        SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
        print("  + Hook added to settings.json")


def calibrate():
    print("\n[4/4] Calibration")
    print("  Open Claude.ai / Claude Code and look at the usage panel.")
    print("  You need two numbers:")
    print("    - 5-hour usage  (e.g. '89%')")
    print("    - Weekly usage  (e.g. '28%')")
    print()

    try:
        pct_5h   = float(input("  Enter current 5-hour  usage % (just the number): ").strip().rstrip("%"))
        pct_week = float(input("  Enter current weekly  usage % (just the number): ").strip().rstrip("%"))
    except (ValueError, EOFError):
        print("  Skipping calibration — run later:")
        print(f'  python "{MONITOR_DIR / "status.py"}" --calibrate --5h X --weekly Y')
        return

    sys.path.insert(0, str(MONITOR_DIR))
    from monitor import get_output_tokens
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)

    tokens_5h = get_output_tokens(now - timedelta(hours=5), now)
    limit_5h  = round(tokens_5h / (pct_5h / 100)) if pct_5h > 0 else 0

    tokens_w  = get_output_tokens(now - timedelta(days=7), now)
    limit_w   = round(tokens_w / (pct_week / 100)) if pct_week > 0 else 0

    config_file = MONITOR_DIR / "config.json"
    config = json.loads(config_file.read_text(encoding="utf-8")) if config_file.exists() else {}
    config["fivehour_limit_output_tokens"] = limit_5h
    config["weekly_limit_output_tokens"]   = limit_w
    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  + 5-hour  limit: {limit_5h:,} tokens  (based on {tokens_5h:,} = {pct_5h}%)")
    print(f"  + Weekly  limit: {limit_w:,} tokens  (based on {tokens_w:,} = {pct_week}%)")


def uninstall():
    print("Uninstalling USAGE NOTIFY...")

    if SETTINGS.exists():
        try:
            settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
            stop_hooks = settings.get("hooks", {}).get("Stop", [])
            for entry in stop_hooks:
                entry["hooks"] = [
                    h for h in entry.get("hooks", [])
                    if "usage_monitor" not in h.get("command", "")
                ]
            SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
            print("  + Hook removed from settings.json")
        except Exception as e:
            print(f"  ! Could not update settings.json: {e}")

    if MONITOR_DIR.exists():
        shutil.rmtree(MONITOR_DIR)
        print(f"  + Removed {MONITOR_DIR}")

    print("Done. Skill files remain in ~/.claude/skills/usage-notify/")


def main():
    if "--uninstall" in sys.argv:
        uninstall()
        return

    print("=" * 52)
    print("  USAGE NOTIFY — Setup")
    print(f"  OS: {OS}  |  Home: {HOME}")
    print("=" * 52)

    install_deps()
    copy_scripts()
    add_hook()
    calibrate()

    print("\n" + "=" * 52)
    print("  Setup complete!")
    print(f'  Check status:    python "{MONITOR_DIR / "status.py"}"')
    print(f'  Re-calibrate:    python "{MONITOR_DIR / "status.py"}" --calibrate --5h X --weekly Y')
    print(f'  Uninstall:       python "{SKILLS_DIR / "setup.py"}" --uninstall')
    print("=" * 52)


if __name__ == "__main__":
    main()
