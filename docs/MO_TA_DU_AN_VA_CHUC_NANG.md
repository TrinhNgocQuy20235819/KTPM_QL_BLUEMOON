# TÀI LIỆU MIÊU TẢ DỰ ÁN VÀ ĐẶC TẢ CHỨC NĂNG HỆ THỐNG
# HỆ THỐNG QUẢN LÝ THU PHÍ CHUNG CƯ BLUE MOON (BMFM)

**Tên dự án:** Phần mềm quản lý thu phí chung cư Blue Moon  
**Tên viết tắt:** BMFM (BlueMoon Fee Management)  
**Nền tảng triển khai:** Ứng dụng Web (Web Application), hoạt động trên trình duyệt máy tính và thiết bị di động  
**Đơn vị thực hiện:** Nhóm 12 – Môn Kỹ thuật phần mềm (KTPM 2026)  
**Nhà tài trợ / Khách hàng:** Ban Quản Trị chung cư Blue Moon  

---

## I. TỔNG QUAN VỀ DỰ ÁN (PROJECT OVERVIEW)

### 1. Hoàn cảnh ra đời
Chung cư Blue Moon có quy mô căn hộ lớn với mật độ dân cư cao. Trước khi triển khai dự án BMFM, công tác quản lý hoàn toàn phụ thuộc vào sổ sách chép tay và các tệp bảng tính Microsoft Excel rời rạc:
- Kế toán phải tự nhân thủ công diện tích từng căn hộ với đơn giá dịch vụ và đếm số lượng xe máy, ô tô của từng hộ để tính tiền.
- Viết biên lai tay từng tờ, đối soát sổ sách cuối tháng mất từ 3 đến 5 ngày.
- Thường xuyên xảy ra sai sót: nhầm lẫn diện tích phòng, bỏ sót số lượng xe gửi phát sinh, khó khăn khi đối soát công nợ cũ của các tháng trước.
- Thiếu tính minh bạch đối với các khoản quỹ xã hội, quỹ khuyến học, từ thiện do cư dân tự nguyện đóng góp.

### 2. Mục tiêu chiến lược của dự án
1. **Tin học hóa toàn diện:** Tự động hóa 100% quy trình từ khai báo danh mục định mức, sinh kỳ hóa đơn hàng tháng, đối soát phiếu thu đến trích xuất sổ phụ công nợ.
2. **Tối ưu hóa năng suất:** Giảm thời gian lập bảng kê nộp phí hàng tháng của toàn bộ chung cư từ **3 ngày xuống dưới 5 giây** nhờ thuật toán tự động tính toán. Loại bỏ hoàn toàn sai sót tính toán số liệu thủ công.
3. **Minh bạch hóa dòng tiền:** Cung cấp bảng tra cứu trực quan công nợ theo từng căn hộ, xuất báo cáo tổng hợp thu nộp định kỳ phục vụ cư dân và Ban Quản Trị giám sát.
4. **Chuẩn hóa dữ liệu dân cư:** Thiết lập cơ sở dữ liệu định danh duy nhất, liên kết chặt chẽ giữa nhân khẩu, diện tích căn hộ và số lượng phương tiện sở hữu.

---

## II. KIẾN TRÚC VÀ CÔNG NGHỆ CỦA HỆ THỐNG WEB

Hệ thống được thiết kế theo mô hình **Web Application hiện đại (Single Page Application - SPA)**, tối ưu hóa tốc độ tải trang, trải nghiệm mượt mà và khả năng in ấn biên lai trực tiếp từ trình duyệt web:

```
[ Trình duyệt Web (Client Browser) ]
  ├── index.html (Cấu trúc Semantic HTML5, 12 Phân hệ Use-Case)
  ├── css/style.css (Hệ thống thiết kế Vanilla CSS, Glassmorphism, Print Stylesheet)
  ├── js/app.js (Logic ứng dụng, chuyển tab, Modal, Render dữ liệu, Chart.js)
  └── js/api.js (Lớp giao tiếp REST API chuẩn Async/Await)
                  │
             HTTP / JSON
                  ▼
[ Máy chủ Web Backend (server.py) ]
  ├── HTTP Request Handler (Routing, CORS, JSON Response)
  ├── Logic Engine (Tự động tính phí m2, xe cộ, áp dụng CR-003 tính theo ngày)
  └── Role-based Access Control (RBAC: Admin, Ban Quản Trị, Kế Toán)
                  │
              SQL Query
                  ▼
[ Cơ sở dữ liệu quan hệ (Database) ]
  ├── database.db (SQLite3 tích hợp sẵn, khởi chạy tức thì 0-dependency)
  └── database_mysql.sql (Kịch bản khởi tạo MySQL 8.0 chuẩn đồ án KTPM)
```

