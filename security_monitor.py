"""
================================================================================
  Windows Live Activity Security Monitor
================================================================================
"""

import os
import sys
import time
import datetime
import threading
import ctypes
import urllib.parse

# ── third-party ──────────────────────────────────────────────────────────────
try:
    import psutil
except ImportError:
    sys.exit("Missing dependency: pip install psutil")

try:
    import win32com.client
    import win32gui
    import pythoncom
except ImportError:
    sys.exit("Missing dependency: pip install pywin32")

try:
    from PIL import ImageGrab
except ImportError:
    sys.exit("Missing dependency: pip install Pillow")

# ── configuration ─────────────────────────────────────────────────────────────
LOG_FILE        = "activity_log.txt"
SCREENSHOT_DIR  = "screenshots"
POLL_INTERVAL   = 1.0       # seconds between Explorer / process polls
MAX_LOG_BYTES   = 10 * 1024 * 1024  # 10 MB — rotate log beyond this size

# ── global state ─────────────────────────────────────────────────────────────
_baseline_pids:     set = set()
_baseline_explorer: set = set()
_seen_pids:         set = set()
_seen_explorer:     set = set()

_lock = threading.Lock()


# ═════════════════════════════════════════════════════════════════════════════
#  Logging & screenshots
# ═════════════════════════════════════════════════════════════════════════════

def _ensure_dirs() -> None:
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _rotate_log_if_needed() -> None:
    """
    FIX #3: Rotate the log file when it exceeds MAX_LOG_BYTES.
    Renames activity_log.txt → activity_log_TIMESTAMP.txt and starts fresh.
    """
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_BYTES:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            archive = LOG_FILE.replace(".txt", f"_{ts}.txt")
            os.rename(LOG_FILE, archive)
            print(f"[*] Log rotated → {archive}")
    except OSError as exc:
        print(f"  [WARN] Log rotation failed: {exc}")


def _log(event_type: str, detail: str) -> None:
    _rotate_log_if_needed()
    line = f"[{_timestamp()}] {event_type}: {detail}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as exc:
        print(f"  [WARN] Could not write log: {exc}")


def _screenshot(label: str) -> None:
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)[:60]
    path = os.path.join(SCREENSHOT_DIR, f"{ts}_{safe}.png")
    try:
        # FIX #2: all_screens=True is not supported on all Pillow versions.
        # Try it first; fall back to single-screen grab on failure.
        try:
            img = ImageGrab.grab(all_screens=True)
        except TypeError:
            img = ImageGrab.grab()
        img.save(path)
    except Exception as exc:
        print(f"  [WARN] Screenshot failed: {exc}")


def _log_and_screenshot(event_type: str, detail: str) -> None:
    _log(event_type, detail)
    _screenshot(f"{event_type}_{detail}")


# ═════════════════════════════════════════════════════════════════════════════
#  Baseline capture
# ═════════════════════════════════════════════════════════════════════════════

def _capture_baseline_pids() -> set:
    try:
        return {p.pid for p in psutil.process_iter()}
    except Exception as exc:
        print(f"  [WARN] Baseline PID capture failed: {exc}")
        return set()


def _get_explorer_folders(shell) -> set:
    paths = set()
    try:
        windows = shell.Windows()
        for i in range(windows.Count):
            try:
                win  = windows.Item(i)
                loc  = win.LocationURL
                name = win.LocationName
                if loc and loc.startswith("file:///"):
                    path = loc[8:].replace("/", "\\")
                    path = urllib.parse.unquote(path)
                    paths.add(path)
                elif name:
                    paths.add(name)
            except Exception:
                continue
    except Exception as exc:
        print(f"  [WARN] Explorer folder enumeration failed: {exc}")
    return paths


def _capture_baseline_explorer(shell) -> set:
    return _get_explorer_folders(shell)


# ═════════════════════════════════════════════════════════════════════════════
#  Process monitor
# ═════════════════════════════════════════════════════════════════════════════

def _monitor_processes() -> None:
    """
    FIX #4 & #5: Replaced bare except:pass with logged exception handling.
    Thread errors are now visible in the log instead of silently dying.
    """
    global _seen_pids
    while True:
        try:
            current = {p.pid: p for p in psutil.process_iter(["pid", "name", "create_time"])}
            new_pids = set(current.keys()) - _baseline_pids - _seen_pids
            for pid in new_pids:
                proc = current.get(pid)
                if proc:
                    try:
                        name = proc.info["name"] or "unknown"
                    except Exception:
                        name = "unknown"
                    with _lock:
                        _seen_pids.add(pid)
                    _log_and_screenshot("Program Opened", name)
        except Exception as exc:
            # FIX #5: Log thread errors so we know if monitoring breaks
            _log("MONITOR ERROR", f"Process monitor exception: {exc}")
        time.sleep(POLL_INTERVAL)


