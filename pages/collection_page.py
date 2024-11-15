import streamlit as st
import pandas as pd
from utils.database import add_flashcard, load_flashcards, delete_flashcard, update_flashcard
from utils.helpers import get_priority_icon
from utils.navigate import go_to_flashcard_page

# Set the page configuration
# st.set_page_config(
#     page_title="Anki-ML✨",
#     page_icon="📚",
#     layout="centered",
#     initial_sidebar_state="collapsed",  # This collapses the sidebar by default
# )

def add_flashcard_action():
    if st.session_state["new_word"] and st.session_state["new_meaning"] and st.session_state["new_example"]:
        add_flashcard(st.session_state["new_word"], st.session_state["new_meaning"], st.session_state["new_example"])
        st.toast(f"Flashcard '{st.session_state['new_word']}' đã được thêm.", icon='🎉')
        st.session_state.flashcards = load_flashcards()
        st.session_state["new_word"] = ""
        st.session_state["new_meaning"] = ""
        st.session_state["new_example"] = ""
    else:
        st.warning("Vui lòng nhập đầy đủ thông tin.")

# Hàm lưu các flashcard đã chọn vào Supabase
def save_extracted_flashcards():
    selected_flashcards = [flashcard for flashcard in st.session_state['extracted_flashcards'] if st.session_state.get(f"select_{flashcard['word']}", False)]
    for flashcard in selected_flashcards:
        word = flashcard['word']
        meaning = flashcard['meaning']
        example = flashcard.get('example', '')

        try:
            add_flashcard(word, meaning, example)
            st.toast(f"Flashcard '{word}' đã được thêm.", icon='🎉')
        except Exception as e:
            st.error(f"Lỗi khi lưu flashcard '{word}' vào Supabase: {e}")
            
    # Cập nhật lại danh sách flashcards sau khi lưu
    st.session_state.flashcards = load_flashcards()
    st.session_state['extracted_flashcards'] = []

# Wrapper function for editing a flashcard
def save_edit_flashcard_action(card_id):
    updated_word = st.session_state.get(f"edit_word_{card_id}", "").strip()
    updated_meaning = st.session_state.get(f"edit_meaning_{card_id}", "").strip()
    updated_example = st.session_state.get(f"edit_example_{card_id}", "").strip()
    if updated_word and updated_meaning and updated_example:
        try:
            update_flashcard(card_id, updated_word, updated_meaning, updated_example)
            st.session_state.flashcard_edit_mode[card_id] = False  # Exit edit mode
            st.session_state.flashcards = load_flashcards()  # Reload flashcards
            st.toast(f"Flashcard '{updated_word}' đã được cập nhật.", icon='✅')
            st.rerun()  # Rerun to refresh the page immediately
        except Exception as e:
            st.error(f"Lỗi khi cập nhật flashcard trong Supabase: {e}")
    else:
        st.warning("Từ vựng, nghĩa và ví dụ không được để trống.")
        
# Wrapper function for deleting a flashcard
def delete_flashcard_action(card_id):
    delete_flashcard(card_id)
    st.session_state.flashcards = load_flashcards()  # Reload flashcards to update the list
    st.rerun()  # Rerun to refresh the page immediately


def render_collection_page():
    
    st.button("🔙 Quay lại", on_click=go_to_flashcard_page(), key="back_to_view")
    st.title("Bộ sưu tập thẻ")

    # Nút thêm flashcard
    with st.expander("➕ Thêm Flashcard Mới"):
        
        # Define input fields for the new flashcard
        new_word = st.text_input("Từ vựng:", key="new_word")
        new_meaning = st.text_input("Nghĩa:", key="meaning")
        new_example = st.text_input("Ví dụ:", key="example")

        # In app.py, inside the "Thêm Flashcard" button's on_click event
        st.button("Thêm Flashcard", on_click=add_flashcard_action)

    # Giao diện thêm Flashcard bằng AI
    with st.expander("➕ Thêm Flashcard với AI"):
        plain_text = st.text_area("Văn bản:", key='plain_text')
        level = st.select_slider(
            "Chọn cấp độ",
            options=[
                "N5",
                "N4",
                "N3",
                "N2",
                "N1",
            ],
            value="N2",
            key="level"
        )

        if st.button("Trích xuất"):
            st.session_state.llm.extract_flashcard_action(plain_text, level)
            
        # Hiển thị danh sách các flashcard đã trích xuất nếu có
        extracted_flashcards = st.session_state.get('extracted_flashcards', [])
        if extracted_flashcards:
            st.write(extracted_flashcards)
            st.write("Chọn các flashcard bạn muốn lưu:")
            for flashcard in extracted_flashcards:
                st.checkbox(f"{flashcard['word']} - {flashcard['meaning']} - {flashcard['example']}", key=f"select_{flashcard['word']}")
                
            # Nút lưu các flashcard đã chọn
            if st.button("Lưu các flashcard đã chọn", on_click=save_extracted_flashcards):
                plain_text = ""
                st.session_state['extracted_flashcards'] = []
                
    # Logic for displaying flashcards in the collection view
    for idx, card in enumerate(st.session_state.flashcards):
        icon = get_priority_icon(card['gold_time'])
        is_editable = st.session_state.flashcard_edit_mode.get(card['id'], False)

        with st.expander(f"{icon} {card['word']} - {card['meaning']}", expanded=False):
            if is_editable:
                # Chế độ chỉnh sửa
                st.text_input("Từ vựng:", value=card['word'], key=f"edit_word_{card['id']}")
                st.text_input("Nghĩa:", value=card['meaning'], key=f"edit_meaning_{card['id']}")
                st.text_area("Ví dụ:", value=card['example'], key=f"edit_example_{card['id']}")

                col_save, col_cancel = st.columns([1, 1])
                with col_save:
                    st.button("Lưu", key=f"save_card_{card['id']}", on_click=lambda card_id=card['id']: save_edit_flashcard_action(card_id), use_container_width=True)
                with col_cancel:
                    st.button("Hủy", key=f"cancel_card_{card['id']}", on_click=lambda card_id=card['id']: st.session_state.flashcard_edit_mode.update({card_id: False}), use_container_width=True)
            else:
                # Display flashcard information
                st.write(f"**Ví dụ:** {card['example']}")
                gold_time_str = card['gold_time'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(card['gold_time']) else "N/A"
                st.write(f"**Gold time:** {gold_time_str}")

                col_edit, col_delete = st.columns([1, 1])
                with col_edit:
                    st.button("Chỉnh sửa", key=f"edit_card_{card['id']}", on_click=lambda card_id=card['id']: st.session_state.flashcard_edit_mode.update({card_id: True}), use_container_width=True)
                with col_delete:
                    st.button("🗑️ Xóa Flashcard", key=f"delete_card_{card['id']}", on_click=lambda card_id=card['id']: delete_flashcard_action(card['id']), use_container_width=True)
                    
    # Nút quay lại trang flashcard_view
    st.button("🔙 Quay lại", on_click=go_to_flashcard_page(), key="back_to_view2")