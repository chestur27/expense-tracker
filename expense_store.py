"""SQLite persistence and validation for the Android expense tracker."""

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation
import os
from pathlib import Path
import sqlite3

def validate_category_name(name: str) -> str:
    name = name.strip() if isinstance(name, str) else ""
    if not name:
        raise ValueError("Enter a category name.")
    if len(name) > 40:
        raise ValueError("Category name must be 40 characters or fewer.")
    return name


@dataclass(frozen=True)
class Expense:
    id: int
    description: str
    cents: int
    spent_on: str
    category: str


@dataclass(frozen=True)
class Salary:
    id: int
    cents: int
    received_on: str
    period_start: str
    period_end: str


def parse_amount(value: str) -> int:
    try:
        amount = Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        raise ValueError("Enter a valid amount.") from None
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
        raise ValueError("Amount must be positive with at most two decimal places.")
    return int(amount * 100)


def validate_expense(description: str, amount: str, spent_on: str, category: str) -> tuple[str, int, str, str]:
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
    if not category or not isinstance(category, str):
        raise ValueError("Select a category.")
    return description, cents, parsed_date.isoformat(), category.strip()


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}₱{Decimal(abs(cents)) / 100:,.2f}"


def validate_salary(amount: str, period_start: str, period_end: str) -> tuple[int, str, str]:
    cents = parse_amount(amount)
    try:
        start = date.fromisoformat(period_start)
        end = date.fromisoformat(period_end)
    except (TypeError, ValueError):
        raise ValueError("Enter a date as YYYY-MM-DD.") from None
    if end < start:
        raise ValueError("Pay period end must be on or after its start.")
    return cents, start.isoformat(), end.isoformat()


