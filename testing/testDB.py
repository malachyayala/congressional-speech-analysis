import requests
import sqlite3
import time
import logging
import sys
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
# GET A KEY AT: https://api.data.gov/signup/
API_KEY = "RgWUXBtZYgRdRoGg8h4fwdjBfekYbsPhCCbMl9sC"  
DB_PATH = "congress_master.db" 
MAX_WORKERS = 5  # Keep this low to respect API limits

# --- LOGGING SETUP ---
# Logs will appear in 'ingest.log' and on your screen
logger = logging.getLogger("CongressIngest")
logger.setLevel(logging.INFO)
fh = logging.FileHandler('ingest.log', mode='w')
fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
logger.addHandler(fh)
logger.addHandler(ch)

fail_logger = logging.getLogger("Failures")
fail_handler = logging.FileHandler('failures.log', mode='a')
fail_handler.setFormatter(logging.Formatter('%(message)s'))
fail_logger.addHandler(fail_handler)
fail_logger.setLevel(logging.ERROR)

class ModernCongressionalIngestor:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.API_KEY = API_KEY
        self.GOVINFO_BASE = "https://api.govinfo.gov"
        self.session = requests.Session()
        self._init_db()

    def _init_db(self):
        """Standardizes schema and enables WAL mode for concurrency."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        
        # Main Speeches Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS speeches (
                speech_id TEXT PRIMARY KEY,
                speech TEXT,
                date INTEGER,
                speakerid INTEGER,
                speaker TEXT,
                is_mapped INTEGER,
                party TEXT,
                state_x TEXT,
                lastname TEXT,
                firstname TEXT,
                congress_session TEXT
            )
        """)
        
        # Tracker Table so you can stop/resume without restarting
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_packages (
                package_id TEXT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def safe_get(self, url, params=None):
        """Robust GET request with exponential backoff for rate limits."""
        params = params or {}
        params['api_key'] = self.API_KEY
        
        for i in range(3):
            try:
                resp = self.session.get(url, params=params, timeout=20)
                if resp.status_code == 200:
                    return resp
                elif resp.status_code == 429:
                    tqdm.write("!! RATE LIMIT HIT (429). Sleeping 60s...")
                    time.sleep(60)
                elif resp.status_code == 404:
                    return None
                else:
                    time.sleep(2)
            except Exception as e:
                time.sleep(2)
        return None

    def clean_speech_text(self, raw_text):
        """
        Removes the GPO headers you identified so they don't clutter the DB.
        """
        # 1. Normalize whitespace (tabs/newlines -> space)
        text = re.sub(r'\s+', ' ', raw_text).strip()
        
        # 2. REMOVE HEADERS
        # Matches: "Congressional Record, Volume 164..." or "[Congressional Record Volume...]"
        text = re.sub(r"\[?Congressional Record[,]? Volume \d+.*?\]", "", text, flags=re.IGNORECASE)
        
        # Matches: "[Senate]" or "[House]" or "[Extensions of Remarks]"
        text = re.sub(r"\[(Senate|House|Extensions of Remarks|Daily Digest)\]", "", text, flags=re.IGNORECASE)
        
        # Matches: "[Pages S8061-S8062]" or "[Page H49]"
        text = re.sub(r"\[?Pages? [HSE]?\d+(-[HSE]?\d+)?\]?", "", text, flags=re.IGNORECASE)
        
        # Matches the date stamp often found in headers e.g., "(Wednesday, January 2, 2019)"
        text = re.sub(r"\([A-Z][a-z]+, [A-Z][a-z]+ \d{1,2}, \d{4}\)", "", text)

        # 3. REMOVE FOOTERS
        text = re.sub(r"From the Congressional Record Online.*?gpo\.gov", "", text, flags=re.IGNORECASE)
        
        # 4. CLEANUP ARTIFACTS
        # The user noted trailing " ] " often appears after the page number
        text = re.sub(r"\]\s*\]", "", text)
        
        return text.strip()

    def _sanitize_metadata(self, value):
        """
        Fixes the 'List/Dict' error. Ensures we always get a clean string.
        """
        # 1. Unwrap Lists (e.g. ['Paul Ryan'])
        while isinstance(value, list):
            value = value[0] if value else None

        # 2. Unwrap Dictionaries (e.g. {'authority-fnf': 'Paul Ryan'})
        if isinstance(value, dict):
            value = (
                value.get('authority-fnf') or 
                value.get('authority-lnf') or 
                value.get('name') or 
                value.get('#text') or 
                value.get('value') or 
                str(value)
            )

        # 3. Final Check
        if value is None:
            return "Unknown"
        
        return str(value).strip()

    def _fetch_single_speech(self, gran, date_str):
        """
        Worker function to process one speech granule.
        """
        gran_id = gran['granuleId']
        
        # --- FILTER 1: Only House/Senate Floor sections ---
        if not any(x in gran_id for x in ['PgH', 'PgS', 'PGH', 'PGS']):
            return ("SKIP", "Not Floor Speech")
        
        # Skip Front/Back matter (indexes, table of contents)
        if 'FrontMatter' in gran_id or 'BackMatter' in gran_id: 
            return ("SKIP", "Front/BackMatter")

        # --- STEP 1: GET METADATA ---
        summary_resp = self.safe_get(gran['granuleLink'])
        if not summary_resp: 
            return ("ERROR", f"{gran_id} - Metadata Fail")
        
        summary_json = summary_resp.json()
        
        # --- STEP 2: GET TEXT ---
        download_links = summary_json.get('download', {})
        txt_url = download_links.get('txtLink')
        
        if not txt_url: 
            return ("ERROR", f"{gran_id} - No Text Link")

        t_resp = self.safe_get(txt_url)
        if not t_resp: 
            return ("ERROR", f"{gran_id} - Text Download Fail")
        
        # Handle encoding quirks
        try:
            raw_html = t_resp.content.decode('utf-8')
        except UnicodeDecodeError:
            raw_html = t_resp.text
            
        soup = BeautifulSoup(raw_html, 'html.parser')
        raw_text = soup.get_text(separator=' ')
        
        # --- STEP 3: CLEAN & VALIDATE ---
        clean_text = self.clean_speech_text(raw_text)
        
        # GHOST FILTER: If the file was JUST a header, it will now be empty.
        if len(clean_text) < 50:
            return ("SKIP", "Empty/Header Only")

        # --- STEP 4: IDENTIFY SPEAKER ---
        members = summary_json.get('members', [])
        
        speaker_name = "Unknown Speaker"
        party = "Unknown"
        state = "Unknown"
        lastname = "Unknown"
        firstname = "Unknown"
        bio_id_num = -1
        is_mapped = 0
        
        if members:
            m = members[0]
            
            # Use the robust sanitizer here
            speaker_name = self._sanitize_metadata(m.get('name', 'Unknown Speaker'))
            party = self._sanitize_metadata(m.get('party', 'Unknown'))
            state = self._sanitize_metadata(m.get('state', 'Unknown'))
            is_mapped = 1
            
            # Try to get Bioguide ID number
            bid = self._sanitize_metadata(m.get('bioguideId', ''))
            if bid and bid != "Unknown":
                digits = ''.join(filter(str.isdigit, bid))
                if digits: bio_id_num = int(digits)

            # Name parsing (Handle "Foxx, Virginia" vs "Virginia Foxx")
            if ',' in speaker_name:
                parts = speaker_name.split(',')
                lastname = parts[0].strip()
                firstname = parts[1].strip() if len(parts) > 1 else ""
                speaker_name = f"{firstname} {lastname}".strip()
            else:
                parts = speaker_name.split()
                if len(parts) > 1:
                    firstname = parts[0]
                    lastname = parts[-1]
                
        else:
            # Fallback: Regex for when API returns no members
            match = re.match(r"^(Mr\.|Ms\.|Mrs\.|The)\s+([A-Za-z\s]+)(\.|:)", clean_text[:50])
            if match:
                title = match.group(1)
                name_raw = match.group(2).strip()
                name_clean = re.sub(r"\s+of\s+[A-Za-z]+$", "", name_raw) # Remove "of Texas"
                
                speaker_name = f"{title} {name_clean}".title()
                lastname = name_clean.split()[-1].title()

        # --- STEP 5: RETURN DATA ---
        try:
            date_int = int(date_str)
        except:
            date_int = 0

        data_tuple = (
            gran_id, 
            clean_text, 
            date_int, 
            bio_id_num, 
            speaker_name,
            is_mapped, 
            party,
            state, 
            lastname, 
            firstname, 
            self._sanitize_metadata(summary_json.get('congress', '0'))
        )
        return ("SUCCESS", data_tuple)

    def process_package(self, pkg, conn):
        pkg_id = pkg['packageId']
        
        # Parse date from ID: CREC-2018-01-05 -> 20180105
        try:
            parts = pkg_id.split('-')
            date_str = f"{parts[1]}{parts[2]}{parts[3]}"
        except:
            date_str = "00000000"

        offset = 0
        page_size = 100
        
        tqdm.write(f"\n   > Processing Record: {pkg_id}")

        while True:
            # Fetch batch of granules
            gran_url = f"{self.GOVINFO_BASE}/packages/{pkg_id}/granules"
            g_resp = self.safe_get(gran_url, params={"pageSize": page_size, "offset": offset})
            
            if not g_resp: break

            data = g_resp.json()
            granules = data.get('granules', [])
            if not granules: break

            cursor = conn.cursor()
            results_to_insert = []
            
            # Concurrency: Process granules in parallel
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_gran = {executor.submit(self._fetch_single_speech, g, date_str): g for g in granules}
                
                for future in tqdm(as_completed(future_to_gran), total=len(granules), desc="      Fetching", leave=True):
                    try:
                        status, result = future.result()
                        
                        if status == "SUCCESS":
                            results_to_insert.append(result)
                        elif status == "ERROR":
                            fail_logger.error(result)
                            
                    except Exception as e:
                        logger.error(f"Thread Error: {e}")

            # Save Batch
            if results_to_insert:
                cursor.executemany("""
                    INSERT OR REPLACE INTO speeches 
                    (speech_id, speech, date, speakerid, speaker, is_mapped, party, state_x, lastname, firstname, congress_session)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, results_to_insert)
                conn.commit()
                
                # Show a preview of the first saved speech to confirm data quality
                sample = results_to_insert[0]
                tqdm.write(f"      [Saved] {sample[0]} | {sample[4]} | Content Len: {len(sample[1])}")

            # Pagination check
            count = data.get('count', 0)
            if offset + len(granules) >= count:
                break
            offset += page_size

        # Mark package as done
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO processed_packages (package_id) VALUES (?)", (pkg_id,))
        conn.commit()

    def ingest_range(self, start_year: int, end_year: int):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        cursor = conn.cursor()
        
        # Resume Logic
        cursor.execute("SELECT package_id FROM processed_packages")
        processed_ids = {row[0] for row in cursor.fetchall()}
        tqdm.write(f"--- Resume Status: {len(processed_ids)} daily records already completed ---")
        
        for year in range(start_year, end_year + 1):
            logger.info(f"--- Gathering list of Daily Records for {year} ---")
            
            all_packages = []
            pkg_list_url = f"{self.GOVINFO_BASE}/published/{year}-01-01/{year}-12-31"
            offset = 0
            page_size = 100
            
            while True:
                tqdm.write(f"Fetching metadata (Offset {offset})...")
                params = {"collection": "CREC", "pageSize": page_size, "offset": offset}
                resp = self.safe_get(pkg_list_url, params=params)
                if not resp: break
                
                data = resp.json()
                packages = data.get('packages', [])
                if not packages: break
                
                all_packages.extend(packages)
                if len(packages) < page_size: break
                offset += page_size

            all_packages.sort(key=lambda x: x['packageId'])
            
            for pkg in tqdm(all_packages, desc=f"Processing {year}"):
                pkg_id = pkg['packageId']
                if pkg_id in processed_ids: continue

                self.process_package(pkg, conn)
                processed_ids.add(pkg_id)
                
        conn.close()

if __name__ == "__main__":
    # Change years as needed
    ingestor = ModernCongressionalIngestor()
    ingestor.ingest_range(2020, 2020)