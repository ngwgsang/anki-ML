import streamlit as st
from components.flashcard_view import flashcard_view
from components.collection_view import flashcard_collection
from components.statistics_view import statistics_view
from components.login_view import login_view
from utils.llms import GeminiFlash


def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    from utils.auth import authenticate
    user_id, is_admin = authenticate("admin", "sangdeptrai")        
    if user_id:
        st.session_state['authenticated'] = True
        st.session_state['user_id'] = user_id  # Lưu user_id vào session_state
        st.session_state['is_admin'] = is_admin
        
    if not st.session_state["authenticated"]:
        login_view()
    else:
        if "llm" not in st.session_state:
            st.session_state["llm"] = GeminiFlash()
        if "extracted_flashcards" not in st.session_state:
            st.session_state.extracted_flashcards = []
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["Flashcard View", "Collection", "Statistics"])

        if page == "Flashcard View":
            flashcard_view()
        elif page == "Collection":
            flashcard_collection()
        elif page == "Statistics":
            statistics_view()

if __name__ == "__main__":
    main()
