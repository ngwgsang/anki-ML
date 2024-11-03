import joblib
import pandas as pd
from datetime import datetime, timedelta

# Tải mô hình SARIMAX đã lưu
loaded_model = joblib.load('model/sarimax_model.pkl')
print("Mô hình SARIMAX đã được tải thành công")

# Giả sử bạn có thời điểm gần nhất đã lật thẻ
# Thời điểm hiện tại bạn muốn dự đoán
last_timestamp = pd.to_datetime("2024-11-01 15:00:00")  # ví dụ thời điểm cuối cùng đã đọc thẻ
current_timestamp = pd.to_datetime(datetime.now())

days_difference = (current_timestamp - last_timestamp).days

# Giả định giá trị `point` tại thời điểm cần dự báo
# Giá trị này có thể là -1, 0 hoặc 1 dựa trên logic bạn muốn áp dụng
current_point = 0  # Thay đổi theo trạng thái hiện tại: -1, 0, hoặc 1

gold_point = current_point
if current_point > -1:
    gold_point += days_difference

# Tạo DataFrame exog cho dự báo với giá trị `point` hiện tại
exog_forecast = pd.DataFrame({"point": [gold_point]})

# Thực hiện dự báo khoảng cách ngày tiếp theo với mô hình đã tải
forecast = loaded_model.get_forecast(steps=1, exog=exog_forecast)
next_gap_days = forecast.predicted_mean.iloc[0]  # Khoảng cách ngày dự báo

# Tính toán thời điểm lật thẻ tiếp theo
next_reading_time = last_timestamp + timedelta(days=next_gap_days)
print("Dự báo thời gian lật thẻ tiếp theo:", next_reading_time)

