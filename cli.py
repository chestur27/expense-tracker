import argparse

def tracker_commands():
    parser = argparse.ArgumentParser(description="Expense Tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_expense = subparsers.add_parser("add")
    subparsers.add_parser("list")
    delete_expense = subparsers.add_parser("delete")
    summary_expense = subparsers.add_parser("summary")

    create_expense.add_argument("--description", required=True, metavar=" ", help="Description of the expense")
    create_expense.add_argument("--amount", type=float, required=True, metavar= " ", help="Amount of the expense")

    delete_expense.add_argument("--id", type=int, required=True, metavar=" ",  help="ID of the expense")

    summary_expense.add_argument("--year", type=int, metavar=" ", help="Total expenses for selected / current year")
    
    args = parser.parse_args()

    return args