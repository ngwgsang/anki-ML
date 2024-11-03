from utils.llm import GeminiFlask
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import joblib
from supabase import create_client
from dotenv import load_dotenv
import os
import time
import json

# Đọc các biến môi trường từ file .env
load_dotenv()

# Lấy thông tin kết nối Supabase từ biến môi trường
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase URL và Key không được tìm thấy. Vui lòng thiết lập trong file .env.")

# Khởi tạo kết nối Supabase
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# Hàm để tải dữ liệu flashcards từ Supabase
def load_flashcards():
    try:
        data = supabase.table('flashcards').select('*').execute()
        flashcards = data.data if data.data else []
        for card in flashcards:
            # Lấy giá trị 'gold_time' và chuyển đổi sang datetime
            gold_time_raw = card.get('gold_time')
            if gold_time_raw:
                card['gold_time'] = pd.to_datetime(gold_time_raw, errors='coerce')
            else:
                # Nếu 'gold_time' không có, đặt là NaT
                card['gold_time'] = pd.NaT
        # Sắp xếp các thẻ dựa trên `gold_time`
        today = pd.Timestamp.now()
        flashcards.sort(
            key=lambda x: (
                # Nếu 'gold_time' không phải NaT và nhỏ hơn hôm nay
                ((x['gold_time'] - today).days if pd.notna(x['gold_time']) and x['gold_time'] < today else float('inf')),
                # Nếu 'gold_time' không phải NaT và lớn hơn hoặc bằng hôm nay
                (x['gold_time'] if pd.notna(x['gold_time']) and x['gold_time'] >= today else float('inf')),
                # Nếu 'gold_time' không phải NaT
                (-x['gold_time'].toordinal() if pd.notna(x['gold_time']) else 0)
            )
        )
        return flashcards
    except Exception as e:
        st.error(f"Lỗi khi lấy dữ liệu từ Supabase: {e}")
        return []

flashcards = []

# Kiểm tra nếu chưa có dữ liệu flashcards trong session_state
if "flashcards" not in st.session_state:
    flashcards = load_flashcards()
    st.session_state.flashcards = flashcards
else:
    flashcards = st.session_state.get("flashcards", [])

# Tải mô hình SARIMAX đã lưu
def load_sarimax_model():
    try:
        model = joblib.load("model/sarimax_model.pkl")
        return model
    except FileNotFoundError:
        st.error("Không tìm thấy file mô hình SARIMAX. Vui lòng đảm bảo file mô hình tồn tại.")
        return None

# Hàm dự báo thời gian luyện tập tiếp theo
def predict_next_gold_time(model, last_timestamp, current_point):
    current_timestamp = pd.to_datetime(datetime.now())
    days_difference = (current_timestamp - last_timestamp).days

    gold_point = current_point
    if current_point > -1:
        gold_point += days_difference

    exog_forecast = pd.DataFrame({"point": [gold_point]})
    forecast = model.get_forecast(steps=1, exog=exog_forecast)
    next_gap_days = forecast.predicted_mean.iloc[0]
    
    return last_timestamp + timedelta(days=next_gap_days)

# Hàm lấy ghi chú của flashcard từ bảng notes và lưu vào session state
def fetch_notes(flashcard_id):
    try:
        response = supabase.table('notes').select('*').eq('flashcard_id', flashcard_id).execute()
        notes = response.data if response.data else []
        st.session_state[f"notes_{flashcard_id}"] = notes  # Lưu ghi chú vào session_state
        return notes
    except Exception as e:
        st.error(f"Lỗi khi lấy dữ liệu ghi chú từ Supabase: {e}")
        return []
    
def stream_data(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)
        
def llm_note_action():
    flashcard_id = st.session_state.current_card_id
    card = st.session_state.flashcards[st.session_state.index]
    prompt = (
        "You are a helpful assistant designed to create concise and informative notes for language flashcards.\n"
        "For each flashcard, you will receive a word and its meaning.\n"
        "Your task is to generate a brief note that helps the user remember the word and how to use it in context.\n"
        "Focus on practical usage and examples when possible.\n"
        "Make sure your notes are clear and easy to understand.\n"
        "CURRENT FLASHCARD INFO\n"
        f"WORD: {card['word']}\n"
        f"MEANING: {card['meaning']}\n"
        f"EXAMPLE: {card['example']}\n"
        f"TASK: {st.session_state.new_note_content}\n"
        f"Generate a note based on this info I provided."
    )
    new_note_content = st.session_state.llm.run(prompt, GEMINI_KEY) 
    if new_note_content:
        try:
            # Lưu ghi chú với title và content
            supabase.table('notes').insert({
                "flashcard_id": flashcard_id,
                "title": st.session_state.new_note_title.strip(),
                "content": new_note_content
            }).execute()
            st.session_state.new_note_title = ""
            st.session_state.new_note_content = ""  # Xóa nội dung sau khi gửi
        except Exception as e:
            st.error(f"Lỗi khi lưu ghi chú vào Supabase: {e}")
    else:
        st.warning("Vui lòng nhập nội dung ghi chú.")
        
