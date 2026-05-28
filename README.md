# Expense Tracker

A CLI-based expense tracker built with Python and SQLite, with planned extensions into ETL workflows and automation.

## Features

- Add expenses with description and amount
- View all expenses in a formatted table
- Delete expenses by ID
- Persistent storage using SQLite

## Tech Stack

- Python (argparse, sqlite3)
- SQLite (local database)

## Usage / Commands

### Add an expense

`python main.py add --description "Lunch" --amount 120`

### List all expenses

`python main.py list`

### Delete an expense

`python main.py delete --id 5`

## Example Output

``` text
Expense List:
---------------------------------------------
ID    Date           Description     Amount
---------------------------------------------
1     2026-04-29     Lunch           120.0
2     2026-04-29     Coffee          50.0
```

## Roadmap

- [x] Basic commands (add, list, delete)
- [ ] Summary of expenses
- [ ] Monthly summary/filtering
- [x] Refactoring / Modularization
- [ ] Mini ETL Pipeline
- [ ] n8n Discord automation integration

## Project Goal

This project is part of a backend learning path and is being extended into a simple ETL system that will:

- Extract data from SQLite
- Transform it into summaries
- Load it into external services (e.g., Discord, spreadsheets)

## Notes

- The SQLite database file (.db) is ignored and not included in the repository.
- The database is automatically created when the app runs.

## License

This project is for learning and portfolio purposes.