### Ưu điểm nổi bật của kiến trúc:
- **Chạy trực tiếp 1-click:** Không cần cài đặt các phần mềm phức tạp như XAMPP, Docker hay Node.js. Chỉ cần chạy file `start.bat` là hệ thống Web tự động khởi động và mở trên trình duyệt.
- **Không phải App cài đặt:** Người dùng và cán bộ chỉ cần truy cập qua địa chỉ Web `http://localhost:8000` trên máy tính hoặc tablet tại văn phòng ban quản trị.
- **Hỗ trợ in ấn chuyên dụng (Laser Printing):** Tích hợp mẫu in biên lai chuẩn có Quốc hiệu, tiêu ngữ, chữ ký và số tiền bằng chữ tiếng Việt, tự động căn chỉnh khổ giấy in A4/A5 khi bấm lệnh In.

---

## III. CHI TIẾT 12 CHỨC NĂNG NGHIỆP VỤ (USE-CASE SPECIFICATIONS)

### UC01: Đăng nhập & Xác thực hệ thống
- **Tác nhân:** Tất cả người dùng (Admin, Ban Quản Trị, Kế toán).
- **Mô tả:** Xác thực tài khoản cán bộ qua tên đăng nhập và mật khẩu; quản lý phiên làm việc; hiển thị thông tin và chức vụ trên thanh điều hướng.
- **Phân quyền (RBAC):**
  - **Quản trị viên (Admin):** Toàn quyền cấu hình tài khoản cán bộ, sao lưu và phục hồi CSDL.
  - **Ban Quản Trị (BQT):** Quản lý căn hộ, cư dân, xe cộ, cấu hình biểu phí, xem báo cáo tổng hợp.
  - **Kế toán / Thu ngân:** Lập đợt thu phí, nhập chỉ số điện nước, thu tiền, in biên lai laser, tra cứu nợ.

### UC02: Quản lý Căn hộ / Hộ khẩu
- **Tác nhân:** Ban Quản Trị, Kế toán.
- **Mô tả:** Quản lý danh mục các căn hộ trong chung cư (ví dụ: A1205, B0402, C1501,...).
- **Các trường dữ liệu:** Số hiệu căn hộ, diện tích sàn sử dụng (m²), số tầng, trạng thái căn hộ (Đang ở, Cho thuê, Còn trống), chủ hộ đại diện, ngày chuyển đến sinh sống.
- **Nghiệp vụ:** Thêm mới căn hộ, tìm kiếm nhanh theo số phòng, lọc theo tầng và tình trạng cư trú.

### UC03: Quản lý Nhân khẩu cư dân
- **Tác nhân:** Ban Quản Trị.
- **Mô tả:** Quản lý hồ sơ định danh của toàn bộ cư dân sinh sống tại chung cư.
- **Các trường dữ liệu:** Họ và tên, mã căn hộ, ngày tháng năm sinh, giới tính, số CCCD/định danh cá nhân, quan hệ với chủ hộ (Chủ hộ, Vợ, Chồng, Con, Bố mẹ, Người thuê), số điện thoại liên lạc.
- **Nghiệp vụ:** Tự động đồng bộ và gán chủ hộ cho căn hộ khi thêm thành viên có quan hệ "Chủ hộ". Tìm kiếm nhanh cư dân theo tên, số CCCD hoặc căn hộ.

### UC04: Quản lý Tạm trú, Tạm vắng
- **Tác nhân:** Ban Quản Trị.
- **Mô tả:** Ghi nhận và theo dõi các biến động cư trú ngắn hạn của cư dân để phục vụ công tác an ninh trật tự và quản lý nhân khẩu.
- **Các trường dữ liệu:** Nhân khẩu đăng ký, phân loại (Đăng ký tạm trú hoặc Khai báo tạm vắng), thời hạn (Từ ngày – Đến ngày), lý do lưu trú hoặc nơi đến.

