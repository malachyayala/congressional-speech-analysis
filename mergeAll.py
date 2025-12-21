import pandas as pd
import os
import sqlite3

# 1. SETUP
data_dir = '/Users/mj/Desktop/Misc/VSCodeStuff/legNLP/raw' 
db_name = 'congress_master.db'

# Define the columns we want to keep, including the new name columns
COLS_TO_KEEP = ['speech_id', 'speech', 'date', 'party', 'state_x', 'lastname', 'firstname', 'congress_session']

def load_congress_data(session_num, folder):
    speeches_path = os.path.join(folder, f'speeches_{session_num}.txt')
    descr_path = os.path.join(folder, f'descr_{session_num}.txt')
    speaker_map_path = os.path.join(folder, f'{session_num}_SpeakerMap.txt')

    if not all(os.path.exists(p) for p in [speeches_path, descr_path, speaker_map_path]):
        return None

    try:
        # Load with high-compatibility settings
        speeches = pd.read_csv(speeches_path, sep='|', encoding='ISO-8859-1', on_bad_lines='skip')
        descr = pd.read_csv(descr_path, sep='|', encoding='ISO-8859-1', on_bad_lines='skip')
        speaker_map = pd.read_csv(speaker_map_path, sep='|', encoding='ISO-8859-1', on_bad_lines='skip')

        # Merge
        merged_df = pd.merge(speeches, descr, on='speech_id', how='left')
        final_df = pd.merge(merged_df, speaker_map, on='speech_id', how='left')
        
        # Add identifiers
        final_df['congress_session'] = int(session_num)
        
        # Filter for desired columns
        available_cols = [c for c in COLS_TO_KEEP if c in final_df.columns]
        df_filtered = final_df[available_cols].copy()
        
        # --- HANDLE BLANK/UNKNOWNS ---
        # Define replacement values for missing data
        fill_values = {
            'lastname': 'Unknown',
            'firstname': 'Unknown',
            'party': 'Unknown',
            'state_x': 'Unknown',
            'speech': '[No Text recorded]'
        }
        # Apply the replacements
        df_filtered.fillna(value=fill_values, inplace=True)
        
        return df_filtered
    
    except Exception as e:
        print(f"Error processing Session {session_num}: {e}")
        return None

# 2. EXECUTION (Rest of your existing loop remains the same)
conn = sqlite3.connect(db_name)

for session_num in range(45, 112):
    session_str = str(session_num).zfill(3)
    
    # Optional: Skip sessions already processed
    try:
        existing = pd.read_sql(f"SELECT COUNT(*) FROM speeches WHERE congress_session = {session_num}", conn)
        if existing.iloc[0,0] > 0:
            print(f"Session {session_str} already in database. Skipping...")
            continue
    except:
        pass

    print(f"--- Processing Session {session_str} ---")
    df = load_congress_data(session_str, data_dir)
    
    if df is not None:
        df.to_sql('speeches', conn, if_exists='append', index=False, chunksize=10000)
        print(f"Success: {len(df)} rows added.")
    else:
        print(f"Files for Session {session_str} not found.")

conn.close()