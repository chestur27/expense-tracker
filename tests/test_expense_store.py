import tempfile
import unittest
from pathlib import Path
import sqlite3
import os
from contextlib import closing
from datetime import date

from expense_store import ExpenseStore, money, parse_amount


class ExpenseStoreTests(unittest.TestCase):
    def setUp(self):
        self.paths = []
        self.store = ExpenseStore(self.new_path())

    def tearDown(self):
        for path in self.paths:
            path.unlink(missing_ok=True)

    def new_path(self):
        fd, name = tempfile.mkstemp(suffix=".db", dir=Path(__file__).parent.parent)
        os.close(fd)
        path = Path(name)
        path.unlink()
        self.paths.append(path)
        return path

    def test_amount_validation(self):
        self.assertEqual(parse_amount("120.50"), 12050)
        self.assertEqual(money(-12050), "-₱120.50")
        for value in ("0", "-1", "1.234", "nan", "hello"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_amount(value)

    def test_month_boundaries_edit_delete_and_persistence(self):
        self.store.add_category("Food & Drinks")
        self.store.add_category("Other")
        december_id = self.store.add("Dinner", "120.50", "2026-12-31", "Food & Drinks")
        january_id = self.store.add("Coffee", "50", "2027-01-01", "Food & Drinks")
        self.assertEqual([x.id for x in self.store.list_month(2026, 12)], [december_id])
        self.assertEqual([x.id for x in self.store.list_month(2027, 1)], [january_id])
        self.assertTrue(self.store.update(december_id, "Lunch", "99.99", "2027-01-02", "Other"))
        reopened = ExpenseStore(self.store.path)
        self.assertEqual(
            [(x.cents, x.category) for x in reopened.list_month(2027, 1)],
            [(9999, "Other"), (5000, "Food & Drinks")],
        )
        self.assertTrue(reopened.delete(january_id))
        self.assertEqual(money(sum(x.cents for x in reopened.list_month(2027, 1))), "₱99.99")

    def test_category_required(self):
        for category in (None, "", "Unknown"):
            with self.subTest(category=category), self.assertRaisesRegex(ValueError, "category"):
                self.store.add("Dinner", "10", "2026-12-31", category)

    def test_custom_categories_rename_and_delete(self):
        self.store.add_category("  Pets  ")
        self.assertIn("Pets", ExpenseStore(self.store.path).list_categories())
        expense_id = self.store.add("Food", "20", "2026-11-01", "Pets")
        with self.assertRaisesRegex(ValueError, "Move or delete"):
            self.store.delete_category("Pets")
        self.store.rename_category("Pets", "Pet Care")
        self.assertEqual(self.store.list_month(2026, 11)[0].category, "Pet Care")
        with self.assertRaisesRegex(ValueError, "category"):
            self.store.add("Food", "20", "2026-11-01", "Pets")
        self.assertTrue(self.store.delete(expense_id))
        self.store.delete_category("Pet Care")
        self.assertNotIn("Pet Care", ExpenseStore(self.store.path).list_categories())

    def test_category_names_and_empty_category_list(self):
        self.assertEqual(self.store.list_categories(), [])
        self.store.add_category("Food & Drinks")
        self.store.add_category("Bills")
        self.store.add_category("Shopping")
        with self.assertRaisesRegex(ValueError, "category name"):
            self.store.add_category("  ")
        with self.assertRaisesRegex(ValueError, "40 characters"):
            self.store.add_category("x" * 41)
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.store.add_category("food & drinks")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.store.rename_category("Bills", "Shopping")
        self.store.rename_category("Bills", "bills")
        self.assertIn("bills", self.store.list_categories())
        for name in self.store.list_categories():
            self.store.delete_category(name)
        self.assertEqual(ExpenseStore(self.store.path).list_categories(), [])

    def test_existing_database_gains_category_without_losing_expenses(self):
        path = self.new_path()
        with closing(sqlite3.connect(path)) as conn:
            conn.execute(
                "CREATE TABLE expenses (id INTEGER PRIMARY KEY, description TEXT NOT NULL, "
                "cents INTEGER NOT NULL, spent_on TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO expenses VALUES (1, 'Old expense', 2500, '2026-11-01')"
            )
            conn.commit()
        migrated = ExpenseStore(path)
        self.assertEqual(migrated.list_month(2026, 11)[0].category, "Uncategorized")
        self.assertEqual(migrated.list_categories(), ["Uncategorized"])
        migrated.add_category("Bills")
        self.assertTrue(migrated.update(1, "Old expense", "25", "2026-11-01", "Bills"))
        self.assertEqual(ExpenseStore(path).list_month(2026, 11)[0].category, "Bills")

    def test_salary_changes_budget_across_months(self):
        self.store.add_category("Food")
        december_salary = self.store.add_salary("1000", "2026-12-01", "2026-12-15", added_on=date(2026, 12, 31))
        january_salary = self.store.add_salary("500.50", "2026-12-16", "2026-12-31", added_on=date(2027, 1, 1))
        expense_id = self.store.add("Dinner", "120.25", "2027-01-02", "Food")
        self.assertEqual([s.id for s in self.store.list_salaries_month(2026, 12)], [december_salary])
        self.assertEqual([s.id for s in self.store.list_salaries_month(2027, 1)], [january_salary])
        self.assertEqual(self.store.balance_through_month(2026, 12), 100000)
        self.assertEqual(self.store.balance_through_month(2027, 1), 138025)
        self.assertTrue(self.store.update_salary(january_salary, "600", "2027-01-01", "2027-01-15"))
        reopened = ExpenseStore(self.store.path)
        self.assertEqual(reopened.balance_through_month(2027, 1), 147975)
        self.assertEqual(reopened.list_salaries_month(2027, 1)[0].received_on, "2027-01-01")
        self.assertEqual(reopened.list_salaries_month(2027, 1)[0].period_end, "2027-01-15")
        self.assertTrue(reopened.delete_salary(december_salary))
        self.assertTrue(reopened.delete(expense_id))
        self.assertEqual(reopened.balance_through_month(2027, 1), 60000)

    def test_salary_validation_and_negative_balance(self):
        for amount, start, end in (
            ("0", "2026-11-01", "2026-11-15"),
            ("10", "invalid", "2026-11-15"),
            ("10", "2026-11-16", "2026-11-15"),
        ):
            with self.subTest(amount=amount, start=start, end=end), self.assertRaises(ValueError):
                self.store.add_salary(amount, start, end)
        self.store.add_category("Bills")
        self.store.add("Rent", "200", "2026-11-01", "Bills")
        self.assertEqual(self.store.balance_through_month(2026, 11), -20000)

    def test_existing_salary_gains_pay_period(self):
        path = self.new_path()
        with closing(sqlite3.connect(path)) as conn:
            conn.execute(
                "CREATE TABLE salaries (id INTEGER PRIMARY KEY, cents INTEGER NOT NULL, "
                "received_on TEXT NOT NULL)"
            )
            conn.execute("INSERT INTO salaries VALUES (1, 100000, '2026-11-05')")
            conn.commit()
        migrated = ExpenseStore(path)
        salary = migrated.list_salaries_month(2026, 11)[0]
        self.assertEqual((salary.period_start, salary.period_end), ("2026-11-05", "2026-11-05"))
        self.assertEqual(migrated.balance_through_month(2026, 11), 100000)
        self.assertEqual(ExpenseStore(path).list_salaries_month(2026, 11)[0], salary)


if __name__ == "__main__":
    unittest.main()
