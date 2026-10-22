# AGENTS.MD - HỆ THỐNG QUẢN LÝ QUỸ, ĐIỂM DANH & LẬP LỊCH ĐỘI BÓNG (FC 6H CHỦ NHẬT)
> **Tài liệu đặc tả kỹ thuật, quy trình phát triển, nhật ký nâng cấp và hướng dẫn vận hành dành cho AI Agents / Developers tiếp nối dự án.**

---

## 1. MỤC TIÊU DỰ ÁN & CÁC YÊU CẦU NGHIỆP VỤ CỐT LÕI

Hệ thống được thiết kế theo đúng quy trình thực tế của Thủ quỹ / Đội trưởng đội bóng đá phong trào, giải quyết triệt để 8 bài toán nghiệp vụ:

1. **Quản lý Thành viên (CRUD đầy đủ)**:
   - Thêm thành viên mới (Họ tên, biệt danh, SĐT, số tiền nạp ban đầu nếu có).
   - Sửa thông tin thành viên (đổi tên, biệt danh, cập nhật số điện thoại).
   - Xóa thành viên (kèm xác nhận an toàn, kích hoạt `PRAGMA foreign_keys = ON;` tự động cascade bản ghi liên quan).
2. **Cộng tiền đóng trực tiếp theo từng trận**:
   - Thành viên nạp tiền quỹ thường đóng trực tiếp tại buổi đá bóng.
   - Thủ quỹ nhập số tiền đóng thêm của thành viên ngay tại ô của trận đó (`+50k`, `+100k`, `+200k`...).
   - Hệ thống tự động cộng dồn số tiền này vào tổng tiền đã đóng của thành viên.
3. **Tự động tính số tiền thừa/thiếu & Đổi màu trực quan (Color Coding)**:
   - Công thức: `Số dư còn lại = Tổng tiền đã đóng (ban đầu + các trận + nạp vãng lai) - Tổng tiền các trận đã tham gia`.
   - **Âm tiền (< 0đ)**: Tự động đổi màu **ĐỎ CẢNH BÁO** (`text-rose-600 bg-rose-50 border-rose-300`) để dễ thấy ai đang nợ tiền sân.
   - **Dương tiền (> 0đ)**: Màu **XANH LÁ** (`text-emerald-700 bg-emerald-50 border-emerald-300`) - còn dư quỹ.
   - **Hết tiền (= 0đ)**: Màu **XÁM TRUNG TÍNH** (`text-slate-600 bg-slate-100 border-slate-300`).
4. **Bảng ma trận & Danh sách thu/chi từng trận**:
   - Hiển thị danh sách thành viên đối soát theo từng trận: ai đi đá, trận đó chi bao nhiêu tiền, trận đó nạp thêm bao nhiêu tiền.
   - Cho phép xem nhanh toàn bộ lịch sử đóng/dùng chi tiết (sao kê cá nhân) của từng thành viên qua modal riêng.
5. **Bộ lập lịch thông minh cho các trận Chủ Nhật (Lịch Dương)**:
   - Mặc định tự động tính và gợi ý lịch các trận vào **Chủ Nhật hàng tuần** theo lịch Dương (khung giờ mặc định 6:00 - 7:30 sáng).
   - Tự động chặn không cho phép tạo 2 trận trùng ngày và giờ.
   - **Linh hoạt điều chỉnh**: Có thể dễ dàng đổi sang Thứ 7, ngày lễ hoặc đổi giờ đá bất kỳ lúc nào nếu có thay đổi đột xuất.
6. **Thống kê tức thì từng trận & Chia tiền làm tròn (Real-time Totals)**:
   - Tự động đếm chính xác **Tổng số thành viên tham gia** trận đó.
   - Tự động cộng tổng **Tiền sân/tiền trận**, tổng **Tiền nạp thu thêm tại trận**.
   - Hỗ trợ nút tự chia đều tiền sân theo số người có mặt, tự động làm tròn lên bội số gần nhất của 1.000đ để thu chi chẵn số.
