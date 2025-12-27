import pandas as pd
import sqlite3
import os
import logging
import csv

# --- CONFIGURATION ---
DATA_DIR = '/Users/mj/VSCodeStuff/legNLP/raw' 
DB_NAME = 'congress_master.db'
LOG_FILE = 'pipeline_rebuild.log'

# Production Columns
COLS_TO_KEEP = [
    'speech_id', 'speech', 'date', 'speakerid', 'speaker', 
    'is_mapped', 'party', 'state_x', 'lastname', 'firstname', 
    'congress_session'
]

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, mode='w'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def load_congress_data(session_num: str, folder: str) -> pd.DataFrame:
    """The 'Architect' Parser: Handles Session 81 OCR bugs & builds speaker metadata."""
    paths = {
        'speeches': os.path.join(folder, f'speeches_{session_num}.txt'),
        'descr': os.path.join(folder, f'descr_{session_num}.txt'),
        'smap': os.path.join(folder, f'{session_num}_SpeakerMap.txt')
    }

    if not all(os.path.exists(p) for p in paths.values()):
        return None

    try:
        # THE FIX: Python engine + QUOTE_NONE solves the EOF error
        params = {
            'sep': '|',
            'encoding': 'ISO-8859-1',
            'on_bad_lines': 'skip',
            'quoting': csv.QUOTE_NONE,
            'engine': 'python', # Python engine is more robust for malformed lines
            'dtype': {'speech_id': str}
        }

        # 1. Read files
        speeches = pd.read_csv(paths['speeches'], **params)
        descr = pd.read_csv(paths['descr'], **params)
        smap = pd.read_csv(paths['smap'], **params)

        # 2. Sequential Merging
        merged = pd.merge(speeches, descr, on='speech_id', how='left')
        final = pd.merge(merged, smap, on='speech_id', how='left')
        
        # 3. Architect Column Logic
        final['is_mapped'] = final['speakerid'].notnull().astype(int)
        # Construct full speaker name from cleaned map data
        final['speaker'] = (final['firstname'].fillna('') + ' ' + final['lastname'].fillna('')).str.strip()
        final['congress_session'] = int(session_num)
        
        # 4. Standardize and Fill
        df_filtered = final[[c for c in COLS_TO_KEEP if c in final.columns]].copy()
        df_filtered.fillna({
            'speakerid': -1, 'speaker': 'Unknown Speaker', 'lastname': 'Unknown',
            'firstname': 'Unknown', 'party': 'Unknown', 'state_x': 'Unknown', 'speech': '[No Text]'
        }, inplace=True)
        
        match_rate = (df_filtered['is_mapped'].sum() / len(df_filtered)) * 100
        logger.info(f"Session {session_num}: {len(df_filtered)} rows. Match Rate: {match_rate:.2f}%")
        
        return df_filtered
    
    except Exception as e:
        logger.error(f"Session {session_num}: Critical Parser Failure: {e}")
        return None

def main():
    logger.info("Starting Full Database Rebuild...")
    conn = sqlite3.connect(DB_NAME)
    
    # Range based on Stanford dataset scope
    for i in range(43, 115):
        session_str = str(i).zfill(3)
        
        # Safety: Clear session if it exists to allow for a clean overwrite
        #conn.execute("DELETE FROM speeches WHERE congress_session = ?", (i,))
        conn.commit()

        df = load_congress_data(session_str, DATA_DIR)
        
        if df is not None:
            # Chunking to prevent memory overflow on large sessions
            df.to_sql('speeches', conn, if_exists='append', index=False, chunksize=10000)
            logger.info(f"Session {session_str}: Successfully committed.")

    conn.close()
    logger.info("Rebuild Complete.")

if __name__ == "__main__":
    main()