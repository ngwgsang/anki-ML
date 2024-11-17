import streamlit as st
import random

random_icon = random.choice(["✨", "🪄", "🦄", "🌱", ""]) 
st.set_page_config(
    page_title="Anki-ML",
    page_icon=random_icon,
    layout="centered",
    initial_sidebar_state="collapsed",
)

from utils.helpers import load_environment_variables
from utils.schedule import load_sarimax_model
from components import render_statistics_page, render_collection_page, render_flashcard_page, render_login_page, render_sidebar
from utils.llms import GeminiFlash


load_environment_variables()

# Kiểm tra nếu chưa có dữ liệu flashcards trong session_state
if "flashcards" not in st.session_state:
    st.session_state.flashcards = []
if "sarimax_model" not in st.session_state:
    st.session_state.sarimax_model = load_sarimax_model()
if "index" not in st.session_state:
    st.session_state.index = 0
if "show_back" not in st.session_state:
    st.session_state.show_back = False
if "flipped" not in st.session_state:
    st.session_state.flipped = False
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = {}  # Lưu trạng thái chỉnh sửa cho từng ghi chú
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"  # Trang hiện tại
if "llm" not in st.session_state:
    st.session_state.llm = GeminiFlash()
if "extracted_flashcards" not in st.session_state:
    st.session_state.extracted_flashcards = []
if "flashcard_edit_mode" not in st.session_state:
    st.session_state.flashcard_edit_mode = {}
if "feedback_list" not in st.session_state:
    st.session_state.feedback_list = []
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "ai_note_content" not in st.session_state:
    st.session_state.ai_note_content = ""
if "authenticated" not in st.session_state:
    st.session_state.authenticated = ""

# App default
render_sidebar()

# Page routing
if st.session_state.current_page == "login":
    render_login_page()
elif st.session_state.current_page == "flashcard":
    render_flashcard_page()
elif st.session_state.current_page == "collection":
    render_collection_page()
elif st.session_state.current_page == "statistics":
    render_statistics_page()