7. **Tách riêng Tiền Sân & Tiền Nước (Tính năng Tick Uống Nước +10k)**:
   - Thủ quỹ nhập riêng: **Tiền Sân** (VD: 300.000đ) và **Tiền Nước**.
   - Mỗi thành viên có 2 checkbox:
     - `[x] Đi đá`: Tham gia chia đều tiền sân (VD: 15 người đá = 20k/người).
     - `[x] Uống nước`: Ai ở lại uống nước thì tick vào -> hệ thống tự động cộng thêm đúng **+10.000đ** (hoặc chỉnh đơn giá nước tùy ý) vào chi phí trận của người đó. Ai về sớm không uống thì chỉ chịu đúng tiền sân!
8. **Hàng đợi duyệt nạp tiền đa thiết bị (Server-side Approval Queue)**:
   - Thành viên nộp tiền quỹ qua quét mã VietQR ngân hàng trên điện thoại cá nhân -> bấm nút *"Tôi đã chuyển khoản - Báo cho Thủ quỹ"*.
   - Thông tin được lưu thẳng vào database máy chủ. Thủ quỹ mở bất kỳ thiết bị nào (điện thoại/máy tính) đều nhận được thông báo kèm badge số lượng để tick duyệt hoặc từ chối.

---

## 2. KIẾN TRÚC HỆ THỐNG THỰC TẾ (PRODUCTION ARCHITECTURE)

Dự án được tối ưu theo triết lý **Zero Dependency (Không phụ thuộc thư viện nặng)**, chạy trực tiếp trên Python thuần và SQLite, sẵn sàng triển khai trên **PythonAnywhere** qua giao diện WSGI:

```
fc 6h50/
├── db.py                # Schema SQLite, kết nối PRAGMA foreign_keys, hàm khởi tạo & seed dữ liệu gốc
├── server.py            # HTTP Server đa luồng (ThreadingHTTPServer) chạy cục bộ & router API RESTful
├── wsgi.py              # WSGI Entry Point (application) chuẩn cho PythonAnywhere / Gunicorn
├── fc_club.db           # SQLite Database chứa toàn bộ dữ liệu thực tế
├── seed_data.json       # Dữ liệu gốc ban đầu của 25 cầu thủ và 5 trận lịch sử (đối soát khớp 100%)
├── public/
│   ├── index.html       # Single-Page App toàn diện (Tailwind CSS, Material Symbols, JS ES6+)
│   ├── qr_code.png      # Ảnh mã QR tĩnh dự phòng
│   └── test_crop.png    # Tài nguyên ảnh
├── README.md            # Hướng dẫn cài đặt và triển khai PythonAnywhere
└── agents.md            # Tài liệu đặc tả kỹ thuật, quy trình & nhật ký nâng cấp này
```

---

## 3. THIẾT KẾ CƠ SỞ DỮ LIỆU THỰC TẾ (SQLITE SCHEMA)

Hệ thống gồm 6 bảng dữ liệu có quan hệ chặt chẽ, hỗ trợ toàn vẹn tham chiếu `FOREIGN KEY ... ON DELETE CASCADE`:

