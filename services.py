from db import get_connection

def add_expense(description, amount):

    trimmed_desc = description.strip()
    if len(trimmed_desc) == 0:
        print("Empty description. Please add a description.")
        return
    if amount < 0:
        print("Negative amount is not allowed.")
        return
    
    db_con = get_connection()
    cursor = db_con.cursor()

    insert_expenses_query = '''
    INSERT INTO expenses (description, amount) 
    VALUES (?, ?)
    '''

    cursor.execute(insert_expenses_query, (trimmed_desc, amount))
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
    
    total_expenses_query = '''
    SELECT sum(amount) AS TOTAL FROM expenses
    '''
    cursor.execute(total_expenses_query)
    total = cursor.fetchone()
    print("-" * 45)
    if total[0] is None:
        print("Total amount: \u20B10")
    else:
        print(f"Total amount: \u20B1{total[0]}")
    db_con.close()

def summary_expense(year):
    db_con = get_connection()
    cursor = db_con.cursor() 

    

def delete_expense(id):
    db_con = get_connection()
    cursor = db_con.cursor()

    cursor.execute("SELECT id FROM expenses WHERE id = ?", (id,))
    expense_id = cursor.fetchone()

    if not expense_id:
        print("No ID found.")
        db_con.close()
        return
    
    cursor.execute("DELETE FROM expenses WHERE id = ?", (id,))
    print("Succesfully deleted an expense.")

    cursor.execute("SELECT EXISTS (SELECT 1 FROM expenses)")
    table_check = cursor.fetchone()
    if table_check[0] == 0:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'expenses'")
    db_con.commit()

    db_con.close()