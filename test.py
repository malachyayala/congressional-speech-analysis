import sqlite3
import pandas as pd

conn = sqlite3.connect('congress_master.db')

# This pulls 0 rows of data but retrieves the column headers
df_sample = pd.read_sql("SELECT * FROM speeches LIMIT 0", conn)

print("--- Table Columns ---")
print(df_sample.columns.tolist())

# To see the data types too:
print("\n--- Column Data Types ---")
print(df_sample.dtypes)

conn.close()