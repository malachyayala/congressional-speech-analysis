from primp import options
import streamlit as st
from src.database import DatabaseManager
from src.components import UIComponents

# --- CONFIGURATION ---
DB_PATH = "congress_master.db"
PAGE_TITLE = "Congressional NLP Dashboard"
LAYOUT = "wide"

class CongressionalDashboard:
    
    def __init__(self):
        st.set_page_config(page_title=PAGE_TITLE, layout=LAYOUT)
        self.db = self._get_db_manager()
        
        if 'page' not in st.session_state:
            st.session_state.page = "Search by ID"

    @st.cache_resource
    def _get_db_manager(_self):
        return DatabaseManager(DB_PATH)

    def render_sidebar(self):
        st.sidebar.title("🏛️ Congress NLP")
        options = ["Search by ID", "Phrase Trends", "Partisan Analysis", "Session Search", "About"]
        selection = st.sidebar.selectbox("Go to Page:", options)
        st.session_state.page = selection
        
        st.sidebar.markdown("---")
        st.sidebar.caption(f"Connected to: `{DB_PATH}`")
        st.sidebar.caption("Pipeline: **DistilBART-MNLI Zero-Shot**")

    def page_search_by_id(self):
        UIComponents.display_header("🔎 Speech Lookup", "Directly retrieve a speech record.")
        col1, col2 = st.columns([3, 1])
        with col1:
            speech_id = st.text_input("Enter Speech ID:", placeholder="e.g., 880029311")
        with col2:
            st.write("") 
            st.write("")
            search_clicked = st.button("Fetch Record", use_container_width=True)

        if search_clicked and speech_id:
            with st.spinner("Querying Database..."):
                df = self.db.get_speech_by_id(speech_id)
            if not df.empty:
                UIComponents.display_speech_card(df.iloc[0])
            else:
                UIComponents.render_error(f"No speech found with ID: {speech_id}")

    def page_phrase_trends(self):
        UIComponents.display_header("📈 Phrase Trends", "Visualize policy topic usage over time.")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            phrase = st.text_input("Enter Policy Phrase:", placeholder="e.g., artificial intelligence, crypto, china")
        with col2:
            st.write("")
            st.write("")
            analyze_clicked = st.button("Visualize Trend", use_container_width=True, key="btn_trend")

        if analyze_clicked and phrase:
            with st.spinner(f"Aggregating 140 years of data for '{phrase}'..."):
                # We default to filtering procedure to show only "Debate"
                df = self.db.get_phrase_mentions_over_time(phrase, filter_proc=True)
            
            UIComponents.display_trend_chart(df, phrase)

    def page_partisan_analysis(self):
        UIComponents.display_header("⚖️ Partisan Split Analysis", "Who 'owns' a specific policy topic?")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            phrase = st.text_input("Enter Policy Topic:", placeholder="e.g. taxes, abortion, border wall")
        with col2:
            st.write("")
            st.write("")
            btn_click = st.button("Calculate Share", use_container_width=True)

        if btn_click and phrase:
            with st.spinner("Calculating partisan ownership on substantive debate..."):
                df = self.db.get_partisan_share(phrase)
            
            UIComponents.display_partisan_share_chart(df, phrase)
            
            with st.expander("View Raw Data"):
                st.dataframe(df)

    def page_session_search(self):
        UIComponents.display_header("🗓️ Session Browser", "Explore the record by specific Congress.")

        col1, col2 = st.columns([3, 1])
        with col1:
            # UPDATED: Max value set to 119 for modern scraped data
            session_num = st.number_input(
                "Enter Session Number:", 
                min_value=43, max_value=119, value=119
            )
        with col2:
            st.write("")
            # UPDATED: Label reflects the new AI Model
            filter_noise = st.checkbox("Hide Procedural (AI)", value=True, help="Uses DistilBART classification to hide administrative/procedural speech.")
        
        if st.button("Browse Session", use_container_width=True):
            with st.spinner(f"Fetching records (AI Denoising={'ON' if filter_noise else 'OFF'})..."):
                df = self.db.get_speeches_by_session(session_num, filter_proc=filter_noise)
            if not df.empty:
                st.success(f"Showing {len(df)} speeches.")
                for _, row in df.iterrows():
                    UIComponents.display_speech_card(row)
                    st.divider()
            else:
                st.warning("No speeches found.")

    def page_about(self):
        UIComponents.display_header("About this Project")
        st.markdown("""
        **Congressional NLP Analysis Assistant**
        
        **New in v2.0:**
        - **Data Coverage:** Extended to 119th Congress (2025).
        - **AI Classification:** Replaced keyword heuristics with a `distilbart-mnli-12-1` Zero-Shot Classifier to distinguish between "Administrative Procedure" and "Political Debate."
        """)

    def run(self):
        self.render_sidebar()
        
        if st.session_state.page == "Search by ID":
            self.page_search_by_id()
        elif st.session_state.page == "Phrase Trends":
            self.page_phrase_trends()
        elif st.session_state.page == "Partisan Analysis":
            self.page_partisan_analysis()
        elif st.session_state.page == "Session Search":
            self.page_session_search()
        elif st.session_state.page == "About":
            self.page_about()

if __name__ == "__main__":
    app = CongressionalDashboard()
    app.run()