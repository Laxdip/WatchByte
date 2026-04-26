"""
================================================================================
  Task Scheduler Setup — Security Monitor Auto-Start at Login
  
  Run this script ONCE as Administrator to register the security monitor
  as a Task Scheduler task. After that, it will start automatically every
  time you log into Windows — no manual launch needed.

  Usage:
      Right-click → "Run as administrator"  (required for Task Scheduler)
      python setup_task_scheduler.py

  To remove the task later:
      python setup_task_scheduler.py --remove
================================================================================
"""

import sys
import os
import subprocess
import argparse
import ctypes

TASK_NAME   = "SecurityMonitor_LoginStart"
SCRIPT_NAME = "security_monitor.py"


def is_admin() -> bool:
    """Check if we're running with Administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def find_pythonw() -> str:
    """
    Find the full path to pythonw.exe (no console window).
    Falls back to python.exe if pythonw.exe is not found.
    """
    python_exe  = sys.executable                          # e.g. C:\Python311\python.exe
    pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")

    if os.path.exists(pythonw_exe):
        return pythonw_exe

    print(f"[WARN] pythonw.exe not found at {pythonw_exe}")
    print(f"[WARN] Falling back to python.exe (a console window WILL appear at login)")
    return python_exe


def find_monitor_script() -> str:
    """
    Resolve the absolute path to security_monitor.py.
    Looks in the same directory as this setup script.
    """
    script_dir    = os.path.dirname(os.path.abspath(__file__))
    monitor_path  = os.path.join(script_dir, SCRIPT_NAME)

    if not os.path.exists(monitor_path):
        sys.exit(
            f"[ERROR] Cannot find {SCRIPT_NAME} in {script_dir}\n"
            f"        Make sure both files are in the same folder."
        )
    return monitor_path


def register_task(pythonw: str, monitor_script: str) -> None:
    """
    Create a Task Scheduler task using schtasks.exe that:
      - Triggers at login of the CURRENT user only
      - Runs pythonw.exe security_monitor.py
      - Sets the working directory so log/screenshot paths resolve correctly
      - Runs with highest privileges (so process names are visible)
      - Does NOT require the user to be logged in to an interactive session
        (the trigger is ONLOGON so this is implicit)
    """
    script_dir = os.path.dirname(monitor_script)

    # Build the schtasks command
    # /XML would be cleaner but requires a temp file; schtasks flags are portable
    cmd = [
        "schtasks", "/Create",
        "/TN", TASK_NAME,                        # Task name
        "/TR", f'"{pythonw}" "{monitor_script}"',# Command to run
        "/SC", "ONLOGON",                        # Trigger: at login
        "/RL", "HIGHEST",                        # Run with highest privileges
        "/F",                                    # Force overwrite if task exists
        "/DELAY", "0000:10",                     # 10-second delay after login
                                                 # (gives Desktop time to load)
    ]

    print(f"\n[*] Registering task: {TASK_NAME}")
    print(f"    Interpreter : {pythonw}")
    print(f"    Script      : {monitor_script}")
    print(f"    Working dir : {script_dir}")
    print(f"    Trigger     : At login (current user)\n")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("[OK] Task registered successfully!\n")
        print("     The monitor will now start automatically every time you log in.")
        print(f"     To verify: open Task Scheduler and look for '{TASK_NAME}'")
        _set_working_directory(script_dir)
    else:
        print(f"[ERROR] schtasks failed (exit code {result.returncode})")
        print(f"        stdout: {result.stdout.strip()}")
        print(f"        stderr: {result.stderr.strip()}")
        sys.exit(1)


def _set_working_directory(working_dir: str) -> None:
    """
    schtasks /Create does not have a /WD flag for working directory.
    We update it via PowerShell after creation so relative paths in the
    monitor script (activity_log.txt, screenshots/) resolve correctly.
    """
    ps_cmd = (
        f'$t = Get-ScheduledTask -TaskName "{TASK_NAME}"; '
        f'$t.Actions[0].WorkingDirectory = "{working_dir}"; '
        f'Set-ScheduledTask -TaskName "{TASK_NAME}" -Action $t.Actions'
    )
    result = subprocess.run(
        ["powershell", "-NonInteractive", "-Command", ps_cmd],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[OK] Working directory set to: {working_dir}")
    else:
        print(f"[WARN] Could not set working directory via PowerShell.")
        print(f"       Logs will be saved to your user profile folder instead.")
        print(f"       stderr: {result.stderr.strip()}")


def remove_task() -> None:
    """Delete the scheduled task."""
    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' removed successfully.")
    else:
        print(f"[ERROR] Could not remove task.")
        print(f"        {result.stderr.strip()}")
        sys.exit(1)


def verify_task() -> None:
    """Print the current status of the scheduled task."""
    cmd = ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("\n── Current task status ──────────────────────────────────────")
        print(result.stdout.strip())
        print("─────────────────────────────────────────────────────────────\n")
    else:
        print(f"[INFO] Task '{TASK_NAME}' not found (not yet registered).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register or remove the Security Monitor login task."
    )
    parser.add_argument(
        "--remove", action="store_true",
        help="Remove the scheduled task instead of creating it."
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show the current status of the scheduled task."
    )
    args = parser.parse_args()

    # ── Platform check ────────────────────────────────────────────────────
    if sys.platform != "win32":
        sys.exit("[ERROR] This script only works on Windows.")

    # ── Admin check ───────────────────────────────────────────────────────
    if not is_admin():
        sys.exit(
            "[ERROR] This script must be run as Administrator.\n"
            "        Right-click the script → 'Run as administrator'."
        )

    # ── Dispatch ──────────────────────────────────────────────────────────
    if args.status:
        verify_task()
        return

    if args.remove:
        remove_task()
        return

    # Default: register the task
    pythonw        = find_pythonw()
    monitor_script = find_monitor_script()

    register_task(pythonw, monitor_script)

    print("\n── Quick reference ──────────────────────────────────────────────")
    print("  Start now (manual) : python security_monitor.py")
    print(f"  Check task status  : python {os.path.basename(__file__)} --status")
    print(f"  Remove task        : python {os.path.basename(__file__)} --remove")
    print("─────────────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
