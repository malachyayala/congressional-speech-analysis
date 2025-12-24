import sqlite3
import pandas as pd

DB_PATH = "congress_master.db"
TARGET_ID = "880029311"

def inspect_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"--- DEBUGGING SPEECH ID: {TARGET_ID} ---")
    
    # CHECK 1: Verify Column Names
    cursor.execute("PRAGMA table_info(speeches)")
    columns = [info[1] for info in cursor.fetchall()]
    print(f"1. Columns found: {columns}")
    
    if "speech_id" not in columns:
        print("❌ CRITICAL: Column 'speech_id' not found!")
        return

    # CHECK 2: Loose Search (Is it there, but formatted differently?)
    # We look for the ID inside the text to catch things like "ID_880029311"
    query = f"SELECT speech_id FROM speeches WHERE speech_id LIKE '%{TARGET_ID}%'"
    cursor.execute(query)
    results = cursor.fetchall()
    
    if not results:
        print("❌ 2. Exact ID not found via SQL LIKE search.")
        
        # CHECK 3: Sample the first 5 IDs to see the format
        print("   Sampling first 5 IDs in DB to check format:")
        cursor.execute("SELECT speech_id FROM speeches LIMIT 5")
        for row in cursor.fetchall():
            print(f"   - '{row[0]}' (Type: {type(row[0])})")
    else:
        found_val = results[0][0]
        print(f"✅ 2. Found match: '{found_val}'")
        print(f"   - Type in Python: {type(found_val)}")
        print(f"   - Exact Match Check: {found_val == TARGET_ID}")
        
        if found_val != TARGET_ID:
            print(f"⚠️ WARNING: Input '{TARGET_ID}' does not match DB '{found_val}' exactly.")
            print("   (Likely hidden whitespace or formatting)")

    conn.close()

if __name__ == "__main__":
    inspect_db()