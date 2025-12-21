import pandas as pd
import os
import sqlite3
import csv

# 1. SETUP
# Use your exact local path
data_dir = '/Users/mj/Desktop/Misc/VSCodeStuff/legNLP/raw' 
db_name = 'congress_master.db'

# The session that failed
target_session = 81 

# The standardized columns for your final database
COLS_TO_KEEP = ['speech_id', 'speech', 'date', 'party', 'state_x', 'lastname', 'firstname', 'congress_session']

def load_single_session(session_num, folder):
    session_str = str(session_num).zfill(3)
    speeches_path = os.path.join(folder, f'speeches_{session_str}.txt')
    descr_path = os.path.join(folder, f'descr_{session_str}.txt')
    speaker_map_path = os.path.join(folder, f'{session_str}_SpeakerMap.txt')

    print(f"Reading files for Session {session_str}...")

    try:
        # THE FIX: quoting=csv.QUOTE_NONE (or 3) prevents the EOF error
        # engine='python' is more stable for handling these malformed lines
        speeches = pd.read_csv(
            speeches_path, 
            sep='|', 
            encoding='ISO-8859-1', 
            on_bad_lines='skip', 
            quoting=csv.QUOTE_NONE, 
            engine='python'
        )
        
        descr = pd.read_csv(
            descr_path, 
            sep='|', 
            encoding='ISO-8859-1', 
            on_bad_lines='skip', 
            quoting=csv.QUOTE_NONE, 
            engine='python'
        )
        
        speaker_map = pd.read_csv(
            speaker_map_path, 
            sep='|', 
            encoding='ISO-8859-1', 
            on_bad_lines='skip', 
            quoting=csv.QUOTE_NONE, 
            engine='python'
        )

        # Merge the three files on speech_id
        merged_df = pd.merge(speeches, descr, on='speech_id', how='left')
        final_df = pd.merge(merged_df, speaker_map, on='speech_id', how='left')
        
        # Add the numeric session identifier
        final_df['congress_session'] = int(session_num)
        
        # Keep only the columns we defined
        available_cols = [c for c in COLS_TO_KEEP if c in final_df.columns]
        df_filtered = final_df[available_cols].copy()
        
        # --- HANDLE BLANKS/UNKNOWNS ---
        fill_values = {
            'lastname': 'Unknown',
            'firstname': 'Unknown',
            'party': 'Unknown',
            'state_x': 'Unknown',
            'speech': '[No Text]',
            'date': '00000000' # Or any placeholder date format you prefer
        }
        df_filtered.fillna(value=fill_values, inplace=True)
        
        return df_filtered
    
    except Exception as e:
        print(f"Error in load_single_session: {e}")
        return None

# 2. RUN THE UPDATE
conn = sqlite3.connect(db_name)

# Clear existing data for this session to avoid duplicates
print(f"Cleaning existing data for Session {target_session} from DB...")
conn.execute("DELETE FROM speeches WHERE congress_session = ?", (target_session,))
conn.commit()

# Process and Save
df = load_single_session(target_session, data_dir)

if df is not None:
    # Use a chunksize to be kind to your RAM
    df.to_sql('speeches', conn, if_exists='append', index=False, chunksize=10000)
    print(f"Successfully added {len(df)} rows for Session {target_session}.")
else:
    print(f"Failed to add Session {target_session}.")

conn.close()