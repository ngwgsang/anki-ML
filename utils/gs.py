import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def get_all_data_from_sheet(uid, gid = 0):
    # Đường dẫn đến tệp JSON khóa xác thực
    json_keyfile = 'anki-ml.json'

    # Phạm vi (scope) của ứng dụng
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    # Tạo đối tượng xác thực từ tệp JSON khóa xác thực và phạm vi
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, scope)

    # Ấn định xác thực cho thư viện gspread
    client = gspread.authorize(creds)

    # Mở Google Sheet bằng tên
    sheet = client.open_by_key(uid)

    worksheet = sheet.get_worksheet_by_id(gid)

    # Đọc giá trị của các ô trong Google Sheet
    d = []
    for row in worksheet.get_all_values()[1:]:
        d.append(
            {
                "row_idx": row[0],
                "word": row[1],
                "meaning": row[2],
                "example": row[3], 
                "gold_time": row[4], 
            }
        )
        
    # In giá trị của các ô
    return d

#  Hàm thêm một hàng mới vào Google Sheet
def add_row_to_sheet(uid, gid, word, meaning, example):
    json_keyfile = 'client.json'
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(uid)
    worksheet = sheet.get_worksheet_by_id(gid)

    # Thêm một hàng mới với từ vựng, nghĩa, ví dụ và thời gian hiện tại
    new_row = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), word, meaning, example]
    worksheet.append_row(new_row)

# Hàm cập nhật thời gian cho hàng dựa vào từ vựng
def update_timestamp_by_row_idx(uid, gid, row_idx, timestamp):
    json_keyfile = 'client.json'
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(uid)
    worksheet = sheet.get_worksheet_by_id(gid)

    # Duyệt qua các hàng để tìm từ vựng
    cell_list = worksheet.findall(row_idx)
    for cell in cell_list:
        # Kiểm tra xem cột của từ vựng là cột 'word' hay không (cột thứ 2 trong sheet)
        if cell.col == 1:
            worksheet.update_cell(cell.row, 5, timestamp)  # Cập nhật thời gian tại cột 1
            break