### UC05: Quản lý Phương tiện gửi xe
- **Tác nhân:** Ban Quản Trị, Kế toán.
- **Mô tả:** Quản lý danh sách xe máy, ô tô, xe đạp điện được cấp thẻ gửi xe của từng căn hộ.
- **Các trường dữ liệu:** Căn hộ sở hữu, loại phương tiện (`XE_MAY`, `O_TO`, `XE_DAP_DIEN`), biển số xe kiểm soát, tên và nhãn hiệu xe (Honda Vision, Mazda CX-5...).
- **Nghiệp vụ:** Số lượng xe được hệ thống tự động tổng hợp để làm căn cứ tính phí trông giữ xe khi lập kỳ thu phí hàng tháng.

### UC06: Quản lý Danh mục khoản thu & Đơn giá cấu hình
- **Tác nhân:** Ban Quản Trị.
- **Mô tả:** Thiết lập bảng đơn giá linh hoạt theo nghị quyết của Hội nghị nhà chung cư mà không cần sửa mã nguồn hệ thống.
- **Phân loại khoản thu:**
  1. **Bắt buộc:**
     - *Phí dịch vụ chung cư:* Tính theo diện tích căn hộ (Khung quy định 2.500 – 16.500 đ/m²/tháng; mức cấu hình hiện hành: 12.000 đ/m²).
     - *Phí quản lý vận hành:* Tính theo diện tích căn hộ (Mức cấu hình hiện hành: 7.000 đ/m²/tháng).
     - *Phí trông giữ phương tiện:* Xe máy (70.000 đ/xe/tháng), Ô tô (1.200.000 đ/xe/tháng), Xe đạp điện (40.000 đ/xe/tháng).
  2. **Thu hộ:** Tiền điện sinh hoạt, tiền nước sạch, internet (nhập số tiền thực tế theo hóa đơn của đơn vị cung cấp dịch vụ).
  3. **Tự nguyện:** Quỹ Vì người nghèo, Quỹ Đền ơn đáp nghĩa 27/7, Quỹ Tết thiếu nhi 1/6 (thu theo mức vận động tự nguyện từng hộ).

### UC07: Lập Đợt thu phí định kỳ theo tháng (Tính năng trọng yếu)
- **Tác nhân:** Kế toán / Thu ngân.
- **Mô tả:** Khởi tạo đợt thu mới cho một kỳ (ví dụ: `2026-11`, `2026-12`), hệ thống tự động sinh dữ liệu công nợ phải nộp cho 100% căn hộ.
- **Thuật toán tự động hóa:**
  - $\text{Phí dịch vụ} = \text{Đơn giá dịch vụ} \times \text{Diện tích căn hộ} \times \text{Hệ số ngày thực tế (CR-003)}$
  - $\text{Phí quản lý} = \text{Đơn giá quản lý} \times \text{Diện tích căn hộ} \times \text{Hệ số ngày thực tế (CR-003)}$
  - $\text{Phí gửi xe} = (\text{Số xe máy} \times 70.000) + (\text{Số ô tô} \times 1.200.000)$
- **Xử lý Change Request CR-003:** Đối với căn hộ mới nhận bàn giao hoặc chuyển đến sinh sống giữa tháng (căn cứ trường `ngay_chuyen_den` trong bảng `HO_KHAU`), hệ thống tự động tính tỷ lệ:
  $$\text{Tỷ lệ ngày} = \frac{30 - \text{Ngày chuyển đến} + 1}{30}$$
  Ví dụ: Căn hộ B0403 chuyển đến ngày 16/10, ở thực tế 15 ngày thì phí dịch vụ và quản lý tháng đó chỉ thu 50%.
- **Bảng đối soát:** Hiển thị danh sách tổng hợp số tiền của từng hộ để kế toán kiểm tra trước khi xác nhận lưu đợt.

### UC08: Nhập tiền điện, nước sinh hoạt thu hộ
- **Tác nhân:** Kế toán.
- **Mô tả:** Nhập số tiền hóa đơn thực tế phát sinh trong tháng của từng căn hộ đối với các dịch vụ điện lưới và nước sạch.
- **Nghiệp vụ:** Cập nhật trực tiếp vào bảng chi tiết thu `CHI_TIET_THU` của đợt thu đang mở, ghi rõ chỉ số hoặc số hiệu hóa đơn đối soát.

