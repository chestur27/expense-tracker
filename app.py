"""Offline Flet interface for the expense tracker."""

import asyncio
from datetime import date, datetime, time
import sys

import flet as ft

from expense_store import Expense, ExpenseStore, Salary, money


def picker_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.astimezone().date() if value.tzinfo else value.date()
    return value


def picker_initial_value(value: date) -> datetime:
    # Noon keeps a calendar day stable when the client converts time zones.
    return datetime.combine(value, time(hour=12))


async def main(page: ft.Page):
    page.title = "Expense Tracker"
    page.padding = 16
    page.theme_mode = ft.ThemeMode.LIGHT
    root_view = page.views[0]
    root_view.can_pop = False

    def confirm_exit():
        async def cancel(_):
            page.pop_dialog()
            await root_view.confirm_pop(False)

        async def exit_app(_):
            page.pop_dialog()
            if page.web:
                await root_view.confirm_pop(True)
            elif page.platform == ft.PagePlatform.ANDROID:
                sys.exit(0)
            else:
                await page.window.destroy()

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Exit Expense Tracker?"),
            content=ft.Text("Are you sure you want to exit?"),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.TextButton("Exit", on_click=exit_app),
            ],
        ))

    root_view.on_confirm_pop = lambda _: confirm_exit()
    page.on_view_pop = lambda _: confirm_exit()

    def show_content(control):
        page.add(ft.SafeArea(content=control, expand=True))

    show_content(ft.Column([
        ft.ProgressRing(),
        ft.Text("Loading Expense Tracker…", size=18, weight=ft.FontWeight.BOLD),
    ], expand=True, alignment=ft.MainAxisAlignment.CENTER,
       horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20))
    page.update()
    store, _ = await asyncio.gather(asyncio.to_thread(ExpenseStore), asyncio.sleep(0.35))

    today = date.today()
    selected_year, selected_month = today.year, today.month
    selected_expense: Expense | None = None
    selected_salary: Salary | None = None
    screen = "expenses"

    def toast(message: str):
        page.show_dialog(ft.SnackBar(content=ft.Text(message), duration=2500))

    def change_month(delta: int):
        nonlocal selected_year, selected_month
        index = selected_year * 12 + selected_month - 1 + delta
        selected_year, zero_month = divmod(index, 12)
        selected_month = zero_month + 1
        render()

    def show_form(expense: Expense | None = None):
        nonlocal selected_expense, screen
        selected_expense = expense
        screen = "expense_form"
        render()

    def show_salary_form(salary: Salary | None = None):
        nonlocal selected_salary, screen
        selected_salary = salary
        screen = "salary_form"
        render()

    def show_screen(name: str):
        nonlocal screen
        screen = name
        render()

    def confirm_delete(expense: Expense):
        def delete(_):
            store.delete(expense.id)
            page.pop_dialog()
            render()
            toast("Expense deleted")

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete expense?"),
            content=ft.Text(f"Delete {expense.description} ({money(expense.cents)})?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.TextButton("Delete", on_click=delete),
            ],
        ))

    def confirm_delete_salary(salary: Salary):
        def delete(_):
            store.delete_salary(salary.id)
            page.pop_dialog()
            render()
            toast("Salary deleted")

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete salary?"),
            content=ft.Text(f"Delete salary of {money(salary.cents)}?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.TextButton("Delete", on_click=delete),
            ],
        ))

    def edit_category(name: str | None = None, on_saved=None):
        field = ft.TextField(label="Category name", value=name or "", max_length=40)

        def save(_):
            try:
                if name is None:
                    store.add_category(field.value)
                else:
                    store.rename_category(name, field.value)
            except ValueError as exc:
                field.error_text = str(exc)
                page.update()
                return
            page.pop_dialog()
            if on_saved:
                on_saved(field.value.strip())
            else:
                render()
            toast("Category updated" if name is not None else "Category added")

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit category" if name else "Add category"),
            content=field,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.TextButton("Save", on_click=save),
            ],
        ))

    def confirm_delete_category(name: str):
        def delete(_):
            store.delete_category(name)
            page.pop_dialog()
            render()
            toast("Category deleted")

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete category?"),
            content=ft.Text(f"Remove {name} from the category list?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.TextButton("Delete", on_click=delete),
            ],
        ))

    def category_options():
        return [
            ft.DropdownOption(
                key=name,
                content=ft.Text(name, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS),
            )
            for name in store.list_categories()
        ]

    def render():
        items = store.list_month(selected_year, selected_month)
        salaries = store.list_salaries_month(selected_year, selected_month)
        total = sum(item.cents for item in items)
        salary_total = sum(item.cents for item in salaries)
        monthly_change = salary_total - total
        balance = store.balance_through_month(selected_year, selected_month)
        month_label = date(selected_year, selected_month, 1).strftime("%B %Y")
        page.clean()

        if screen == "expense_form":
            expense = selected_expense
            description = ft.TextField(label="Description", value=expense.description if expense else "", max_length=120)
            amount = ft.TextField(
                label="Amount (PHP)",
                value=f"{expense.cents / 100:.2f}" if expense else "",
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            category = ft.Dropdown(
                label="Category",
                value=expense.category if expense else None,
                options=category_options(),
                helper_text="Add a category to get started." if not store.list_categories() else None,
            )

            def category_added(name):
                category.options = category_options()
                category.value = name
                category.error_text = None
                category.helper_text = None
                page.update()
            chosen_date = date.fromisoformat(expense.spent_on) if expense else date.today()
            date_label = ft.Text(chosen_date.strftime("%B %d, %Y"))

            def on_date_change(_):
                nonlocal chosen_date
                value = picker.value
                if value:
                    chosen_date = picker_date(value)
                    date_label.value = chosen_date.strftime("%B %d, %Y")
                    page.update()

            picker = ft.DatePicker(value=picker_initial_value(chosen_date), on_change=on_date_change)

            def save(_):
                nonlocal selected_year, selected_month
                description.error_text = None
                amount.error_text = None
                category.error_text = None
                try:
                    if expense:
                        store.update(expense.id, description.value, amount.value, chosen_date.isoformat(), category.value)
                    else:
                        store.add(description.value, amount.value, chosen_date.isoformat(), category.value)
                except ValueError as exc:
                    message = str(exc)
                    field = (description if "description" in message.lower()
                             else category if "category" in message.lower() else amount)
                    field.error_text = message
                    page.update()
                    return
                selected_year, selected_month = chosen_date.year, chosen_date.month
                show_screen("expenses")
                toast("Expense updated" if expense else "Expense added")

            show_content(ft.Column([
                ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: show_screen("expenses")),
                    ft.Text("Edit expense" if expense else "Add expense", size=24, weight=ft.FontWeight.BOLD),
                ]),
                description,
                amount,
                category,
                ft.TextButton(
                    "Add category",
                    icon=ft.Icons.ADD,
                    on_click=lambda _: edit_category(on_saved=category_added),
                ),
                ft.Row([ft.Text("Date"), date_label, ft.TextButton("Change", on_click=lambda _: page.show_dialog(picker))]),
                ft.FilledButton("Save expense", icon=ft.Icons.SAVE, on_click=save),
            ], spacing=18, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
            return

        if screen == "salary_form":
            salary = selected_salary
            amount = ft.TextField(
                label="Salary amount (PHP)",
                value=f"{salary.cents / 100:.2f}" if salary else "",
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            added_on = date.fromisoformat(salary.received_on) if salary else date.today()
            period_start = date.fromisoformat(salary.period_start) if salary else added_on.replace(day=1)
            period_end = date.fromisoformat(salary.period_end) if salary else added_on
            start_label = ft.Text(period_start.strftime("%b %d, %Y"))
            end_label = ft.Text(period_end.strftime("%b %d, %Y"))
            period_error = ft.Text("", color=ft.Colors.RED, visible=False)

            def on_start_change(_):
                nonlocal period_start
                if start_picker.value:
                    period_start = picker_date(start_picker.value)
                    start_label.value = period_start.strftime("%b %d, %Y")
                    page.update()

            def on_end_change(_):
                nonlocal period_end
                if end_picker.value:
                    period_end = picker_date(end_picker.value)
                    end_label.value = period_end.strftime("%b %d, %Y")
                    page.update()

            start_picker = ft.DatePicker(value=picker_initial_value(period_start), on_change=on_start_change)
            end_picker = ft.DatePicker(value=picker_initial_value(period_end), on_change=on_end_change)

            def save_salary(_):
                nonlocal selected_year, selected_month
                amount.error_text = None
                period_error.visible = False
                try:
                    if salary:
                        store.update_salary(salary.id, amount.value, period_start.isoformat(), period_end.isoformat())
                    else:
                        store.add_salary(amount.value, period_start.isoformat(), period_end.isoformat(), added_on=added_on)
                except ValueError as exc:
                    if "period" in str(exc).lower() or "date" in str(exc).lower():
                        period_error.value = str(exc)
                        period_error.visible = True
                    else:
                        amount.error_text = str(exc)
                    page.update()
                    return
                selected_year, selected_month = added_on.year, added_on.month
                show_screen("salary")
                toast("Salary updated" if salary else "Salary added")

            show_content(ft.Column([
                ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: show_screen("salary")),
                    ft.Text("Edit salary" if salary else "Add salary", size=24, weight=ft.FontWeight.BOLD),
                ]),
                amount,
                ft.Text(f"Date added: {added_on.strftime('%b %d, %Y')}"),
                ft.Row([ft.Text("Period start", expand=True), start_label,
                        ft.TextButton("Change", on_click=lambda _: page.show_dialog(start_picker))]),
                ft.Row([ft.Text("Period end", expand=True), end_label,
                        ft.TextButton("Change", on_click=lambda _: page.show_dialog(end_picker))]),
                period_error,
                ft.FilledButton("Save salary", icon=ft.Icons.SAVE, on_click=save_salary),
            ], spacing=18, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
            return

        if screen == "categories":
            names = store.list_categories()
            controls = [ft.Row([
                ft.Text("Categories", size=24, weight=ft.FontWeight.BOLD, expand=True),
                ft.FilledButton("Add", icon=ft.Icons.ADD, on_click=lambda _: edit_category()),
            ])]
            if not names:
                controls.append(ft.Text("No categories yet. Add one to use it with expenses."))
            for name in names:
                count = store.category_usage(name)
                controls.append(ft.Row([
                    ft.Column([
                        ft.Text(name, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{count} expense{'s' if count != 1 else ''}", size=12),
                    ], expand=True, spacing=2),
                    ft.IconButton(ft.Icons.EDIT, tooltip="Rename", on_click=lambda _, x=name: edit_category(x)),
                    ft.IconButton(
                        ft.Icons.DELETE,
                        tooltip="Move or delete expenses before removing this category" if count else "Delete",
                        disabled=count > 0,
                        on_click=lambda _, x=name: confirm_delete_category(x),
                    ),
                ]))
            show_content(ft.Column(controls, spacing=16, scroll=ft.ScrollMode.AUTO, expand=True))
            page.navigation_bar = navigation_bar()
            page.update()
            return

        heading = ft.Row([
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda _: change_month(-1)),
            ft.Text(month_label, size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda _: change_month(1)),
        ])
        budget_card = ft.Container(
            content=ft.Column([
                ft.Text("Available budget", size=12, no_wrap=True),
                ft.Text(money(balance), size=22, weight=ft.FontWeight.BOLD, no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS, tooltip=money(balance)),
                ft.Text(f"Through {month_label}", size=11, no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS),
            ]),
            padding=14,
            border_radius=16,
            bgcolor=ft.Colors.BLUE_50,
            height=132,
            expand=True,
        )
        controls = [heading]
        if screen == "expenses":
            expense_card = ft.Container(
                content=ft.Column([
                    ft.Text("Expenses this month", size=12, no_wrap=True),
                    ft.Text(money(total), size=22, weight=ft.FontWeight.BOLD, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS, tooltip=money(total)),
                    ft.Text(f"{len(items)} expense{'s' if len(items) != 1 else ''}", size=11),
                ]),
                padding=14,
                border_radius=16,
                bgcolor=ft.Colors.ORANGE_50,
                height=132,
                expand=True,
            )
            controls.append(ft.Row([budget_card, expense_card], spacing=10))
            controls.append(ft.Row([
                ft.Text("Expenses", size=20, weight=ft.FontWeight.BOLD, expand=True),
                ft.FilledButton("Add", icon=ft.Icons.ADD, on_click=lambda _: show_form()),
            ]))
            if not items:
                controls.append(ft.Text("No expenses this month. Add one to get started."))
            for item in items:
                controls.append(ft.Row([
                    ft.Column([
                        ft.Text(item.description, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{item.category} · {date.fromisoformat(item.spent_on).strftime('%b %d, %Y')}", size=12),
                    ], expand=True, spacing=2),
                    ft.Text(money(item.cents)),
                    ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda _, x=item: show_form(x)),
                    ft.IconButton(ft.Icons.DELETE, tooltip="Delete", on_click=lambda _, x=item: confirm_delete(x)),
                ]))
        elif screen == "salary":
            salary_card = ft.Container(
                content=ft.Column([
                    ft.Text("Salary this month", size=12, no_wrap=True),
                    ft.Text(money(salary_total), size=22, weight=ft.FontWeight.BOLD, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS, tooltip=money(salary_total)),
                    ft.Text(f"{len(salaries)} payment{'s' if len(salaries) != 1 else ''}", size=11),
                ]),
                padding=14,
                border_radius=16,
                bgcolor=ft.Colors.GREEN_50,
                height=132,
                expand=True,
            )
            controls.append(ft.Row([budget_card, salary_card], spacing=10))
            controls.append(ft.Row([
                ft.Text("Salary", size=20, weight=ft.FontWeight.BOLD, expand=True),
                ft.FilledButton("Add", icon=ft.Icons.ADD, on_click=lambda _: show_salary_form()),
            ]))
            if not salaries:
                controls.append(ft.Text("No salary recorded this month."))
            for salary in salaries:
                controls.append(ft.Row([
                    ft.Column([
                        ft.Text("Salary", weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"Pay period: {date.fromisoformat(salary.period_start).strftime('%b %d')} – "
                            f"{date.fromisoformat(salary.period_end).strftime('%b %d, %Y')}", size=12,
                        ),
                        ft.Text(f"Added {date.fromisoformat(salary.received_on).strftime('%b %d, %Y')}", size=12),
                    ], expand=True, spacing=2),
                    ft.Text(money(salary.cents)),
                    ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda _, x=salary: show_salary_form(x)),
                    ft.IconButton(ft.Icons.DELETE, tooltip="Delete", on_click=lambda _, x=salary: confirm_delete_salary(x)),
                ]))
        else:
            change_card = ft.Container(
                content=ft.Column([
                    ft.Text("Change this month", size=12, no_wrap=True),
                    ft.Text(money(monthly_change), size=22, weight=ft.FontWeight.BOLD,
                            no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                            tooltip=money(monthly_change)),
                    ft.Text("Salary less expenses", size=11, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS),
                ]),
                padding=14,
                border_radius=16,
                bgcolor=ft.Colors.GREEN_50 if monthly_change >= 0 else ft.Colors.ORANGE_50,
                height=132,
                expand=True,
            )
            controls.append(ft.Row([budget_card, change_card], spacing=10))
            controls.append(ft.Text("Budget tracker", size=20, weight=ft.FontWeight.BOLD))
            controls.append(ft.Row([ft.Text("Salary", expand=True), ft.Text(money(salary_total))]))
            controls.append(ft.Row([ft.Text("Expenses", expand=True), ft.Text(money(total))]))
            controls.append(ft.Text("Spending by category", size=18, weight=ft.FontWeight.BOLD))
            category_totals = {}
            for item in items:
                category_totals[item.category] = category_totals.get(item.category, 0) + item.cents
            for name, cents in sorted(category_totals.items(), key=lambda entry: (-entry[1], entry[0])):
                controls.append(ft.Row([ft.Text(name, expand=True), ft.Text(money(cents))]))
            if not items:
                controls.append(ft.Text("No expenses this month."))

        show_content(ft.Column(controls, spacing=16, scroll=ft.ScrollMode.AUTO, expand=True))
        page.navigation_bar = navigation_bar()
        page.update()

    def navigation_bar():
        return ft.NavigationBar(
            selected_index={"expenses": 0, "salary": 1, "summary": 2, "categories": 3}.get(screen, 0),
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.RECEIPT_LONG, label="Expenses"),
                ft.NavigationBarDestination(icon=ft.Icons.ATTACH_MONEY, label="Salary"),
                ft.NavigationBarDestination(icon=ft.Icons.BAR_CHART, label="Summary"),
                ft.NavigationBarDestination(icon=ft.Icons.LABEL, label="Categories"),
            ],
            on_change=lambda event: show_screen(("expenses", "salary", "summary", "categories")[event.control.selected_index]),
        )

    render()


if __name__ == "__main__":
    ft.run(main)
