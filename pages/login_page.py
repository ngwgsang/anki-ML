import streamlit as st
from utils.auth import authenticate

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
            # st.success("Logged in successfully!")
            st.write(st.session_state.current_page)
        else:
            st.error("Incorrect username or password. Please try again.")
    else:
        st.error("Please fill in both username and password.")

def render_login_page():
    st.title("Login")
    st.text_input("Username", key="username")
    st.text_input("Password", type="password", key="password")
    st.button("Login", on_click=login_action)
