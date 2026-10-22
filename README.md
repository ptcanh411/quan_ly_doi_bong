# Quản Lý Quỹ & Điểm Danh FC 6H Sáng Chủ Nhật

Hệ thống theo dõi quỹ, điểm danh và chia tiền sân tự động cho đội bóng FC 6H Chủ Nhật.

## ✨ Tính năng chính:
- **Bảng ma trận thông minh**: Theo dõi chi tiết từng trận đấu, tự động tính tổng nạp, tổng trừ và số dư còn lại (cảnh báo đỏ khi âm nợ, xanh khi dương quỹ).
- **Điểm danh & chia tiền sân**: Tự động chia đều tiền sân cho các thành viên có mặt, tick riêng tiền nước (+10k/người).
- **Gợi ý nạp quỹ & Tạo mã VietQR**: Các mức tiền đóng nhanh gọn gàng, tự sinh mã QR thanh toán ngân hàng chính xác.
- **Hàng đợi duyệt nạp tiền đa thiết bị**: Thành viên bấm "Báo đã chuyển khoản" từ điện thoại cá nhân -> Lưu trực tiếp vào Database máy chủ -> Thủ quỹ mở bất kỳ thiết bị nào cũng nhận được thông báo để tick duyệt tức thì.
- **Bảo mật & Phân quyền Admin**: Xác thực token an toàn qua Backend API. Mật khẩu Admin bảo vệ qua biến môi trường `ADMIN_PASSWORD` (mặc định: `ptcanh411`).
- **Sao lưu & Khôi phục (Backup / Restore)**: Cho phép Thủ quỹ tải bản sao lưu (.json) về máy tính cá nhân dự phòng và khôi phục 1-click khi cần.
- **Máy chủ đa luồng (Multi-threaded)**: Xử lý đồng thời nhiều truy cập mượt mà.

---

## 🚀 Hướng dẫn chạy cục bộ (Local / Mạng LAN):
```bash
python server.py
```
Mở trình duyệt: `http://localhost:8000` (hoặc IP mạng LAN hiển thị trên terminal để mở từ điện thoại cùng mạng WiFi).

---

## 🌐 Hướng dẫn triển khai trên PythonAnywhere:
1. **Clone repository vào PythonAnywhere**:
   Mở Bash console trên PythonAnywhere:
   ```bash
   git clone https://github.com/ptcanh411/quan_ly_doi_bong.git
   cd quan_ly_doi_bong
   ```
2. **Cấu hình Web App**:
   - Vào tab **Web** trên PythonAnywhere Dashboard -> bấm **Add a new web app** -> chọn **Manual configuration** -> chọn **Python 3.10** hoặc **3.11**.
   - **Source code**: `/home/<username>/quan_ly_doi_bong`
   - **Working directory**: `/home/<username>/quan_ly_doi_bong`
3. **Cấu hình file WSGI (WSGI configuration file)**:
   Mở file WSGI cấu hình của PythonAnywhere (`/var/www/<username>_pythonanywhere_com_wsgi.py`) và sửa nội dung thành:
   ```python
   import sys
   import os

   path = '/home/<username>/quan_ly_doi_bong'
   if path not in sys.path:
       sys.path.insert(0, path)

   from wsgi import application
   ```
4. **Bấm nút "Reload <username>.pythonanywhere.com"** và truy cập vào trang web của bạn!
