import streamlit as st
from utils.auth import authenticate

def login_view():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        user_id, is_admin = authenticate(username, password)  # Nhận user_id từ authenticate
        if user_id:
            st.session_state['authenticated'] = True
            st.session_state['user_id'] = user_id  # Lưu user_id vào session_state
            st.session_state['is_admin'] = is_admin
            st.success("Logged in successfully!")
        else:
            st.error("Incorrect username or password. Please try again.")
