# 🐶 WatchByte

> Know who touched your PC while you were gone.

A Windows activity monitor that logs every program launched, folder accessed, and file opened — and takes a screenshot for each event. Built for students and security enthusiasts who want to know if someone used their PC without permission.

---

## 📸 What It Captures

| Event | Details |
|---|---|
| **Program Launched** | Name of every new process started |
| **Folder Accessed** | Every folder navigated in File Explorer |
| **File Opened** | Every file opened (via Windows Recent Items) |
| **Screenshots** | One screenshot taken per event automatically |

All events are saved to `activity_log.txt` with timestamps. Screenshots go into a `screenshots/` folder.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install psutil pywin32 Pillow
```

### 2. Run manually
```bash
python security_monitor.py
```

### 3. Auto-start at login (recommended)
Run **once** as Administrator:
```bash
python setup_task_scheduler.py
```
After this, the monitor starts automatically every time you log into Windows.

---

## 📁 Project Structure

```
WatchByte/
├── security_monitor.py       # Main monitor — logs events + screenshots
├── setup_task_scheduler.py   # Registers auto-start at login via Task Scheduler
├── activity_log.txt          # Generated at runtime
└── screenshots/              # Generated at runtime
```

---

## ⚙️ How It Works

1. **Baseline snapshot** — on startup, records all currently running processes and open Explorer windows so pre-existing activity is never reported
2. **Process monitor** — polls `psutil` every second for new PIDs
3. **Explorer monitor** — polls `Shell.Application` COM for new folder navigation
4. **File open detection** — watches Windows Recent Items folder for new `.lnk` shortcuts (Windows creates one every time a file is opened)
5. **Screenshot** — captures the full screen on every detected event

---

## 🛠️ Task Scheduler Commands

```bash
# Register auto-start (run as Admin)
python setup_task_scheduler.py

# Check task status
python setup_task_scheduler.py --status

# Remove auto-start
python setup_task_scheduler.py --remove
```

---

## 📋 Requirements

- Windows 10 / 11
- Python 3.8+
- Administrator rights (recommended, for full process visibility)

---

## ⚠️ Ethical Notice

This tool is intended for monitoring **your own PC only**. Do not deploy on any device you do not own or without the explicit consent of the user. Unauthorized surveillance is illegal.

---

## 🧰 Built With

- [`psutil`](https://github.com/giampaolo/psutil) — process monitoring
- [`pywin32`](https://github.com/mhammond/pywin32) — Windows COM / Shell API
- [`Pillow`](https://python-pillow.org/) — screenshots

---

## 📄 License

MIT License — free to use, modify, and distribute.
