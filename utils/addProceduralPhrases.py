import json
import os
import csv
import sys

# --- CONFIGURATION ---
FILTERS_FILE = "filters.json"
PROCEDURAL_FILE = "C:\\Users\\ayala.ma\\Documents\\VScodeStuff\\congressional-speech-analysis\\vocabulary\\procedural.txt"
def load_procedural_terms(filepath):
    """
    Reads the Stanford procedural.txt file.
    Expected format: pipe-delimited (|) with the phrase in the first column.
    Example: "mr speaker|1"
    """
    terms = set()
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            # The codebook says files are pipe-delimited
            reader = csv.reader(f, delimiter='|')
            for row in reader:
                if row and len(row) > 0:
                    # Clean the phrase: lowercase and strip whitespace
                    phrase = row[0].strip().lower()
                    if phrase:
                        terms.add(phrase)
        print(f"Successfully loaded {len(terms)} procedural phrases from {filepath}")
        return list(terms)
        
    except FileNotFoundError:
        print(f"Error: Could not find '{filepath}'. Make sure it is in this folder.")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing procedural file: {e}")
        sys.exit(1)

def update_json(terms):
    """
    Injects the terms into filters.json under 'denoising_lexicon' -> 'procedural_stopwords'.
    """
    if not os.path.exists(FILTERS_FILE):
        print(f"Error: {FILTERS_FILE} not found. Please create it first.")
        sys.exit(1)

    try:
        with open(FILTERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Ensure the directory structure exists
        if "denoising_lexicon" not in data:
            data["denoising_lexicon"] = {}
        
        # We overwrite or append? Let's overwrite to ensure it stays in sync with the file
        # Sort them for readability
        data["denoising_lexicon"]["procedural_stopwords"] = sorted(terms)
        
        # Write back to file
        with open(FILTERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            
        print(f"Success! Added {len(terms)} terms to {FILTERS_FILE}.")
        print("You can now access them in your analysis script via: filters['denoising_lexicon']['procedural_stopwords']")

    except json.JSONDecodeError:
        print(f"Error: {FILTERS_FILE} contains invalid JSON. Please fix it before running this script.")
        sys.exit(1)

if __name__ == "__main__":
    print("--- UPDATING FILTERS JSON ---")
    procedural_terms = load_procedural_terms(PROCEDURAL_FILE)
    update_json(procedural_terms)