# streamlitMain.py
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
        
        # Initialize session state for page navigation
        if 'page' not in st.session_state:
            st.session_state.page = "Search by ID"

    @st.cache_resource
    def _get_db_manager(_self):
        return DatabaseManager(DB_PATH)

    def render_sidebar(self):
        st.sidebar.title("🏛️ Congress NLP")
        # Added "Phrase Trends" to options
        options = ["Search by ID", "Phrase Trends", "Partisan Analysis", "Session Search", "About"]
        selection = st.sidebar.selectbox("Go to Page:", options)
        st.session_state.page = selection
        
        st.sidebar.markdown("---")
        st.sidebar.caption(f"Connected to: `{DB_PATH}`")

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
        """
        Feature 2: Visualization of phrase usage over time.
        """
        UIComponents.display_header("📈 Phrase Trends", "Visualize policy topic usage over time by party.")
        
        # Input Section
        col1, col2 = st.columns([3, 1])
        with col1:
            phrase = st.text_input("Enter Policy Phrase:", placeholder="e.g., civil rights, gold standard, vietnam")
        with col2:
            st.write("")
            st.write("")
            # 'key' argument ensures this button doesn't conflict with others
            analyze_clicked = st.button("Visualize Trend", use_container_width=True, key="btn_trend")

        # Logic
        if analyze_clicked and phrase:
            with st.spinner(f"Aggregating 140 years of data for '{phrase}'..."):
                df = self.db.get_phrase_mentions_over_time(phrase)
            
            UIComponents.display_trend_chart(df, phrase)

    def page_about(self):
        UIComponents.display_header("About this Project")
        st.markdown("""
        **Congressional NLP Analysis Assistant**
        An interface to analyze the US Congressional Record (43rd-114th Congress).
        """)

    def page_partisan_analysis(self):
            """
            Feature 3: The new Partisan Share tool.
            """
            UIComponents.display_header("⚖️ Partisan Split Analysis", "Who 'owns' a specific policy topic?")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                phrase = st.text_input("Enter Policy Topic:", placeholder="e.g. taxes, abortion, vietnam")
            with col2:
                st.write("")
                st.write("")
                btn_click = st.button("Calculate Share", use_container_width=True)

            if btn_click and phrase:
                with st.spinner("Calculating partisan ownership..."):
                    df = self.db.get_partisan_share(phrase)
                
                UIComponents.display_partisan_share_chart(df, phrase)
                
                # Optional: Show the raw data table for transparency
                with st.expander("View Raw Data"):
                    st.dataframe(df)

    def page_session_search(self):
        """
        Feature 4: Browse speeches by Session Number.
        """
        UIComponents.display_header("🗓️ Session Browser", "Explore the record by specific Congress.")

        # 1. Input Section
        col1, col2 = st.columns([3, 1])
        with col1:
            session_num = st.number_input(
                "Enter Session Number:", 
                min_value=43, max_value=114, value=114
            )
        with col2:
            # Checkbox for the filter
            st.write("")
            filter_noise = st.checkbox("Hide Procedural Noise", value=True)
        
        if st.button("Browse Session", use_container_width=True):
            with st.spinner(f"Fetching records (Filter={filter_noise})..."):
                # Pass the checkbox value to the DB manager
                df = self.db.get_speeches_by_session(session_num, only_mapped=filter_noise)
            if not df.empty:
                st.success(f"Showing {len(df)} substantive speeches.")
                for _, row in df.iterrows():
                    UIComponents.display_speech_card(row)
                    st.divider()
            else:
                st.warning("No speeches found (try disabling the filter if the session is small).")

    def run(self):
            self.render_sidebar()
            
            if st.session_state.page == "Search by ID":
                self.page_search_by_id()
            elif st.session_state.page == "Phrase Trends":
                self.page_phrase_trends()
            elif st.session_state.page == "Partisan Analysis":
                self.page_partisan_analysis()
            elif st.session_state.page == "Session Search": # <--- Add routing
                self.page_session_search()
            elif st.session_state.page == "About":
                self.page_about()

if __name__ == "__main__":
    app = CongressionalDashboard()
    app.run()