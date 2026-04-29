import argparse
import sqlite3

def tracker_commands():
    parser = argparse.ArgumentParser(description="Expense Tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_expense = subparsers.add_parser("add")
    subparsers.add_parser("list")
    delete_expense = subparsers.add_parser("delete")

    create_expense.add_argument("--description", required=True, metavar=" ", help="Description of the expense")
    create_expense.add_argument("--amount", type=float, required=True, metavar= " ", help="Amount of the expense")

    delete_expense.add_argument("--id", type=int, required=True, metavar=" ",  help="ID of the expense")
    
    args = parser.parse_args()

    return args

def expense_process():
    result = tracker_commands()
    match result.command:
        case "add":
            add_expense(result.description, result.amount )
            return 
        case "list":
            show_expense_list()
            return
        case "delete":
            delete_expense(result.id)
            return

def db_init():
    with sqlite3.connect('expenses.db') as conn:
        cursor = conn.cursor()

        create_table_query = '''
        CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        date TEXT DEFAULT CURRENT_TIMESTAMP
        )
        '''

        cursor.execute(create_table_query)
        conn.commit()

def add_expense(description, amount):
    with sqlite3.connect('expenses.db') as conn:
        cursor = conn.cursor()

        insert_expenses_query = '''
        INSERT INTO expenses (description, amount) 
        VALUES (?, ?)
        '''

        cursor.execute(insert_expenses_query, (description, amount))
        conn.commit()

        print("Expenses added successfully!")

def show_expense_list():
    with sqlite3.connect('expenses.db') as conn:
        cursor = conn.cursor()

        fetch_expenses_query = '''
        SELECT id, DATE(date), description, amount FROM expenses
        '''
        cursor.execute(fetch_expenses_query)

        all_expenses = cursor.fetchall()
        print("Expense List:")
        table_header = ["ID", "Date", "Description", "Amount"]
        print("-" * 45)
        print(f"{table_header[0]:<5} {table_header[1]:<15} {table_header[2]:<15} {table_header[3]:<10}")
        print("-" * 45)
        for expense in all_expenses:
            print(f"{expense[0]:<5} {expense[1]:<15} {expense[2]:<15} {expense[3]:<10}")

def delete_expense(id):
    with sqlite3.connect('expenses.db') as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM expenses WHERE id = ?", (id,))
        conn.commit()


def main():
    db_init()
    expense_process()

if __name__ == "__main__":
    main()