import streamlit as st
import random
import time 
from utils.auth import logout_and_clear_state
from assets.styles import BADGE_STYLE

def get_badge(is_admin):
    if is_admin:
        return "Xin chào J97 🪄"
    else:
        return "Đom đóm 🪰"
    
def badge_action(badge):
    
    if "J97":
        msg = [
            "Thiên lý ơi 🌱",
            "Em có thể ở lại đây không 🙄",
            "Biết chăng ngoài trời mưa giông ⛈️",
            "Nhiều cô đơn lắm em 🥵"
        ]
        for msg in msg:
            time.sleep(0.7)
            st.toast(msg)

def render_sidebar():
    if st.session_state.authenticated:
        badge = get_badge(st.session_state.is_admin)
        is_ff = st.sidebar.toggle("Đom đóm", value=True, disabled=False)
        st.sidebar.button(
            badge,
            use_container_width=True,
            on_click= lambda badge = badge : badge_action(badge),
            type="primary"
        )
        st.sidebar.button("Đăng xuất", on_click=logout_and_clear_state, use_container_width=True)
    