import streamlit as st
import pandas as pd
import altair as alt

class UIComponents:

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
            speaker_name = row.get('speaker', 'Unknown Speaker')
            
            # Dynamic Header based on AI Classification
            is_proc = row.get('is_procedure')
            
            col_head, col_badge = st.columns([3, 1])
            with col_head:
                st.subheader(f"🗣️ {speaker_name}")
            with col_badge:
                if is_proc == 1:
                    st.markdown("🔴 **PROCEDURE**")
                elif is_proc == 0:
                    st.markdown("🟢 **DEBATE**")
                else:
                    st.markdown("⚪ **UNCERTAIN**")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Date", str(row.get('date', 'N/A')))
            c2.metric("Party", row.get('party', 'Unknown'))
            c3.metric("Session", f"{row.get('congress_session', 'N/A')}th")
            c4.metric("State", row.get('state_x', 'N/A'))

            st.caption(f"Speech ID: {row.get('speech_id', 'Unknown')}")
            st.text_area(
                label="Transcript",
                value=row.get('speech', ''),
                height=200,
                disabled=True
            )
            
    @staticmethod
    def display_trend_chart(df: pd.DataFrame, phrase: str):
        if df.empty:
            st.warning(f"No mentions found for '{phrase}'.")
            return

        df['party_name'] = df['party'].map(UIComponents.PARTY_MAP)

        chart = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X('year:O', title='Year'),
            y=alt.Y('mention_count:Q', title='Mentions (Substantive Only)'),
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
        if df.empty:
            st.warning(f"No sufficient data to calculate partisan share for '{phrase}'.")
            return

        st.subheader(f"Partisan Control of '{phrase}'")

        line = alt.Chart(df).mark_line(color='purple', point=True).encode(
            x=alt.X('congress_session:O', title='Session'),
            y=alt.Y('rep_share:Q', title='Republican Share (0-1)', axis=alt.Axis(format='%')),
            tooltip=['congress_session', 'D_count', 'R_count', alt.Tooltip('rep_share', format='.1%')]
        )

        rule = alt.Chart(pd.DataFrame({'y': [0.5]})).mark_rule(color='black', strokeDash=[5, 5]).encode(y='y')

        share_chart = (line + rule).properties(height=250, title="Republican Share of Mentions")

        volume_chart = alt.Chart(df).mark_bar(color='#cccccc').encode(
            x=alt.X('congress_session:O', title='Session'),
            y=alt.Y('total:Q', title='Total Substantive Mentions'),
            tooltip=['congress_session', 'total']
        ).properties(height=150, title="Total Mentions Volume")

        st.altair_chart(share_chart & volume_chart, use_container_width=True)