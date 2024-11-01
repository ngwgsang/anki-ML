import pandas as pd
import numpy as np
from datetime import timedelta
from sklearn.metrics import mean_squared_error, mean_absolute_error
from statsmodels.tsa.arima.model import ARIMA
import matplotlib.pyplot as plt
import joblib
# Số lượng mẫu cần tạo
num_samples = 100

# Tạo danh sách các thời điểm luyện tập (giả lập) với độ trễ ngẫu nhiên
start_date = pd.to_datetime("2023-01-01 08:00:00")
timestamps = [start_date]

# Giả lập khoảng cách giữa các lần luyện tập từ 1-5 ngày với độ ngẫu nhiên
for i in range(1, num_samples):
    days_gap = np.random.randint(1, 6)  # khoảng cách ngẫu nhiên từ 1 đến 5 ngày
    next_time = timestamps[-1] + timedelta(days=days_gap)
    timestamps.append(next_time)

# Tạo DataFrame với dữ liệu thời gian
df = pd.DataFrame({"timestamp": timestamps})

# Tính khoảng cách giữa các lần luyện tập và chuyển đổi thành ngày
df["days_since_last_read"] = df["timestamp"].diff().dt.total_seconds() / (60 * 60 * 24)
df.dropna(inplace=True)  # Bỏ giá trị NaN ở hàng đầu tiên




# Huấn luyện mô hình ARIMA
model = ARIMA(df["days_since_last_read"], order=(1, 1, 1))  # Điều chỉnh (p, d, q) nếu cần thiết
model_fit = model.fit()

# Hiển thị kết quả dự báo trên toàn bộ tập dữ liệu
df["predicted_days_gap"] = model_fit.predict(start=1, end=len(df))

# # Vẽ biểu đồ để quan sát dự báo
# plt.figure(figsize=(12, 6))
# plt.plot(df["days_since_last_read"], label="Actual Days Gap")
# plt.plot(df["predicted_days_gap"], label="Predicted Days Gap", linestyle="--")
# plt.legend()
# plt.xlabel("Sample Index")
# plt.ylabel("Days Gap")
# plt.title("Actual vs. Predicted Days Gap between Practice Sessions")
# plt.show()

# Tính toán lỗi MSE và MAE
mse = mean_squared_error(df["days_since_last_read"][1:], df["predicted_days_gap"][1:])
mae = mean_absolute_error(df["days_since_last_read"][1:], df["predicted_days_gap"][1:])

print("Mean Squared Error (MSE):", mse)
print("Mean Absolute Error (MAE):", mae)

# Lưu mô hình đã huấn luyện
joblib.dump(model_fit, 'arima_model.pkl')
print("Mô hình đã được lưu vào file 'arima_model.pkl'")