```sql
-- 1. Bảng Cầu thủ / Thành viên
CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    nickname TEXT,
    phoneNumber TEXT,
    initialDeposit REAL DEFAULT 0,
    isActive INTEGER DEFAULT 1,
    displayOrder INTEGER DEFAULT 0,
    createdAt TEXT,
    updatedAt TEXT
);

-- 2. Bảng Trận đấu
CREATE TABLE IF NOT EXISTS matches (
    id TEXT PRIMARY KEY,
    matchDate TEXT NOT NULL,
    title TEXT,
    timeSlot TEXT DEFAULT '06:00 - 07:30',
    stadiumName TEXT DEFAULT 'Sân bóng 6h50',
    pitchFee REAL DEFAULT 0,
    drinksFee REAL DEFAULT 0,
    defaultDrinkPerPerson REAL DEFAULT 10000,
    totalCost REAL DEFAULT 0,
    status TEXT DEFAULT 'SCHEDULED',
    isHidden INTEGER DEFAULT 0,
    notes TEXT,
    createdAt TEXT,
    updatedAt TEXT
);

-- 3. Chi tiết Cầu thủ trong từng Trận đấu (Mối quan hệ Nhiều - Nhiều)
CREATE TABLE IF NOT EXISTS match_player_records (
    id TEXT PRIMARY KEY,
    matchId TEXT NOT NULL,
    playerId TEXT NOT NULL,
    isPresent INTEGER DEFAULT 0,
    hasDrinks INTEGER DEFAULT 0,
    drinkAmount REAL DEFAULT 0,
    pitchShare REAL DEFAULT 0,
    feeCharged REAL DEFAULT 0,
    addedDeposit REAL DEFAULT 0,
    note TEXT,
    createdAt TEXT,
    updatedAt TEXT,
    UNIQUE(matchId, playerId),
    FOREIGN KEY(matchId) REFERENCES matches(id) ON DELETE CASCADE,
    FOREIGN KEY(playerId) REFERENCES players(id) ON DELETE CASCADE
);

-- 4. Giao dịch nạp quỹ trực tiếp / ngoài trận
CREATE TABLE IF NOT EXISTS deposit_transactions (
    id TEXT PRIMARY KEY,
    playerId TEXT NOT NULL,
    amount REAL NOT NULL,
    depositDate TEXT NOT NULL,
    note TEXT,
    createdAt TEXT,
    FOREIGN KEY(playerId) REFERENCES players(id) ON DELETE CASCADE
);

-- 5. Hàng đợi yêu cầu duyệt nạp tiền (Multi-device Queue)
CREATE TABLE IF NOT EXISTS deposit_requests (
    id TEXT PRIMARY KEY,
    playerId TEXT NOT NULL,
    amount REAL NOT NULL,
    depositDate TEXT NOT NULL,
    note TEXT,
    status TEXT DEFAULT 'PENDING', -- PENDING | APPROVED | REJECTED
    createdAt TEXT,
    reviewedAt TEXT,
    FOREIGN KEY(playerId) REFERENCES players(id) ON DELETE CASCADE
);

-- 6. Quản lý phiên đăng nhập Admin
CREATE TABLE IF NOT EXISTS admin_tokens (
    token TEXT PRIMARY KEY,
    createdAt TEXT,
    expiresAt TEXT
);

-- 7. Cấu hình CLB & Tài khoản VietQR
CREATE TABLE IF NOT EXISTS club_config (
    id TEXT PRIMARY KEY,
    clubName TEXT DEFAULT 'FC 6H SÁNG CHỦ NHẬT',
    bankCode TEXT DEFAULT '970422',
    bankAccount TEXT DEFAULT '0362226752',
    accountHolder TEXT DEFAULT 'PHAM TRONG CANH',
    defaultTimeSlot TEXT DEFAULT '06:00 - 07:30'
);
```

---

## 4. BẢNG ĐẶC TẢ RESTFUL API ENDPOINTS

Toàn bộ các endpoint can thiệp dữ liệu đều được bảo vệ bởi middleware `require_admin(self)` thông qua header `X-Admin-Token` hoặc `Authorization: Bearer <token>`.

### 4.1. Public Endpoints (Thành viên & Người dùng xem chung)
- `GET /api/players`: Danh sách thành viên kèm tổng nạp, tổng dùng, số dư tính toán động.
- `GET /api/matches`: Danh sách toàn bộ các trận đấu và thông số tổng hợp.
- `GET /api/matches/<id>`: Chi tiết điểm danh và tiền đóng của từng người trong 1 trận.
- `GET /api/deposits`: Toàn bộ lịch sử nạp quỹ công khai của câu lạc bộ.
- `GET /api/deposit-requests`: Danh sách các yêu cầu nạp tiền đang chờ duyệt.
- `POST /api/deposit-requests`: Thành viên gửi thông báo đã chuyển khoản `{ playerId, amount, note, depositDate }`.
- `GET /api/config`: Cấu hình tên đội bóng, số tài khoản, tên chủ thẻ.
- `GET /api/summary`: Thống kê tổng quan quỹ: tổng tiền đóng, tổng tiền chi, số dư hiện tại, số trận đã đá.
- `POST /api/auth/login`: Xác thực mật khẩu Admin `{ password }`, sinh token phiên 30 ngày.
- `GET /api/auth/verify`: Kiểm tra tính hợp lệ của token Admin hiện tại.

