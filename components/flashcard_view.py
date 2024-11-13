import streamlit as st
from datetime import timedelta, datetime
from utils.helpers import add_furigana, add_highlight, calculate_time_until_gold, get_priority_icon
from utils.database import load_flashcards, update_gold_time
from assets.styles import FLASHCARD_VIEW_STYLE

def flashcard_view():
    st.markdown(FLASHCARD_VIEW_STYLE, unsafe_allow_html=True)
    
    # Load flashcards once
    flashcards = load_flashcards(st.session_state.user_id)
    
    if "index" not in st.session_state:
        st.session_state.index = 0
    if "show_back" not in st.session_state:
        st.session_state.show_back = False
    if "feedback_list" not in st.session_state:
        st.session_state.feedback_list = []
    if "sync_needed" not in st.session_state:
        st.session_state.sync_needed = False

    if flashcards:
        card = flashcards[st.session_state.index]
        st.session_state.current_card_id = card['id']

        def handle_feedback(feedback_value):
            """Handle user feedback by adding it to feedback_list without updating immediately."""
            current_gold_time = card.get('gold_time', datetime.now())
            if feedback_value == 1:  # 😎 - Tốt
                new_gold_time = current_gold_time + timedelta(days=2)
            elif feedback_value == 0:  # 🤔 - Bình thường
                new_gold_time = current_gold_time + timedelta(days=1)
            else:  # 😱 - Tệ
                new_gold_time = current_gold_time + timedelta(hours=12)

            # Append feedback to the feedback list without triggering a reload
            feedback = {'card_id': card['id'], 'new_gold_time': new_gold_time, 'feedback_value': feedback_value}
            st.session_state.feedback_list.append(feedback)
            st.session_state.sync_needed = True

        # Display the flashcard content based on whether it's front or back
        if st.session_state.show_back:
            example_text = add_highlight(add_furigana(card['example']), card['word'])
            st.markdown(f"""
                <div class='flashcard-box'>
                    {add_furigana(card['word'])}<br>
                    {card['meaning']}<br>
                    {example_text}
                </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("😱", on_click=lambda: handle_feedback(-1), key=f"bad_{card['id']}"):
                    pass
            with col2:
                if st.button("🤔", on_click=lambda: handle_feedback(0), key=f"normal_{card['id']}"):
                    pass
            with col3:
                if st.button("😎", on_click=lambda: handle_feedback(1), key=f"good_{card['id']}"):
                    pass
            st.session_state.show_back = False
        else:
            time_until_gold = calculate_time_until_gold(card['gold_time'])
            st.markdown(f"""
                <div class='flashcard-box'>
                    {add_furigana(card['word'])}
                    <div class='gold-time'>Gold time: {time_until_gold}</div>
                </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("⬅️ Back", key="prev"):
                    st.session_state.index = (st.session_state.index - 1) % len(flashcards)
            with col2:
                if st.button("Flip 🔄", key="flip"):
                    st.session_state.show_back = True
            with col3:
                if st.button("➡️ Next", key="next"):
                    st.session_state.index = (st.session_state.index + 1) % len(flashcards)

        # Display the sync button only if there are items in the feedback list
        if st.session_state.sync_needed:
            if st.button("🔄 Đồng bộ"):
                with st.expander("Đang đồng bộ..."):
                    progress_bar = st.progress(0)
                    total_feedback = len(st.session_state.feedback_list)
                    progress_step = 100 / total_feedback

                    for i, feedback in enumerate(st.session_state.feedback_list, 1):
                        update_gold_time(feedback['card_id'], feedback['new_gold_time'])
                        progress_bar.progress(int(i * progress_step))
                    
                    # Clear the feedback list and reset sync_needed flag after syncing
                    st.session_state.feedback_list = []
                    st.session_state.sync_needed = False
                    st.success("Đã đồng bộ dữ liệu thành công!")
    else:
        st.warning("No flashcards available. Please add flashcards to start learning.")
