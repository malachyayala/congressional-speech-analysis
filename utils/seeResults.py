import sqlite3
import pandas as pd
import spacy
from spacy import displacy
import webbrowser
import os
import sys
import json

# --- CONFIGURATION ---
DB_PATH = "congress_master.db"
FILTERS_PATH = "filters.json"
SPACY_MODEL = "en_core_web_md"

# Phrases that indicate a speech is likely just "Parliamentary Skeleton" (Noise)
# We use these to skip speeches entirely before we even try to analyze them.
PROCEDURAL_TRIGGERS = [
    "unanimous consent",
    "quorum call",
    "yield the floor",
    "yield back",
    "pledge of allegiance",
    "motion to adjourn",
    "morning business",
    "mr. speaker",
    "mr. president"
]

def load_filters():
    """
    Loads the policy and denoising filters from filters.json.
    """
    try:
        with open(FILTERS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: '{FILTERS_PATH}' not found. Make sure it is in the same folder.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: '{FILTERS_PATH}' is not valid JSON.")
        sys.exit(1)

def is_substantive(text):
    """
    Returns True if the speech looks like a real debate.
    Returns False if it looks like procedural noise (e.g., 'I ask unanimous consent...').
    """
    text_lower = text.lower().strip()
    
    # RULE 1: Length check (redundant with SQL but good for safety)
    if len(text) < 500: 
        return False
    
    # RULE 2: Trigger phrases in the first 150 characters
    # (Procedural motions usually happen at the very start)
    intro = text_lower[:150]
    if "unanimous consent" in intro: return False
    if "quorum call" in intro: return False
    if "pledge of allegiance" in intro: return False

    return True

def get_quality_speech(limit=1):
    """
    Tries to find a 'meaty' speech by fetching a batch and filtering out the noise.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # SQL OPTIMIZATION:
        # We only fetch speeches > 1000 chars. This instantly drops ~40% of the noise.
        query = """
            SELECT speech_id, speech, party, date, congress_session 
            FROM speeches 
            WHERE LENGTH(speech) > 1000
            ORDER BY RANDOM() 
            LIMIT 20
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            print("Database is empty or no long speeches found.")
            sys.exit(1)
            
        # Python Filtering Loop: Check our batch for the first "good" speech
        for index, row in df.iterrows():
            if is_substantive(row['speech']):
                return df.iloc[[index]]
        
        print("Warning: Fetched 20 long speeches but none passed the strict content filter.")
        print("Returning the longest one found as a fallback.")
        # Fallback: Return the longest speech in the batch
        longest_idx = df['speech'].str.len().idxmax()
        return df.loc[[longest_idx]]
        
    except sqlite3.Error as e:
        print(f"Database Error: {e}")
        sys.exit(1)

def apply_denoising(doc, filters, verbose=True):
    """
    The Core Filter:
    1. Loads your historical policy terms.
    2. Loads your procedural stopwords.
    3. Keeps entities ONLY if they are Policy Terms OR useful Standard Entities (ORG, GPE, LAW).
    """
    kept_entities = []
    
    # 1. SETUP: Build lookup sets
    
    # A. Policy Terms (from policy_bridge)
    policy_terms = set()
    term_to_category = {} 
    if 'policy_bridge' in filters:
        for category, data in filters['policy_bridge'].items():
            for term in data.get('historical_terms', []):
                clean_term = term.replace('_', ' ').lower()
                policy_terms.add(clean_term)
                term_to_category[clean_term] = category

    # B. Procedural Stopwords (from denoising_lexicon)
    procedural_stops = set(filters.get('denoising_lexicon', {}).get('procedural_stopwords', []))

    print(f"\n--- DENOISING REPORT ---")
    
    # 2. FILTERING LOOP
    for ent in doc.ents:
        text_clean = ent.text.lower().strip()
        
        # CHECK 1: Is it explicitly procedural noise?
        if text_clean in procedural_stops:
            # Skip it (Do not add to kept_entities)
            continue 

        # CHECK 2: Is it a Policy Term?
        is_policy = text_clean in policy_terms
        
        # CHECK 3: Is it a standard entity we care about?
        # We generally want ORGs (Banks, Unions), GPEs (States, Countries), and LAWs (Bills)
        is_standard = ent.label_ in ["ORG", "GPE", "LAW", "NORP"]
        
        # DECISION
        if is_policy or is_standard:
            kept_entities.append(ent)
            
            # Optional: Verbose logging to see what's happening
            if verbose and is_policy:
                print(f"[KEPT POLICY] '{ent.text}' -> {term_to_category.get(text_clean)}")
            
    return kept_entities

# --- VISUALIZATION OPTIONS ---

def option_1_interactive(doc, kept_ents):
    """Starts a local web server to explore the text."""
    print("\n--- Starting Interactive Server ---")
    print("Go to http://localhost:5000 to see your speech.")
    print("Press Ctrl+C to stop.")
    
    # Overwrite entities so displaCy only highlights the filtered results
    doc.ents = kept_ents
    displacy.serve(doc, style="ent", port=5000)

def option_2_html_report(doc, kept_ents, speech_id):
    """Saves the visualization to a file."""
    print("\n--- Generating HTML Report ---")
    
    doc.ents = kept_ents
    html = displacy.render(doc, style="ent", page=True)
    
    filename = f"ner_report_{speech_id}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"Saved to: {os.path.abspath(filename)}")
    webbrowser.open('file://' + os.path.realpath(filename))

def option_3_dataframe(kept_ents, speech_id, filters):
    """Prints a clean data table of what was found."""
    print("\n--- Extracted Data Table ---")
    
    data = []
    
    # Rebuild map for labeling source
    term_map = {}
    if 'policy_bridge' in filters:
        for cat, content in filters['policy_bridge'].items():
            for term in content.get('historical_terms', []):
                term_map[term.replace('_', ' ').lower()] = cat

    for ent in kept_ents:
        clean_text = ent.text.lower()
        
        # Determine Source
        source = "NER Model"
        category = ent.label_ 
        
        if clean_text in term_map:
            source = "Policy Filter"
            category = term_map[clean_text]

        data.append({
            "Entity": ent.text,
            "Type": category,
            "Source": source
        })
    
    df = pd.DataFrame(data)
    
    if not df.empty:
        # Sort so Policy items appear at the top
        df = df.sort_values(by="Source", ascending=False)
        print(df.to_string(index=False))
        print(f"\nTotal Entities: {len(df)}")
    else:
        print("No significant entities found in this speech segment.")

# --- MAIN EXECUTION ---

if __name__ == "__main__":
    # 1. Setup
    print(f"1. Loading spaCy model: {SPACY_MODEL}...")
    try:
        nlp = spacy.load(SPACY_MODEL)
    except OSError:
        print(f"Model not found. Run: python -m spacy download {SPACY_MODEL}")
        sys.exit(1)

    print(f"2. Loading filters from: {FILTERS_PATH}...")
    filters = load_filters()

    # 2. Get Data
    print("3. Searching for a SUBSTANTIVE speech (skipping procedural noise)...")
    df_sample = get_quality_speech()
    
    row = df_sample.iloc[0]
    speech_text = row['speech']
    speech_id = row['speech_id']
    
    print(f"\nAnalyzing Speech: {speech_id}")
    print(f"Date: {row['date']} | Congress: {row['congress_session']} | Party: {row['party']}")
    # Preview to verify quality
    preview = speech_text[:100].replace('\n', ' ')
    print(f"Preview: {preview}...")
    print("-" * 60)

    # 3. Processing
    doc = nlp(speech_text)
    print(f"Original Entities Found: {len(doc.ents)}")
    
    valid_ents = apply_denoising(doc, filters, verbose=True)
    print(f"Entities Remaining After Denoising: {len(valid_ents)}")

    # 4. Menu
    print("-" * 60)
    print("Select Visualization:")
    print("  [1] Interactive Server (Best for exploring)")
    print("  [2] HTML Report (Best for sharing)")
    print("  [3] Data Table (Best for verifying data)")
    
    choice = input("Enter 1, 2, or 3: ").strip()

    if choice == "1":
        option_1_interactive(doc, valid_ents)
    elif choice == "2":
        option_2_html_report(doc, valid_ents, speech_id)
    elif choice == "3":
        option_3_dataframe(valid_ents, speech_id, filters)
    else:
        print("Invalid selection.")