### 4.2. Admin-Protected Endpoints (Chỉ dành cho Thủ quỹ / Admin)
- `POST /api/deposit-requests/<id>/approve`: Duyệt yêu cầu nạp tiền -> Tự động ghi vào sổ quỹ và cập nhật trạng thái `APPROVED`.
- `POST /api/deposit-requests/<id>/reject`: Từ chối yêu cầu chuyển khoản không hợp lệ.
- `POST /api/players`: Thêm mới thành viên.
- `PUT /api/players/<id>`: Cập nhật thông tin thành viên.
- `DELETE /api/players/<id>`: Xóa thành viên (cascade tự động).
- `POST /api/matches`: Tạo trận đấu mới (hỗ trợ cờ `autoNextSunday`).
- `PUT /api/matches/<id>`: Cập nhật thông tin trận đấu và toàn bộ bản ghi điểm danh cầu thủ.
- `DELETE /api/matches/<id>`: Xóa trận đấu (cascade tự động).
- `POST /api/batch-save`: Lưu đồng loạt kết quả sửa đổi từ bảng ma trận máy tính.
- `PUT /api/config`: Cập nhật cấu hình CLB và tài khoản nhận tiền.
- `GET /api/backup`: Trích xuất toàn bộ dữ liệu Database thành file JSON tải về máy tính.
- `POST /api/restore`: Tải file JSON lên để ghi đè phục hồi toàn bộ cơ sở dữ liệu.
- `POST /api/reseed`: Reset cơ sở dữ liệu về dữ liệu chuẩn ban đầu.
- `POST /api/auth/logout`: Hủy token phiên đăng nhập Admin.

---

## 5. DỮ LIỆU ĐỐI SOÁT TÀI CHÍNH GỐC (SEED DATA AUDIT)

Dữ liệu gồm 25 thành viên và 5 trận đấu đã diễn ra (19/9, 27/9, 4/10, 11/10, 18/10), đã đối soát chính xác 100% tài chính:
- **Tổng tiền đóng**: `1.426.000đ`
- **Tổng tiền dùng**: `1.322.000đ`
- **Số dư hiện tại**: `+104.000đ`
- **4 thành viên âm quỹ**: Kiên bắc (-20k), Phi Đỗ (-10k), nguyên (-10k), duy (-10k).

---

## 6. NHẬT KÝ QUY TRÌNH PHÁT TRIỂN & CÁC MỐC NÂNG CẤP (CHANGELOG)

### Milestone 1: Khởi tạo & Chuyển đổi số từ Google Sheets
- Khởi tạo kiến trúc Python thuần + SQLite + Single Page App frontend.
- Nhập toàn bộ dữ liệu gốc từ `seed_data.json` khớp đúng số dư `+104.000đ`.
- Xây dựng 2 chế độ hiển thị: **Bảng Ma trận (Sheet View)** cho PC và **Thẻ Điểm danh (Card View)** cho Mobile.

### Milestone 2: Tối ưu UI/UX Mobile & Làm tròn tiền sân
- Thiết kế thanh điều hướng dưới đáy (Navbar) dạng lưới 5 cột bằng nhau (`grid grid-cols-5`), loại bỏ hoàn toàn hiện tượng thanh trượt ngang trên điện thoại màn hình nhỏ.
- Thêm sự kiện bấm vào Logo/Tên đội bóng ở Header để quay lại bảng Sổ quỹ trang chủ ngay lập tức.
- Bổ sung thuật toán làm tròn tiền sân chia đều: tự động làm tròn lên bội số gần nhất của 1.000đ (`Math.ceil(share / 1000) * 1000`).

### Milestone 3: Tối ưu các nút gợi ý nạp tiền quỹ
- Loại bỏ toàn bộ các dòng chữ phụ mờ (*"Mức 1 trận sân"*, *"1 trận Đá + Nước"*, v.v.) theo yêu cầu của Thủ quỹ.
- Chuyển 6 mức nạp (`20k`, `30k`, `50k`, `100k`, `200k`, `500k`) thành dạng nút bấm nhỏ gọn (chips/pills), vừa khít với kích thước số tiền gợi ý, giải phóng không gian màn hình điện thoại.

