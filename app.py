import streamlit as st
import json
from utils.gs import get_all_data_from_sheet, update_timestamp_by_row_idx
import random
import pandas as pd
from datetime import datetime, timedelta
import joblib

flashcards = []

# Kiểm tra nếu chưa có 'uid' và 'gid' trong session_state
if "uid" not in st.session_state or "gid" not in st.session_state:
    st.sidebar.header("Upload JSON Config")
    uploaded_file = st.sidebar.file_uploader("Please upload a JSON file with 'uid' and 'gid'", type="json")
    
    # Xử lý file JSON đã tải lên
    if uploaded_file is not None:
        config = json.load(uploaded_file)
        st.session_state.uid = config.get("uid")
        st.session_state.gid = config.get("gid")

        # Lấy dữ liệu từ Google Sheet và lưu vào session_state
        if st.session_state.uid and st.session_state.gid is not None:
            flashcards = get_all_data_from_sheet(uid=st.session_state.uid, gid=st.session_state.gid)
            
            # Chuyển đổi cột `gold_time` về định dạng ngày nếu chưa có
            for card in flashcards:
                card['gold_time'] = pd.to_datetime(card.get('gold_time', '1900-01-01'), errors='coerce')

            # Sắp xếp thẻ dựa trên yêu cầu:
            today = pd.Timestamp.now()
            flashcards.sort(
                key=lambda x: (
                    (x['gold_time'] - today).days if x['gold_time'] < today else float('inf'),  # gold_time gần nhất đã vượt qua
                    x['gold_time'] if x['gold_time'] >= today else float('inf'),  # gold_time sắp đến hạn
                    -x['gold_time'].toordinal() if pd.notna(x['gold_time']) else 0  # gold_time xa nhất
                )
            )
            st.session_state.flashcards = flashcards
        else:
            st.error("JSON file does not contain 'uid' or 'gid'. Please upload a valid JSON file.")
else:
    # Nếu dữ liệu đã được tải lên và có trong session_state
    flashcards = st.session_state.get("flashcards", [])

# Tải mô hình ARIMA đã lưu
def load_arima_model():
    try:
        model = joblib.load("model/arima.pkl")
        return model
    except FileNotFoundError:
        st.error("Model file not found. Please ensure the model file exists.")
        return None

# Hàm dự báo thời gian luyện tập tiếp theo
def predict_next_gold_time(model, last_timestamp):
    forecast = model.forecast(steps=1)
    next_gap_days = forecast.iloc[0]  # Khoảng cách ngày dự báo
    return last_timestamp + timedelta(days=next_gap_days)

# Nếu flashcards có dữ liệu, tiếp tục hiển thị thẻ
if flashcards:
    # Khởi tạo trạng thái của thẻ
    if "index" not in st.session_state:
        st.session_state.index = 0
    if "show_back" not in st.session_state:
        st.session_state.show_back = False

    # Tải mô hình ARIMA từ file
    model = load_arima_model()

    # Hàm để lật thẻ (mặt trước -> mặt sau)
    def flip_card():
        if not st.session_state.show_back:
            st.session_state.show_back = True
        else:
            # Lấy thời gian hiện tại
            current_time = pd.Timestamp.now()
            
            # Dự đoán thời gian luyện tập tiếp theo nếu có model
            if model:
                gold_time = predict_next_gold_time(model, current_time)
            else:
                gold_time = current_time + timedelta(days=2)  # Giả định nếu không có mô hình

            # Cập nhật thời gian lật trong Google Sheet
            update_timestamp_by_row_idx(
                uid=st.session_state.uid, 
                gid=st.session_state.gid, 
                row_idx= flashcards[st.session_state.index]["row_idx"],
                timestamp= gold_time.strftime('%Y-%m-%d %H:%M:%S')
            )
            next_card()
        
    # Hàm để lấy thẻ tiếp theo
    def next_card():
        st.session_state.index = (st.session_state.index + 1) % len(flashcards)
        st.session_state.show_back = False

    # Hàm để lấy thẻ trước đó
    def prev_card():
        st.session_state.index = (st.session_state.index - 1) % len(flashcards)
        st.session_state.show_back = False

    # Lấy thẻ hiện tại dựa vào chỉ số
    card = flashcards[st.session_state.index]

    # Tùy chỉnh CSS cho hộp thẻ
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
        b{
            color: red;
        }
        .gold_time{
            position: absolute;
            right: 20px;
            bottom: 10px;
            font-size: 14px;
        }
        </style>
        """, unsafe_allow_html=True
    )

    # Hiển thị mặt trước hoặc mặt sau của thẻ dựa vào trạng thái
    if st.session_state.show_back:
        example_text = card['example'].replace('"', '<b>', 1).replace('"', '</b>', 1)
        st.markdown(f"""<div class='flashcard-box'>{card['word']}<br>{card['meaning']}<br>{example_text}</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='flashcard-box'>{card['word']}<span class='gold_time'>gold time: {card['gold_time']}</span></div>", unsafe_allow_html=True)

    # Hiển thị các nút trong container ngang hàng
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("⬅️ Back", on_click=prev_card, use_container_width=True)
        with col2:
            st.button("🔥 Flip", on_click=flip_card, use_container_width=True)
        with col3:
            st.button("➡️ Next", on_click=next_card, use_container_width=True)

else:
    # Thông báo yêu cầu người dùng tải lên file JSON nếu chưa có dữ liệu
    st.warning("Please upload a JSON file with 'uid' and 'gid' in the sidebar to load flashcards.")
