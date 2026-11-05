# Expense Tracker

A small, offline Android expense tracker built with Python, Flet, and SQLite. This is an early personal project that I plan to improve over time.

## Current features

- Add expenses with a description, amount, and date
- View expenses and totals by month
- Edit expenses and delete them with confirmation
- Store data locally on the device

Amounts are displayed in Philippine pesos (PHP).

## Run locally

Requires Python 3.13. On Windows, open a terminal in this repository and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install "flet[all]==1.0.5"
flet run app.py
```

## Build for Android

With the virtual environment active, run:

```powershell
flet build apk --python-version 3.13
```

The APK will be in `build/apk/`. The first build may download Flutter, JDK 17, and the Android SDK. See [Flet's Android build guide](https://flet.dev/docs/publish/android/) for requirements.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Project status

The app is usable for personal tracking, but still in early development. It has no account, cloud sync, import, export, or backup. Clearing the app's data or uninstalling it may remove saved expenses. The database and generated APK are intentionally excluded from Git.

The project began as a command-line tracker. Its earlier CLI code remains available in Git history; the current app starts from `app.py` and stores data through `expense_store.py`.
