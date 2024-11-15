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

# Hàm chuyển đến trang flashcard
def go_to_flashcard_page():
    st.session_state.current_page = "flashcard"

# Hàm chuyển đến trang thống kê
def go_to_statistics_page():
    st.session_state.current_page = "statistics"

# Hàm chuyển đến trang flashcard collection
def go_to_collection_page():
    st.session_state.current_page = "collection"
        
# Hàm chuyển đến trang login
def go_to_login_page():
    st.session_state.current_page = "login"
        