### UC09: Ghi nhận nộp phí & Xuất biên lai in Laser (Tính năng trọng yếu)
- **Tác nhân:** Kế toán / Thu ngân.
- **Mô tả:** Tiếp nhận cư dân đến nộp tiền, đối soát công nợ, ghi nhận giao dịch và in biên lai thu tiền chuẩn.
- **Quy trình tác nghiệp:**
  1. Nhập số căn hộ (ví dụ: `A1205`), hệ thống lập tức tải danh sách toàn bộ các khoản nợ của hộ đó trong kỳ hiện tại và kỳ trước.
  2. Chọn khoản thu cần nộp, nhập số tiền thực nhận (hỗ trợ nộp một phần hoặc nộp đủ toàn bộ).
  3. Chọn phương thức thanh toán (Tiền mặt hoặc Chuyển khoản ngân hàng), nhập họ tên người nộp.
  4. Hệ thống kiểm tra hợp lệ, tự động sinh mã phiếu thu duy nhất theo quy chuẩn: `PT-YYYYMMDD-XXXX`.
  5. Cập nhật số tiền đã nộp `so_tien_da_nop` và chuyển trạng thái tương ứng (`CHUA_NOP` ➔ `NOP_THIEU` ➔ `DA_NOP_DU`).
  6. **Xuất biên lai Laser:** Mở hộp thoại mẫu biên lai in laser chuẩn cho cư dân bao gồm:
     - Quốc hiệu, tiêu ngữ: "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM".
     - Tên Ban Quản Trị chung cư Blue Moon.
     - Mã phiếu thu, số căn hộ, diện tích sàn, họ tên người nộp.
     - Bảng chi tiết khoản thu: Số tiền phải nộp, Thực nộp lần này, Còn lại.
     - Tổng số tiền bằng số và số tiền bằng chữ tiếng Việt (hàm tự động dịch tiền thành chữ chuẩn ngữ pháp).
     - Nơi ký và ghi rõ họ tên của Người nộp tiền và Thu ngân / Kế toán.
     - Hỗ trợ bấm nút in để in trực tiếp ra máy in laser A4/A5 hoặc lưu thành tệp PDF.

### UC10: Thống kê, tra cứu & Báo cáo
- **Tác nhân:** Ban Quản Trị, Kế toán.
- **Mô tả:** Cung cấp bức tranh toàn cảnh về tình hình tài chính và dòng tiền của chung cư.
- **Các thành phần trực quan:**
  - *Thẻ KPI:* Tổng số căn hộ, tỷ lệ lấp đầy, tổng số tiền phải thu, tổng số tiền đã thu, tổng nợ đọng, tỷ lệ hoàn thành thu nộp (%).
  - *Biểu đồ Chart.js:* So sánh trực quan giữa số tiền phải thu và số tiền đã thu theo từng loại phí (Phí dịch vụ, Phí quản lý, Phí xe ô tô, Phí xe máy...).
  - *Bảng nợ đọng:* Liệt kê top các căn hộ nợ đọng nhiều nhất để Ban Quản Trị có kế hoạch gửi thông báo đôn đốc.
  - *Xuất dữ liệu:* Nút xuất báo cáo ra tệp tin CSV để mở trên Excel hoặc in trực tiếp báo cáo từ trình duyệt.

### UC11: Quản lý Tài khoản & Phân quyền cán bộ (RBAC)
- **Tác nhân:** Quản trị viên (Admin).
- **Mô tả:** Quản lý danh sách tài khoản cán bộ công tác tại văn phòng ban quản lý.
- **Nghiệp vụ:** Cấp tài khoản mới, phân nhóm vai trò (`ADMIN`, `BAN_QUAN_TRI`, `KE_TOAN`), khóa tài khoản hoặc mở khóa tài khoản khi có biến động nhân sự.

### UC12: Sao lưu & Phục hồi CSDL
- **Tác nhân:** Quản trị viên (Admin).
- **Mô tả:** Đảm bảo an toàn và tính toàn vẹn dữ liệu của chung cư.
- **Nghiệp vụ:**
  - *Sao lưu (Backup):* Tải về bản trích xuất toàn bộ dữ liệu của 9 bảng thực thể dưới định dạng tệp JSON có gắn dấu thời gian.
  - *Phục hồi (Restore):* Cho phép nạp lại tệp JSON sao lưu để khôi phục trạng thái dữ liệu trong trường hợp hệ thống gặp sự cố hoặc cần chuyển dữ liệu sang máy chủ mới.

