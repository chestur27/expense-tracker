from db import get_connection

def add_expense(description, amount):
    db_con = get_connection()
    cursor = db_con.cursor()

    insert_expenses_query = '''
    INSERT INTO expenses (description, amount) 
    VALUES (?, ?)
    '''

    cursor.execute(insert_expenses_query, (description, amount))
    db_con.commit()

    print("Expenses added successfully!")
    db_con.close()
    

def show_expense_list():
    db_con = get_connection()
    cursor = db_con.cursor()

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

    db_con.close()
        

def delete_expense(id):
    db_con = get_connection()
    cursor = db_con.cursor()

    cursor.execute("DELETE FROM expenses WHERE id = ?", (id,))
    db_con.commit()

    db_con.close()