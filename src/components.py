# src/components.py
import streamlit as st
import pandas as pd
import altair as alt

class UIComponents:

    """
    A library of reusable UI elements.
    """
    
        # Define strict colors: Blue for Dem, Red for Rep
    PARTY_COLORS = ["#0000FF", "#FF0000"]  # Blue, Red
    
    PARTY_MAP = {
        "D": "Democrat",
        "R": "Republican"
    }


    @staticmethod
    def display_header(title: str, subtitle: str = ""):
        st.title(title)
        if subtitle:
            st.markdown(f"*{subtitle}*")
        st.markdown("---")

    @staticmethod
    def display_speech_card(row: pd.Series):
        with st.container():
            # Add a Header for the Speaker Name [cite: 165]
            speaker_name = row.get('speaker', 'Unknown Speaker')
            st.subheader(f"Speaker: {speaker_name}")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Date", str(row.get('date', 'N/A')))
            c2.metric("Party", row.get('party', 'Unknown'))
            c3.metric("Session", f"{row.get('congress_session', 'N/A')}th")
            c4.metric("State", row.get('state_x', 'N/A'))

            # Tag unmapped speeches visually so you know why they might be "noise"
            if row.get('is_mapped') == 0:
                st.warning("⚠️ Procedural/Unmapped Speech") [cite: 101]

            st.caption(f"Speech ID: {row.get('speech_id', 'Unknown')}")
            st.text_area(
                label="Transcript",
                value=row.get('speech', ''),
                height=300,
                disabled=True
            )
            
    @staticmethod
    def display_trend_chart(df: pd.DataFrame, phrase: str):
        """
        Renders a trend chart with strict Red/Blue coloring.
        """
        if df.empty:
            st.warning(f"No mentions found for '{phrase}'.")
            return

        # 1. Clean Data: Map 'D'/'R' to full names
        df['party_name'] = df['party'].map(UIComponents.PARTY_MAP)

        # 2. Create Chart with explicit color mapping
        # We use a 'scale' to map the domain (Party Names) to the range (Colors)
        chart = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X('year:O', title='Year'),
            y=alt.Y('mention_count:Q', title='Mentions'),
            color=alt.Color(
                'party_name', 
                scale=alt.Scale(
                    domain=['Democrat', 'Republican'], 
                    range=UIComponents.PARTY_COLORS
                ),
                legend=alt.Legend(title="Party")
            ),
            tooltip=['year', 'party_name', 'mention_count']
        ).properties(
            title=f"Political Debate on '{phrase}'",
            height=400
        ).interactive()

        st.altair_chart(chart, use_container_width=True)

    @staticmethod
    def render_error(msg: str, details: str = None):
        st.error(msg)
        if details:
            with st.expander("Technical Details"):
                st.code(details)

    @staticmethod
    def display_partisan_share_chart(df: pd.DataFrame, phrase: str):
        """
        Renders a split chart:
        1. Top: The 'Partisan Share' (Are Republicans saying it more?)
        2. Bottom: The raw volume (Is it being said at all?)
        """
        if df.empty:
            st.warning(f"No sufficient data to calculate partisan share for '{phrase}'.")
            return

        st.subheader(f"Partisan Control of '{phrase}'")

        # CHART 1: Republican Share (Line Chart)
        # We create a base chart for the line
        line = alt.Chart(df).mark_line(color='purple', point=True).encode(
            x=alt.X('congress_session:O', title='Session'),
            y=alt.Y('rep_share:Q', title='Republican Share (0-1)', axis=alt.Axis(format='%')),
            tooltip=['congress_session', 'D_count', 'R_count', alt.Tooltip('rep_share', format='.1%')]
        )

        # We add a horizontal rule at 50% (0.5) to show neutrality
        rule = alt.Chart(pd.DataFrame({'y': [0.5]})).mark_rule(color='black', strokeDash=[5, 5]).encode(y='y')

        # Combine Line + Rule
        share_chart = (line + rule).properties(height=250, title="Republican Share of Mentions")

        # CHART 2: Total Volume (Bar Chart)
        # This gives context. 100% share matters less if only 1 person said it.
        volume_chart = alt.Chart(df).mark_bar(color='#cccccc').encode(
            x=alt.X('congress_session:O', title='Session'),
            y=alt.Y('total:Q', title='Total Mentions'),
            tooltip=['congress_session', 'total']
        ).properties(height=150, title="Total Mentions Volume")

        # Display them stacked vertically
        st.altair_chart(share_chart & volume_chart, use_container_width=True)