### UC13: Cổng Thông Tin Cư Dân & Đóng Tiền Online (Resident Portal - Tính năng mở rộng)
- **Tác nhân:** Cư dân / Chủ hộ (Khách).
- **Mô tả:** Cung cấp giao diện trực tuyến riêng biệt cho từng chủ hộ để theo dõi công nợ, thời hạn nộp phí và thực hiện thanh toán online tiện lợi mà không cần đến văn phòng ban quản lý.
- **Quyền hạn & Giao diện:**
  - Khi chủ hộ đăng nhập hoặc chuyển sang vai trò Cư Dân, hệ thống tự động ẩn các chức năng quản trị nhạy cảm của BQT và Kế toán, chỉ hiển thị thông tin thuộc về căn hộ của chính mình.
- **Các nghiệp vụ chính:**
  1. **Xem thông tin căn hộ:** Diện tích sàn ($m^2$), số tầng, danh sách các thành viên gia đình và phương tiện gửi xe đã đăng ký.
  2. **Tra cứu hóa đơn & Hạn nộp tiền:**
     - Danh sách chi tiết các khoản phí phát sinh theo từng đợt (Phí dịch vụ, phí quản lý, phí xe, điện nước thu hộ, các quỹ từ thiện).
     - Hiển thị rõ ràng: Số tiền phải nộp, Số tiền đã nộp, **Số tiền còn nợ**, và **Hạn nộp tiền (Deadline)**.
     - Cảnh báo trực quan: Nhãn màu xanh (Còn trong hạn nộp), Nhãn màu vàng (Sắp đến hạn), Nhãn màu đỏ (Đã quá hạn nộp tiền).
  3. **Cổng thanh toán trực tuyến VietQR 24/7:**
     - Cho phép cư dân bấm nút "Đóng tiền Online" cho từng khoản hoặc nút "Đóng tiền toàn bộ bằng VietQR".
     - Hệ thống tự động tạo mã **VietQR chuẩn ngân hàng (NAPAS 247)** có gắn sẵn số tiền chính xác, số tài khoản của Ban Quản Trị chung cư Blue Moon (`0987654321` - MBBank) và cú pháp chuyển khoản định danh duy nhất (ví dụ: `BMFM A1205 PHI DICH VU`).
     - Cư dân mở ứng dụng ngân hàng bất kỳ (Vietcombank, MB, BIDV, Techcombank, MoMo...) quét mã QR để chuyển khoản.
  4. **Xác nhận thanh toán & Xuất biên lai điện tử (E-Receipt):**
     - Sau khi chuyển khoản, cư dân bấm xác nhận thanh toán trực tuyến. Hệ thống lập tức trừ sạch công nợ trong CSDL, sinh mã phiếu thu điện tử duy nhất `PT-ONLINE-YYYYMMDD-XXXX`.
     - Tự động hiển thị mẫu **Biên lai điện tử chuẩn in Laser** có đóng dấu xác nhận trực tuyến để cư dân tải về hoặc in ra lưu trữ.
  5. **Xem lịch sử thanh toán:** Bảng tổng hợp toàn bộ các lần đã nộp tiền trước đây để cư dân đối soát minh bạch bất kỳ lúc nào.

---

## IV. THIẾT KẾ CƠ SỞ DỮ LIỆU QUAN HỆ (ERD)

Hệ thống được thiết kế chuẩn hóa dữ liệu với 9 bảng quan hệ chặt chẽ:

```
[HO_KHAU] 1 ──── N [NHAN_KHAU] 1 ──── N [TAM_TRU_TAM_VANG]
    │
    ├───── 1 ──── N [PHUONG_TIEN]
    │
    └───── 1 ──── N [CHI_TIET_THU] N ──── 1 [KHOAN_THU]
                         │
                         ├──── N ──── 1 [DOT_THU]
                         │
                         └──── 1 ──── N [PHIEU_THU] N ──── 1 [NGUOI_DUNG]
```

