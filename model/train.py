import pandas as pd
from datetime import timedelta
from sklearn.metrics import mean_absolute_error
from statsmodels.tsa.statespace.sarimax import SARIMAX
import matplotlib.pyplot as plt
import joblib

# Số lượng mẫu cần tạo
num_samples = 200

# Tạo dữ liệu timestamp và days_since_last_read theo quy tắc
start_date = pd.to_datetime("2023-01-01 08:00:00")
timestamps = [start_date]

# Tạo dữ liệu days_since_last_read dựa trên logic mới
days_gaps = []
points = []
gap_value = 0  # Biến để theo dõi khoảng cách ôn tập hiện tại

for i in range(num_samples):
    if i < num_samples // 3:
        # -1: Đang quên, bắt đầu với 1 giờ (1/24 ngày), tăng dần
        gap_value = 2 / 24 + (i % 3) * (1 / 36)  # Tăng theo giờ
        points.append(-1)
    elif i < 2 * num_samples // 3:
        gap_value = 1 + (i % 3)  # Tăng dần lên từ 2 ngày
        points.append(0)
    else:
        # 1: Nhớ rõ, bắt đầu với 2 ngày, tăng lên 4 ngày và tăng dần
        gap_value = 2 * (1 + (i % 3))  # Tăng lên theo bội số 2 ngày
        points.append(1)
    
    # Lưu khoảng cách vào danh sách
    days_gaps.append(gap_value)
    # Tạo mốc thời gian tiếp theo
    timestamps.append(timestamps[-1] + timedelta(days=gap_value))

# Tạo DataFrame với dữ liệu
df = pd.DataFrame({
    "timestamp": timestamps[1:],  # Bỏ phần tử đầu tiên (không có khoảng cách)
    "days_since_last_read": days_gaps,
    "point": points
})

# Huấn luyện mô hình SARIMAX với `days_since_last_read` là biến mục tiêu và `point` là đặc trưng
model = SARIMAX(df["days_since_last_read"], exog=df[["point"]], order=(1, 1, 1))
model_fit = model.fit(disp=False)

# Dự báo trong mẫu với `exog` có cùng số lượng hàng
df["predicted_days_gap"] = model_fit.predict(start=1, end=len(df)-1, exog=df[["point"]][1:len(df)])

# Vẽ biểu đồ để quan sát dự báo
plt.figure(figsize=(12, 6))
plt.plot(df["days_since_last_read"], label="Actual Days Gap")
plt.plot(df["predicted_days_gap"], label="Predicted Days Gap", linestyle="--")
plt.legend()
plt.xlabel("Sample Index")
plt.ylabel("Days Gap")
plt.title("Actual vs. Predicted Days Gap between Practice Sessions")
plt.show()

# Tính toán lỗi MAE
# Bỏ qua giá trị đầu tiên vì nó không có giá trị dự báo
actual = df["days_since_last_read"][1:]
predicted = df["predicted_days_gap"][1:]
mae = mean_absolute_error(actual, predicted)

print("Mean Absolute Error (MAE):", mae)

# Lưu mô hình đã huấn luyện
joblib.dump(model_fit, 'model/sarimax_model.pkl')
print("Mô hình đã được lưu vào file 'model/sarimax_model.pkl'")
