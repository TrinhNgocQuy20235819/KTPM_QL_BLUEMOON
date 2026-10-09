-- ====================================================================
-- DỰ ÁN QUẢN LÝ THU PHÍ CHUNG CƯ BLUE MOON (BMFM - BlueMoon Fee Management)
-- Đơn vị thực hiện: Nhóm 12 - Môn Kỹ thuật phần mềm (KTPM 2026)
-- Hệ quản trị cơ sở dữ liệu: MySQL 8.0+
-- File: database_mysql.sql
-- Mô tả: Khởi tạo cấu trúc bảng CSDL chuẩn quan hệ (9 bảng) và dữ liệu mẫu
-- ====================================================================

-- 1. TẠO CƠ SỞ DỮ LIỆU
CREATE DATABASE IF NOT EXISTS `bluemoon_db` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `bluemoon_db`;

-- Xóa bảng cũ nếu đã tồn tại theo thứ tự ràng buộc khóa ngoại
DROP TABLE IF EXISTS `PHIEU_THU`;
DROP TABLE IF EXISTS `CHI_TIET_THU`;
DROP TABLE IF EXISTS `DOT_THU`;
DROP TABLE IF EXISTS `KHOAN_THU`;
DROP TABLE IF EXISTS `PHUONG_TIEN`;
DROP TABLE IF EXISTS `TAM_TRU_TAM_VANG`;
DROP TABLE IF EXISTS `NHAN_KHAU`;
DROP TABLE IF EXISTS `HO_KHAU`;
DROP TABLE IF EXISTS `NGUOI_DUNG`;

-- ====================================================================
-- 2. TẠO CÁC BẢNG QUẢN LÝ THỰC THỂ (ERD)
-- ====================================================================

-- Bảng 1: NGUOI_DUNG (Tài khoản cán bộ và Cư dân/Khách - UC01, UC11)
CREATE TABLE `NGUOI_DUNG` (
    `ma_tk` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Mã định danh tài khoản',
    `ten_dang_nhap` VARCHAR(50) NOT NULL UNIQUE COMMENT 'Tên đăng nhập',
    `mat_khau_hash` VARCHAR(255) NOT NULL COMMENT 'Mật khẩu đã băm (BCrypt hoặc SHA-256)',
    `ho_ten` VARCHAR(100) NOT NULL COMMENT 'Họ và tên cán bộ hoặc cư dân',
    `vai_tro` ENUM('ADMIN', 'BAN_QUAN_TRI', 'KE_TOAN', 'CU_DAN') NOT NULL DEFAULT 'CU_DAN' COMMENT 'Vai trò phân quyền',
    `ma_ho` INT NULL COMMENT 'Mã căn hộ liên kết (dành riêng cho vai trò Cư dân / Chủ hộ)',
    `so_dien_thoai` VARCHAR(15) NULL COMMENT 'Số điện thoại liên hệ',
    `trang_thai` ENUM('HOAT_DONG', 'KHOA') NOT NULL DEFAULT 'HOAT_DONG' COMMENT 'Trạng thái tài khoản',
    `ngay_tao` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Ngày tạo tài khoản'
) ENGINE=InnoDB COMMENT='Bảng người dùng và phân quyền hệ thống';

-- Bảng 2: HO_KHAU (Quản lý căn hộ và thông tin hộ gia đình - UC02)
CREATE TABLE `HO_KHAU` (
    `ma_ho` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Mã định danh duy nhất của hộ căn hộ',
    `so_can_ho` VARCHAR(10) NOT NULL UNIQUE COMMENT 'Số hiệu căn hộ (Ví dụ: A1205, B0402)',
    `dien_tich` DECIMAL(6,2) NOT NULL COMMENT 'Diện tích sàn sử dụng (m2) làm căn cứ tính phí',
    `so_tang` INT NOT NULL DEFAULT 1 COMMENT 'Tầng của căn hộ',
    `ma_chu_ho` INT NULL COMMENT 'Mã nhân khẩu là chủ hộ (khóa ngoại mềm trỏ tới NHAN_KHAU)',
    `trang_thai` ENUM('DANG_O', 'TRONG', 'CHO_THUE') NOT NULL DEFAULT 'DANG_O' COMMENT 'Tình trạng căn hộ',
    `ngay_chuyen_den` DATE DEFAULT '2026-01-01' COMMENT 'Ngày chuyển đến sinh sống (phục vụ Change Request CR-003 tính số ngày thực tế)',
    `ngay_tao` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian ghi nhận vào hệ thống'
) ENGINE=InnoDB COMMENT='Bảng thông tin căn hộ và hộ khẩu';