def llm_extract_flashcard_action():
    
    plain_text = st.session_state.get("plain_text", '').strip()     
    level = st.session_state.get("level", '').strip()     
    if len(plain_text) < 10: 
        st.error("Văn bản quá ngắn!")
    else:
        prompt = (
            "You are a helpful assistant designed to create concise and informative for Japanese language flashcards.\n"
            "For each flashcard, you will receive a word in Japanese and its meaning in Vietnamese.\n"
            "Use this JSON schema:\n"
            "Flashcard = {'word': str, 'meaning': str, 'example': str}\n"
            "Return: list[Flashcard]\n",
            "Generate 1 - 5 flashcard at level {}.\n",
            f"\n\nTEXT: {level}"
        )
        new_flashcards = st.session_state.llm.run_json(prompt, GEMINI_KEY)
        st.session_state['extracted_flashcards'] = json.loads(new_flashcards)

# Hàm lưu các flashcard đã chọn vào Supabase
def save_extracted_flashcards():
    selected_flashcards = [flashcard for flashcard in st.session_state['extracted_flashcards'] if st.session_state.get(f"select_{flashcard['word']}", False)]
    for flashcard in selected_flashcards:
        word = flashcard['word']
        meaning = flashcard['meaning']
        example = flashcard.get('example', '')

        try:
            # Lưu từng flashcard vào Supabase
            supabase.table('flashcards').insert({
                "word": word,
                "meaning": meaning,
                "example": example,
                "gold_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }).execute()
            st.toast(f"Flashcard '{word}' đã được thêm.", icon='🎉')
        except Exception as e:
            st.error(f"Lỗi khi lưu flashcard '{word}' vào Supabase: {e}")

    # Cập nhật lại danh sách flashcards sau khi lưu
    st.session_state.flashcards = load_flashcards()
    st.session_state['extracted_flashcards'] = []  # Xóa flashcards sau khi lưu xong

# Hàm lưu ghi chú mới vào bảng notes và session state
def save_note_action():
    flashcard_id = st.session_state.current_card_id
    new_title = st.session_state.new_note_title.strip()
    new_content = st.session_state.new_note_content.strip()
    if new_title and new_content:
        try:
            # Lưu ghi chú với title và content
            supabase.table('notes').insert({
                "flashcard_id": flashcard_id,
                "title": new_title,
                "content": new_content
            }).execute()
            st.session_state.new_note_title = ""
            st.session_state.new_note_content = ""  # Xóa nội dung sau khi gửi
        except Exception as e:
            st.error(f"Lỗi khi lưu ghi chú vào Supabase: {e}")
    else:
        st.warning("Vui lòng nhập tiêu đề và nội dung ghi chú.")

# Hàm xóa ghi chú và cập nhật session state
def delete_note_action(note_id):
    flashcard_id = st.session_state.current_card_id
    try:
        supabase.table('notes').delete().eq('id', note_id).execute()
    except Exception as e:
        st.error(f"Lỗi khi xóa ghi chú từ Supabase: {e}")

# Hàm cập nhật ghi chú và session state
def save_edit_note_action(note_id):
    updated_title = st.session_state.get(f"edit_note_title_{note_id}", "").strip()
    updated_content = st.session_state.get(f"edit_note_content_{note_id}", "").strip()
    if updated_title and updated_content:
        try:
            supabase.table('notes').update({
                "title": updated_title,
                "content": updated_content
            }).eq('id', note_id).execute()
            st.session_state.edit_mode[note_id] = False  # Thoát chế độ chỉnh sửa
        except Exception as e:
            st.error(f"Lỗi khi cập nhật ghi chú trong Supabase: {e}")
    else:
        st.warning("Tiêu đề và nội dung ghi chú không được để trống.")

# Hàm chuyển đến trang flashcard collection
def go_to_flashcard_collection():
    st.session_state.current_page = "flashcard_collection"

# Hàm thêm flashcard mới
def add_flashcard():
    word = st.session_state.get('new_word', '').strip()
    meaning = st.session_state.get('new_meaning', '').strip()
    example = st.session_state.get('new_example', '').strip()
    if word and meaning and example:
        try:
            # Thêm 'gold_time' mặc định là thời gian hiện tại
            supabase.table('flashcards').insert({
                "word": word,
                "meaning": meaning,
                "example": example,
                "gold_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }).execute()
            st.toast(f"Flashcard '{word}' đã được thêm.", icon='🎉')
            # Xóa nội dung nhập
            st.session_state.new_word = ""
            st.session_state.new_meaning = ""
            st.session_state.new_example = ""
            # Cập nhật danh sách flashcards ngay sau khi thêm
            st.session_state.flashcards = load_flashcards()
        except Exception as e:
            st.error(f"Lỗi khi thêm flashcard vào Supabase: {e}")
    else:
        st.warning("Vui lòng nhập đầy đủ thông tin.")

# Hàm xóa flashcard
def delete_flashcard(card_id):
    try:
        supabase.table('flashcards').delete().eq('id', card_id).execute()
        st.success("Flashcard đã được xóa.")
        # Cập nhật danh sách flashcards
        st.session_state.flashcards = load_flashcards()
    except Exception as e:
        st.error(f"Lỗi khi xóa flashcard từ Supabase: {e}")

# Hàm để lấy biểu tượng ưu tiên dựa trên gold_time
def get_priority_icon(gold_time):
    now = pd.Timestamp.now()
    if pd.isna(gold_time):
        return "🟢"
    time_diff = gold_time - now
    days_diff = time_diff.total_seconds() / (3600 * 24)
    if days_diff < 0:
        return "🔴"
    elif days_diff <= 1:
        return "🟠"
    elif days_diff <= 2:
        return "🔵"
    else:
        return "🟢"

# Nếu flashcards có dữ liệu, tiếp tục hiển thị thẻ
if flashcards:
    if "index" not in st.session_state:
        st.session_state.index = 0
    if "show_back" not in st.session_state:
        st.session_state.show_back = False
    if "flipped" not in st.session_state:
        st.session_state.flipped = False
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = {}  # Lưu trạng thái chỉnh sửa cho từng ghi chú
    if "current_page" not in st.session_state:
        st.session_state.current_page = "flashcard_view"  # Trang hiện tại
    if "llm" not in st.session_state:
        st.session_state.llm = GeminiFlask()
    if "extracted_flashcards" not in st.session_state:
        st.session_state.extracted_flashcards = []
        
    # Tải mô hình SARIMAX từ file
    model = load_sarimax_model()

    # Cập nhật `gold_time` trong Supabase
    def update_timestamp_by_id(card_id, gold_time):
        try:
            supabase.table('flashcards').update({'gold_time': gold_time.strftime('%Y-%m-%d %H:%M:%S')}).eq('id', card_id).execute()
            st.session_state.flashcards = load_flashcards()
        except Exception as e:
            st.error(f"Lỗi khi cập nhật dữ liệu trong Supabase: {e}")

    # Hàm để xử lý phản hồi của người dùng
    def update_gold_time_based_on_feedback(feedback_value):
        card = st.session_state.flashcards[st.session_state.index]
        last_timestamp = card['gold_time']
        
        if pd.isna(last_timestamp):
            last_timestamp = pd.Timestamp.now()

        if model:
            gold_time = predict_next_gold_time(model, last_timestamp, feedback_value)
        else:
            gold_time = last_timestamp + timedelta(days=2)

        card_id = card["id"]
        update_timestamp_by_id(card_id, gold_time)

        next_card()

    # Hàm để lấy thẻ tiếp theo
    def next_card():
        st.session_state.index = (st.session_state.index + 1) % len(st.session_state.flashcards)
        st.session_state.show_back = False
        st.session_state.flipped = False

    # Hàm để lấy thẻ trước đó
    def prev_card():
        st.session_state.index = (st.session_state.index - 1) % len(st.session_state.flashcards)
        st.session_state.show_back = False
        st.session_state.flipped = False

    # Tính khoảng thời gian còn lại đến gold_time
    def calculate_time_until_gold(gold_time):
        now = pd.Timestamp.now()
        if pd.isna(gold_time):
            return "N/A"
        time_diff = gold_time - now
        if time_diff.total_seconds() <= 0:
            return "Bây giờ"
        hours, remainder = divmod(int(time_diff.total_seconds()), 3600)
        minutes = remainder // 60
        return f"{hours} giờ {minutes} phút nữa"

    # Kiểm tra trang hiện tại
    if st.session_state.current_page == "flashcard_view":
        # Lấy thẻ hiện tại dựa vào chỉ số
        card = st.session_state.flashcards[st.session_state.index]
        st.session_state.current_card_id = card['id']

        # Tùy chỉnh CSS cho hộp thẻ và nút
        st.markdown(
            """
            <style>
            .flashcard-box {
                border: 2px solid black;
                padding: 80px 20px;
                border-radius: 10px;
                background-color: #f9f9f9;
                text-align: center;
                margin: 10px 0;
                font-size: 20px;
                color: black;
                position: relative;
            }
            b {
                color: red;
            }
            .gold_time {
                position: absolute;
                right: 20px;
                bottom: 10px;
                font-size: 14px;
            }
            .note-box {
                background-color: #f0f0f0;
                padding: 10px;
                margin-top: 10px;
                border-radius: 5px;
                font-size: 16px;
                color: #333;
            }
            .bottom-left-button {
                position: fixed;
                bottom: 10px;
                left: 10px;
            }
            </style>
            """, unsafe_allow_html=True
        )

        # Hiển thị mặt trước hoặc mặt sau của thẻ dựa vào trạng thái
        if st.session_state.show_back:
            example_text = card['example'].replace('"', '<b>', 1).replace('"', '</b>', 1)
            st.markdown(f"""<div class='flashcard-box'>{card['word']}<br>{card['meaning']}<br>{example_text}</div>""", unsafe_allow_html=True)
            
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
            notes = st.session_state.get(f"notes_{card['id']}", fetch_notes(card['id']))
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
                            st.button("Xóa", key=f"delete_{note_id}", on_click=lambda note_id=note_id: delete_note_action(note_id), use_container_width=True)
                            
            st.divider()
            # Đặt component thêm ghi chú vào expander
            with st.expander("➕ Thêm ghi chú", expanded=False):
                st.text_input("Tiêu đề ghi chú:", key="new_note_title")
                st.text_area("Nội dung ghi chú:", key="new_note_content")
                col1, col2 = st.columns(2)
                with col1:
                    st.button("Gửi", on_click=save_note_action, use_container_width=True)
                with col2:
                    st.button("Magic 🪄", on_click=llm_note_action, use_container_width=True)
        else:
            time_until_gold = calculate_time_until_gold(card['gold_time'])
            st.markdown(f"<div class='flashcard-box'>{card['word']}<span class='gold_time'>Gold time: {time_until_gold}</span></div>", unsafe_allow_html=True)

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
        with st.container():
            st.button("📚 Bộ sưu tập", on_click=go_to_flashcard_collection, key="collection_button", help="Xem bộ sưu tập flashcard", args=None, kwargs=None, type="primary", use_container_width=False, disabled=False)
    elif st.session_state.current_page == "flashcard_collection":
        st.title("Bộ sưu tập Flashcard")

        # Nút thêm flashcard
        with st.expander("➕ Thêm Flashcard Mới"):
            st.text_input("Từ vựng:", key='new_word')
            st.text_input("Nghĩa:", key='new_meaning')
            st.text_input("Ví dụ:", key='new_example')
            st.button("Thêm Flashcard", on_click=add_flashcard)

        # Giao diện thêm Flashcard bằng AI
        with st.expander("➕ Thêm Flashcard với AI", expanded=True):
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
                llm_extract_flashcard_action()
                
            # Hiển thị danh sách các flashcard đã trích xuất nếu có
            extracted_flashcards = st.session_state.get('extracted_flashcards', [])
            if extracted_flashcards:
                st.write(extracted_flashcards)
                st.write("Chọn các flashcard bạn muốn lưu:")
                for flashcard in extracted_flashcards:
                    st.checkbox(f"{flashcard['word']} - {flashcard['meaning']} - {flashcard['example']}", key=f"select_{flashcard['word']}")
                    
                # Nút lưu các flashcard đã chọn
                if st.button("Lưu các flashcard đã chọn", on_click=save_extracted_flashcards):
                    st.session_state['extracted_flashcards'] = []  # Xóa flashcards sau khi lưu xong
                    plain_text = ""
                    
        # Hiển thị danh sách các flashcard
        for idx, card in enumerate(st.session_state.flashcards):
            icon = get_priority_icon(card['gold_time'])
            with st.expander(f"{icon} {card['word']} - {card['meaning']}", expanded=False):
                st.write(f"**Ví dụ:** {card['example']}")
                gold_time_str = card['gold_time'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(card['gold_time']) else "N/A"
                st.write(f"**Gold time:** {gold_time_str}")
                st.button("🗑️ Xóa Flashcard", key=f"delete_card_{card['id']}", on_click=lambda card_id=card['id']: delete_flashcard(card_id))

        # Nút quay lại trang flashcard_view
        st.button("🔙 Quay lại", on_click=lambda: st.session_state.update(current_page="flashcard_view"), key="back_to_view")
