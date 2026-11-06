import asyncio
import os
import tempfile
import unittest
from datetime import date, datetime, time, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import app
import flet as ft
from expense_store import ExpenseStore


class FakePage:
    def __init__(self):
        self.controls = []
        self.dialogs = []
        self.frames = []
        self.views = [FakeView()]
        self.web = True
        self.platform = None

    def clean(self):
        self.controls = []

    def add(self, control):
        self.controls.append(control)

    def update(self):
        self.frames.append(list(self.controls))

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None


class FakeView:
    def __init__(self):
        self.can_pop = True
        self.on_confirm_pop = None
        self.confirmed = []

    async def confirm_pop(self, should_pop):
        self.confirmed.append(should_pop)


class AppDateTests(unittest.TestCase):
    def setUp(self):
        fd, name = tempfile.mkstemp(suffix=".db", dir=Path(__file__).parent.parent)
        os.close(fd)
        self.path = Path(name)
        self.path.unlink()
        self.store = ExpenseStore(self.path)
        self.page = FakePage()
        with patch.object(app, "ExpenseStore", return_value=self.store):
            asyncio.run(app.main(self.page))

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def navigate(self, index):
        self.page.navigation_bar.on_change(
            SimpleNamespace(control=SimpleNamespace(selected_index=index))
        )

    def change_form_date(self, date_row_index, selected):
        form = self.page.controls[0].controls
        form[date_row_index].controls[2].on_click(None)
        picker = self.page.dialogs[-1]
        picker.value = datetime.combine(selected, time(hour=12))
        picker.on_change(None)
        self.page.pop_dialog()

    def test_picker_normalizes_aware_timestamp_and_initializes_at_noon(self):
        selected = date(2027, 1, 1)
        self.assertEqual(app.picker_initial_value(selected).hour, 12)
        timestamp = datetime(2026, 12, 31, 16, tzinfo=timezone.utc)
        self.assertEqual(app.picker_date(timestamp), timestamp.astimezone().date())

    def test_loading_view_and_exit_confirmation(self):
        self.assertEqual(type(self.page.frames[0][0].controls[0]).__name__, "ProgressRing")
        self.assertFalse(self.page.views[0].can_pop)
        self.page.views[0].on_confirm_pop(None)
        dialog = self.page.dialogs[-1]
        self.assertEqual(dialog.title.value, "Exit Expense Tracker?")
        asyncio.run(dialog.actions[0].on_click(None))
        self.assertEqual(self.page.views[0].confirmed, [False])
        self.page.views[0].on_confirm_pop(None)
        dialog = self.page.dialogs[-1]
        asyncio.run(dialog.actions[1].on_click(None))
        self.assertEqual(self.page.views[0].confirmed, [False, True])

    def test_android_exit_action(self):
        self.page.web = False
        self.page.platform = ft.PagePlatform.ANDROID
        self.page.views[0].on_confirm_pop(None)
        with self.assertRaises(SystemExit) as exit_result:
            asyncio.run(self.page.dialogs[-1].actions[1].on_click(None))
        self.assertEqual(exit_result.exception.code, 0)

    def test_budget_and_expenses_have_separate_cards(self):
        cards = self.page.controls[0].controls[1].controls
        self.assertEqual(cards[0].content.controls[0].value, "Available budget")
        self.assertEqual(cards[1].content.controls[0].value, "Expenses this month")
        self.navigate(1)
        cards = self.page.controls[0].controls[1].controls
        self.assertEqual(cards[0].content.controls[0].value, "Available budget")
        self.assertEqual(cards[1].content.controls[0].value, "Salary this month")
        self.navigate(2)
        cards = self.page.controls[0].controls[1].controls
        self.assertEqual(cards[0].content.controls[0].value, "Available budget")
        self.assertEqual(cards[1].content.controls[0].value, "Change this month")

    def test_salary_pay_period_and_expense_date(self):
        self.navigate(1)
        self.page.controls[0].controls[2].controls[1].on_click(None)
        self.change_form_date(3, date(2027, 1, 1))
        self.change_form_date(4, date(2027, 1, 15))
        form = self.page.controls[0].controls
        form[1].value = "1000"
        form[6].on_click(None)
        added_on = date.today()
        salary = self.store.list_salaries_month(added_on.year, added_on.month)[0]
        self.assertEqual(salary.received_on, added_on.isoformat())
        self.assertEqual((salary.period_start, salary.period_end), ("2027-01-01", "2027-01-15"))
        self.assertEqual(self.page.controls[0].controls[0].controls[1].value, added_on.strftime("%B %Y"))

        self.store.add_category("Food")
        self.navigate(0)
        self.page.controls[0].controls[2].controls[1].on_click(None)
        self.change_form_date(5, date(2027, 2, 1))
        form = self.page.controls[0].controls
        form[1].value = "Lunch"
        form[2].value = "50"
        form[3].value = "Food"
        form[6].on_click(None)
        self.assertEqual(self.store.list_month(2027, 2)[0].spent_on, "2027-02-01")
        self.assertEqual(self.page.controls[0].controls[0].controls[1].value, "February 2027")

        self.page.controls[0].controls[3].controls[2].on_click(None)
        self.change_form_date(5, date(2027, 3, 1))
        self.page.controls[0].controls[6].on_click(None)
        self.assertEqual(self.store.list_month(2027, 2), [])
        self.assertEqual(self.store.list_month(2027, 3)[0].spent_on, "2027-03-01")
        self.assertEqual(self.page.controls[0].controls[0].controls[1].value, "March 2027")


if __name__ == "__main__":
    unittest.main()
