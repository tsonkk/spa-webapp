# Deploy lên Streamlit Community Cloud (miễn phí)

App này chạy tốt trên **Streamlit Community Cloud** — nền tảng miễn phí, sinh ra để
chạy Streamlit (lo luôn WebSocket), deploy thẳng từ GitHub.

> **Lưu ý quan trọng về CPLEX:** host miễn phí chỉ cài được **CPLEX Community Edition**
> (qua `cplex` trong `requirements.txt`), **giới hạn 1000 biến / 1000 ràng buộc**.
> - Instance mẫu và các lớp thật cỡ vài chục sinh viên → chạy tốt.
> - Instance lớn (≈100–200 SV) có thể vượt giới hạn → app sẽ báo "Instance quá lớn cho
>   CPLEX Community", không crash. Muốn chạy instance lớn thì dùng máy có **CPLEX đầy đủ (academic)**.

## Bước 1 — Đưa code lên GitHub

Đẩy **nội dung bên trong thư mục `spa_webapp/`** lên **thư mục gốc** của một repo GitHub
(để `app.py`, `core/`, `requirements.txt`, `.streamlit/`, `template_spa.xlsx` nằm ngay gốc repo).

```bash
cd spa_webapp
git init
git add .
git commit -m "SPA web app"
git branch -M main
git remote add origin https://github.com/<tài-khoản>/<tên-repo>.git
git push -u origin main
```

Repo để **public** (tài khoản free chỉ được 1 app private; public thì không giới hạn số app).

## Bước 2 — Deploy trên Streamlit Community Cloud

1. Vào **https://share.streamlit.io** → đăng nhập bằng GitHub (cấp quyền truy cập repo).
2. Bấm **"Create app" / "New app"** → chọn **"Deploy a public app from GitHub"**.
3. Điền:
   - **Repository**: `<tài-khoản>/<tên-repo>`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Mở **"Advanced settings"** → chọn **Python version = 3.12** (bản đã kiểm chứng chạy với `cplex` community).
5. Bấm **Deploy**. Lần đầu mất vài phút để cài `cplex` + các thư viện.

Xong sẽ có link dạng `https://<tên-app>.streamlit.app`.

## Lưu ý khi dùng

- **App ngủ sau ~12 giờ không có truy cập.** Lần vào kế tiếp sẽ thấy trang "waking up" vài giây rồi tự chạy lại.
- Giới hạn free: ~1 GB RAM, không custom domain. Với công cụ minh họa này thì thoải mái.
- Cập nhật app: chỉ cần `git push`, Streamlit Cloud tự deploy lại.
- Muốn đổi dữ liệu: dùng nút **"Dùng dữ liệu mẫu"** hoặc **upload file Excel** ngay trên giao diện (không cần sửa repo).

## Nếu muốn không giới hạn kích thước về sau

Community Edition chặn ở 1000 biến/ràng buộc. Hai lối đi nếu cần instance lớn online:
- Chạy app ở máy/máy chủ có **CPLEX đầy đủ (academic)** — không giới hạn.
- Hoặc làm thêm một backend solver **mã nguồn mở** (PuLP+CBC / OR-Tools) cho bản deploy —
  core đã tách package nên thêm không khó (khác solver bài báo, cần cân nhắc cho luận văn).
