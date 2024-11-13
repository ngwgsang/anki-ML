import streamlit as st
from utils.database import load_flashcards, add_flashcard, delete_flashcard, update_flashcard
from utils.helpers import add_furigana

def flashcard_collection():
    st.title("Bộ sưu tập")
    
    # Thêm flashcard mới bằng cách nhập thủ công
    with st.expander("➕ Add New Flashcard"):
        word = st.text_input("Word")
        meaning = st.text_input("Meaning")
        example = st.text_area("Example")
        if st.button("Add Flashcard"):
            add_flashcard(st.session_state.user_id, word, meaning, example)
            st.success("Flashcard added successfully!")
            st.session_state.flashcards = load_flashcards(st.session_state.user_id)  # Cập nhật danh sách flashcards

    # Thêm flashcard tự động bằng AI
    with st.expander("➕ Add Flashcard with AI"):
        # Nhập văn bản và chọn cấp độ
        plain_text = st.text_area("Enter text to extract flashcards")
        level = st.select_slider(
            "Select JLPT Level",
            options=["N5", "N4", "N3", "N2", "N1"],
            value="N3"
        )

        # Xử lý khi nhấn nút trích xuất
        if st.button("Extract Flashcards"):
            extracted_flashcards = st.session_state.llm.extract_flashcard_action(plain_text, level)
            
            # Kiểm tra kết quả trả về từ hàm extract_flashcard_action
            if extracted_flashcards:
                st.session_state['extracted_flashcards'] = extracted_flashcards
                st.success("Flashcards extracted successfully!")
                st.write("Extracted flashcards:", extracted_flashcards)
           
        # Hiển thị flashcard được trích xuất và lựa chọn để lưu
        extracted_flashcards = st.session_state.get('extracted_flashcards', [])
        if extracted_flashcards:
            st.write("Choose flashcards to save:")
            selected_flashcards = []
            for flashcard in extracted_flashcards:
                word = flashcard['word'] if "word" in flashcard.keys() else ""
                meaning = flashcard['meaning'] if "meaning" in flashcard.keys() else ""
                example = flashcard['example'] if "example" in flashcard.keys() else ""                
                if st.checkbox(
                    f"{word} - {meaning} - {example}", key=f"select_{word}"):
                    selected_flashcards.append(flashcard)
            
            # Lưu các flashcard đã chọn
            if st.button("Save Selected Flashcards"):
                for flashcard in selected_flashcards:
                    add_flashcard(
                        st.session_state.user_id,
                        flashcard['word'],
                        flashcard['meaning'],
                        flashcard['example']
                    )
                st.session_state['extracted_flashcards'] = []  # Xóa flashcards sau khi lưu xong
                st.success("Selected flashcards saved successfully!")

    # Hiển thị danh sách flashcards đã lưu
    flashcards = load_flashcards(st.session_state.user_id)
    for card in flashcards:
        card_id = card['id']
        
        # Sử dụng session_state để lưu trạng thái chỉnh sửa
        is_editing = st.session_state.get(f"is_editing_{card_id}", False)
        
        with st.expander(f"{add_furigana(card['word'])} - {card['meaning']}"):
            if is_editing:
                # Form chỉnh sửa
                new_word = st.text_input("Word", value=card['word'], key=f"word_{card_id}")
                new_meaning = st.text_input("Meaning", value=card['meaning'], key=f"meaning_{card_id}")
                new_example = st.text_area("Example", value=card['example'], key=f"example_{card_id}")
                
                if st.button("Save", key=f"save_{card_id}"):
                    update_flashcard(card_id, {
                        "word": new_word,
                        "meaning": new_meaning,
                        "example": new_example
                    })
                    st.session_state[f"is_editing_{card_id}"] = False  # Đóng chế độ chỉnh sửa
                    st.session_state.flashcards = load_flashcards(st.session_state.user_id)  # Cập nhật danh sách flashcards
                    st.rerun()
                
                if st.button("Cancel", key=f"cancel_{card_id}"):
                    st.session_state[f"is_editing_{card_id}"] = False  # Đóng chế độ chỉnh sửa
                    st.rerun()
            else:
                # Hiển thị thông tin flashcard khi không ở chế độ chỉnh sửa
                st.write(f"**Example:** {add_furigana(card['example'])}")
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("Edit", key=f"edit_{card_id}"):
                        st.session_state[f"is_editing_{card_id}"] = True
                        st.rerun()
                with col2:
                    if st.button("Delete", key=f"delete_{card_id}"):
                        delete_flashcard(card_id)
                        st.session_state.flashcards = load_flashcards(st.session_state.user_id)  # Cập nhật danh sách flashcards
                        st.rerun()
