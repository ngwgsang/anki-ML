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
import re


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
    else:
        gold_point -= round(days_difference / 3)
        
    exog_forecast = pd.DataFrame({"point": [gold_point]})
    forecast = model.get_forecast(steps=1, exog=exog_forecast)
    next_gap_days = forecast.predicted_mean.iloc[0]
    
    return last_timestamp + timedelta(days=next_gap_days)

# Function to convert kanji with furigana (e.g., 漢字(かんじ)) to HTML ruby tags
def add_furigana(text):
    # Pattern to match kanji followed by furigana in either standard parentheses () or full-width parentheses （）
    furigana_pattern = r'([一-龯])\((.*?)\)|([一-龯])（(.*?)）'
    
    # Substitute kanji-furigana pairs with ruby tags
    def replace_match(match):
        # If the match uses standard parentheses
        if match.group(1) and match.group(2):
            kanji = match.group(1)
            furigana = match.group(2)
        # If the match uses full-width parentheses
        elif match.group(3) and match.group(4):
            kanji = match.group(3)
            furigana = match.group(4)
        else:
            return match.group(0)  # If no match, return as is
        
        return f"<ruby>{kanji}<rt>{furigana}</rt></ruby>"

    # Use the replace function for all matches in the text
    return re.sub(furigana_pattern, replace_match, text)

def add_highlight(text, highlight_word=None):
    
    bold_pattern = r'\*\*(.*?)\*\*'
    text = re.sub(bold_pattern, r'<b>\1</b>', text)
    
    if highlight_word:
        # Escape `highlight_word` for regex in case it contains special characters
        escaped_word = re.escape(highlight_word)
        # Only highlight if not already in bold
        text = re.sub(fr'(?<!<b>)({escaped_word})(?!<\/b>)', r'<b>\1</b>', text)
    
    return text

# Hàm chuyển đến trang thống kê
def go_to_statistics_page():
    st.session_state.current_page = "statistics"

# Hàm tải tất cả các ghi chú từ Supabase
def load_all_notes():
    try:
        data = supabase.table('notes').select('*').execute()
        notes = data.data if data.data else []
        return notes
    except Exception as e:
        st.error(f"Lỗi khi lấy dữ liệu ghi chú từ Supabase: {e}")
        return []

