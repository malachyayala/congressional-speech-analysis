import pandas as pd
from collections import Counter
import re

# 1. Load your master CSV
df = pd.read_csv('congress_045_master.csv')

# 2. Define Congressional Stopwords from Table 13 of the Codebook
# These are the procedural words that dilute your topic model
congress_stopwords = {
    'absent', 'adjourn', 'ask', 'can', 'chairman', 'committee', 'con', 'democrat', 
    'etc', 'gentleladies', 'gentlelady', 'gentleman', 'gentlemen', 'gentlewoman', 
    'gentlewomen', 'hereabout', 'hereafter', 'hereat', 'hereby', 'herein', 
    'hereinafter', 'hereinbefore', 'hereinto', 'hereof', 'hereon', 'hereto', 
    'heretofore', 'hereunder', 'hereunto', 'hereupon', 'herewith', 'month', 'mr', 
    'mrs', 'nai', 'nay', 'none', 'now', 'part', 'per', 'pro', 'republican', 'say', 
    'senator', 'shall', 'sir', 'speak', 'speaker', 'tell', 'thank', 'thereabout', 
    'thereafter', 'thereagainst', 'thereat', 'therebefore', 'therebeforn', 
    'thereby', 'therefor', 'therefore', 'therefrom', 'therein', 'thereinafter', 
    'thereof', 'thereon', 'thereto', 'theretofore', 'thereunder', 'thereunto', 
    'thereupon', 'therewith', 'therewithal', 'today', 'whereabouts', 'whereafter', 
    'whereas', 'whereat', 'whereby', 'wherefore', 'wherefrom', 'wherein', 
    'whereinto', 'whereof', 'whereon', 'whereto', 'whereunder', 'whereupon', 
    'wherever', 'wherewith', 'wherewithal', 'will', 'yea', 'yes', 'yield'
}

# Standard English stopwords to add to the list
standard_stopwords = {'the', 'to', 'of', 'and', 'a', 'in', 'that', 'is', 'it', 'for', 'be', 'on', 'with', 'as', 'this', 'was', 'by', 'not', 'i', 'from', 'are', 'which', 'he', 'his', 'at', 'has', 'but', 'or', 'an', 'they', 'their', 'we', 'so', 'been', 'there', 'if', 'all', 'any', 'my', 'me', 'no', 'upon', 'one', 'more', 'would', 'could', 'should', 'than', 'them', 'who', 'said', 'him', 'what'}

# Combine them
all_stopwords = congress_stopwords.union(standard_stopwords)

def get_policy_words(texts, n=10):
    all_words = []
    for text in texts:
        # Tokenize: lowercase and keep only alphanumeric
        words = re.findall(r'\b\w+\b', str(text).lower())
        # Filter: remove words in stoplist and words shorter than 3 letters
        all_words.extend([w for w in words if w not in all_stopwords and len(w) > 2])
    return Counter(all_words).most_common(n)

# 3. Analyze by Party
# Filter out rows without a party and stick to the two main ones
df_filtered = df.dropna(subset=['party'])
df_filtered = df_filtered[df_filtered['party'].isin(['D', 'R'])]

print("--- Cleaned Top Words: Democrats (D) ---")
print(get_policy_words(df_filtered[df_filtered['party'] == 'D']['speech']))

print("\n--- Cleaned Top Words: Republicans (R) ---")
print(get_policy_words(df_filtered[df_filtered['party'] == 'R']['speech']))

import pandas as pd
from collections import Counter
import re

# 1. Load the data
df = pd.read_csv('congress_045_master.csv')

# 2. Expanded Stopword List (Standard + Congressional Table 13)
# Including those pesky "have", "were", "had" words
stop_list = {
    'have', 'had', 'were', 'was', 'been', 'being', 'has', 'did', 'does', 'their', 'them',
    'this', 'that', 'these', 'those', 'which', 'who', 'whom', 'whose', 'what', 'when',
    'where', 'why', 'how', 'bill', 'house', 'senate', 'senator', 'states', 'government',
    'committee', 'gentleman', 'gentlemen', 'mr', 'mrs', 'speaker', 'shall', 'should',
    'would', 'could', 'may', 'might', 'must', 'can', 'will', 'very', 'more', 'most',
    'other', 'some', 'such', 'than', 'then', 'there', 'here', 'any', 'all', 'every',
    'each', 'now', 'today', 'question', 'time', 'its', 'said', 'say', 'saying', 'tell',
    'asked', 'ordered', 'provide', 'under', 'into', 'upon', 'after', 'before', 'member'
}

# Add the specific Stanford procedural words
stanford_procedural = {'adjourn', 'absent', 'nai', 'nay', 'yea', 'yes', 'yield', 'pro', 'con'}
final_stops = stop_list.union(stanford_procedural)

def get_policy_content(texts, n=15):
    all_words = []
    for text in texts:
        words = re.findall(r'\b\w+\b', str(text).lower())
        # Filter for length > 3 to remove "act", "law", etc. if you want even deeper cleaning
        all_words.extend([w for w in words if w not in final_stops and len(w) > 3])
    return Counter(all_words).most_common(n)

# 3. Partisan Comparison
df_clean = df.dropna(subset=['party'])
df_clean = df_clean[df_clean['party'].isin(['D', 'R'])]

print("--- 45th Congress Policy Keywords (D) ---")
print(get_policy_content(df_clean[df_clean['party'] == 'D']['speech']))

print("\n--- 45th Congress Policy Keywords (R) ---")
print(get_policy_content(df_clean[df_clean['party'] == 'R']['speech']))