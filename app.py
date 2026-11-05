"""Offline Flet interface for the expense tracker."""

from datetime import date, datetime

import flet as ft

from expense_store import Expense, ExpenseStore, money


def main(page: ft.Page):
    store = ExpenseStore()
    today = date.today()
    selected_year, selected_month = today.year, today.month
    selected_expense: Expense | None = None
    screen = "expenses"

    page.title = "Expense Tracker"
    page.padding = 16
    page.theme_mode = ft.ThemeMode.LIGHT

    def change_month(delta: int):
        nonlocal selected_year, selected_month
        index = selected_year * 12 + selected_month - 1 + delta
        selected_year, zero_month = divmod(index, 12)
        selected_month = zero_month + 1
        render()

    def show_form(expense: Expense | None = None):
        nonlocal selected_expense, screen
        selected_expense = expense
        screen = "form"
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

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete expense?"),
            content=ft.Text(f"Delete {expense.description} ({money(expense.cents)})?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.TextButton("Delete", on_click=delete),
            ],
        ))

    def render():
        items = store.list_month(selected_year, selected_month)
        total = sum(item.cents for item in items)
        month_label = date(selected_year, selected_month, 1).strftime("%B %Y")
        page.clean()

        if screen == "form":
            expense = selected_expense
            description = ft.TextField(label="Description", value=expense.description if expense else "", max_length=120)
            amount = ft.TextField(
                label="Amount (PHP)",
                value=f"{expense.cents / 100:.2f}" if expense else "",
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            chosen_date = date.fromisoformat(expense.spent_on) if expense else today
            date_label = ft.Text(chosen_date.strftime("%B %d, %Y"))

            def on_date_change(_):
                nonlocal chosen_date
                value = picker.value
                if value:
                    chosen_date = value.date() if isinstance(value, datetime) else value
                    date_label.value = chosen_date.strftime("%B %d, %Y")
                    page.update()

            picker = ft.DatePicker(value=chosen_date, on_change=on_date_change)

            def save(_):
                description.error = None
                amount.error = None
                try:
                    if expense:
                        store.update(expense.id, description.value, amount.value, chosen_date.isoformat())
                    else:
                        store.add(description.value, amount.value, chosen_date.isoformat())
                except ValueError as exc:
                    message = str(exc)
                    (description if "description" in message.lower() else amount).error = message
                    page.update()
                    return
                show_screen("expenses")

            page.add(ft.Column([
                ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: show_screen("expenses")),
                    ft.Text("Edit expense" if expense else "Add expense", size=24, weight=ft.FontWeight.BOLD),
                ]),
                description,
                amount,
                ft.Row([ft.Text("Date"), date_label, ft.TextButton("Change", on_click=lambda _: page.show_dialog(picker))]),
                ft.FilledButton("Save expense", icon=ft.Icons.SAVE, on_click=save),
            ], spacing=18))
            return

        heading = ft.Row([
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=lambda _: change_month(-1)),
            ft.Text(month_label, size=20, weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda _: change_month(1)),
        ])
        summary = ft.Container(
            content=ft.Column([
                ft.Text("Monthly spending", size=14),
                ft.Text(money(total), size=32, weight=ft.FontWeight.BOLD),
                ft.Text(f"{len(items)} expense{'s' if len(items) != 1 else ''}"),
            ]),
            padding=20,
            border_radius=16,
            bgcolor=ft.Colors.BLUE_50,
        )
        controls = [heading, summary]
        if screen == "expenses":
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
                        ft.Text(date.fromisoformat(item.spent_on).strftime("%b %d, %Y"), size=12),
                    ], expand=True, spacing=2),
                    ft.Text(money(item.cents)),
                    ft.IconButton(ft.Icons.EDIT, tooltip="Edit", on_click=lambda _, x=item: show_form(x)),
                    ft.IconButton(ft.Icons.DELETE, tooltip="Delete", on_click=lambda _, x=item: confirm_delete(x)),
                ]))
        else:
            controls.append(ft.Text("Monthly summary", size=20, weight=ft.FontWeight.BOLD))
            controls.append(ft.Text("Use the arrows to review another month."))

        page.add(ft.Column(controls, spacing=16, scroll=ft.ScrollMode.AUTO, expand=True))
        page.navigation_bar = ft.NavigationBar(
            selected_index=0 if screen == "expenses" else 1,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.RECEIPT_LONG, label="Expenses"),
                ft.NavigationBarDestination(icon=ft.Icons.BAR_CHART, label="Summary"),
            ],
            on_change=lambda event: show_screen("expenses" if event.control.selected_index == 0 else "summary"),
        )
        page.update()

    render()


if __name__ == "__main__":
    ft.run(main)