def load_study_progress():
    try:
        response = supabase.table('study_progress').select('*').order('date').execute()
        study_progress = response.data if response.data else []
        return pd.DataFrame(study_progress)
    except Exception as e:
        st.error(f"Error fetching study progress data: {e}")
        return pd.DataFrame()

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
    # prompt = (
    #     "You are a helpful assistant designed to create concise and informative notes for language flashcards.\n"
    #     "For each flashcard, you will receive a word and its meaning.\n"
    #     "Your task is to generate a brief note that helps the user remember the word and how to use it in context.\n"
    #     "Focus on practical usage and examples when possible.\n"
    #     "Make sure your notes are clear and easy to understand.\n"
    #     "CURRENT FLASHCARD INFO\n"
    #     f"WORD: {card['word']}\n"
    #     f"MEANING: {card['meaning']}\n"
    #     f"EXAMPLE: {card['example']}\n"
    #     f"TASK: {st.session_state.new_note_content}\n"
    #     f"Generate a note based on this info I provided, language must be Vietnamese"
    # )
    prompt = (
        "Bạn là một trợ lý hữu ích, được thiết kế để tạo các ghi chú ngắn gọn và dễ hiểu cho flashcard học ngôn ngữ.\n"
        "Với mỗi flashcard, bạn sẽ nhận được một từ và nghĩa của từ đó.\n"
        "Nhiệm vụ của bạn là tạo một ghi chú ngắn giúp người dùng ghi nhớ từ và cách sử dụng từ đó trong ngữ cảnh thực tế.\n"
        "Tập trung vào các ví dụ sử dụng từ trong thực tế để người học dễ dàng áp dụng.\n"
        "Đảm bảo rằng các ghi chú của bạn rõ ràng, dễ hiểu, và viết bằng tiếng Việt.\n\n"
        "Đối với cách đọc thì hãy dùng hiragana để thể hiện, không được sử dụng romanji hay Tiếng Việt.\n\n"
        "### THÔNG TIN HIỆN TẠI CỦA FLASHCARD\n"
        f"- **Từ:** {card['word']}\n"
        f"- **Nghĩa:** {card['meaning']}\n"
        f"- **Ví dụ:** {card['example']}\n\n"
        "### NHIỆM VỤ\n"
        f"- **Yêu cầu:** {st.session_state.new_note_content}\n"
        "Hãy tạo ghi chú ngắn gọn (không được lặp lại thông tin trên), và trình bày dưới dạng markdown bằng tiếng Việt."
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
            "N1: Advanced level, includes complex vocabulary often used in professional or academic contexts.\n"
            "N2: Upper-intermediate level, with vocabulary frequently used in business or media.\n"
            "N3: Intermediate level, covering vocabulary needed for daily life and workplace interactions.\n"
            "N4: Basic level, with words for everyday conversation and simple reading materials.\n"
            "N5: Beginner level, covering fundamental vocabulary for simple communication.\n"

            "Use this JSON schema:\n"
            "Flashcard = {'word': str, 'meaning': str, 'example': str}\n"
            "Return: list[Flashcard]\n",
            f"Generate some flashcard at level {level} from the TEXT i provided\n",
            f"\n\nTEXT: {plain_text}"
            "For each flashcard, you will receive a word in Japanese and its meaning in Vietnamese.\n"
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

def save_edit_flashcard_action(card_id):
    updated_word = st.session_state.get(f"edit_word_{card_id}", "").strip()
    updated_meaning = st.session_state.get(f"edit_meaning_{card_id}", "").strip()
    updated_example = st.session_state.get(f"edit_example_{card_id}", "").strip()
    if updated_word and updated_meaning and updated_example:
        try:
            supabase.table('flashcards').update({
                "word": updated_word,
                "meaning": updated_meaning,
                "example": updated_example
            }).eq('id', card_id).execute()
            st.session_state.flashcard_edit_mode[card_id] = False  # Thoát chế độ chỉnh sửa
            st.session_state.flashcards = load_flashcards()  # Làm mới danh sách flashcards
            st.toast(f"Flashcard '{updated_word}' đã được cập nhật.", icon='✅')
        except Exception as e:
            st.error(f"Lỗi khi cập nhật flashcard trong Supabase: {e}")
    else:
        st.warning("Từ vựng, nghĩa và ví dụ không được để trống.")

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
        # Xóa flashcard từ bảng 'flashcards'
        supabase.table('flashcards').delete().eq('id', card_id).execute()
        
        # Xóa các ghi chú liên quan từ bảng 'notes'
        supabase.table('notes').delete().eq('flashcard_id', card_id).execute()
        
        st.toast("Xóa thành công.", icon='🎉')
        # Cập nhật danh sách flashcards
        st.session_state.flashcards = load_flashcards()
    except Exception as e:
        st.error(f"Lỗi khi xóa flashcard hoặc ghi chú từ Supabase: {e}")
        
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
    if "flashcard_edit_mode" not in st.session_state:
        st.session_state.flashcard_edit_mode = {}
    if "feedback_list" not in st.session_state:
        st.session_state.feedback_list = []

    # Tải mô hình SARIMAX từ file
    model = load_sarimax_model()

    # Cập nhật `gold_time` trong Supabase
    def update_timestamp_by_id(card_id, gold_time):
        try:
            supabase.table('flashcards').update({'gold_time': gold_time.strftime('%Y-%m-%d %H:%M:%S')}).eq('id', card_id).execute()
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
        if model:
            gold_time = predict_next_gold_time(model, last_timestamp, feedback_value)
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
                    # supabase.table('flashcards').update({'gold_time': gold_time.strftime('%Y-%m-%d %H:%M:%S')}).eq('id', card_id).execute()
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
                today_str = datetime.now().strftime('%Y-%m-%d')
                time.sleep(0.5)  # Simulate update delay
                # Replace this section with your Supabase update code
                response = supabase.table('study_progress').select('*').eq('date', today_str).execute()
                if response.data:
                    existing_progress = response.data[0]
                    supabase.table('study_progress').update({
                        "good_count": existing_progress["good_count"] + study_progress['good_count'],
                        "normal_count": existing_progress["normal_count"] + study_progress['normal_count'],
                        "bad_count": existing_progress["bad_count"] + study_progress['bad_count']
                    }).eq('date', today_str).execute()
                else:
                    new_entry = {
                        "date": today_str,
                        "good_count": study_progress['good_count'],
                        "normal_count": study_progress['normal_count'],
                        "bad_count": study_progress['bad_count']
                    }
                    supabase.table('study_progress').insert(new_entry).execute()
            except Exception as e:
                st.error(f"Lỗi khi cập nhật tiến độ học: {e}")

            # Final update for the progress bar
            progress_bar.progress(100)
            status_label.text("Hoàn tất đồng bộ.")

        # Clear the feedback list after synchronization
        st.session_state.feedback_list = []

        # Reload flashcards to update changes
        st.session_state.flashcards = load_flashcards()  # Uncomment to reload flashcards if needed


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
            example_text = add_highlight(add_furigana(card['example']), card['word'])
            st.markdown(f"""<div class='flashcard-box'>{add_furigana(card['word'])}<br>{card['meaning']}<br>{example_text}</div>""", unsafe_allow_html=True)
            
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
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                st.button("📚 Bộ sưu tập", on_click=go_to_flashcard_collection, key="collection_button", help="Xem bộ sưu tập flashcard", type="primary", use_container_width=True)
            with col2:
                st.button("📊 Thống kê", on_click=go_to_statistics_page, key="statistics_button", help="Xem thống kê", type="primary", use_container_width=True)
            with col3:
                st.button("🔄 Đồng bộ", on_click=sync_data, key="sync_button", help="Đồng bộ dữ liệu với cơ sở dữ liệu", type="primary", use_container_width=True)

            
    elif st.session_state.current_page == "flashcard_collection":
        st.button("🔙 Quay lại", on_click=lambda: st.session_state.update(current_page="flashcard_view"), key="back_to_view")
        st.title("Bộ sưu tập thẻ")

        # Nút thêm flashcard
        with st.expander("➕ Thêm Flashcard Mới"):
            st.text_input("Từ vựng:", key='new_word')
            st.text_input("Nghĩa:", key='new_meaning')
            st.text_input("Ví dụ:", key='new_example')
            st.button("Thêm Flashcard", on_click=add_flashcard)

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
                    # Hiển thị thông tin flashcard
                    st.write(f"**Ví dụ:** {card['example']}")
                    gold_time_str = card['gold_time'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(card['gold_time']) else "N/A"
                    st.write(f"**Gold time:** {gold_time_str}")
                    col_edit, col_delete = st.columns([1, 1])
                    with col_edit:
                        st.button("Chỉnh sửa", key=f"edit_card_{card['id']}", on_click=lambda card_id=card['id']: st.session_state.flashcard_edit_mode.update({card_id: True}), use_container_width=True)
                    with col_delete:
                        st.button("🗑️ Xóa Flashcard", key=f"delete_card_{card['id']}", on_click=lambda card_id=card['id']: delete_flashcard(card_id), use_container_width=True)

        # Nút quay lại trang flashcard_view
        st.button("🔙 Quay lại", on_click=lambda: st.session_state.update(current_page="flashcard_view"), key="back_to_view2")
    
    elif st.session_state.current_page == "statistics":
        st.button("🔙 Quay lại", on_click=lambda: st.session_state.update(current_page="flashcard_view"), key="back_to_view")
        st.title("📊 Thống kê")
        # Create two columns for the cards
        col1, col2 = st.columns(2)

        # Card 1: Total Flashcards
        total_flashcards = len(st.session_state.flashcards)
        with col1:
            st.button(
                f"{total_flashcards} thẻ",
                type="primary",
                use_container_width=True,
                disabled=True,
            )

        # Card 2: Total Notes
        all_notes = load_all_notes()
        total_notes = len(all_notes)
        with col2:
            st.button(
                f"{total_notes} ghi chú",
                type="primary",
                use_container_width=True,
                disabled=True,
            )

        
        st.divider()
        # Load study progress data
        study_progress_df = load_study_progress()
                
        if not study_progress_df.empty:
            st.markdown("### Tiến Độ Học Tập")

            # Convert 'date' column to datetime and set it as the index
            study_progress_df['date'] = pd.to_datetime(study_progress_df['date'])
            study_progress_df = study_progress_df.set_index('date')
            
            # Drop the 'id' column if it exists
            study_progress_df = study_progress_df.drop(columns=['id'], errors='ignore')

            # Rename columns to desired labels
            study_progress_df = study_progress_df.rename(columns={
                'good_count': 'Quá dễ 😎',
                'normal_count': 'Hông chắc 🤔',
                'bad_count': 'Cái qq j z😱'
            })

            # Plot the renamed DataFrame with Streamlit's line chart
            st.line_chart(study_progress_df, color=["#73EC8B", "#FF6600", "#FF4545"])


        st.divider()
        # 1. Biểu đồ phân phối các flashcard theo trạng thái Gold Time
        st.markdown("### Phân phối thẻ")

        # Define a dictionary to count each status
        status_counts = {'🔴': 0, '🟠': 0, '🔵': 0, '🟢': 0}

        # Calculate the status counts by using get_priority_icon function
        for card in st.session_state.flashcards:
            icon = get_priority_icon(card['gold_time'])
            status_counts[icon] += 1

        # Map icons to meaningful labels for the chart
        status_labels = {
            '🔴': 'Quá hạn',
            '🟠': 'Sắp đến hạn',
            '🔵': 'Còn 1-2 ngày',
            '🟢': 'Còn thời gian'
        }

        # Convert counts to a DataFrame for visualization
        status_df = pd.DataFrame({
            'Trạng thái': [status_labels[icon] for icon in status_counts],
            'Số lượng': list(status_counts.values())
        }).set_index('Trạng thái')

        # Display the bar chart
        st.bar_chart(status_df)

        # 2. Biểu đồ số lượng ghi chú trên mỗi flashcard
        st.divider()
        st.markdown("### Số lượng Ghi chú")
        note_counts = {}
        for note in all_notes:
            flashcard_id = note['flashcard_id']
            note_counts[flashcard_id] = note_counts.get(flashcard_id, 0) + 1

        flashcard_ids = [card['id'] for card in st.session_state.flashcards]
        counts = [note_counts.get(flashcard_id, 0) for flashcard_id in flashcard_ids]
        words = [card['word'] for card in st.session_state.flashcards]

        # Tạo DataFrame cho biểu đồ
        note_counts_df = pd.DataFrame({
            'Flashcard': words,
            'Số lượng Ghi chú': counts
        })
        note_counts_df.set_index('Flashcard', inplace=True)

        # Hiển thị biểu đồ cột
        st.bar_chart(note_counts_df.head(20), horizontal=True)

        # Nút quay lại trang flashcard_view
        st.button("🔙 Quay lại", on_click=lambda: st.session_state.update(current_page="flashcard_view"), key="back_to_view_statistics")