# ═════════════════════════════════════════════════════════════════════════════
#  Explorer folder monitor
# ═════════════════════════════════════════════════════════════════════════════

def _monitor_explorer() -> None:
    global _seen_explorer

    # COM must be initialised on the thread that uses it
    pythoncom.CoInitialize()
    shell = win32com.client.Dispatch("Shell.Application")

    recent_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Recent")
    baseline_recent = _snapshot_recent(recent_dir)
    seen_recent: set = set()

    while True:
        try:
            # ── Explorer folder navigation ──────────────────────────────────
            current_folders = _get_explorer_folders(shell)
            new_folders = current_folders - _baseline_explorer - _seen_explorer
            for folder in new_folders:
                with _lock:
                    _seen_explorer.add(folder)
                _log_and_screenshot("Folder Accessed", folder)

            # ── File opens via Recent Items shortcuts ──────────────────────
            current_recent = _snapshot_recent(recent_dir)
            new_links = current_recent - baseline_recent - seen_recent
            for lnk_path in new_links:
                seen_recent.add(lnk_path)
                target = _resolve_lnk(lnk_path)
                if target:
                    _log_and_screenshot("File Opened", target)

        except Exception as exc:
            # FIX #4: Log thread errors instead of silently swallowing them
            _log("MONITOR ERROR", f"Explorer monitor exception: {exc}")

        time.sleep(POLL_INTERVAL)


def _snapshot_recent(recent_dir: str) -> set:
    try:
        return {
            os.path.join(recent_dir, f)
            for f in os.listdir(recent_dir)
            if f.lower().endswith(".lnk")
        }
    except Exception as exc:
        print(f"  [WARN] Recent folder snapshot failed: {exc}")
        return set()


def _resolve_lnk(lnk_path: str) -> str:
    """
    FIX #1: Removed the erroneous pythoncom.CoInitialize() call that was
    here before. COM is already initialized on this thread (the explorer
    monitor thread called CoInitialize at startup). Calling it again inside
    a helper caused "CoInitialize has not been called" / RPC errors on some
    systems. The fix is simply to not call it again.
    """
    try:
        shell_link = win32com.client.Dispatch("WScript.Shell")
        shortcut   = shell_link.CreateShortCut(lnk_path)
        target     = shortcut.Targetpath
        return target if target else ""
    except Exception as exc:
        print(f"  [WARN] Could not resolve shortcut {lnk_path}: {exc}")
        return ""


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    _ensure_dirs()

    start_msg = (
        f"\n{'='*70}\n"
        f"  Security Monitor STARTED at {_timestamp()}\n"
        f"  Log file   : {os.path.abspath(LOG_FILE)}\n"
        f"  Screenshots: {os.path.abspath(SCREENSHOT_DIR)}\n"
        f"{'='*70}\n"
    )
    print(start_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(start_msg)

    print("[*] Capturing baseline state …")

    global _baseline_pids, _baseline_explorer, _seen_pids, _seen_explorer

    _baseline_pids = _capture_baseline_pids()
    _seen_pids     = set(_baseline_pids)

    pythoncom.CoInitialize()
    _shell_main        = win32com.client.Dispatch("Shell.Application")
    _baseline_explorer = _capture_baseline_explorer(_shell_main)
    _seen_explorer     = set(_baseline_explorer)

    print(f"[*] Baseline: {len(_baseline_pids)} processes, "
          f"{len(_baseline_explorer)} Explorer windows.")
    print("[*] Monitoring … Press Ctrl+C to stop.\n")

    t_proc = threading.Thread(target=_monitor_processes, daemon=True)
    t_expl = threading.Thread(target=_monitor_explorer,  daemon=True)

    t_proc.start()
    t_expl.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Monitor stopped by user.")
        stop_msg = f"[{_timestamp()}] Monitor stopped.\n{'='*70}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(stop_msg)


if __name__ == "__main__":
    if sys.platform != "win32":
        print("[ERROR] This script is designed for Windows only.")
        sys.exit(1)

    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False

    if not is_admin:
        print("[WARN] Not running as Administrator. Some process names may be")
        print("       inaccessible. Re-launch as Admin for full coverage.\n")

    main()