### Danh sách các bảng dữ liệu:
1. `HO_KHAU`: `ma_ho` (PK), `so_can_ho`, `dien_tich`, `so_tang`, `ma_chu_ho` (FK), `trang_thai`, `ngay_chuyen_den`.
2. `NHAN_KHAU`: `ma_nk` (PK), `ma_ho` (FK), `ho_ten`, `ngay_sinh`, `gioi_tinh`, `so_cccd`, `quan_he_chu_ho`, `so_dien_thoai`.
3. `TAM_TRU_TAM_VANG`: `ma_ttv` (PK), `ma_nk` (FK), `loai`, `tu_ngay`, `den_ngay`, `ly_do`.
4. `PHUONG_TIEN`: `ma_pt` (PK), `ma_ho` (FK), `loai_xe`, `bien_so`, `ten_xe`.
5. `KHOAN_THU`: `ma_kt` (PK), `ten_khoan_thu`, `loai`, `cach_tinh`, `don_gia`, `ghi_chu`, `kich_hoat`.
6. `DOT_THU`: `ma_dot` (PK), `ten_dot`, `thang_nam`, `ngay_bat_dau`, `han_nop`, `trang_thai`.
7. `CHI_TIET_THU`: `ma_ct` (PK), `ma_dot` (FK), `ma_ho` (FK), `ma_kt` (FK), `so_tien_phai_nop`, `so_tien_da_nop`, `trang_thai`, `ghi_chu`.
8. `PHIEU_THU`: `ma_phieu` (PK), `ma_ct` (FK), `so_tien`, `ngay_nop`, `nguoi_nop`, `phuong_thuc`, `ma_tk_thu` (FK), `ghi_chu`.
9. `NGUOI_DUNG`: `ma_tk` (PK), `ten_dang_nhap`, `mat_khau`, `ho_ten`, `vai_tro` ('ADMIN', 'BAN_QUAN_TRI', 'KE_TOAN', 'CU_DAN'), `ma_ho` (FK trỏ tới căn hộ của cư dân), `so_dien_thoai`, `trang_thai`.

---

## V. HƯỚNG DẪN CÀI ĐẶT VÀ SỬ DỤNG

### 1. Khởi động hệ thống trên Windows (Cách nhanh nhất)
1. Mở thư mục dự án `d:\KTPM2026`.
2. Nhấp đúp chuột vào file **`start.bat`**.
3. Cửa sổ dòng lệnh sẽ chạy máy chủ Python và trình duyệt web sẽ tự động mở tại địa chỉ:
   ```
   http://localhost:8000
   ```

### 2. Khởi động bằng dòng lệnh (Manual)
Mở PowerShell hoặc Command Prompt tại thư mục dự án và gõ:
```bash
py server.py
# hoặc
python server.py
```

### 3. Danh sách tài khoản đăng nhập mẫu sẵn có:
| Tên đăng nhập | Mật khẩu | Họ và tên | Vai trò phân quyền | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| `admin` | `admin123` | Quản trị viên Hệ thống | Quản trị viên (ADMIN) | Toàn quyền cấu hình |
| `bqt_truongban` | `bqt123` | Trưởng Ban Quản Trị | Ban Quản Trị (BAN_QUAN_TRI) | Quản lý căn hộ, cư dân, xe |
| `ketoan_minh` | `ketoan123` | Kế toán Nguyễn Hồng Minh | Kế toán / Thu ngân (KE_TOAN) | Lập đợt thu, thu tiền, in biên lai |
| `cudan_a1205` | `123456` | Nguyễn Văn An | Cư dân / Chủ hộ (CU_DAN) | **Chủ hộ A1205 (Xem nợ, đóng VietQR)** |
| `cudan_b0402` | `123456` | Phạm Quỳnh Nga | Cư dân / Chủ hộ (CU_DAN) | **Chủ hộ B0402 (Xem nợ, đóng VietQR)** |
| `cudan_b0403` | `123456` | Vũ Đức Thành | Cư dân / Chủ hộ (CU_DAN) | **Chủ hộ B0403 (CR-003, đóng VietQR)** |

*Ghi chú tiện lợi:* Trên thanh tiêu đề Topbar của giao diện Web, có sẵn mục **"Vai trò thử nghiệm" (Role Switcher)** gồm 4 vai trò:
1. `Kế toán / Thu ngân`
2. `Ban quản trị (BQT)`
3. `Quản trị viên (Admin)`
4. `Cư dân / Chủ hộ (A1205)`  
Giúp người dùng và thầy cô giáo kiểm thử ngay lập tức giao diện và tính năng của từng vai trò chỉ với 1 thao tác chọn.
