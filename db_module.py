# db_module.py

import pyodbc

def get_db_connection():
    """Establish and return a SQL Server database connection."""
    try:
        connection = pyodbc.connect(
            "DRIVER={SQL Server};"
            "SERVER=LAPTOP-SBLEMHDL\\SQLEXPRESS;"  # Update with your SQL Server name
            "DATABASE=LibraryDB;"                 # Update with your database name
            "Trusted_Connection=yes;"             # Windows Authentication
        )
        return connection
    except pyodbc.Error as e:
        print(f"❌ Error connecting to SQL Server: {e}")
        return None
