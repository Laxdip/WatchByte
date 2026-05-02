# WatchByte

A Windows activity monitor that logs every program launched, folder accessed, and file opened and takes a screenshot for each event. Built for students and security enthusiasts who want to know if someone used their PC without permission.

---

## What It Captures

- **Program Launched** – Name of every new process started
- **Folder Accessed** – Every folder navigated in File Explorer
- **File Opened** – Every file opened (via Windows Recent Items)
- **Screenshots** – One screenshot taken per event automatically

All events are saved to `activity_log.txt` with timestamps. Screenshots go into a `screenshots/` folder.

---

## Quick Start
```
1. Install dependencies
pip install psutil pywin32 Pillow

2. Run manually
python security_monitor.py

3. Auto-start at login (recommended)
Run **once** as Administrator:
python setup_task_scheduler.py
```
After this, the monitor starts automatically every time you log into Windows.

---

## How It Works

1. **Baseline snapshot** — on startup, records all currently running processes and open Explorer windows so pre-existing activity is never reported
2. **Process monitor** — polls `psutil` every second for new PIDs
3. **Explorer monitor** — polls `Shell.Application` COM for new folder navigation
4. **File open detection** — watches Windows Recent Items folder for new `.lnk` shortcuts (Windows creates one every time a file is opened)
5. **Screenshot** — captures the full screen on every detected event

---

## Task Scheduler Commands

```bash
# Register auto-start (run as Admin)
python setup_task_scheduler.py

# Check task status
python setup_task_scheduler.py --status

# Remove auto-start
python setup_task_scheduler.py --remove
```

---
## Stealth Tips

Want to hide `security_monitor.py` from Task Manager? Here's how (use responsibly):
```cmd
1. Easiest - Windows Service
sc create "WindowsLiveMonitor" binPath= "\"C:\Program Files\Python39\pythonw.exe\" \"C:\path\to\security_monitor.py\"" start= auto

2. Sneakier - Rename pythonw.exe
copy C:\Windows\System32\pythonw.exe C:\Windows\Temp\svchost.exe
C:\Windows\Temp\svchost.exe security_monitor.py

3. Hidden Launcher (included)
start /b "" pythonw.exe security_monitor.py

4. Startup Persistence
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v "WindowsLiveService" /t REG_SZ /d "pythonw.exe C:\path\to\security_monitor.py"
```
> **Bottom line:** Complete invisibility requires rootkit techniques. This is a monitoring tool, not malware. Use only on systems you own or have permission to monitor.
---

## Requirements

- Windows 10 / 11
- Python 3.8+
- Administrator rights (recommended, for full process visibility)

---

## Troubleshooting
`Antivirus flags` → Add exclusion | `Access denied` → Run as Admin | `No screenshots` → Reinstall Pillow

---

## ⚠️ Ethical Notice

This tool is intended for monitoring **your own PC only**. Do not deploy on any device you do not own or without the explicit consent of the user. Unauthorized surveillance is illegal.

---

## Built With

- [`psutil`](https://github.com/giampaolo/psutil) — process monitoring
- [`pywin32`](https://github.com/mhammond/pywin32) — Windows COM / Shell API
- [`Pillow`](https://python-pillow.org/) — screenshots

---

## License

MIT License - free to use, modify, and distribute.
