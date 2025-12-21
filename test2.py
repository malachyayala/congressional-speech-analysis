import sqlite3
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction import text
from tqdm import tqdm

# 1. DATABASE CONNECTION
conn = sqlite3.connect('congress_master.db')
query = "SELECT speech, party, congress_session FROM speeches WHERE congress_session = 111 LIMIT 10000"
df_sample = pd.read_sql(query, conn)
conn.close()

# 2. DEFINITIONS
policy_categories = {
    'Economy/Money': ['silver', 'gold', 'currency', 'coinage', 'bank', 'treasury', 'resumption'],
    'Defense/Army': ['army', 'military', 'officer', 'war', 'pension', 'defense', 'soldier'],
    'Infrastructure': ['railroad', 'bridge', 'river', 'harbor', 'public lands', 'post office'],
    'Budget/Tax': ['appropriation', 'revenue', 'tax', 'deficit', 'spending', 'internal revenue'],
    'Justice': ['court', 'judge', 'justice', 'district', 'law', 'civil rights']
}
policy_vocab = [word for sublist in policy_categories.values() for word in sublist]

congress_procedural = {'gentleman', 'speaker', 'chairman', 'yield', 'time', 'adjourn', 'senator', 'president'}
states = {'new york', 'illinois', 'ohio', 'virginia', 'california'}
master_stops = list(text.ENGLISH_STOP_WORDS.union(congress_procedural).union(states))

def deep_clean(raw_text):
    txt = str(raw_text).lower()
    txt = re.sub(r'[^a-z\s]', '', txt)
    return " ".join(txt.split())

# Pre-clean the speeches once for both passes
print("Pre-cleaning speeches...")
cleaned_speeches = [deep_clean(s) for s in tqdm(df_sample['speech'], desc="Cleaning")]

# ---------------------------------------------------------
# PASS 1: DISCOVERY (Find the most unique words overall)
# ---------------------------------------------------------
print("\n--- Running Pass 1: Discovery (Finding Top 50 Unique Words) ---")
discovery_vectorizer = TfidfVectorizer(
    stop_words=master_stops, 
    max_df=0.7, 
    min_df=5, 
    ngram_range=(1, 2)
)
discovery_matrix = discovery_vectorizer.fit_transform(cleaned_speeches)

# Sum the TF-IDF scores for each word across the whole sample
discovery_scores = discovery_matrix.sum(axis=0).A1
discovery_words = discovery_vectorizer.get_feature_names_out()
discovery_results = sorted(zip(discovery_words, discovery_scores), key=lambda x: x[1], reverse=True)

print("\nTop 50 Most Unique Words (Check these for noise!):")
for i, (word, score) in enumerate(discovery_results[:50]):
    print(f"{i+1}. {word:<20} ({score:.2f})")

# ---------------------------------------------------------
# PASS 2: TARGETED (Policy Dictionary Scores)
# ---------------------------------------------------------
print("\n--- Running Pass 2: Targeted (Policy Dictionary Analysis) ---")
targeted_vectorizer = TfidfVectorizer(
    vocabulary=policy_vocab, 
    ngram_range=(1, 2)
)
targeted_matrix = targeted_vectorizer.fit_transform(cleaned_speeches)

# Aggregate results by Party
targeted_df = pd.DataFrame(targeted_matrix.toarray(), columns=targeted_vectorizer.get_feature_names_out())
targeted_df['party'] = df_sample['party']
party_priorities = targeted_df.groupby('party').sum().transpose()

print("\nPartisan Policy Weights:")
if 'D' in party_priorities.columns:
    print("\nDemocrats (D):")
    print(party_priorities['D'].sort_values(ascending=False).head(10))
if 'R' in party_priorities.columns:
    print("\nRepublicans (R):")
    print(party_priorities['R'].sort_values(ascending=False).head(10))