import sqlite3
import time

DB_PATH = "congress_master.db"

def check_status():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        print("Checking database... (counting 10 million rows takes a moment)")
        
        # 1. Get Total Speeches
        # Optimization: If your DB is massive, this count might be slow. 
        # If it hangs, we can cache this number (approx 9,791,293)
        c.execute("SELECT COUNT(speech_id) FROM speeches")
        total = c.fetchone()[0]
        
        # 2. Get Speeches Already Done
        c.execute("SELECT COUNT(speech_id) FROM speeches WHERE is_procedure IS NOT NULL")
        done = c.fetchone()[0]
        
        conn.close()
        
        # 3. Calculate Progress
        remaining = total - done
        percent = (done / total) * 100
        
        # --- NEW SPEED METRICS ---
        # Based on your log: 25,000 rows in ~3 min 52 sec (232s)
        # 25,000 / 232 = ~107 rows/sec
        # 107 * 60 = ~6,420 rows/min
        
        rows_per_min = 6400 
        
        mins_left = remaining / rows_per_min
        hours_left = mins_left / 60
        days_left = hours_left / 24
        
        print("-" * 40)
        print(f"Total Speeches:    {total:,}")
        print(f"Processed:         {done:,}")
        print(f"Remaining:         {remaining:,}")
        print(f"Progress:          {percent:.2f}%")
        print("-" * 40)
        print(f"Current Speed:     ~{rows_per_min:,} rows/min")
        
        if hours_left > 24:
             print(f"Est. Time Left:    {days_left:.1f} days ({hours_left:.1f} hours)")
        else:
             print(f"Est. Time Left:    {hours_left:.1f} hours")
        print("-" * 40)

    except Exception as e:
        print(f"Error checking status: {e}")

if __name__ == "__main__":
    while True:
        check_status()
        # Refresh every 60 seconds so you can leave it running
        time.sleep(60)
        print("\nRefreshing...\n")