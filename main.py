from cli import tracker_commands
from services import add_expense, show_expense_list, delete_expense
from db import db_init

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

def main():
    db_init()
    expense_process()

if __name__ == "__main__":
    main()