import streamlit as st
from assets.styles import FLASHCARD_VIEW_STYLE
from utils.helpers import add_furigana, add_highlight, calculate_time_until_gold, stream_data
from utils.database import load_flashcards, load_notes, delete_note, update_note, update_gold_time, add_note, update_study_progress
from utils.navigate import next_card, prev_card, go_to_collection_page, go_to_statistics_page
from utils.schedule import predict_next_gold_time
from utils.audio import generate_audio
from datetime import datetime, timedelta
import pandas as pd
import time

# Cập nhật `gold_time` trong Supabase
def update_timestamp_by_id(card_id, gold_time):
    try:
        # supabase.table('flashcards').update({'gold_time': gold_time.strftime('%Y-%m-%d %H:%M:%S')}).eq('id', card_id).execute()
        update_gold_time(card_id, gold_time.strftime('%Y-%m-%d %H:%M:%S'))
        st.session_state.flashcards = load_flashcards()
    except Exception as e:
        st.error(f"Lỗi khi cập nhật dữ liệu trong Supabase: {e}")

def update_gold_time_based_on_feedback(feedback_value):
    
    card = st.session_state.flashcards[st.session_state.index]
    card_id = card["id"]
    last_timestamp = card['gold_time']

    if pd.isna(last_timestamp):
        last_timestamp = pd.Timestamp.now()

    # Tính toán gold_time dựa trên phản hồi
    if st.session_state.sarimax_model:
        gold_time = predict_next_gold_time(st.session_state.sarimax_model, last_timestamp, feedback_value)
    else:
        gold_time = last_timestamp + timedelta(days=2)

    # Lưu phản hồi và gold_time vào session_state
    st.session_state.feedback_list.append({
        'card_id': card_id,
        'gold_time': gold_time,
        'feedback_value': feedback_value
    })

    next_card()  # Chuyển đến thẻ tiếp theo sau khi phản hồi
        
def sync_data():
    feedback_list = st.session_state.get('feedback_list', [])

    if not feedback_list:
        st.info("Không có dữ liệu mới để đồng bộ.")
        return

    # Use st.empty() to create a dynamic placeholder for the expander
    expander_placeholder = st.empty()

    with expander_placeholder.expander("Đang đồng bộ..."):
        # Initialize the progress bar
        progress_bar = st.progress(0)
        total_feedback = len(feedback_list)
        progress_step = 1 / (total_feedback + 1)  # +1 for study_progress update

        # Label for showing current progress step
        status_label = st.empty()

        # Prepare data to update the study_progress table
        study_progress = {'good_count': 0, 'normal_count': 0, 'bad_count': 0}

        # Sync gold_time for each card and accumulate study progress
        for idx, feedback in enumerate(feedback_list):
            card_id = feedback['card_id']
            gold_time = feedback['gold_time']
            feedback_value = feedback['feedback_value']

            # Update gold_time in the database
            try:
                status_label.text(f"Đang cập nhật gold_time cho thẻ ID {card_id}...")
                time.sleep(0.5)  # Simulate update delay
                # Replace this line with your actual Supabase update code
            except Exception as e:
                st.error(f"Lỗi khi cập nhật gold_time cho flashcard ID {card_id}: {e}")

            # Accumulate study progress
            if feedback_value == 1:
                study_progress['good_count'] += 1
            elif feedback_value == 0:
                study_progress['normal_count'] += 1
            elif feedback_value == -1:
                study_progress['bad_count'] += 1

            # Update the progress bar
            progress_bar.progress(int((idx + 1) * progress_step * 100))

        # Update the study_progress table
        try:
            status_label.text("Đang cập nhật tiến độ học...")
            time.sleep(0.5)  # Simulate update delay
            update_study_progress(
                {
                    "good_count": study_progress['good_count'],
                    "normal_count": study_progress['normal_count'],
                    "bad_count": study_progress['bad_count']
                }
            )

        except Exception as e:
            st.error(f"Lỗi khi cập nhật tiến độ học: {e}")

        # Final update for the progress bar
        progress_bar.progress(100)
        status_label.text("Hoàn tất đồng bộ.")

    # Clear the feedback list after synchronization
    st.session_state.feedback_list = []

    # Reload flashcards to update changes
    st.session_state.flashcards = load_flashcards()  # Uncomment to reload flashcards if needed


