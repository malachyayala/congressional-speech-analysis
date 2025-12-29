import sqlite3
import pandas as pd
import logging
import json
import os

# --- CONFIGURATION ---
FILTERS_PATH = r"C:\Users\ayala.ma\Documents\VScodeStuff\congressional-speech-analysis\filters.json"

class DatabaseManager:
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._setup_logging()
        self.procedural_terms = self._load_procedural_filters()

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _load_procedural_filters(self):
        if os.path.exists(FILTERS_PATH):
            try:
                with open(FILTERS_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    lexicon = data.get('denoising_lexicon', {})
                    terms = lexicon.get('procedural_bigrams', [])
                    self.logger.info(f"Loaded {len(terms)} procedural terms from filters.json")
                    return set(terms)
            except Exception as e:
                self.logger.error(f"Failed to load filters.json: {e}")
                return set()
        return set()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_speech_by_id(self, speech_id: str) -> pd.DataFrame:
        clean_id = str(speech_id).strip()
        # Including is_mapped and speaker for dashboard metadata
        query = """
        SELECT speech_id, date, speaker, party, state_x, speech, congress_session, is_mapped
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

    def get_phrase_mentions_over_time(self, phrase: str, only_mapped: bool = True) -> pd.DataFrame:
        """
        Analyzes trends. only_mapped=True (default) removes procedural noise 
        to ensure partisan signals are accurate.
        """
        mapping_filter = "AND is_mapped = 1" if only_mapped else ""
        
        query = f"""
        SELECT 
            CAST(date / 10000 AS INTEGER) as year,
            party,
            COUNT(*) as mention_count
        FROM speeches 
        WHERE speech LIKE ? 
          AND party IN ('D', 'R')
          {mapping_filter}
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
        # Architect Note: We ALWAYS filter for is_mapped here because 
        # unmapped speeches lack valid party data per the Codebook.
        query = """
        SELECT 
            congress_session,
            SUM(CASE WHEN party = 'D' THEN 1 ELSE 0 END) as D_count,
            SUM(CASE WHEN party = 'R' THEN 1 ELSE 0 END) as R_count,
            COUNT(*) as total
        FROM speeches 
        WHERE speech LIKE ? 
          AND is_mapped = 1
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
        """Final failsafe check using procedural bigram density."""
        if not text: return False
        words = str(text).lower().split()
        if len(words) < 10: return False
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        noise_count = sum(1 for b in bigrams if b in self.procedural_terms)
        return (noise_count / len(words)) < 0.30

    def get_speeches_by_session(self, session: int, limit: int = 20, only_mapped: bool = True) -> pd.DataFrame:
        """
        Primary fetch for Dashboard. only_mapped=True uses the SQL engine 
        to strip procedural noise instantly.
        """
        mapping_filter = "WHERE congress_session = ? AND is_mapped = 1" if only_mapped else "WHERE congress_session = ?"
        
        query = f"""
        SELECT speech_id, date, speaker, party, state_x, speech, congress_session
        FROM speeches 
        {mapping_filter}
        LIMIT ?
        """
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(query, conn, params=(int(session), limit))
            conn.close()
            return df
        except Exception as e:
            self.logger.error(f"Session query failed: {e}")
            return pd.DataFrame()