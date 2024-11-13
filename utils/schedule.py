import joblib
import streamlit as st
import pandas as pd
from datetime import timedelta, datetime


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