# Hàm lưu ghi chú mới vào bảng notes và session state
def save_note_action():
    flashcard_id = st.session_state.current_card_id
    new_title = st.session_state.new_note_title.strip()
    new_content = st.session_state.new_note_content.strip()
    if new_content:
        if new_title == "":
            add_note(flashcard_id, "🌱 Note", new_content)
        else:
            add_note(flashcard_id, new_title, new_content)
        st.session_state.new_note_title = ""
        st.session_state.new_note_content = ""
    else:
        st.toast("Vui lòng nhập nội dung")

def take_note_with_ai_action():
    if st.session_state["new_note_content"]:
        if st.session_state["new_note_title"] == "":
            st.session_state["new_note_title"] = "🤖 Note AI"
        
        note = st.session_state.llm.take_note_action()
        add_note(st.session_state.current_card_id, st.session_state.new_note_title.strip(), note)

        st.session_state.new_note_title = ""
        st.session_state.new_note_content = ""
    else:
        st.toast("Vui lòng nhập nội dung")

# Hàm cập nhật ghi chú và session state
def save_edit_note_action(note_id):
    updated_title = st.session_state.get(f"edit_note_title_{note_id}", "").strip()
    updated_content = st.session_state.get(f"edit_note_content_{note_id}", "").strip()
    if updated_title and updated_content:
        try:
            update_note(note_id, updated_title, updated_content)
            st.session_state.edit_mode[note_id] = False  # Thoát chế độ chỉnh sửa
            
            # Reset the session state values for the note inputs
            st.session_state[f"edit_note_title_{note_id}"] = ""
            st.session_state[f"edit_note_content_{note_id}"] = ""
            
            st.success("Note updated successfully!")
        except Exception as e:
            st.error(f"Lỗi khi cập nhật ghi chú trong Supabase: {e}")
    else:
        st.warning("Tiêu đề và nội dung ghi chú không được để trống.")


