import streamlit as st
from utils.database import supabase

def authenticate(username, password):
    response = supabase.table('users').select('*').eq('username', username).eq('password', password).execute()
    if response.data:
        user = response.data[0]
        return user['id'], user['is_admin']
    else:
        return None, False

def logout_and_clear_state():
    st.session_state.current_page = "login"
    st.session_state.index = 0
    st.session_state.show_back = False
    st.session_state.flipped = False
    st.session_state.edit_mode = {}  # Lưu trạng thái chỉnh sửa cho từng ghi chú
    st.session_state.extracted_flashcards = []
    st.session_state.flashcard_edit_mode = {}
    st.session_state.feedback_list = []

def check_login_status():
    if 'user_id' not in st.session_state:
        return False
    return True
