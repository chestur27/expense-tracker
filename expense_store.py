"""SQLite persistence and validation for the Android expense tracker."""

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation
import os
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class Expense:
    id: int
    description: str
    cents: int
    spent_on: str


def parse_amount(value: str) -> int:
    try:
        amount = Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        raise ValueError("Enter a valid amount.") from None
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
        raise ValueError("Amount must be positive with at most two decimal places.")
    return int(amount * 100)


def validate_expense(description: str, amount: str, spent_on: str) -> tuple[str, int, str]:
    description = description.strip()
    if not description:
        raise ValueError("Enter a description.")
    if len(description) > 120:
        raise ValueError("Description must be 120 characters or fewer.")
    cents = parse_amount(amount)
    try:
        parsed_date = date.fromisoformat(spent_on)
    except ValueError:
        raise ValueError("Enter a date as YYYY-MM-DD.") from None
    return description, cents, parsed_date.isoformat()


def money(cents: int) -> str:
    return f"₱{Decimal(cents) / 100:,.2f}"


class ExpenseStore:
    def __init__(self, path: str | Path | None = None):
        data_dir = Path(os.environ.get("FLET_APP_STORAGE_DATA", "."))
        self.path = Path(path) if path is not None else data_dir / "expenses_mobile.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                cents INTEGER NOT NULL CHECK(cents > 0),
                spent_on TEXT NOT NULL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(spent_on)")

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def add(self, description: str, amount: str, spent_on: str) -> int:
        description, cents, spent_on = validate_expense(description, amount, spent_on)
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO expenses (description, cents, spent_on) VALUES (?, ?, ?)",
                (description, cents, spent_on),
            )
            return cursor.lastrowid

    def update(self, expense_id: int, description: str, amount: str, spent_on: str) -> bool:
        description, cents, spent_on = validate_expense(description, amount, spent_on)
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE expenses SET description=?, cents=?, spent_on=? WHERE id=?",
                (description, cents, spent_on, expense_id),
            )
            return cursor.rowcount > 0

    def delete(self, expense_id: int) -> bool:
        with self._connect() as conn:
            return conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,)).rowcount > 0

    def list_month(self, year: int, month: int) -> list[Expense]:
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, description, cents, spent_on FROM expenses "
                "WHERE spent_on >= ? AND spent_on < ? ORDER BY spent_on DESC, id DESC",
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        return [Expense(**dict(row)) for row in rows]
