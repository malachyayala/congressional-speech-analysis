import sqlite3
import pandas as pd
import logging
import json
import os

# --- CONFIGURATION ---
# We use the path you provided in your previous snippet
FILTERS_PATH = r"C:\Users\ayala.ma\Documents\VScodeStuff\congressional-speech-analysis\filters.json"

class DatabaseManager:
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._setup_logging()
        # Load the procedural terms immediately upon initialization
        self.procedural_terms = self._load_procedural_filters()

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _load_procedural_filters(self):
        """
        Loads the 'procedural_bigrams' list from filters.json.
        Returns a Python Set for O(1) lookup speed.
        """
        if os.path.exists(FILTERS_PATH):
            try:
                with open(FILTERS_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Navigate to ['denoising_lexicon']['procedural_bigrams']
                    # We use .get() to avoid crashing if keys are missing
                    lexicon = data.get('denoising_lexicon', {})
                    terms = lexicon.get('procedural_bigrams', [])
                    
                    self.logger.info(f"Loaded {len(terms)} procedural terms from filters.json")
                    return set(terms) # Convert to set for fast searching
            except Exception as e:
                self.logger.error(f"Failed to load filters.json: {e}")
                return set()
        else:
            self.logger.warning(f"filters.json not found at {FILTERS_PATH}")
            return set()

    def get_connection(self):
        """Creates a connection to the database."""
        return sqlite3.connect(self.db_path)

    def get_speech_by_id(self, speech_id: str) -> pd.DataFrame:
        clean_id = str(speech_id).strip()
        query = """
        SELECT speech_id, date, party, state_x, speech, congress_session
        FROM speeches 
        WHERE speech_id = ?
        """
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(query, conn, params=(clean_id,))
            conn.close()
            return df
        except Exception as e:
            self.logger.error(f"Error fetching speech {clean_id}: {e}")
            return pd.DataFrame()

    def get_phrase_mentions_over_time(self, phrase: str) -> pd.DataFrame:
        query = """
        SELECT 
            CAST(date / 10000 AS INTEGER) as year,
            party,
            COUNT(*) as mention_count
        FROM speeches 
        WHERE speech LIKE ? 
          AND party IN ('D', 'R')
        GROUP BY year, party
        ORDER BY year ASC
        """
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(query, conn, params=(f"%{phrase}%",))
            conn.close()
            return df
        except Exception as e:
            self.logger.error(f"Trend query failed: {e}")
            return pd.DataFrame()

    def get_partisan_share(self, phrase: str) -> pd.DataFrame:
        query = """
        SELECT 
            congress_session,
            SUM(CASE WHEN party = 'D' THEN 1 ELSE 0 END) as D_count,
            SUM(CASE WHEN party = 'R' THEN 1 ELSE 0 END) as R_count,
            COUNT(*) as total
        FROM speeches 
        WHERE speech LIKE ? 
          AND party IN ('D', 'R')
        GROUP BY congress_session
        ORDER BY congress_session ASC
        """
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(query, conn, params=(f"%{phrase}%",))
            conn.close()
            if not df.empty:
                df['rep_share'] = df['R_count'] / df['total']
            return df
        except Exception as e:
            self.logger.error(f"Partisan share query failed: {e}")
            return pd.DataFrame()

    def is_substantive(self, text: str) -> bool:
        """
        Uses filters.json logic to determine if a speech is procedural.
        """
        if not text: return False
        
        # 1. Basic Cleaning
        words = str(text).lower().split()
        
        # 2. Length Check (Too short = likely noise)
        if len(words) < 10: 
            return False

        # 3. Bigram Check (The core logic from your snippet)
        # Create bigrams: "i yield", "yield the", "the floor"
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        
        # Count how many bigrams match your JSON file
        noise_count = sum(1 for b in bigrams if b in self.procedural_terms)
        
        # 4. Density Threshold
        # If more than 30% of the bigrams are procedural, discard it.
        return (noise_count / len(words)) < 0.30

    def get_speeches_by_session(self, session: int, limit: int = 20, filter_procedural: bool = False) -> pd.DataFrame:
        # Oversample to ensure we have enough left after filtering
        fetch_limit = limit * 10 if filter_procedural else limit
        
        query = """
        SELECT speech_id, date, party, state_x, speech, congress_session
        FROM speeches 
        WHERE congress_session = ?
        LIMIT ?
        """
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(query, conn, params=(int(session), fetch_limit))
            conn.close()
            
            if df.empty: return df

            if filter_procedural:
                # Apply the JSON-based filter
                df['is_valid'] = df['speech'].apply(self.is_substantive)
                df = df[df['is_valid']].drop(columns=['is_valid'])
                
            return df.head(limit)
            
        except Exception as e:
            self.logger.error(f"Session query failed: {e}")
            return pd.DataFrame()