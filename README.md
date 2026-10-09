# DỰ ÁN QUẢN LÝ THU PHÍ CHUNG CƯ BLUE MOON (BMFM)
**Môn học:** Kỹ thuật phần mềm (KTPM 2026)  
**Nhóm thực hiện:** Nhóm 12  
**Loại ứng dụng:** Web Application (Ứng dụng Web hoạt động trên trình duyệt)

---

## 🚀 HƯỚNG DẪN KHỞI CHẠY NHANH (1-CLICK)

1. Nhấp đúp chuột vào file **`start.bat`** tại thư mục này.
2. Trình duyệt web sẽ tự động mở địa chỉ: **`http://localhost:8000`**.
3. Toàn bộ 12 Use-Case của hệ thống đã sẵn sàng với đầy đủ dữ liệu mẫu của chung cư Blue Moon.

*(Nếu dùng dòng lệnh PowerShell/CMD: Chạy lệnh `py server.py` hoặc `python server.py`)*

---

## 📁 CẤU TRÚC THƯ MỤC DỰ ÁN

```
d:/KTPM2026/
├── start.bat                  # File khởi động nhanh Web App và tự mở trình duyệt
├── server.py                  # Máy chủ Backend REST API (Python 3, SQLite3, tự động tính phí)
├── database.db                # File cơ sở dữ liệu SQLite3 chứa dữ liệu mẫu ban đầu
├── database_mysql.sql         # Script CSDL MySQL 8.0 chuẩn theo tài liệu môn học (ERD 9 bảng)
│
├── public/                    # Thư mục giao diện Web Frontend (SPA)
│   ├── index.html             # Giao diện chính đầy đủ 12 Use-Case
│   ├── css/
│   │   └── style.css          # Hệ thống thiết kế Vanilla CSS, Dark/Light theme, mẫu in laser
│   └── js/
│       ├── api.js             # Lớp giao tiếp gọi REST API backend
│       └── app.js             # Logic xử lý giao diện, chuyển tab, tính toán, in biên lai
│
└── docs/                      # Tài liệu dự án chi tiết
    ├── MO_TA_DU_AN_VA_CHUC_NANG.md  # Tài liệu miêu tả chi tiết dự án & 12 Use-Case
    └── KE_HOACH_PHAT_TRIEN_SCRUM.md # Kế hoạch phát triển 12 tuần theo mô hình Scrum
```

---

## 🎯 DANH SÁCH 12 USE-CASE ĐÃ XÂY DỰNG HOÀN CHỈNH

1. **UC01 - Đăng nhập & Xác thực:** Phân quyền theo vai trò (RBAC: Admin, Ban Quản Trị, Kế toán). Có nút chuyển đổi vai trò nhanh trên Topbar.
2. **UC02 - Quản lý Căn hộ / Hộ khẩu:** Thêm, sửa, xóa, tìm kiếm căn hộ, diện tích sàn, số phòng, tình trạng căn hộ, gán chủ hộ.
3. **UC03 - Quản lý Nhân khẩu:** Khai báo cư dân, số CCCD, ngày sinh, quan hệ với chủ hộ, số điện thoại.
4. **UC04 - Quản lý Tạm trú, Tạm vắng:** Đăng ký tạm trú / tạm vắng, thời hạn lưu trú, lý do biến động.
5. **UC05 - Quản lý Phương tiện gửi xe:** Quản lý xe máy (70.000 đ/tháng), ô tô (1.200.000 đ/tháng), biển số theo căn hộ.
6. **UC06 - Cấu hình Khoản thu & Đơn giá:** Quản lý danh mục phí bắt buộc, tự nguyện, thu hộ; đơn giá linh hoạt theo m2, theo xe, theo hộ.
7. **UC07 - Lập đợt thu phí tháng tự động:** Tự động 100% tính toán phí cho toàn bộ căn hộ trong 1 giây (hỗ trợ Change Request **CR-003** tính theo số ngày ở thực tế nếu chuyển đến giữa tháng).
8. **UC08 - Điện nước thu hộ:** Nhập số tiền hóa đơn điện, nước sinh hoạt thực tế của từng hộ.
9. **UC09 - Thu phí & In biên lai laser:** Tra cứu công nợ căn hộ, nộp tiền từng khoản hoặc toàn bộ, sinh mã phiếu thu duy nhất, xuất mẫu biên lai in laser chuẩn Quốc hiệu tiêu ngữ và dấu mộc BQT.
10. **UC10 - Thống kê & Báo cáo:** Dashboard KPI tài chính, biểu đồ doanh thu theo khoản thu, top nợ đọng, xuất báo cáo CSV và in báo cáo.
11. **UC11 - Phân quyền cán bộ:** Quản lý tài khoản cán bộ, khóa/mở khóa tài khoản.
12. **UC12 - Sao lưu & Phục hồi CSDL:** Tải bản sao lưu JSON, phục hồi CSDL khi có sự cố.
13. **UC13 - Cổng Cư Dân & Đóng Tiền Online (Mở rộng):** Chủ hộ đăng nhập xem các khoản tiền còn nợ, hạn nộp (deadline), cảnh báo quá hạn, quét mã VietQR 24/7 đóng tiền online và nhận biên lai điện tử tức thì!

---

## 👥 TÀI KHOẢN MẪU THỬ NGHIỆM

| Tên đăng nhập | Mật khẩu | Họ và tên | Vai trò | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| `admin` | `admin123` | Quản trị viên Hệ thống | `ADMIN` | Quản trị IT & CSDL |
| `bqt_truongban` | `bqt123` | Trưởng Ban Quản Trị | `BAN_QUAN_TRI` | Quản lý chung cư |
| `ketoan_minh` | `ketoan123` | Kế toán Nguyễn Hồng Minh | `KE_TOAN` | Thu ngân, lập đợt thu |
| `cudan_a1205` | `123456` | Nguyễn Văn An | `CU_DAN` | **Chủ hộ A1205 (Đóng VietQR)** |
| `cudan_b0402` | `123456` | Phạm Quỳnh Nga | `CU_DAN` | **Chủ hộ B0402 (Đóng VietQR)** |
| `cudan_b0403` | `123456` | Vũ Đức Thành | `CU_DAN` | **Chủ hộ B0403 (CR-003)** |

*(Bạn cũng có thể chuyển đổi nhanh 4 vai trò ngay trên thanh công cụ Topbar mà không cần đăng nhập lại!)*