# Lấy thẻ hiện tại dựa vào chỉ số
def render_flashcard_page():
    st.session_state.flashcards = load_flashcards()
    if len(st.session_state.flashcards) > 0: 
        card = st.session_state.flashcards[st.session_state.index]
        st.session_state.current_card_id = card['id']
        
        # Tùy chỉnh CSS cho hộp thẻ và nút
        st.markdown(FLASHCARD_VIEW_STYLE, unsafe_allow_html=True)

        # Hiển thị mặt trước hoặc mặt sau của thẻ dựa vào trạng thái
        if st.session_state.show_back:
            example_text = add_highlight(add_furigana(card['example']), card['word'])
            st.markdown(f"""<div class='flashcard-box'>{add_furigana(card['word'])}<br>{card['meaning']}<br>{example_text}</div>""", unsafe_allow_html=True)
            try:
                audio_data = generate_audio(card['word'])
                st.audio(audio_data, format="audio/mp3")
            except:
                st.warning("Tạm thời không thể tạo audio 🙇‍♂️")

            # Hiển thị các lựa chọn phản hồi sau khi lật thẻ
            with st.container():
                col2, col3, col4 = st.columns(3)
                with col2:
                    st.button("😱", on_click=lambda: update_gold_time_based_on_feedback(-1), use_container_width=True)
                with col3:
                    st.button("🤔", on_click=lambda: update_gold_time_based_on_feedback(0), use_container_width=True)
                with col4:
                    st.button("😎", on_click=lambda: update_gold_time_based_on_feedback(1), use_container_width=True)

            # Lấy và hiển thị ghi chú cho flashcard hiện tại
            st.write("### Ghi chú")
            notes = st.session_state.get(f"notes_{card['id']}", load_notes(card['id']))
            for note in notes:
                note_id = note['id']
                # Xác định nếu `edit_mode` cho note_id được bật
                is_editable = st.session_state.edit_mode.get(note_id, False)

                with st.expander(note['title'], expanded=False):
                    if is_editable:
                        # Chế độ chỉnh sửa
                        st.text_input("Tiêu đề:", value=note['title'], key=f"edit_note_title_{note_id}")
                        st.text_area("Nội dung ghi chú:", value=note['content'], key=f"edit_note_content_{note_id}")
                        col_edit, col_cancel = st.columns([1, 1])
                        with col_edit:
                            st.button("Lưu", key=f"save_{note_id}", on_click=lambda note_id=note_id: save_edit_note_action(note_id), use_container_width=True)
                        with col_cancel:
                            st.button("Hủy", key=f"cancel_{note_id}", on_click=lambda note_id=note_id: st.session_state.edit_mode.update({note_id: False}), use_container_width=True)
                    else:
                        # Hiển thị ghi chú
                        st.markdown(note['content'])
                        col_edit, col_delete = st.columns([1, 1])
                        with col_edit:
                            st.button("Chỉnh sửa", key=f"edit_{note_id}", on_click=lambda note_id=note_id: st.session_state.edit_mode.update({note_id: True}), use_container_width=True)
                        with col_delete:
                            st.button("Xóa", key=f"delete_{note_id}", on_click=lambda note_id=note_id: delete_note(note_id), use_container_width=True)
                            
            st.divider()
            # Đặt component thêm ghi chú vào expander
            with st.expander("➕ Thêm ghi chú", expanded=False):
                st.text_input("Tiêu đề ghi chú:", key="new_note_title")
                st.text_area("Nội dung ghi chú:", key="new_note_content")
                col1, col2 = st.columns(2)
                with col1:
                    st.button("Gửi", on_click=save_note_action, use_container_width=True)
                with col2:
                    st.button("Magic 🪄", on_click=take_note_with_ai_action, use_container_width=True)
                    
        else:
            time_until_gold = calculate_time_until_gold(card['gold_time'])
            st.markdown(f"<div class='flashcard-box'>{add_furigana(card['word'])}<span class='gold_time'>Gold time: {time_until_gold}</span></div>", unsafe_allow_html=True)

        # Hiển thị các nút điều hướng và nút lật thẻ
        with st.container():
            col1, col2, col3 = st.columns(3)
            if not st.session_state.flipped:  # Chỉ hiển thị nút Flip nếu thẻ chưa lật
                with col1:
                    st.button("⬅️ Quay lại", on_click=prev_card, use_container_width=True)
                with col2:
                    st.button("🔥", on_click=lambda: st.session_state.update(show_back=not st.session_state.show_back, flipped=True), use_container_width=True)
                with col3:
                    st.button("➡️ Tiếp tục", on_click=next_card, use_container_width=True)

        # Thêm nút ở góc trái bên dưới màn hình
        st.markdown(
            """
            <style>
            .bottom-left-button {
                position: fixed;
                bottom: 10px;
                left: 10px;
            }
            </style>
            """, unsafe_allow_html=True
        )
    else:
        st.warning("Bạn chưa có thẻ nào!")
        
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("📚 Bộ sưu tập", on_click=go_to_collection_page, key="collection_button", help="Xem bộ sưu tập flashcard", type="primary", use_container_width=True)
        with col2:
            st.button("📊 Thống kê", on_click=go_to_statistics_page, key="statistics_button", help="Xem thống kê", type="primary", use_container_width=True)
        with col3:
            st.button("🔄 Đồng bộ", on_click=sync_data, key="sync_button", help="Đồng bộ dữ liệu với cơ sở dữ liệu", type="primary", use_container_width=True)
             