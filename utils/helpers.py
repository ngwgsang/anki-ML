import re
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import os
import streamlit as st


def add_furigana(text):
    """
    Chuyển đổi văn bản có chứa kanji với furigana sang thẻ HTML `ruby`.
    Ví dụ: 漢字(かんじ) sẽ được chuyển thành <ruby>漢字<rt>かんじ</rt></ruby>.
    
    Parameters:
        text (str): Văn bản có chứa furigana.
    
    Returns:
        str: Văn bản đã được chuyển đổi sang HTML `ruby`.
    """
    furigana_pattern = r'([一-龯])\((.*?)\)|([一-龯])（(.*?)）'
    
    def replace_match(match):
        if match.group(1) and match.group(2):
            kanji = match.group(1)
            furigana = match.group(2)
        elif match.group(3) and match.group(4):
            kanji = match.group(3)
            furigana = match.group(4)
        else:
            return match.group(0)
        
        return f"<ruby>{kanji}<rt>{furigana}</rt></ruby>"

    return re.sub(furigana_pattern, replace_match, text)

def add_highlight(text, highlight_word=None):
    """
    Thêm bôi đậm vào từ khóa trong văn bản. Văn bản cũng có thể chứa các ký hiệu ** ** để đánh dấu bôi đậm.
    
    Parameters:
        text (str): Văn bản gốc.
        highlight_word (str, optional): Từ khóa cần bôi đậm.
    
    Returns:
        str: Văn bản đã được thêm bôi đậm.
    """
    bold_pattern = r'\*\*(.*?)\*\*'
    text = re.sub(bold_pattern, r'<b>\1</b>', text)
    
    if highlight_word:
        escaped_word = re.escape(highlight_word)
        text = re.sub(fr'(?<!<b>)({escaped_word})(?!<\/b>)', r'<b>\1</b>', text)
    
    return text

def calculate_time_until_gold(gold_time):
    """
    Tính thời gian còn lại cho đến thời điểm `gold_time`.
    
    Parameters:
        gold_time (datetime or pd.Timestamp): Thời gian gold_time của flashcard.
    
    Returns:
        str: Chuỗi biểu diễn thời gian còn lại (ví dụ: "2 giờ 30 phút nữa").
    """
    now = pd.Timestamp.now()
    if pd.isna(gold_time):
        return "N/A"
    
    time_diff = gold_time - now
    if time_diff.total_seconds() <= 0:
        return "Bây giờ"
    
    hours, remainder = divmod(int(time_diff.total_seconds()), 3600)
    minutes = remainder // 60
    return f"{hours} giờ {minutes} phút nữa"

def get_priority_icon(gold_time):
    """
    Xác định biểu tượng ưu tiên dựa trên thời gian `gold_time`.
    
    Parameters:
        gold_time (datetime or pd.Timestamp): Thời gian gold_time của flashcard.
    
    Returns:
        str: Biểu tượng trạng thái phù hợp.
    """
    now = pd.Timestamp.now()
    if pd.isna(gold_time):
        return "🟢"  # No gold_time set, mark as green.
    
    days_diff = (gold_time - now).total_seconds() / (3600 * 24)
    
    if days_diff < 0:
        return "🔴"  # Overdue
    elif days_diff <= 1:
        return "🟠"  # Due within a day
    elif days_diff <= 2:
        return "🔵"  # Due within 1-2 days
    else:
        return "🟢"  # Enough time remaining

def stream_data(text, delay=0.02):
    """
    Chia văn bản thành các từ và tạo luồng văn bản dần dần để hiển thị tuần tự.
    
    Parameters:
        text (str): Văn bản cần hiển thị dần dần.
        delay (float): Thời gian trễ giữa mỗi từ (tính bằng giây).
    
    Yields:
        str: Mỗi từ trong văn bản kèm khoảng trắng.
    """
    import time
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)

def load_environment_variables():
    load_dotenv()
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'GEMINI_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        st.error(f"Missing environment variables: {', '.join(missing_vars)}")
    else:
        st.session_state.SUPABASE_URL = os.getenv('SUPABASE_URL')
        st.session_state.SUPABASE_KEY = os.getenv('SUPABASE_KEY')
        st.session_state.GEMINI_KEY = os.getenv('GEMINI_KEY')
