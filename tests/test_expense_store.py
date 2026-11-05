import tempfile
import unittest
from pathlib import Path

from expense_store import ExpenseStore, money, parse_amount


class ExpenseStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.store = ExpenseStore(Path(self.temp.name) / "test.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_amount_validation(self):
        self.assertEqual(parse_amount("120.50"), 12050)
        for value in ("0", "-1", "1.234", "nan", "hello"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_amount(value)

    def test_month_boundaries_edit_delete_and_persistence(self):
        december_id = self.store.add("Dinner", "120.50", "2026-12-31")
        january_id = self.store.add("Coffee", "50", "2027-01-01")
        self.assertEqual([x.id for x in self.store.list_month(2026, 12)], [december_id])
        self.assertEqual([x.id for x in self.store.list_month(2027, 1)], [january_id])
        self.assertTrue(self.store.update(december_id, "Lunch", "99.99", "2027-01-02"))
        reopened = ExpenseStore(self.store.path)
        self.assertEqual([x.cents for x in reopened.list_month(2027, 1)], [9999, 5000])
        self.assertTrue(reopened.delete(january_id))
        self.assertEqual(money(sum(x.cents for x in reopened.list_month(2027, 1))), "₱99.99")


if __name__ == "__main__":
    unittest.main()
