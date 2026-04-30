import sqlite3

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

def get_connection():
    connection = sqlite3.connect('expenses.db')

    return connection