### Milestone 4: Code Review toàn diện & Nâng cấp bảo mật, đa thiết bị, PythonAnywhere
- **Xóa bỏ Render**: Loại bỏ file `render.yaml` thừa, tối ưu dự án 100% cho nền tảng **PythonAnywhere** qua file `wsgi.py`.
- **Hàng đợi duyệt nạp đa thiết bị**: Khắc phục triệt để lỗi lưu `localStorage`, chuyển toàn bộ thông báo chuyển khoản vào bảng `deposit_requests` trên server để Thủ quỹ mở bất kỳ thiết bị nào cũng nhận được thông báo duyệt tức thì.
- **Bảo mật Backend**: Xóa mật khẩu lộ thiên ở frontend, triển khai xác thực Token qua API `POST /api/auth/login`, bảo vệ toàn bộ API nhạy cảm bằng middleware `require_admin`.
- **Sao lưu & Khôi phục (Backup / Restore)**: Tích hợp chức năng xuất/nhập toàn bộ cơ sở dữ liệu dạng file `.json` 1-click.
- **Máy chủ đa luồng**: Nâng cấp `server.py` lên `ThreadingHTTPServer` và bật `PRAGMA foreign_keys = ON;` trong `db.py`.

---

## 7. HƯỚNG DẪN TRIỂN KHAI TRÊN PYTHONANYWHERE

1. **Clone mã nguồn vào PythonAnywhere**:
   Mở Bash Console:
   ```bash
   git clone https://github.com/ptcanh411/quan_ly_doi_bong.git
   cd quan_ly_doi_bong
   ```
2. **Cấu hình Web App trên Dashboard**:
   - Tab **Web** -> **Add a new web app** -> **Manual configuration** -> Chọn **Python 3.10** hoặc **3.11**.
   - **Source code**: `/home/<username>/quan_ly_doi_bong`
   - **Working directory**: `/home/<username>/quan_ly_doi_bong`
3. **Cấu hình file WSGI (`/var/www/<username>_pythonanywhere_com_wsgi.py`)**:
   Sửa toàn bộ nội dung file thành:
   ```python
   import sys
   import os

   path = '/home/<username>/quan_ly_doi_bong'
   if path not in sys.path:
       sys.path.insert(0, path)

   from wsgi import application
   ```
4. **Bấm "Reload"** trên giao diện PythonAnywhere để hoàn tất.

---

## 8. NGUYÊN TẮC BẢO TRÌ DÀNH CHO AI AGENTS TIẾP THEO

Khi tiếp nhận phát triển hoặc sửa đổi dự án, AI Agent cần tuân thủ nghiêm ngặt 5 nguyên tắc:

1. **Tính bất biến của công thức tài chính**: Tuyệt đối không thay đổi logic tính `TotalPaid`, `TotalUsed`, `Balance` và thuật toán làm tròn tiền sân nếu không có yêu cầu rõ ràng từ người dùng.
2. **Bảo mật API**: Bất kỳ endpoint nào làm thay đổi dữ liệu (POST, PUT, DELETE) bắt buộc phải qua hàm kiểm tra quyền Admin (`require_admin(self)`).
3. **Tính độc lập thư viện (Zero Dependencies)**: Giữ vững kiến trúc chuẩn Python standard library để đảm bảo hệ thống deploy nhẹ nhàng và chạy ổn định không lỗi version package.
4. **Tương thích kép (server.py & wsgi.py)**: Mọi endpoint mới thêm vào `server.py` phải đảm bảo tương thích hoàn toàn với lớp `WSGIResponseContext` trong `wsgi.py`.
5. **Đồng bộ đa thiết bị**: Không lưu các dữ liệu nghiệp vụ quan trọng (yêu cầu nạp tiền, điểm danh, lịch sử) vào `localStorage` của trình duyệt; luôn luôn lưu vào SQLite Database.
