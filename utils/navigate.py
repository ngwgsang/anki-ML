import streamlit as st

# Hàm để lấy thẻ tiếp theo
def next_card():
    st.session_state.index = (st.session_state.index + 1) % len(st.session_state.flashcards)
    st.session_state.show_back = False
    st.session_state.flipped = False

# Hàm để lấy thẻ trước đó
def prev_card():
    st.session_state.index = (st.session_state.index - 1) % len(st.session_state.flashcards)
    st.session_state.show_back = False
    st.session_state.flipped = False