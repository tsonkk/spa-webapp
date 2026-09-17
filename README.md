# SPA Web App — Phân công Sinh viên – Đề tài (MILP + CPLEX)

Công cụ minh họa & kiểm chứng bốn mô hình MILP cho bài toán Student-Project
Allocation, mô phỏng quy trình 4 bước của Khoa. Chạy local bằng Streamlit,
giải bằng CPLEX (docplex).

## Quy trình 4 bước

1. **Danh sách sinh viên** — hiển thị từ sheet `Students`.
2. **Đề tài & sức chứa** — hiển thị từ sheet `Projects`.
3. **Nguyện vọng đăng ký** — hiển thị `Registrations` (+ trọng số ws, wp) và `Groups`, kèm đồ thị hai phía đầu vào.
4. **Phân công** — chọn MILP1/2/3/4 → CPLEX giải → bảng phân công, đồ thị lời giải (cạnh tô đỏ), và OBJ / UB / GAP / thời gian.

App **chỉ đọc & hiển thị** dữ liệu từ file Excel. Muốn sửa dữ liệu → sửa trong
Excel rồi nạp lại.

## Cấu trúc

```
spa_webapp/
├── core/                 # logic thuần Python, độc lập giao diện
│   ├── loader.py         # đọc Excel 4 sheet -> (S,P,E,ws,wp,c,G) + kiểm tra file
│   ├── bounds.py         # cận trên UB1..UB4
│   ├── solver.py         # dựng & giải 4 MILP bằng CPLEX + trích lời giải + đo thời gian
│   └── visualizer.py     # vẽ đồ thị hai phía (input / lời giải)
├── app.py                # giao diện Streamlit (lớp vỏ mỏng, gọi core)
├── data/                 # dữ liệu Excel
│   ├── template_spa.xlsx        # file mẫu (ví dụ 5 SV / 4 đề tài trong bài)
│   ├── C06MG01_10_7_1.xlsx      # dữ liệu thật lớp C06MG01 (10 SV / 7 ĐT)
│   └── T14MG01_35_22_5.xlsx     # dữ liệu thật lớp T14MG01 (35 SV / 22 ĐT)
└── requirements.txt
```

## Cài đặt & chạy

Yêu cầu: **Python 3.9+** và **CPLEX** (xem mục dưới).

```bash
cd spa_webapp
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Trình duyệt tự mở ở `http://localhost:8501`. Bấm **"Dùng dữ liệu mẫu"** ở thanh
bên trái để chạy thử ngay với ví dụ trong bài.

## Về CPLEX

`docplex` (trong `requirements.txt`) là lớp mô hình hóa; nó cần một **engine CPLEX**:

- **Đã cài IBM CPLEX Studio** (bản academic — như máy đã chạy thực nghiệm cho bài báo): `docplex` tự nhận, không giới hạn kích thước. **Khuyến nghị dùng cách này.**
- **Chỉ `pip install cplex`** (Community Edition): chạy được nhưng **giới hạn 1000 biến / 1000 ràng buộc**. Đủ cho các instance nhỏ (vài chục SV), nhưng **instance 100–200 SV sẽ vượt trần** → dùng bản Studio đầy đủ để tái hiện đúng kết quả bài báo.

## Định dạng file Excel

Xem sheet **"Hướng dẫn"** trong `data/template_spa.xlsx`. Tóm tắt:

| Sheet | Cột |
|---|---|
| `Students` | `student_id`*, `student_name` |
| `Projects` | `project_id`*, `project_name`, `capacity`*, `supervisor` |
| `Registrations` | `student_id`*, `project_id`*, `student_pref` (ws), `supervisor_interest` (wp) |
| `Groups` | `group_id`*, `student_id`* |

(* = bắt buộc). Quy ước trọng số: **số càng lớn = càng ưu tiên**. Nhóm nhập theo
`group_id` (mỗi thành viên một dòng); app tự bung thành các cặp cho ràng buộc
co-assignment. MILP1 chỉ cần 3 sheet đầu (2 cột của `Registrations`); MILP2 thêm
`student_pref`; MILP3 thêm `supervisor_interest`; MILP4 thêm `Groups`.
