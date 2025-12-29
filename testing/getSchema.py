import sqlite3

# Connect to your DB
db_path = "congress_master.db" 
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print(f"--- DATABASE STRUCTURE FOR {db_path} ---\n")

for table_name in tables:
    table = table_name[0]
    print(f"TABLE: {table}")
    
    # Get the CREATE statement
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';")
    create_stmt = cursor.fetchone()[0]
    print(create_stmt)
    print("-" * 40)
    
    # Optional: Get row counts to see how much data is in each
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"Approx Rows: {count:,}")
    print("=" * 40 + "\n")

conn.close()