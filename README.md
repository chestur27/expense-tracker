# Expense Tracker

A small, offline Android expense tracker built with Python, Flet, and SQLite. This is an early personal project that I plan to improve over time.

## Current features

- Add expenses with a description, amount, date, and category
- Add, rename, and remove categories from the Categories tab
- View expenses and totals by month
- See category totals in the monthly summary
- Record salary payments with a pay period and automatic date added, then track the available balance after expenses
- Review salary, expenses, and the monthly change in the Summary tab
- Edit expenses and delete them with confirmation
- Store data locally on the device
- Show a loading screen on startup and confirm before exiting with Android Back

Amounts are displayed in Philippine pesos (PHP).
Existing expenses are marked "Uncategorized" when the app upgrades its local database; edit them to choose a category.
The category list starts empty. Add categories from the expense form or Categories tab; they are saved locally. Renaming one updates its expenses, and you can remove it after its expenses have been moved or deleted.
The available balance carries forward: it is all salary received through the selected month minus all expenses dated through that month. Expenses recorded before any salary can make it negative.
Salary entries use the date they were added for the budget. The pay period dates describe the work covered by that payment. Existing salary entries use their recorded date as both pay period dates until edited.

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
