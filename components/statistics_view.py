import streamlit as st
import pandas as pd
from utils.database import load_study_progress, load_flashcards
from utils.helpers import get_priority_icon

def statistics_view():
    st.title("Learning Statistics")

    study_progress_df = load_study_progress(st.session_state.user_id)
    if not study_progress_df.empty:
        st.line_chart(study_progress_df.set_index("date"))
    else:
        st.warning("No study progress data available.")

    flashcards = load_flashcards(st.session_state.user_id)
    status_counts = {'🔴': 0, '🟠': 0, '🔵': 0, '🟢': 0}
    for card in flashcards:
        icon = get_priority_icon(card['gold_time'])
        status_counts[icon] += 1

    status_df = pd.DataFrame.from_dict(status_counts, orient='index', columns=['Count'])
    st.bar_chart(status_df)
