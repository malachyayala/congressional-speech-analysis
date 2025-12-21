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

# 2. DEFINE THE POLICY DICTIONARY
policy_categories = {
    'Economy/Money': ['silver', 'gold', 'currency', 'coinage', 'bank', 'treasury', 'resumption'],
    'Defense/Army': ['army', 'military', 'officer', 'war', 'pension', 'defense', 'soldier'],
    'Infrastructure': ['railroad', 'bridge', 'river', 'harbor', 'public lands', 'post office'],
    'Budget/Tax': ['appropriation', 'revenue', 'tax', 'deficit', 'spending', 'internal revenue'],
    'Justice': ['court', 'judge', 'justice', 'district', 'law', 'civil rights']
}

# Flatten for the vectorizer
policy_vocab = [word for sublist in policy_categories.values() for word in sublist]

# 3. CONSOLIDATED STOPWORDS (For general cleaning before TF-IDF)
congress_procedural = {'gentleman', 'speaker', 'chairman', 'yield', 'time', 'adjourn', 'senator', 'president', 'pledge', 'allegiance'}
states = {'new york', 'illinois', 'ohio', 'virginia', 'california'}
master_stops = list(text.ENGLISH_STOP_WORDS.union(congress_procedural).union(states))

# 4. PRE-PROCESSING FUNCTION
def deep_clean(raw_text):
    txt = str(raw_text).lower()
    # Remove numbers and punctuation
    txt = re.sub(r'[^a-z\s]', '', txt)
    # Standardize whitespace
    return " ".join(txt.split())

# 5. TF-IDF WITH VOCABULARY PARAMETER
# We pass the policy_vocab here to ignore all ceremonial and procedural text
vectorizer = TfidfVectorizer(
    vocabulary=policy_vocab, 
    stop_words=master_stops,
    ngram_range=(1, 2)
)

# Apply cleaning and transform
cleaned_speeches = [deep_clean(s) for s in tqdm(df_sample['speech'], desc="Cleaning")]
tfidf_matrix = vectorizer.fit_transform(cleaned_speeches)

# 6. AGGREGATE RESULTS BY PARTY
# Convert to DataFrame for easier analysis
tfidf_df = pd.DataFrame(tfidf_matrix.toarray(), columns=vectorizer.get_feature_names_out())
tfidf_df['party'] = df_sample['party']

# Get the top policy priorities for Democrats and Republicans
party_priorities = tfidf_df.groupby('party').sum().transpose()

print("\n--- Top Policy Priorities in Session 111 (Summed TF-IDF) ---")
print("Democrats (D):")
print(party_priorities['D'].sort_values(ascending=False).head(10))
print("\nRepublicans (R):")
print(party_priorities['R'].sort_values(ascending=False).head(10))