def month_bounds(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start.isoformat(), end.isoformat()


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
                spent_on TEXT NOT NULL,
                category TEXT NOT NULL
            )""")
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(expenses)")}
            if "category" not in columns:
                conn.execute(
                    "ALTER TABLE expenses ADD COLUMN category TEXT NOT NULL DEFAULT 'Uncategorized'"
                )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(spent_on)")
            conn.execute("""CREATE TABLE IF NOT EXISTS salaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cents INTEGER NOT NULL CHECK(cents > 0),
                received_on TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL
            )""")
            salary_columns = {row["name"] for row in conn.execute("PRAGMA table_info(salaries)")}
            if "period_start" not in salary_columns:
                conn.execute("ALTER TABLE salaries ADD COLUMN period_start TEXT")
                conn.execute("UPDATE salaries SET period_start=received_on WHERE period_start IS NULL")
            if "period_end" not in salary_columns:
                conn.execute("ALTER TABLE salaries ADD COLUMN period_end TEXT")
                conn.execute("UPDATE salaries SET period_end=received_on WHERE period_end IS NULL")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_salaries_date ON salaries(received_on)")
            conn.execute("""CREATE TABLE IF NOT EXISTS categories (
                name TEXT PRIMARY KEY COLLATE NOCASE
            )""")
            conn.execute(
                "INSERT OR IGNORE INTO categories (name) "
                "SELECT DISTINCT category FROM expenses WHERE category IS NOT NULL AND category <> ''"
            )

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def add(self, description: str, amount: str, spent_on: str, category: str) -> int:
        description, cents, spent_on, category = validate_expense(description, amount, spent_on, category)
        with self._connect() as conn:
            category = self._require_category(conn, category)
            cursor = conn.execute(
                "INSERT INTO expenses (description, cents, spent_on, category) VALUES (?, ?, ?, ?)",
                (description, cents, spent_on, category),
            )
            return cursor.lastrowid

    def update(self, expense_id: int, description: str, amount: str, spent_on: str, category: str) -> bool:
        description, cents, spent_on, category = validate_expense(description, amount, spent_on, category)
        with self._connect() as conn:
            category = self._require_category(conn, category)
            cursor = conn.execute(
                "UPDATE expenses SET description=?, cents=?, spent_on=?, category=? WHERE id=?",
                (description, cents, spent_on, category, expense_id),
            )
            return cursor.rowcount > 0

    def delete(self, expense_id: int) -> bool:
        with self._connect() as conn:
            return conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,)).rowcount > 0

    @staticmethod
    def _require_category(conn: sqlite3.Connection, name: str) -> str:
        row = conn.execute("SELECT name FROM categories WHERE name=?", (name,)).fetchone()
        if row is None:
            raise ValueError("Select a category.")
        return row["name"]

    def list_categories(self) -> list[str]:
        with self._connect() as conn:
            return [row["name"] for row in conn.execute(
                "SELECT name FROM categories ORDER BY name COLLATE NOCASE"
            )]

    def category_usage(self, name: str) -> int:
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM expenses WHERE category=?", (name,)
            ).fetchone()[0]

    def add_category(self, name: str) -> None:
        name = validate_category_name(name)
        with self._connect() as conn:
            try:
                conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            except sqlite3.IntegrityError:
                raise ValueError("That category already exists.") from None

    def rename_category(self, old_name: str, new_name: str) -> None:
        new_name = validate_category_name(new_name)
        with self._connect() as conn:
            old_name = self._require_category(conn, old_name)
            duplicate = conn.execute("SELECT name FROM categories WHERE name=?", (new_name,)).fetchone()
            if duplicate and duplicate["name"].casefold() != old_name.casefold():
                raise ValueError("That category already exists.")
            conn.execute("UPDATE categories SET name=? WHERE name=?", (new_name, old_name))
            conn.execute("UPDATE expenses SET category=? WHERE category=?", (new_name, old_name))

    def delete_category(self, name: str) -> None:
        with self._connect() as conn:
            name = self._require_category(conn, name)
            if conn.execute("SELECT 1 FROM expenses WHERE category=? LIMIT 1", (name,)).fetchone():
                raise ValueError("Move or delete this category's expenses first.")
            conn.execute("DELETE FROM categories WHERE name=?", (name,))

    def list_month(self, year: int, month: int) -> list[Expense]:
        start, end = month_bounds(year, month)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, description, cents, spent_on, category FROM expenses "
                "WHERE spent_on >= ? AND spent_on < ? ORDER BY spent_on DESC, id DESC",
                (start, end),
            ).fetchall()
        return [Expense(**dict(row)) for row in rows]

    def add_salary(self, amount: str, period_start: str, period_end: str, *, added_on: date | None = None) -> int:
        cents, period_start, period_end = validate_salary(amount, period_start, period_end)
        received_on = (added_on or date.today()).isoformat()
        with self._connect() as conn:
            return conn.execute(
                "INSERT INTO salaries (cents, received_on, period_start, period_end) VALUES (?, ?, ?, ?)",
                (cents, received_on, period_start, period_end),
            ).lastrowid

    def update_salary(self, salary_id: int, amount: str, period_start: str, period_end: str) -> bool:
        cents, period_start, period_end = validate_salary(amount, period_start, period_end)
        with self._connect() as conn:
            return conn.execute(
                "UPDATE salaries SET cents=?, period_start=?, period_end=? WHERE id=?",
                (cents, period_start, period_end, salary_id),
            ).rowcount > 0

    def delete_salary(self, salary_id: int) -> bool:
        with self._connect() as conn:
            return conn.execute("DELETE FROM salaries WHERE id=?", (salary_id,)).rowcount > 0

    def list_salaries_month(self, year: int, month: int) -> list[Salary]:
        start, end = month_bounds(year, month)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, cents, received_on, period_start, period_end FROM salaries "
                "WHERE received_on >= ? AND received_on < ? "
                "ORDER BY received_on DESC, id DESC",
                (start, end),
            ).fetchall()
        return [Salary(**dict(row)) for row in rows]

    def balance_through_month(self, year: int, month: int) -> int:
        _, end = month_bounds(year, month)
        with self._connect() as conn:
            salary_cents = conn.execute(
                "SELECT COALESCE(SUM(cents), 0) FROM salaries WHERE received_on < ?",
                (end,),
            ).fetchone()[0]
            expense_cents = conn.execute(
                "SELECT COALESCE(SUM(cents), 0) FROM expenses WHERE spent_on < ?",
                (end,),
            ).fetchone()[0]
        return salary_cents - expense_cents
