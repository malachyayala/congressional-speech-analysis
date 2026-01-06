import sqlite3
import polars as pl
import torch
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
from tqdm.auto import tqdm
import sys
import time
import logging

# --- CONFIGURATION ---
DB_PATH = "congress_master.db"
CHUNK_SIZE = 50000       # Increased chunk size to keep GPU fed
BATCH_SIZE = 1024         # 4080 Super can handle this easily with DistilBART
CONFIDENCE_THRESHOLD = 0.70
MODEL_NAME = "valhalla/distilbart-mnli-12-1"

# PROCEDURE KEYWORDS
PROCEDURAL_KEYWORDS = [
    "yield back", "yield the floor", "without objection", "so ordered",
    "move to adjourn", "clerk will report", "recognize the gentleman",
    "recognize the gentlewoman", "unanimous consent", "ask for the yeas and nays",
    "quorum call", "resume consideration", "motion to reconsider",
    "mr. speaker", "madam speaker", "mr. president", "madam president"
]

def setup_database():
    """Enable WAL mode for concurrency speedups."""
    conn = sqlite3.connect(DB_PATH)
    # WAL allows simultaneous reading and writing
    conn.execute("PRAGMA journal_mode=WAL;")
    # Normal sync is safe for WAL and much faster
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.commit()
    conn.close()

def run_keyword_purge_optimized():
    """
    Polars (CPU) is often faster than SQLite LIKE for complex text scanning.
    We fetch IDs/Text, filter in memory, and push updates back.
    """
    print("--- STEP 1: OPTIMIZED KEYWORD PURGE ---")
    start = time.time()
    
    conn = sqlite3.connect(DB_PATH)
    
    # Fetch data that hasn't been checked yet
    # Limit to short speeches to avoid false positives in long debates
    query = """
    SELECT speech_id, speech 
    FROM speeches 
    WHERE is_procedure IS NULL 
    AND length(speech) < 500
    """
    
    try:
        # Load into Polars
        df = pl.read_database(query, conn)
        
        if df.height == 0:
            print("No candidates for purge found.")
            return

        print(f"Scanning {df.height:,} candidates via Polars...")

        # Create a regex pattern: (yield back|so ordered|...)
        # Escaping isn't strictly necessary for these simple phrases but good practice
        pattern = "|".join(PROCEDURAL_KEYWORDS)
        
        # Filter rows matching the pattern (Case insensitive)
        matches = df.filter(
            pl.col("speech").str.to_lowercase().str.contains(pattern)
        )
        
        if matches.height > 0:
            print(f"Found {matches.height:,} procedural matches. Updating DB...")
            
            # Convert to list of tuples for executemany: [(1, id1), (1, id2)...]
            update_data = [(1, x) for x in matches["speech_id"].to_list()]
            
            conn.executemany(
                "UPDATE speeches SET is_procedure = ? WHERE speech_id = ?", 
                update_data
            )
            conn.commit()
            print(f"Purge Complete. Time: {time.time() - start:.2f}s")
        else:
            print("No procedural matches found.")
            
    except Exception as e:
        print(f"Purge error: {e}")
    finally:
        conn.close()
    print("-" * 40)

def run_ai_classification_optimized():
    print("--- STEP 2: OPTIMIZED AI CLASSIFICATION (MERGED & FIXED) ---")
    
    # 1. Hardware Setup (From V2: Windows/RTX Optimization)
    if torch.cuda.is_available():
        device = 0
        print(f"GPU Detected: {torch.cuda.get_device_name(0)}")
        # CRITICAL for RTX 40-series: Use float16 and Tensor Cores
        dtype = torch.float16 
        torch.set_float32_matmul_precision('high')
    else:
        device = -1
        dtype = torch.float32
        print("Running on CPU (Slow)")

    # 2. Model Loading (From V2: Compilation Support)
    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME).to(device)

    # Optional: Compile model for speed (Windows/Linux support varies, so we try/except)
    try:
        print("Attempting to compile model with torch.compile...")
        model = torch.compile(model)
        print("Model compiled successfully.")
    except Exception as e:
        print(f"Skipping torch.compile (not supported or error): {e}")

    # Initialize Pipeline
    classifier = pipeline(
        "zero-shot-classification",
        model=model,
        tokenizer=tokenizer,
        device=device,
        torch_dtype=dtype,  # Explicitly set FP16 here
        batch_size=BATCH_SIZE
    )
        
    labels = ["administrative procedure", "political debate"]

    # 3. Processing Loop (From V1: Manual Batching for Better Control)
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            
            # Fetch remaining NULLs using Polars
            query = f"""
            SELECT speech_id, speech 
            FROM speeches 
            WHERE is_procedure IS NULL 
            LIMIT {CHUNK_SIZE}
            """
            
            df = pl.read_database(query, conn)
            
            if df.height == 0:
                print("Job complete. No more unclassified speeches found.")
                conn.close()
                break

            print(f"Processing chunk of {df.height:,} speeches...")
            
            texts = df['speech'].to_list()
            speech_ids = df['speech_id'].to_list()
            
            updates = []
            
            # Manual Batching Loop (More stable progress bars than V2 iterator)
            # We process the Polars chunk in smaller GPU batches
            for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="GPU Inference"):
                batch_texts = texts[i : i + BATCH_SIZE]
                batch_ids = speech_ids[i : i + BATCH_SIZE]
                
                # Inference
                results = classifier(batch_texts, candidate_labels=labels, multi_label=False)
                
                # Map results to IDs
                for speech_id, res in zip(batch_ids, results):
                    top_label = res['labels'][0]
                    score = res['scores'][0]
                    
                    if top_label == "administrative procedure" and score > CONFIDENCE_THRESHOLD:
                        is_proc = 1
                    else:
                        is_proc = 0
                    
                    updates.append((is_proc, speech_id))

            # Bulk Write Results
            print(f"Saving {len(updates):,} rows to database...")
            conn.executemany("UPDATE speeches SET is_procedure = ? WHERE speech_id = ?", updates)
            conn.commit()
            conn.close()
            
        except KeyboardInterrupt:
            print("\nStopped by user.")
            sys.exit(0)
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            # Optional: break loop on error to prevent infinite error scrolling
            sys.exit(1)

if __name__ == "__main__":
    setup_database()
    run_keyword_purge_optimized()
    run_ai_classification_optimized()