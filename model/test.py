import joblib
import pandas as pd
from datetime import timedelta

# Tải mô hình ARIMA đã lưu
loaded_model = joblib.load('model/arima.pkl')
print("Mô hình đã được tải thành công")

# Giả sử bạn có thời điểm gần nhất đã lật thẻ
# Thời điểm hiện tại bạn muốn dự đoán
last_timestamp = pd.to_datetime("2024-11-01 15:00:00")  # ví dụ thời điểm cuối cùng đã đọc thẻ

# Dự báo khoảng cách ngày tiếp theo với mô hình đã tải
forecast = loaded_model.forecast(steps=1)
next_gap_days = forecast.iloc[0]  # Khoảng cách ngày dự báo

# Tính toán thời điểm lật thẻ tiếp theo
next_reading_time = last_timestamp + timedelta(days=next_gap_days)
print("Dự báo thời gian lật thẻ tiếp theo:", next_reading_time)
