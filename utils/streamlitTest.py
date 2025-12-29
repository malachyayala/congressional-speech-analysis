import streamlit as st
import sqlite3
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import os
import re
from collections import Counter
import random

# --- Configuration & Paths ---
DB_PATH = r"C:\Users\ayala.ma\Documents\VScodeStuff\congressional-speech-analysis\congress_master.db"
FILTER_PATH = r"C:\Users\ayala.ma\Documents\VScodeStuff\congressional-speech-analysis\filters.json"

# --- Page Config ---
st.set_page_config(page_title="Legislative Intelligence Tool", layout="wide", page_icon="🏛️")

# --- Database & Filter Functions ---
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data
def load_filters():
    if os.path.exists(FILTER_PATH):
        with open(FILTER_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def is_substantive(text, procedural_set):
    words = str(text).lower().split()
    if len(words) < 10: return False 
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
    noise_count = sum(1 for b in bigrams if b in procedural_set)
    return (noise_count / len(words)) < 0.30

def extract_context(text, phrase, window=5):
    """Extracts neighboring terms around a target phrase."""
    words = str(text).lower().split()
    phrase_words = phrase.split()
    n = len(phrase_words)
    context_words = []
    
    for i in range(len(words) - n + 1):
        if words[i:i+n] == phrase_words:
            start = max(0, i - window)
            end = min(len(words), i + n + window)
            # Exclude the phrase itself from context counts
            context_segment = words[start:i] + words[i+n:end]
            context_words.extend(context_segment)
    return context_words

# --- Surprise Me Terms (Historical High-Impact) ---
SURPRISE_TERMS = [
    "free silver", "gold standard", "protective tariff", "civil rights", 
    "income tax", "social security", "vietnam war", "interstate commerce",
    "voting rights", "national bank", "internal improvement", "pension fund"
]

# --- App Interface ---
st.title("🏛️ Legislative Intelligence & Partisan Trend Tool")

# Initialize Session State for Phrase
if 'phrase_a' not in st.session_state:
    st.session_state.phrase_a = "civil rights"

# Sidebar Controls
with st.sidebar:
    st.header("🔍 Search Engine")
    
    # Feature 5: Surprise Me Button
    if st.button("🎲 Surprise Me (Policy Discovery)"):
        st.session_state.phrase_a = random.choice(SURPRISE_TERMS)
    
    target_a = st.text_input("Primary Phrase (A):", value=st.session_state.phrase_a).lower()
    
    # Feature 4: Comparison Mode
    compare_mode = st.checkbox("Enable Comparison Mode (A vs B)")
    target_b = ""
    if compare_mode:
        target_b = st.text_input("Comparison Phrase (B):", value="infrastructure").lower()
    
    st.divider()
    view_type = st.radio("Visualization Mode:", ["Partisan Share", "Total Count"])
    threshold = st.slider("Capture Threshold:", 0.5, 1.0, 0.75)

# --- Main Logic ---
conn = get_connection()
filters = load_filters()

if filters:
    procedural_terms = set(filters['denoising_lexicon']['procedural_bigrams'])
    
    def get_clean_data(phrase):
        search = f"%{phrase}%"
        # Optimized query using existing DB schema [cite: 228, 229]
        query = "SELECT congress_session, party, speech FROM speeches WHERE speech LIKE ?"
        df = pd.read_sql_query(query, conn, params=(search,))
        if df.empty: return pd.DataFrame()
        df['is_substantive'] = df['speech'].apply(lambda x: is_substantive(x, procedural_terms))
        return df[df['is_substantive']]

    with st.spinner("Analyzing legislative history..."):
        data_a = get_clean_data(target_a)
        data_b = get_clean_data(target_b) if compare_mode and target_b else pd.DataFrame()

    if not data_a.empty:
        # Aggregation
        def get_stats(df):
            stats = df.groupby(['congress_session', 'party']).size().unstack(fill_value=0)
            for p in ['D', 'R']:
                if p not in stats.columns: stats[p] = 0
            stats['total'] = stats['D'] + stats['R']
            stats['rep_share'] = stats['R'] / stats['total']
            return stats

        stats_a = get_stats(data_a)
        
        # --- Main Chart Section ---
        fig = go.Figure()
        
        if view_type == "Partisan Share":
            fig.add_trace(go.Scatter(x=stats_a.index, y=stats_a['rep_share'], name=f"Phrase A: {target_a}", line=dict(color='#8e44ad', width=3)))
            if not data_b.empty:
                stats_b = get_stats(data_b)
                fig.add_trace(go.Scatter(x=stats_b.index, y=stats_b['rep_share'], name=f"Phrase B: {target_b}", line=dict(color='#2ecc71', width=3)))
            fig.add_hline(y=0.5, line_dash="dash", line_color="black")
            fig.update_yaxes(title="Republican Share", range=[-0.05, 1.05])
        else:
            fig.add_trace(go.Bar(x=stats_a.index, y=stats_a['total'], name=f"Mentions: {target_a}", marker_color='#3498db'))
            if not data_b.empty:
                stats_b = get_stats(data_b)
                fig.add_trace(go.Bar(x=stats_b.index, y=stats_b['total'], name=f"Mentions: {target_b}", marker_color='#e67e22'))
            fig.update_yaxes(title="Total Substantive Mentions")

        st.plotly_chart(fig, use_container_width=True)

        # --- Sub-Analysis Layout ---
        col_left, col_right = st.columns([1, 1])

        with col_left:
            # Feature 3: Partisan Gap Table
            st.subheader("🔥 Top 5 Polarized Sessions")
            stats_a['gap'] = (stats_a['rep_share'] - 0.5).abs()
            polarized = stats_a.sort_values('gap', ascending=False).head(5)
            st.table(polarized[['D', 'R', 'total', 'rep_share']])

        with col_right:
            # Feature 2: Semantic Context (Neighboring Terms)
            st.subheader("🔗 Semantic Context (Neighboring Terms)")
            all_context = []
            for s in data_a['speech'].sample(min(len(data_a), 200)):
                all_context.extend(extract_context(s, target_a))
            
            # Filter context words against standard and congressional stopwords [cite: 181, 238]
            stop_list = set(filters['denoising_lexicon']['congressional_stopwords']) | {"the", "and", "that", "this", "was", "for"}
            filtered_context = [w for w in all_context if w not in stop_list and len(w) > 3]
            
            context_counts = Counter(filtered_context).most_common(10)
            if context_counts:
                context_df = pd.DataFrame(context_counts, columns=['Word', 'Count'])
                st.altair_chart(px.bar(context_df, x='Count', y='Word', orientation='h'))
            else:
                st.write("Not enough contextual data.")

        # Feature 1: Most Partisan Speeches Gallery
        st.divider()
        st.subheader(f"📖 Notable Speeches containing '{target_a}'")
        
        # Pull only sessions where target_a actually appears
        available_sessions = sorted(data_a['congress_session'].unique(), reverse=True)
        selected_session = st.selectbox("Investigate rhetoric in session:", options=available_sessions)
        
        # Pull top speeches for session (sorted by count of phrase)
        session_data = data_a[data_a['congress_session'] == selected_session]
        # Quick heuristic: longer speeches with more keyword density 
        session_data['relevance'] = session_data['speech'].str.count(target_a)
        gallery = session_data.sort_values('relevance', ascending=False).head(5)

        for _, row in gallery.iterrows():
            with st.expander(f"Speech by {row['party']} Member | Mentions: {row['relevance']}"):
                highlighted = row['speech'].replace(target_a, f"**{target_a.upper()}**")
                st.write(highlighted)

    else:
        st.warning(f"No results found for '{target_a}'.")
else:
    st.error("filters.json missing or corrupted.")

conn.close()