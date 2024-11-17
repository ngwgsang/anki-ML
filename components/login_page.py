import streamlit as st
from utils.auth import authenticate
import random

# Danh sách icon mẫu
icons = ["✨", "🔥", "🌟", "🍀", "🌈", "🦄", "🌻", "🕊️", "⚡"]

# Hàm tạo lưới 4x5
def render_grid():
    # Duyệt qua 4 hàng
    for row in range(4):
        cols = st.columns(5)  # Tạo 5 cột
        for col_index in range(5):
            # Lấy một icon ngẫu nhiên
            icon = random.choice(icons)
            # Tạo ID duy nhất cho mỗi nút dựa trên vị trí của nó
            unique_id = f"button_{row}_{col_index}"
            # Hiển thị nút trong cột tương ứng
            cols[col_index].button(icon, key=unique_id)
                
def login_action():
    username = st.session_state.get("username", "").strip()
    password = st.session_state.get("password", "").strip()

    if username and password:
        user_id, is_admin = authenticate(username, password)
        if user_id:
            st.session_state.authenticated = True
            st.session_state.user_id = user_id  # Save user ID to session state
            st.session_state.is_admin = is_admin
            st.session_state.current_page = "flashcard"  # Set the current page to flashcard
            st.balloons()
        else:
            st.error("Incorrect username or password. Please try again.")
    else:
        st.error("Please fill in both username and password.")

def render_login_page():
    st.title("Đăng nhập")
    col1, col2 = st.columns([3, 2])
    with col1:
        st.text_input("Tên đăng nhập", key="username", max_chars=32)
        st.text_input("Mật khẩu", type="password", key="password", max_chars=32)
        st.button("Đăng nhập", on_click=login_action , use_container_width=True, type="primary")
    with col2:
        render_grid()