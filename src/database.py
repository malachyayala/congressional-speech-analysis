import sqlite3
import pandas as pd
import logging

class DatabaseManager:
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_speech_by_id(self, speech_id: str) -> pd.DataFrame:
        clean_id = str(speech_id).strip()
        # Added is_procedure to the select list
        query = """
        SELECT speech_id, date, speaker, party, state_x, speech, congress_session, is_procedure
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

    def get_phrase_mentions_over_time(self, phrase: str, filter_proc: bool = True) -> pd.DataFrame:
        """
        Analyzes trends. 
        filter_proc=True (default) removes AI-classified procedural noise (is_procedure=1).
        """
        # If filter is on, we ONLY want is_procedure = 0 (Political Debate)
        proc_filter = "AND is_procedure = 0" if filter_proc else ""
        
        query = f"""
        SELECT 
            CAST(date / 10000 AS INTEGER) as year,
            party,
            COUNT(*) as mention_count
        FROM speeches 
        WHERE speech LIKE ? 
          AND party IN ('D', 'R')
          {proc_filter}
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
        """
        Calculates who 'owns' a topic. 
        Strictly filters for 'Political Debate' (is_procedure=0) to avoid skewing data 
        with 'I move to adjourn' type speeches.
        """
        query = """
        SELECT 
            congress_session,
            SUM(CASE WHEN party = 'D' THEN 1 ELSE 0 END) as D_count,
            SUM(CASE WHEN party = 'R' THEN 1 ELSE 0 END) as R_count,
            COUNT(*) as total
        FROM speeches 
        WHERE speech LIKE ? 
          AND is_procedure = 0
          AND party IN ('D', 'R')
        GROUP BY congress_session
        ORDER BY congress_session ASC
        """
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(query, conn, params=(f"%{phrase}%",))
            conn.close()
            if not df.empty:
                # Calculate Republican Share
                df['rep_share'] = df['R_count'] / df['total']
            return df
        except Exception as e:
            self.logger.error(f"Partisan share query failed: {e}")
            return pd.DataFrame()

    def get_speeches_by_session(self, session: int, limit: int = 20, filter_proc: bool = True) -> pd.DataFrame:
        """
        Primary fetch for Dashboard. 
        filter_proc=True uses the ML classification to hide administrative rows.
        """
        proc_filter = "AND is_procedure = 0" if filter_proc else ""
        
        query = f"""
        SELECT speech_id, date, speaker, party, state_x, speech, congress_session, is_procedure
        FROM speeches 
        WHERE congress_session = ? 
        {proc_filter}
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