-- Bảng 3: NHAN_KHAU (Quản lý cư dân sinh sống trong chung cư - UC03)
CREATE TABLE `NHAN_KHAU` (
    `ma_nk` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Mã định danh nhân khẩu',
    `ma_ho` INT NOT NULL COMMENT 'Khóa ngoại trỏ đến HO_KHAU',
    `ho_ten` VARCHAR(100) NOT NULL COMMENT 'Họ và tên cư dân',
    `ngay_sinh` DATE NOT NULL COMMENT 'Ngày tháng năm sinh',
    `gioi_tinh` ENUM('NAM', 'NU', 'KHAC') NOT NULL DEFAULT 'NAM' COMMENT 'Giới tính',
    `so_cccd` VARCHAR(20) NULL UNIQUE COMMENT 'Số CCCD/Định danh cá nhân (bảo mật dữ liệu)',
    `quan_he_chu_ho` VARCHAR(50) NOT NULL COMMENT 'Quan hệ với chủ hộ: Chủ hộ, Vợ, Chồng, Con, Bố mẹ,...',
    `so_dien_thoai` VARCHAR(15) NULL COMMENT 'Số điện thoại liên lạc',
    `ngay_tao` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Ngày khai báo thông tin',
    CONSTRAINT `fk_nk_ho_khau` FOREIGN KEY (`ma_ho`) REFERENCES `HO_KHAU` (`ma_ho`) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Bảng quản lý nhân khẩu cư dân';

-- Cập nhật khóa ngoại chủ hộ cho HO_KHAU (sau khi NHAN_KHAU đã được tạo)
ALTER TABLE `HO_KHAU` 
ADD CONSTRAINT `fk_hk_chu_ho` FOREIGN KEY (`ma_chu_ho`) REFERENCES `NHAN_KHAU` (`ma_nk`) ON DELETE SET NULL;

-- Bảng 4: TAM_TRU_TAM_VANG (Quản lý biến động cư trú - UC04)
CREATE TABLE `TAM_TRU_TAM_VANG` (
    `ma_ttv` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Mã bản ghi tạm trú/tạm vắng',
    `ma_nk` INT NOT NULL COMMENT 'Mã nhân khẩu đăng ký',
    `loai` ENUM('TAM_TRU', 'TAM_VANG') NOT NULL COMMENT 'Phân loại: Tạm trú hoặc Tạm vắng',
    `tu_ngay` DATE NOT NULL COMMENT 'Từ ngày bắt đầu',
    `den_ngay` DATE NOT NULL COMMENT 'Đến ngày kết thúc',
    `ly_do` VARCHAR(255) NULL COMMENT 'Lý do đăng ký hoặc nơi đi/nơi đến',
    `ngay_tao` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Ngày lập phiếu',
    CONSTRAINT `fk_ttv_nhan_khau` FOREIGN KEY (`ma_nk`) REFERENCES `NHAN_KHAU` (`ma_nk`) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Bảng quản lý tạm trú và tạm vắng';

-- Bảng 5: PHUONG_TIEN (Quản lý xe cộ gửi tại chung cư - UC05)
CREATE TABLE `PHUONG_TIEN` (
    `ma_pt` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Mã phương tiện',
    `ma_ho` INT NOT NULL COMMENT 'Mã hộ sở hữu xe',
    `loai_xe` ENUM('XE_MAY', 'O_TO', 'XE_DAP_DIEN') NOT NULL COMMENT 'Loại xe gửi',
    `bien_so` VARCHAR(20) NOT NULL COMMENT 'Biển số xe kiểm soát',
    `ten_xe` VARCHAR(100) NULL COMMENT 'Nhãn hiệu, màu xe (ví dụ: Honda Vision trắng)',
    `ngay_dang_ky` DATE DEFAULT (CURRENT_DATE) COMMENT 'Ngày bắt đầu gửi xe',
    CONSTRAINT `fk_pt_ho_khau` FOREIGN KEY (`ma_ho`) REFERENCES `HO_KHAU` (`ma_ho`) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Bảng phương tiện gửi xe của từng căn hộ';

-- Bảng 6: KHOAN_THU (Danh mục các khoản thu và đơn giá cấu hình động - UC06)
CREATE TABLE `KHOAN_THU` (
    `ma_kt` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Mã loại khoản thu',
    `ten_khoan_thu` VARCHAR(100) NOT NULL COMMENT 'Tên khoản thu (Phí dịch vụ, Phí quản lý, Phí xe,...)',
    `loai` ENUM('BAT_BUOC', 'TU_NGUYEN', 'THU_HO') NOT NULL COMMENT 'Phân loại khoản thu',
    `cach_tinh` ENUM('THEO_DIEN_TICH', 'THEO_XE_MAY', 'THEO_O_TO', 'THEO_HO', 'NHAP_TAY') NOT NULL COMMENT 'Quy tắc công thức tính tiền',
    `don_gia` DECIMAL(12,0) NOT NULL DEFAULT 0 COMMENT 'Đơn giá cấu hình linh hoạt (đồng/m2 hoặc đồng/xe)',
    `ghi_chu` VARCHAR(255) NULL COMMENT 'Ghi chú mô tả khoản thu',
    `kich_hoat` TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Trạng thái áp dụng (1: Đang dùng, 0: Ngừng)'
) ENGINE=InnoDB COMMENT='Bảng cấu hình danh mục khoản thu';

-- Bảng 7: DOT_THU (Quản lý các đợt thu theo tháng/kỳ - UC07)
CREATE TABLE `DOT_THU` (
    `ma_dot` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Mã đợt thu',
    `ten_dot` VARCHAR(100) NOT NULL COMMENT 'Tên đợt thu (Ví dụ: Thu phí tháng 11/2026)',
    `thang_nam` VARCHAR(7) NOT NULL UNIQUE COMMENT 'Kỳ thu dạng YYYY-MM (Ví dụ: 2026-11)',
    `ngay_bat_dau` DATE NOT NULL COMMENT 'Ngày bắt đầu mở đợt thu',
    `han_nop` DATE NOT NULL COMMENT 'Hạn nộp tiền cuối cùng',
    `trang_thai` ENUM('DANG_THU', 'DA_KHOA') NOT NULL DEFAULT 'DANG_THU' COMMENT 'Trạng thái đợt thu',
    `ngay_tao` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Ngày lập đợt thu'
) ENGINE=InnoDB COMMENT='Bảng đợt thu phí định kỳ theo tháng';

-- Bảng 8: CHI_TIET_THU (Chi tiết tiền phải nộp của từng căn hộ theo từng khoản thu - UC07, UC08)
CREATE TABLE `CHI_TIET_THU` (
    `ma_ct` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Mã chi tiết khoản thu phát sinh',
    `ma_dot` INT NOT NULL COMMENT 'Thuộc đợt thu nào',
    `ma_ho` INT NOT NULL COMMENT 'Căn hộ phải nộp',
    `ma_kt` INT NOT NULL COMMENT 'Khoản thu nào',
    `so_tien_phai_nop` DECIMAL(12,0) NOT NULL DEFAULT 0 COMMENT 'Số tiền hệ thống tính tự động hoặc nhập vào',
    `so_tien_da_nop` DECIMAL(12,0) NOT NULL DEFAULT 0 COMMENT 'Số tiền cư dân đã đóng thực tế',
    `trang_thai` ENUM('CHUA_NOP', 'NOP_THIEU', 'DA_NOP_DU') NOT NULL DEFAULT 'CHUA_NOP' COMMENT 'Trạng thái nộp phí',
    `ghi_chu` VARCHAR(255) NULL COMMENT 'Ghi chú chi tiết (ví dụ: chỉ số điện nước, tỷ lệ số ngày)',
    CONSTRAINT `fk_ct_dot_thu` FOREIGN KEY (`ma_dot`) REFERENCES `DOT_THU` (`ma_dot`) ON DELETE CASCADE,
    CONSTRAINT `fk_ct_ho_khau` FOREIGN KEY (`ma_ho`) REFERENCES `HO_KHAU` (`ma_ho`) ON DELETE CASCADE,
    CONSTRAINT `fk_ct_khoan_thu` FOREIGN KEY (`ma_kt`) REFERENCES `KHOAN_THU` (`ma_kt`) ON DELETE CASCADE,
    UNIQUE KEY `uk_dot_ho_kt` (`ma_dot`, `ma_ho`, `ma_kt`)
) ENGINE=InnoDB COMMENT='Bảng chi tiết khoản thu của từng căn hộ trong đợt';

-- Bảng 9: PHIEU_THU (Biên lai ghi nhận nộp tiền và in phiếu laser - UC09)
CREATE TABLE `PHIEU_THU` (
    `ma_phieu` VARCHAR(30) PRIMARY KEY COMMENT 'Mã phiếu thu duy nhất (Ví dụ: PT-202611-0001)',
    `ma_ct` INT NOT NULL COMMENT 'Mã chi tiết khoản thu được nộp',
    `so_tien` DECIMAL(12,0) NOT NULL COMMENT 'Số tiền thực nộp trong lần này',
    `ngay_nop` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm nộp tiền',
    `nguoi_nop` VARCHAR(100) NOT NULL COMMENT 'Họ và tên người đến nộp tiền',
    `phuong_thuc` ENUM('TIEN_MAT', 'CHUYEN_KHOAN') NOT NULL DEFAULT 'TIEN_MAT' COMMENT 'Hình thức thanh toán',
    `ma_tk_thu` INT NULL COMMENT 'Mã tài khoản kế toán ghi nhận phiếu',
    `ghi_chu` VARCHAR(255) NULL COMMENT 'Ghi chú thêm trên biên lai',
    CONSTRAINT `fk_pt_chi_tiet_thu` FOREIGN KEY (`ma_ct`) REFERENCES `CHI_TIET_THU` (`ma_ct`) ON DELETE CASCADE,
    CONSTRAINT `fk_pt_nguoi_dung` FOREIGN KEY (`ma_tk_thu`) REFERENCES `NGUOI_DUNG` (`ma_tk`) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Bảng biên lai phiếu thu tiền';

-- ====================================================================
-- 3. CHÈN DỮ LIỆU MẪU BAN ĐẦU (SEED DATA CHUNG CƯ BLUE MOON)
-- ====================================================================

-- 3.1. Tài khoản cán bộ & Cư dân
INSERT INTO `NGUOI_DUNG` (`ten_dang_nhap`, `mat_khau_hash`, `ho_ten`, `vai_tro`, `ma_ho`, `so_dien_thoai`) VALUES
('admin', 'admin123', 'Quản trị viên Hệ thống', 'ADMIN', NULL, '0901234567'),
('bqt_truongban', 'bqt123', 'Trưởng Ban Quản Trị', 'BAN_QUAN_TRI', NULL, '0912345678'),
('ketoan_minh', 'ketoan123', 'Kế toán Nguyễn Hồng Minh', 'KE_TOAN', NULL, '0987654321'),
('cudan_a1205', '123456', 'Nguyễn Văn An (Chủ hộ A1205)', 'CU_DAN', 1, '0911222333'),
('cudan_b0402', '123456', 'Phạm Quỳnh Nga (Chủ hộ B0402)', 'CU_DAN', 3, '0977666555'),
('cudan_b0403', '123456', 'Vũ Đức Thành (Chủ hộ B0403)', 'CU_DAN', 4, '0966555444');

-- 3.2. Căn hộ mẫu (Blue Moon Tower)
INSERT INTO `HO_KHAU` (`ma_ho`, `so_can_ho`, `dien_tich`, `so_tang`, `trang_thai`, `ngay_chuyen_den`) VALUES
(1, 'A1205', 85.50, 12, 'DANG_O', '2026-01-10'),
(2, 'A1206', 70.00, 12, 'DANG_O', '2026-02-15'),
(3, 'B0402', 95.00, 4, 'DANG_O', '2026-01-05'),
(4, 'B0403', 65.50, 4, 'DANG_O', '2026-10-16'), -- Chuyển đến giữa tháng để test CR-003
(5, 'C1501', 120.00, 15, 'DANG_O', '2026-03-01'),
(6, 'C1502', 75.00, 15, 'CHO_THUE', '2026-04-20'),
(7, 'A0801', 82.00, 8, 'TRONG', '2026-10-01');

-- 3.3. Nhân khẩu mẫu
INSERT INTO `NHAN_KHAU` (`ma_nk`, `ma_ho`, `ho_ten`, `ngay_sinh`, `gioi_tinh`, `so_cccd`, `quan_he_chu_ho`, `so_dien_thoai`) VALUES
(1, 1, 'Nguyễn Văn An', '1980-05-12', 'NAM', '001080012345', 'Chủ hộ', '0911222333'),
(2, 1, 'Trần Thị Mai', '1984-08-20', 'NU', '001184054321', 'Vợ', '0911222444'),
(3, 1, 'Nguyễn Minh Quân', '2012-11-10', 'NAM', '001212009876', 'Con', NULL),
(4, 2, 'Lê Hoàng Long', '1975-02-28', 'NAM', '001075034567', 'Chủ hộ', '0988777666'),
(5, 3, 'Phạm Quỳnh Nga', '1990-09-15', 'NU', '001190087654', 'Chủ hộ', '0977666555'),
(6, 4, 'Vũ Đức Thành', '1992-12-05', 'NAM', '001092043210', 'Chủ hộ', '0966555444'),
(7, 5, 'Hoàng Gia Bảo', '1968-07-22', 'NAM', '001068019283', 'Chủ hộ', '0944333222'),
(8, 6, 'Đặng Thu Trang', '1995-04-18', 'NU', '001195076543', 'Chủ hộ', '0933222111');

-- Cập nhật chủ hộ cho các căn hộ
UPDATE `HO_KHAU` SET `ma_chu_ho` = 1 WHERE `ma_ho` = 1;
UPDATE `HO_KHAU` SET `ma_chu_ho` = 4 WHERE `ma_ho` = 2;
UPDATE `HO_KHAU` SET `ma_chu_ho` = 5 WHERE `ma_ho` = 3;
UPDATE `HO_KHAU` SET `ma_chu_ho` = 6 WHERE `ma_ho` = 4;
UPDATE `HO_KHAU` SET `ma_chu_ho` = 7 WHERE `ma_ho` = 5;
UPDATE `HO_KHAU` SET `ma_chu_ho` = 8 WHERE `ma_ho` = 6;

-- 3.4. Phương tiện gửi xe mẫu
INSERT INTO `PHUONG_TIEN` (`ma_ho`, `loai_xe`, `bien_so`, `ten_xe`) VALUES
(1, 'XE_MAY', '29B1-888.88', 'Honda SH 150i'),
(1, 'XE_MAY', '29B1-678.90', 'Honda AirBlade'),
(1, 'O_TO', '30F-123.45', 'Mazda CX-5'),
(2, 'XE_MAY', '29C1-555.55', 'Yamaha Grande'),
(3, 'O_TO', '30G-999.99', 'Mercedes C200'),
(4, 'XE_MAY', '29D1-333.33', 'Honda Wave Alpha'),
(5, 'O_TO', '30H-888.66', 'Toyota Camry'),
(5, 'XE_MAY', '29E1-777.77', 'Vespa Sprint');

-- 3.5. Danh mục khoản thu chuẩn (Theo bảng 2-3 trong tài liệu SRS)
INSERT INTO `KHOAN_THU` (`ma_kt`, `ten_khoan_thu`, `loai`, `cach_tinh`, `don_gia`, `ghi_chu`, `kich_hoat`) VALUES
(1, 'Phí dịch vụ chung cư', 'BAT_BUOC', 'THEO_DIEN_TICH', 12000, 'Khung quy định 2.500 - 16.500 đ/m2/tháng', 1),
(2, 'Phí quản lý vận hành', 'BAT_BUOC', 'THEO_DIEN_TICH', 7000, 'Mức áp dụng hiện hành 7.000 đ/m2/tháng', 1),
(3, 'Phí trông giữ xe máy', 'BAT_BUOC', 'THEO_XE_MAY', 70000, 'Đơn giá 70.000 đ/xe máy/tháng', 1),
(4, 'Phí trông giữ xe ô tô', 'BAT_BUOC', 'THEO_O_TO', 1200000, 'Đơn giá 1.200.000 đ/xe ô tô/tháng', 1),
(5, 'Tiền điện sinh hoạt (Thu hộ)', 'THU_HO', 'NHAP_TAY', 0, 'Nhập theo hóa đơn thực tế của Điện lực', 1),
(6, 'Tiền nước sinh hoạt (Thu hộ)', 'THU_HO', 'NHAP_TAY', 0, 'Nhập theo hóa đơn thực tế của Cty Nước sạch', 1),
(7, 'Quỹ Vì người nghèo', 'TU_NGUYEN', 'THEO_HO', 50000, 'Vận động ủng hộ vì người nghèo', 1),
(8, 'Quỹ Đền ơn đáp nghĩa 27/7', 'TU_NGUYEN', 'THEO_HO', 50000, 'Ủng hộ tri ân ngày thương binh liệt sĩ', 1),
(9, 'Quỹ Tết thiếu nhi 1/6', 'TU_NGUYEN', 'THEO_HO', 100000, 'Quỹ tổ chức sự kiện thiếu nhi chung cư', 1);

-- 3.6. Đợt thu phí tháng 11/2026 mẫu
INSERT INTO `DOT_THU` (`ma_dot`, `ten_dot`, `thang_nam`, `ngay_bat_dau`, `han_nop`, `trang_thai`) VALUES
(1, 'Thu phí tháng 11/2026', '2026-11', '2026-11-01', '2026-11-25', 'DANG_THU');

-- 3.7. Chi tiết thu tháng 11/2026 (Sinh tự động cho căn A1205: 85.5m2, 2 xe máy, 1 ô tô)
-- Phí dịch vụ: 85.5 * 12.000 = 1.026.000 đ
-- Phí quản lý: 85.5 * 7.000 = 598.500 đ
-- Phí xe máy: 2 * 70.000 = 140.000 đ
-- Phí xe ô tô: 1 * 1.200.000 = 1.200.000 đ
-- Tiền điện thu hộ: 650.000 đ
-- Tiền nước thu hộ: 180.000 đ
INSERT INTO `CHI_TIET_THU` (`ma_ct`, `ma_dot`, `ma_ho`, `ma_kt`, `so_tien_phai_nop`, `so_tien_da_nop`, `trang_thai`) VALUES
(1, 1, 1, 1, 1026000, 1026000, 'DA_NOP_DU'),
(2, 1, 1, 2, 598500, 598500, 'DA_NOP_DU'),
(3, 1, 1, 3, 140000, 140000, 'DA_NOP_DU'),
(4, 1, 1, 4, 1200000, 1200000, 'DA_NOP_DU'),
(5, 1, 1, 5, 650000, 650000, 'DA_NOP_DU'),
(6, 1, 1, 6, 180000, 180000, 'DA_NOP_DU'),
-- Căn B0402 (95m2, 1 ô tô):
(7, 1, 3, 1, 1140000, 0, 'CHUA_NOP'),
(8, 1, 3, 2, 665000, 0, 'CHUA_NOP'),
(9, 1, 3, 4, 1200000, 0, 'CHUA_NOP'),
-- Căn B0403 (chuyển đến 16/10/2026, 65.5m2, 1 xe máy) -> Test tính tiền nộp thiếu
(10, 1, 4, 1, 786000, 400000, 'NOP_THIEU'),
(11, 1, 4, 2, 458500, 0, 'CHUA_NOP'),
(12, 1, 4, 3, 70000, 70000, 'DA_NOP_DU');

-- 3.8. Phiếu thu biên lai mẫu đã nộp
INSERT INTO `PHIEU_THU` (`ma_phieu`, `ma_ct`, `so_tien`, `ngay_nop`, `nguoi_nop`, `phuong_thuc`, `ma_tk_thu`, `ghi_chu`) VALUES
('PT-202611-0001', 1, 1026000, '2026-11-05 08:30:00', 'Nguyễn Văn An', 'CHUYEN_KHOAN', 3, 'Thanh toán phí dịch vụ tháng 11'),
('PT-202611-0002', 2, 598500, '2026-11-05 08:30:00', 'Nguyễn Văn An', 'CHUYEN_KHOAN', 3, 'Thanh toán phí quản lý tháng 11'),
('PT-202611-0003', 3, 140000, '2026-11-05 08:30:00', 'Nguyễn Văn An', 'TIEN_MAT', 3, 'Thanh toán phí 2 xe máy'),
('PT-202611-0004', 4, 1200000, '2026-11-05 08:30:00', 'Nguyễn Văn An', 'CHUYEN_KHOAN', 3, 'Thanh toán phí 1 ô tô'),
('PT-202611-0005', 10, 400000, '2026-11-06 14:15:00', 'Vũ Đức Thành', 'TIEN_MAT', 3, 'Nộp tạm ứng phí dịch vụ'),
('PT-202611-0006', 12, 70000, '2026-11-06 14:15:00', 'Vũ Đức Thành', 'TIEN_MAT', 3, 'Nộp phí xe máy tháng 11');
