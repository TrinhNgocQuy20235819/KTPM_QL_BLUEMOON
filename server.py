# -*- coding: utf-8 -*-
"""
====================================================================
DỰ ÁN QUẢN LÝ THU PHÍ CHUNG CƯ BLUE MOON (BMFM)
Đơn vị thực hiện: Nhóm 12 - Môn Kỹ thuật phần mềm (KTPM 2026)
File: server.py
Mô tả: Máy chủ Web Backend REST API & Static File Server chạy bằng Python chuẩn
       Tích hợp cơ sở dữ liệu SQLite3, đáp ứng trọn vẹn 12 Use-Case của hệ thống.
====================================================================
"""

import http.server
import socketserver
import json
import sqlite3
import os
import sys
import urllib.parse
from datetime import datetime, date
import mimetypes

# Đảm bảo in tiếng Việt trên console Windows không bị lỗi bảng mã cp1252
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Cấu hình cổng mạng và thư mục tĩnh
PORT = 8000
DB_FILE = os.path.join(os.path.dirname(__file__), "database.db")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "public")

# ====================================================================
# KHỞI TẠO CƠ SỞ DỮ LIỆU SQLITE (Tương đương lược đồ MySQL 8.0)
# ====================================================================
def get_db():
    """Tạo kết nối đến cơ sở dữ liệu SQLite và trả về kết nối dạng row_factory"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_database():
    """Khởi tạo bảng và nạp dữ liệu mẫu ban đầu nếu CSDL chưa tồn tại"""
    conn = get_db()
    cursor = conn.cursor()

    # 1. Bảng NGUOI_DUNG (Tài khoản cán bộ & Cư dân/Khách - RBAC)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS NGUOI_DUNG (
        ma_tk INTEGER PRIMARY KEY AUTOINCREMENT,
        ten_dang_nhap TEXT NOT NULL UNIQUE,
        mat_khau TEXT NOT NULL,
        ho_ten TEXT NOT NULL,
        vai_tro TEXT NOT NULL CHECK(vai_tro IN ('ADMIN', 'BAN_QUAN_TRI', 'KE_TOAN', 'CU_DAN')),
        ma_ho INTEGER,
        so_dien_thoai TEXT,
        trang_thai TEXT NOT NULL DEFAULT 'HOAT_DONG' CHECK(trang_thai IN ('HOAT_DONG', 'KHOA')),
        ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ma_ho) REFERENCES HO_KHAU(ma_ho) ON DELETE SET NULL
    )
    """)

    # Đảm bảo cột ma_ho tồn tại nếu CSDL đã khởi tạo từ trước
    try:
        cursor.execute("ALTER TABLE NGUOI_DUNG ADD COLUMN ma_ho INTEGER")
    except Exception:
        pass

    # 2. Bảng HO_KHAU (Căn hộ)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS HO_KHAU (
        ma_ho INTEGER PRIMARY KEY AUTOINCREMENT,
        so_can_ho TEXT NOT NULL UNIQUE,
        dien_tich REAL NOT NULL,
        so_tang INTEGER NOT NULL DEFAULT 1,
        ma_chu_ho INTEGER,
        trang_thai TEXT NOT NULL DEFAULT 'DANG_O' CHECK(trang_thai IN ('DANG_O', 'TRONG', 'CHO_THUE')),
        ngay_chuyen_den TEXT DEFAULT '2026-01-01',
        ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Bảng NHAN_KHAU (Cư dân)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS NHAN_KHAU (
        ma_nk INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_ho INTEGER NOT NULL,
        ho_ten TEXT NOT NULL,
        ngay_sinh TEXT NOT NULL,
        gioi_tinh TEXT NOT NULL DEFAULT 'NAM' CHECK(gioi_tinh IN ('NAM', 'NU', 'KHAC')),
        so_cccd TEXT UNIQUE,
        quan_he_chu_ho TEXT NOT NULL,
        so_dien_thoai TEXT,
        ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ma_ho) REFERENCES HO_KHAU(ma_ho) ON DELETE CASCADE
    )
    """)

    # 4. Bảng TAM_TRU_TAM_VANG (Biến động cư trú)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TAM_TRU_TAM_VANG (
        ma_ttv INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_nk INTEGER NOT NULL,
        loai TEXT NOT NULL CHECK(loai IN ('TAM_TRU', 'TAM_VANG')),
        tu_ngay TEXT NOT NULL,
        den_ngay TEXT NOT NULL,
        ly_do TEXT,
        ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(ma_nk) REFERENCES NHAN_KHAU(ma_nk) ON DELETE CASCADE
    )
    """)

    # 5. Bảng PHUONG_TIEN (Xe cộ đăng ký gửi)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS PHUONG_TIEN (
        ma_pt INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_ho INTEGER NOT NULL,
        loai_xe TEXT NOT NULL CHECK(loai_xe IN ('XE_MAY', 'O_TO', 'XE_DAP_DIEN')),
        bien_so TEXT NOT NULL,
        ten_xe TEXT,
        ngay_dang_ky TEXT DEFAULT CURRENT_DATE,
        FOREIGN KEY(ma_ho) REFERENCES HO_KHAU(ma_ho) ON DELETE CASCADE
    )
    """)

    # 6. Bảng KHOAN_THU (Danh mục các khoản thu & Đơn giá cấu hình linh hoạt)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS KHOAN_THU (
        ma_kt INTEGER PRIMARY KEY AUTOINCREMENT,
        ten_khoan_thu TEXT NOT NULL,
        loai TEXT NOT NULL CHECK(loai IN ('BAT_BUOC', 'TU_NGUYEN', 'THU_HO')),
        cach_tinh TEXT NOT NULL CHECK(cach_tinh IN ('THEO_DIEN_TICH', 'THEO_XE_MAY', 'THEO_O_TO', 'THEO_HO', 'NHAP_TAY')),
        don_gia REAL NOT NULL DEFAULT 0,
        ghi_chu TEXT,
        kich_hoat INTEGER NOT NULL DEFAULT 1
    )
    """)

    # 7. Bảng DOT_THU (Đợt thu phí theo kỳ tháng/năm)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS DOT_THU (
        ma_dot INTEGER PRIMARY KEY AUTOINCREMENT,
        ten_dot TEXT NOT NULL,
        thang_nam TEXT NOT NULL UNIQUE,
        ngay_bat_dau TEXT NOT NULL,
        han_nop TEXT NOT NULL,
        trang_thai TEXT NOT NULL DEFAULT 'DANG_THU' CHECK(trang_thai IN ('DANG_THU', 'DA_KHOA')),
        ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 8. Bảng CHI_TIET_THU (Chi tiết tiền từng hộ phải nộp theo từng khoản)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CHI_TIET_THU (
        ma_ct INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_dot INTEGER NOT NULL,
        ma_ho INTEGER NOT NULL,
        ma_kt INTEGER NOT NULL,
        so_tien_phai_nop REAL NOT NULL DEFAULT 0,
        so_tien_da_nop REAL NOT NULL DEFAULT 0,
        trang_thai TEXT NOT NULL DEFAULT 'CHUA_NOP' CHECK(trang_thai IN ('CHUA_NOP', 'NOP_THIEU', 'DA_NOP_DU')),
        ghi_chu TEXT,
        FOREIGN KEY(ma_dot) REFERENCES DOT_THU(ma_dot) ON DELETE CASCADE,
        FOREIGN KEY(ma_ho) REFERENCES HO_KHAU(ma_ho) ON DELETE CASCADE,
        FOREIGN KEY(ma_kt) REFERENCES KHOAN_THU(ma_kt) ON DELETE CASCADE,
        UNIQUE(ma_dot, ma_ho, ma_kt)
    )
    """)

    # 9. Bảng PHIEU_THU (Biên lai thu tiền)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS PHIEU_THU (
        ma_phieu TEXT PRIMARY KEY,
        ma_ct INTEGER NOT NULL,
        so_tien REAL NOT NULL,
        ngay_nop TEXT DEFAULT CURRENT_TIMESTAMP,
        nguoi_nop TEXT NOT NULL,
        phuong_thuc TEXT NOT NULL DEFAULT 'TIEN_MAT' CHECK(phuong_thuc IN ('TIEN_MAT', 'CHUYEN_KHOAN')),
        ma_tk_thu INTEGER,
        ghi_chu TEXT,
        FOREIGN KEY(ma_ct) REFERENCES CHI_TIET_THU(ma_ct) ON DELETE CASCADE,
        FOREIGN KEY(ma_tk_thu) REFERENCES NGUOI_DUNG(ma_tk) ON DELETE SET NULL
    )
    """)

    # 10. Bảng YEU_CAU_KIEN_NGHI (Đề xuất & Kiến nghị của các phòng gửi tới Ban Quản Trị / Admin duyệt)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS YEU_CAU_KIEN_NGHI (
        ma_yc INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_ho INTEGER NOT NULL,
        tieu_de TEXT NOT NULL,
        loai_yeu_cau TEXT NOT NULL CHECK(loai_yeu_cau IN ('SUA_CHUA', 'AN_NINH', 'VE_SINH', 'THU_PHI', 'TIEN_ICH', 'KHAC')),
        noi_dung TEXT NOT NULL,
        ngay_gui TEXT DEFAULT CURRENT_TIMESTAMP,
        nguoi_gui TEXT,
        trang_thai TEXT NOT NULL DEFAULT 'CHO_DUYET' CHECK(trang_thai IN ('CHO_DUYET', 'DA_DUYET', 'DANG_XU_LY', 'DA_XU_LY', 'TU_CHOI')),
        phan_hoi TEXT,
        ngay_duyet TEXT,
        nguoi_duyet TEXT,
        FOREIGN KEY(ma_ho) REFERENCES HO_KHAU(ma_ho) ON DELETE CASCADE
    )
    """)

    # Tự động tạo dữ liệu mẫu cho YEU_CAU_KIEN_NGHI nếu bảng chưa có dữ liệu
    cursor.execute("SELECT COUNT(*) as cnt FROM YEU_CAU_KIEN_NGHI")
    if cursor.fetchone()['cnt'] == 0:
        cursor.execute("SELECT ma_ho, so_can_ho FROM HO_KHAU WHERE so_can_ho IN ('A1205', 'B1104', 'B0402', 'A1801', 'C0502')")
        ho_map = {r['so_can_ho']: r['ma_ho'] for r in cursor.fetchall()}
        
        sample_proposals = [
            (ho_map.get('A1205', 6), 'Đề nghị thay bóng đèn chiếu sáng hành lang tầng 12 tháp A', 'SUA_CHUA',
             'Bóng đèn hành lang ngay trước cửa phòng 1205 bị chớp tắt liên tục từ tối qua, đề nghị BQT cử kỹ thuật kiểm tra thay thế.',
             '2026-11-15 08:30:00', 'Nguyễn Văn An', 'DA_DUYET',
             'BQT đã tiếp nhận đề xuất và chuyển cho bộ phận kỹ thuật điện tòa nhà xử lý trong chiều nay.', '2026-11-15 09:15:00', 'Bùi Minh Tuấn (BQT)'),
            
            (ho_map.get('B1104', 18), 'Đăng ký cấp thêm 01 thẻ cư dân thang máy cho người thân', 'TIEN_ICH',
             'Gia đình tôi mới có em gái chuyển lên học đại học ở cùng, xin đăng ký cấp thêm 01 thẻ từ thang máy.',
             '2026-11-16 10:00:00', 'Trịnh Ngọc Quý', 'CHO_DUYET',
             None, None, None),

            (ho_map.get('B0402', 13), 'Kiểm tra áp lực nước sinh hoạt giờ cao điểm buổi tối', 'SUA_CHUA',
             'Khung giờ 18h30 - 20h hàng ngày nước xả vòi sen rất yếu, mong BQT và kỹ thuật kiểm tra lại máy bơm tăng áp tầng 4.',
             '2026-11-14 19:40:00', 'Phạm Quỳnh Nga', 'DANG_XU_LY',
             'Tổ kỹ thuật đang đo áp lực đường ống trục đứng và bảo trì van điều áp.', '2026-11-15 08:00:00', 'Admin Hệ Thống'),

            (ho_map.get('A1801', 10), 'Đề xuất bổ sung camera an ninh và ghế đá khu vực sân chơi trẻ em', 'AN_NINH',
             'Khu vực sân chơi chung tầng 1 góc tháp A vào buổi chiều rất đông các cháu nhỏ vui chơi, đề xuất BQT lắp thêm camera và ghế nghỉ.',
             '2026-11-10 14:20:00', 'Vương Đình Quang', 'DA_XU_LY',
             'BQT đã hoàn thành lắp đặt camera an ninh góc sân chơi và bổ sung 2 ghế đá vào ngày 12/11/2026.', '2026-11-12 16:30:00', 'Bùi Minh Tuấn (BQT)'),

            (ho_map.get('C0502', 24), 'Thắc mắc về chỉ số tiền điện thu hộ kỳ tháng 10/2026', 'THU_PHI',
             'Chỉ số điện gia đình dùng trong tháng 10 tăng so với tháng 9, đề nghị kiểm tra lại công tơ điện tử.',
             '2026-11-11 09:10:00', 'Lê Đức Minh', 'TU_CHOI',
             'BQT và Kế toán đã cùng cán bộ EVN đối soát niêm chì và chỉ số công tơ điện tử, kết quả hoàn toàn trùng khớp với hóa đơn.', '2026-11-12 10:00:00', 'Kế toán Nguyễn Hồng Minh')
        ]
        cursor.executemany("""
        INSERT INTO YEU_CAU_KIEN_NGHI (ma_ho, tieu_de, loai_yeu_cau, noi_dung, ngay_gui, nguoi_gui, trang_thai, phan_hoi, ngay_duyet, nguoi_duyet)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_proposals)
        conn.commit()

    # Kiểm tra xem đã có dữ liệu mẫu mở rộng chưa (nếu < 20 căn hộ thì nạp CSDL đầy đủ)
    cursor.execute("SELECT COUNT(*) as cnt FROM HO_KHAU")
    if cursor.fetchone()['cnt'] < 20:
        # Xóa sạch dữ liệu cũ theo thứ tự khóa ngoại
        for t in ['PHIEU_THU', 'CHI_TIET_THU', 'DOT_THU', 'KHOAN_THU', 'PHUONG_TIEN', 'TAM_TRU_TAM_VANG', 'NHAN_KHAU', 'NGUOI_DUNG', 'HO_KHAU']:
            cursor.execute(f"DELETE FROM {t}")
        try:
            cursor.execute("DELETE FROM sqlite_sequence")
        except Exception:
            pass

        # 1. BẢNG HO_KHAU (29 căn hộ phân bố 3 tháp A, B, C)
        apartments = [
            (1, 'A0201', 68.50, 2, 'DANG_O', '2025-05-10'),
            (2, 'A0402', 72.00, 4, 'DANG_O', '2025-06-15'),
            (3, 'A0603', 85.50, 6, 'CHO_THUE', '2026-03-01'),
            (4, 'A0801', 82.00, 8, 'DANG_O', '2025-08-20'),
            (5, 'A1002', 95.00, 10, 'DANG_O', '2025-09-01'),
            (6, 'A1205', 85.50, 12, 'DANG_O', '2026-01-10'),
            (7, 'A1206', 70.00, 12, 'DANG_O', '2026-02-15'),
            (8, 'A1403', 105.00, 14, 'DANG_O', '2025-11-12'),
            (9, 'A1602', 115.00, 16, 'DANG_O', '2025-12-05'),
            (10, 'A1801', 145.00, 18, 'DANG_O', '2025-04-01'),
            (11, 'B0202', 55.00, 2, 'TRONG', '2026-10-01'),
            (12, 'B0301', 65.00, 3, 'DANG_O', '2026-01-15'),
            (13, 'B0402', 95.00, 4, 'DANG_O', '2026-01-05'),
            (14, 'B0403', 65.50, 4, 'DANG_O', '2026-10-16'),
            (15, 'B0601', 78.00, 6, 'DANG_O', '2025-07-20'),
            (16, 'B0705', 88.00, 7, 'CHO_THUE', '2026-02-01'),
            (17, 'B0902', 92.50, 9, 'DANG_O', '2025-10-10'),
            (18, 'B1104', 102.00, 11, 'DANG_O', '2025-08-15'),
            (19, 'B1203', 86.00, 12, 'DANG_O', '2026-04-10'),
            (20, 'B1502', 130.00, 15, 'DANG_O', '2025-03-20'),
            (21, 'C0302', 58.00, 3, 'TRONG', '2026-10-01'),
            (22, 'C0501', 75.00, 5, 'DANG_O', '2025-09-18'),
            (23, 'C0604', 82.50, 6, 'DANG_O', '2026-02-28'),
            (24, 'C0802', 90.00, 8, 'DANG_O', '2025-11-05'),
            (25, 'C1005', 98.00, 10, 'DANG_O', '2025-06-30'),
            (26, 'C1201', 85.00, 12, 'CHO_THUE', '2026-05-15'),
            (27, 'C1501', 120.00, 15, 'DANG_O', '2026-03-01'),
            (28, 'C1502', 75.00, 15, 'DANG_O', '2026-04-20'),
            (29, 'C1703', 140.00, 17, 'DANG_O', '2025-01-10')
        ]
        cursor.executemany("INSERT INTO HO_KHAU (ma_ho, so_can_ho, dien_tich, so_tang, trang_thai, ngay_chuyen_den) VALUES (?, ?, ?, ?, ?, ?)", apartments)

        # 2. BẢNG NHAN_KHAU (80 cư dân)
        residents = [
            (1, 1, 'Trương Văn Hùng', '1978-04-12', 'NAM', '001078001122', 'Chủ hộ', '0912111222'),
            (2, 1, 'Nguyễn Thị Kim', '1982-09-18', 'NU', '001182003344', 'Vợ', '0912111333'),
            (3, 1, 'Trương Tuấn Anh', '2010-03-25', 'NAM', '001210005566', 'Con', None),
            (4, 2, 'Đoàn Quốc Toàn', '1983-11-05', 'NAM', '001083002233', 'Chủ hộ', '0983222333'),
            (5, 2, 'Ngô Thúy Hiền', '1986-07-22', 'NU', '001186004455', 'Vợ', '0983222444'),
            (6, 2, 'Đoàn Hải Đăng', '2014-08-14', 'NAM', '001214006677', 'Con', None),
            (7, 3, 'Kim Jin-woo', '1985-02-14', 'NAM', '079085001234', 'Chủ hộ', '0909123456'),
            (8, 3, 'Lee Seo-yeon', '1989-10-20', 'NU', '079189004321', 'Vợ', '0909654321'),
            (9, 4, 'Đỗ Văn Minh', '1972-06-30', 'NAM', '001072008899', 'Chủ hộ', '0913888999'),
            (10, 4, 'Lê Tuyết Mai', '1976-12-15', 'NU', '001176007788', 'Vợ', '0913888777'),
            (11, 4, 'Đỗ Thu Hương', '2004-05-19', 'NU', '001204009900', 'Con', '0913888666'),
            (12, 5, 'Bùi Công Tuấn', '1980-01-18', 'NAM', '001080003311', 'Chủ hộ', '0978333111'),
            (13, 5, 'Tạ Minh Tâm', '1984-04-26', 'NU', '001184005522', 'Vợ', '0978333222'),
            (14, 5, 'Bùi Tuấn Kiệt', '2013-12-08', 'NAM', '001213007733', 'Con', None),
            (15, 6, 'Nguyễn Văn An', '1980-05-12', 'NAM', '001080012345', 'Chủ hộ', '0911222333'),
            (16, 6, 'Trần Thị Mai', '1984-08-20', 'NU', '001184054321', 'Vợ', '0911222444'),
            (17, 6, 'Nguyễn Minh Quân', '2012-11-10', 'NAM', '001212009876', 'Con', None),
            (18, 7, 'Lê Hoàng Long', '1975-02-28', 'NAM', '001075034567', 'Chủ hộ', '0988777666'),
            (19, 7, 'Hoàng Thu Thảo', '1979-09-14', 'NU', '001179045678', 'Vợ', '0988777555'),
            (20, 7, 'Lê Gia Hưng', '2008-07-02', 'NAM', '001208056789', 'Con', '0988777444'),
            (21, 8, 'Phạm Văn Hải', '1976-08-19', 'NAM', '001076014422', 'Chủ hộ', '0914144222'),
            (22, 8, 'Đinh Ngọc Lan', '1981-03-24', 'NU', '001181015533', 'Vợ', '0914144333'),
            (23, 8, 'Phạm Hải Nam', '2009-10-15', 'NAM', '001209016644', 'Con', None),
            (24, 8, 'Phạm Thùy Chi', '2016-04-12', 'NU', '001216017755', 'Con', None),
            (25, 9, 'Mai Văn Thịnh', '1982-12-01', 'NAM', '001082016611', 'Chủ hộ', '0916166111'),
            (26, 9, 'Nguyễn Phương Oanh', '1987-05-18', 'NU', '001187017722', 'Vợ', '0916166222'),
            (27, 9, 'Mai Anh Thư', '2015-06-20', 'NU', '001215018833', 'Con', None),
            (28, 10, 'Vương Đình Quang', '1969-10-10', 'NAM', '001069018800', 'Chủ hộ', '0918188000'),
            (29, 10, 'Lâm Thúy Nga', '1974-02-14', 'NU', '001174019911', 'Vợ', '0918188111'),
            (30, 10, 'Vương Đình Khang', '2001-08-25', 'NAM', '001201020022', 'Con', '0918188222'),
            (31, 10, 'Vương Minh Châu', '2007-11-30', 'NU', '001207021133', 'Con', None),
            (32, 12, 'Cao Văn Bách', '1991-03-15', 'NAM', '001091003301', 'Chủ hộ', '0933033001'),
            (33, 12, 'Đào Yến Nhi', '1994-07-28', 'NU', '001194004402', 'Vợ', '0933033002'),
            (34, 13, 'Phạm Quỳnh Nga', '1990-09-15', 'NU', '001190087654', 'Chủ hộ', '0977666555'),
            (35, 13, 'Nguyễn Tiến Dũng', '1988-11-20', 'NAM', '001088098765', 'Chồng', '0977666444'),
            (36, 13, 'Nguyễn Bảo Ngọc', '2018-04-10', 'NU', '001218001122', 'Con', None),
            (37, 14, 'Vũ Đức Thành', '1992-12-05', 'NAM', '001092043210', 'Chủ hộ', '0966555444'),
            (38, 14, 'Bùi Phương Thảo', '1995-06-18', 'NU', '001195054321', 'Vợ', '0966555333'),
            (39, 15, 'Trần Trọng Nghĩa', '1981-08-11', 'NAM', '001081006601', 'Chủ hộ', '0961066001'),
            (40, 15, 'Nguyễn Thanh Hoa', '1985-01-29', 'NU', '001185007702', 'Vợ', '0961066002'),
            (41, 15, 'Trần Bảo Lâm', '2011-09-15', 'NAM', '001211008803', 'Con', None),
            (42, 16, 'John Smith', '1986-05-04', 'NAM', '079086007755', 'Chủ hộ', '0977112233'),
            (43, 16, 'Emily Smith', '1990-12-12', 'NU', '079190008866', 'Vợ', '0977445566'),
            (44, 17, 'Lương Đình Cường', '1979-04-05', 'NAM', '001079009901', 'Chủ hộ', '0992099001'),
            (45, 17, 'Phạm Bích Ngọc', '1983-10-17', 'NU', '001183010002', 'Vợ', '0992099002'),
            (46, 17, 'Lương Thái Sơn', '2012-02-22', 'NAM', '001212011103', 'Con', None),
            (47, 18, 'Trịnh Ngọc Quý', '1985-07-14', 'NAM', '001085011401', 'Chủ hộ', '0911011401'),
            (48, 18, 'Nguyễn Minh Trang', '1989-11-03', 'NU', '001189012502', 'Vợ', '0911011402'),
            (49, 18, 'Trịnh Quang Minh', '2017-06-25', 'NAM', '001217013603', 'Con', None),
            (50, 19, 'Chu Văn Đạt', '1987-03-21', 'NAM', '001087012301', 'Chủ hộ', '0923012301'),
            (51, 19, 'Vũ Thùy Linh', '1991-08-09', 'NU', '001191013402', 'Vợ', '0923012302'),
            (52, 19, 'Chu Hải Phong', '2019-11-14', 'NAM', '001219014503', 'Con', None),
            (53, 20, 'Tạ Hoàng Nam', '1973-09-08', 'NAM', '001073015201', 'Chủ hộ', '0952015201'),
            (54, 20, 'Trần Diệu Linh', '1978-04-16', 'NU', '001178016302', 'Vợ', '0952015202'),
            (55, 20, 'Tạ Gia Phúc', '2005-12-30', 'NAM', '001205017403', 'Con', '0952015203'),
            (56, 20, 'Vũ Thị Lợi', '1948-02-10', 'NU', '001148018504', 'Bố mẹ', None),
            (57, 22, 'Phan Hồng Nhung', '1986-10-11', 'NU', '001186005501', 'Chủ hộ', '0905005501'),
            (58, 22, 'Đỗ Trọng Tấn', '1983-05-17', 'NAM', '001083006602', 'Chồng', '0905005502'),
            (59, 22, 'Đỗ Quỳnh Chi', '2014-03-08', 'NU', '001214007703', 'Con', None),
            (60, 23, 'Nghiêm Xuân Thành', '1979-12-25', 'NAM', '001079006641', 'Chủ hộ', '0964006641'),
            (61, 23, 'Dương Kiều Trang', '1984-06-19', 'NU', '001184007752', 'Vợ', '0964006642'),
            (62, 23, 'Nghiêm Đức Anh', '2010-09-02', 'NAM', '001210008863', 'Con', None),
            (63, 24, 'Bạch Quốc Huy', '1982-01-30', 'NAM', '001082008821', 'Chủ hộ', '0982008821'),
            (64, 24, 'Triệu Thùy Dung', '1987-08-14', 'NU', '001187009932', 'Vợ', '0982008822'),
            (65, 24, 'Bạch Ngọc Hà', '2016-10-21', 'NU', '001216010043', 'Con', None),
            (66, 25, 'Hồ Anh Quân', '1980-07-07', 'NAM', '001080010051', 'Chủ hộ', '0910010051'),
            (67, 25, 'Lưu Thúy Quỳnh', '1985-02-18', 'NU', '001185011162', 'Vợ', '0910010052'),
            (68, 25, 'Hồ Minh Nhật', '2013-05-09', 'NAM', '001213012273', 'Con', None),
            (69, 26, 'Lý Gia Hưng', '1993-04-15', 'NAM', '001093012011', 'Chủ hộ', '0912012011'),
            (70, 26, 'Nguyễn Kiều My', '1996-09-22', 'NU', '001196013122', 'Vợ', '0912012012'),
            (71, 27, 'Hoàng Gia Bảo', '1968-07-22', 'NAM', '001068019283', 'Chủ hộ', '0944333222'),
            (72, 27, 'Đặng Hồng Vân', '1973-11-15', 'NU', '001173028394', 'Vợ', '0944333333'),
            (73, 27, 'Hoàng Minh Khôi', '2000-03-10', 'NAM', '001200037485', 'Con', '0944333444'),
            (74, 27, 'Hoàng Thảo Vy', '2006-08-25', 'NU', '001206046576', 'Con', None),
            (75, 28, 'Đặng Thu Trang', '1995-04-18', 'NU', '001195076543', 'Chủ hộ', '0933222111'),
            (76, 28, 'Trần Quang Hải', '1992-09-09', 'NAM', '001092065432', 'Chồng', '0933222000'),
            (77, 29, 'Dương Minh Tuấn', '1971-03-03', 'NAM', '001071017031', 'Chủ hộ', '0917017031'),
            (78, 29, 'Phạm Quỳnh Chi', '1976-08-20', 'NU', '001176018142', 'Vợ', '0917017032'),
            (79, 29, 'Dương Minh Đức', '2002-05-14', 'NAM', '001202019253', 'Con', '0917017033'),
            (80, 29, 'Dương Ngọc Diệp', '2009-12-01', 'NU', '001209020364', 'Con', None)
        ]
        cursor.executemany("INSERT INTO NHAN_KHAU (ma_nk, ma_ho, ho_ten, ngay_sinh, gioi_tinh, so_cccd, quan_he_chu_ho, so_dien_thoai) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", residents)

        # Cập nhật mã chủ hộ cho HO_KHAU
        chu_ho_map = {
            1: 1, 2: 4, 3: 7, 4: 9, 5: 12, 6: 15, 7: 18, 8: 21, 9: 25, 10: 28,
            12: 32, 13: 34, 14: 37, 15: 39, 16: 42, 17: 44, 18: 47, 19: 50, 20: 53,
            22: 57, 23: 60, 24: 63, 25: 66, 26: 69, 27: 71, 28: 75, 29: 77
        }
        for ma_ho, ma_chu_ho in chu_ho_map.items():
            cursor.execute("UPDATE HO_KHAU SET ma_chu_ho = ? WHERE ma_ho = ?", (ma_chu_ho, ma_ho))

        # 3. BẢNG NGUOI_DUNG (Cán bộ & Cư dân đại diện các tháp)
        users = [
            ('admin', 'admin123', 'Quản trị viên Hệ thống', 'ADMIN', None, '0901234567'),
            ('bqt_truongban', 'bqt123', 'Trưởng Ban Quản Trị (Hoàng Gia Bảo)', 'BAN_QUAN_TRI', None, '0944333222'),
            ('bqt_phoban', 'bqt123', 'Phó Ban Quản Trị (Lê Hoàng Long)', 'BAN_QUAN_TRI', None, '0988777666'),
            ('ketoan_minh', 'ketoan123', 'Kế toán trưởng Nguyễn Hồng Minh', 'KE_TOAN', None, '0987654321'),
            ('ketoan_thu', 'ketoan123', 'Thu ngân viên Trần Thị Mai', 'KE_TOAN', None, '0911222444'),
            ('cudan_a1205', '123456', 'Nguyễn Văn An (Chủ hộ A1205)', 'CU_DAN', 6, '0911222333'),
            ('cudan_a0801', '123456', 'Đỗ Văn Minh (Chủ hộ A0801)', 'CU_DAN', 4, '0913888999'),
            ('cudan_a1801', '123456', 'Vương Đình Quang (Chủ hộ A1801)', 'CU_DAN', 10, '0918188000'),
            ('cudan_b0402', '123456', 'Phạm Quỳnh Nga (Chủ hộ B0402)', 'CU_DAN', 13, '0977666555'),
            ('cudan_b0403', '123456', 'Vũ Đức Thành (Chủ hộ B0403)', 'CU_DAN', 14, '0966555444'),
            ('cudan_b1104', '123456', 'Trịnh Ngọc Quý (Chủ hộ B1104)', 'CU_DAN', 18, '0911011401'),
            ('cudan_c0501', '123456', 'Phan Hồng Nhung (Chủ hộ C0501)', 'CU_DAN', 22, '0905005501'),
            ('cudan_c1501', '123456', 'Hoàng Gia Bảo (Chủ hộ C1501)', 'CU_DAN', 27, '0944333222'),
            ('cudan_c1703', '123456', 'Dương Minh Tuấn (Chủ hộ C1703)', 'CU_DAN', 29, '0917017031')
        ]
        cursor.executemany("INSERT INTO NGUOI_DUNG (ten_dang_nhap, mat_khau, ho_ten, vai_tro, ma_ho, so_dien_thoai) VALUES (?, ?, ?, ?, ?, ?)", users)

        # 4. BẢNG PHUONG_TIEN (49 phương tiện)
        vehicles = [
            (1, 'XE_MAY', '29B1-123.45', 'Honda AirBlade'), (1, 'XE_MAY', '29B1-234.56', 'Honda Vision'),
            (2, 'XE_MAY', '29B2-345.67', 'Yamaha Grande'), (2, 'O_TO', '30G-112.23', 'Toyota Vios'),
            (3, 'XE_MAY', '29C1-456.78', 'Honda Lead'), (4, 'XE_MAY', '29C2-567.89', 'Honda SH 125i'),
            (4, 'O_TO', '30H-223.34', 'Hyundai Tucson'), (5, 'XE_MAY', '29D1-678.90', 'Yamaha NVX'),
            (5, 'O_TO', '30H-334.45', 'Kia Seltos'), (6, 'XE_MAY', '29B1-888.88', 'Honda SH 150i'),
            (6, 'XE_MAY', '29B1-678.90', 'Honda AirBlade'), (6, 'O_TO', '30F-123.45', 'Mazda CX-5'),
            (7, 'XE_MAY', '29C1-555.55', 'Yamaha Grande'), (7, 'XE_DAP_DIEN', '29MD-012.34', 'VinFast Feliz'),
            (8, 'XE_MAY', '29E1-111.22', 'Honda Vision'), (8, 'O_TO', '30G-445.56', 'Ford Everest'),
            (9, 'XE_MAY', '29E2-222.33', 'Vespa Primavera'), (9, 'O_TO', '30H-556.67', 'Honda CR-V'),
            (10, 'O_TO', '30K-999.99', 'Mercedes-Benz E300'), (10, 'O_TO', '30K-888.88', 'Porsche Macan'),
            (10, 'XE_MAY', '29E3-999.99', 'BMW R1250'), (12, 'XE_MAY', '29F1-333.44', 'Honda Winner X'),
            (13, 'O_TO', '30G-999.99', 'Mercedes C200'), (13, 'XE_MAY', '29F2-444.55', 'Honda SH Mode'),
            (14, 'XE_MAY', '29D1-333.33', 'Honda Wave Alpha'), (15, 'XE_MAY', '29G1-555.66', 'Yamaha Exciter'),
            (15, 'O_TO', '30F-667.78', 'Mazda 3'), (16, 'XE_MAY', '29G2-666.77', 'Honda AirBlade'),
            (17, 'XE_MAY', '29H1-777.88', 'Honda Lead'), (17, 'O_TO', '30E-778.89', 'VinFast VF8'),
            (18, 'XE_MAY', '29H2-888.99', 'Honda SH 150i'), (18, 'O_TO', '30G-889.90', 'Toyota Camry'),
            (19, 'XE_MAY', '29K1-111.00', 'Yamaha Janus'), (20, 'O_TO', '30F-990.01', 'Lexus RX350'),
            (20, 'XE_MAY', '29K2-222.11', 'Vespa Sprint'), (22, 'XE_MAY', '29L1-333.22', 'Honda Vision'),
            (22, 'O_TO', '30H-001.12', 'Kia Carnival'), (23, 'XE_MAY', '29L2-444.33', 'Honda Future'),
            (24, 'XE_MAY', '29M1-555.44', 'Honda SH 125i'), (24, 'O_TO', '30G-112.34', 'Hyundai SantaFe'),
            (25, 'XE_MAY', '29M2-666.55', 'Yamaha Grande'), (26, 'XE_MAY', '29N1-777.66', 'Honda AirBlade'),
            (27, 'O_TO', '30H-888.66', 'Toyota Camry'), (27, 'XE_MAY', '29E1-777.77', 'Vespa Sprint'),
            (27, 'XE_MAY', '29N2-888.77', 'Honda Lead'), (28, 'XE_MAY', '29P1-999.88', 'Honda Vision'),
            (29, 'O_TO', '30K-777.77', 'BMW X5'), (29, 'O_TO', '30K-666.66', 'Mercedes GLC 300'),
            (29, 'XE_MAY', '29P2-111.99', 'Honda SH 350i')
        ]
        cursor.executemany("INSERT INTO PHUONG_TIEN (ma_ho, loai_xe, bien_so, ten_xe) VALUES (?, ?, ?, ?)", vehicles)

        # 5. BẢNG TAM_TRU_TAM_VANG
        temporary = [
            (7, 'TAM_TRU', '2026-03-01', '2027-03-01', 'Chuyên gia Hàn Quốc làm việc tại Samsung R&D'),
            (8, 'TAM_TRU', '2026-03-01', '2027-03-01', 'Vợ đi cùng chuyên gia'),
            (42, 'TAM_TRU', '2026-02-01', '2027-02-01', 'Giảng viên tiếng Anh tại trường quốc tế'),
            (43, 'TAM_TRU', '2026-02-01', '2027-02-01', 'Vợ chuyên gia'),
            (69, 'TAM_TRU', '2026-05-15', '2027-05-15', 'Kỹ sư phần mềm thuê nhà ở dài hạn'),
            (70, 'TAM_TRU', '2026-05-15', '2027-05-15', 'Vợ người thuê'),
            (3, 'TAM_VANG', '2026-08-01', '2026-12-31', 'Tham gia khóa huấn luyện năng khiếu thể thao'),
            (11, 'TAM_VANG', '2026-09-01', '2027-06-30', 'Sinh viên du học trao đổi tại Nhật Bản'),
            (30, 'TAM_VANG', '2026-06-01', '2027-06-01', 'Du học thạc sĩ tại Anh Quốc'),
            (55, 'TAM_VANG', '2026-09-15', '2027-01-15', 'Học kỳ quân sự đại học tại Xuân Hòa'),
            (73, 'TAM_VANG', '2026-10-01', '2026-11-15', 'Công tác dự án kỹ thuật tại Đà Nẵng'),
            (79, 'TAM_VANG', '2026-08-15', '2027-05-30', 'Học đại học tại TP. Hồ Chí Minh')
        ]
        cursor.executemany("INSERT INTO TAM_TRU_TAM_VANG (ma_nk, loai, tu_ngay, den_ngay, ly_do) VALUES (?, ?, ?, ?, ?)", temporary)

        # 6. BẢNG KHOAN_THU
        fees = [
            (1, 'Phí dịch vụ chung cư', 'BAT_BUOC', 'THEO_DIEN_TICH', 12000, 'Khung quy định: 2.500 - 16.500 đ/m2/tháng', 1),
            (2, 'Phí quản lý vận hành', 'BAT_BUOC', 'THEO_DIEN_TICH', 7000, 'Mức áp dụng hiện hành: 7.000 đ/m2/tháng', 1),
            (3, 'Phí trông giữ xe máy', 'BAT_BUOC', 'THEO_XE_MAY', 70000, 'Đơn giá: 70.000 đ/xe máy/tháng', 1),
            (4, 'Phí trông giữ xe ô tô', 'BAT_BUOC', 'THEO_O_TO', 1200000, 'Đơn giá: 1.200.000 đ/xe ô tô/tháng', 1),
            (5, 'Tiền điện sinh hoạt (Thu hộ)', 'THU_HO', 'NHAP_TAY', 0, 'Nhập theo hóa đơn thực tế của Điện lực EVN', 1),
            (6, 'Tiền nước sinh hoạt (Thu hộ)', 'THU_HO', 'NHAP_TAY', 0, 'Nhập theo hóa đơn thực tế của Cty Nước sạch', 1),
            (7, 'Quỹ Vì người nghèo', 'TU_NGUYEN', 'THEO_HO', 50000, 'Vận động ủng hộ vì người nghèo năm 2026', 1),
            (8, 'Quỹ Đền ơn đáp nghĩa 27/7', 'TU_NGUYEN', 'THEO_HO', 50000, 'Ủng hộ tri ân ngày thương binh liệt sĩ', 1),
            (9, 'Quỹ Tết thiếu nhi 1/6', 'TU_NGUYEN', 'THEO_HO', 100000, 'Quỹ tổ chức sự kiện thiếu nhi chung cư Blue Moon', 1)
        ]
        cursor.executemany("INSERT INTO KHOAN_THU (ma_kt, ten_khoan_thu, loai, cach_tinh, don_gia, ghi_chu, kich_hoat) VALUES (?, ?, ?, ?, ?, ?, ?)", fees)

        # 7. BẢNG DOT_THU
        cursor.execute("INSERT INTO DOT_THU (ma_dot, ten_dot, thang_nam, ngay_bat_dau, han_nop, trang_thai) VALUES (1, 'Thu phí tháng 10/2026', '2026-10', '2026-10-01', '2026-10-25', 'DA_KHOA')")
        cursor.execute("INSERT INTO DOT_THU (ma_dot, ten_dot, thang_nam, ngay_bat_dau, han_nop, trang_thai) VALUES (2, 'Thu phí tháng 11/2026', '2026-11', '2026-11-01', '2026-11-25', 'DANG_THU')")

        # 8. BẢNG CHI_TIET_THU & PHIEU_THU
        active_apts = cursor.execute("SELECT * FROM HO_KHAU WHERE trang_thai != 'TRONG'").fetchall()
        veh_counts = {}
        for r in cursor.execute("SELECT ma_ho, loai_xe, COUNT(*) as c FROM PHUONG_TIEN GROUP BY ma_ho, loai_xe").fetchall():
            if r['ma_ho'] not in veh_counts:
                veh_counts[r['ma_ho']] = {'XE_MAY': 0, 'O_TO': 0, 'XE_DAP_DIEN': 0}
            veh_counts[r['ma_ho']][r['loai_xe']] = r['c']

        chi_tiet_records = []
        for apt in active_apts:
            ma_ho = apt['ma_ho']
            dien_tich = apt['dien_tich']
            xe = veh_counts.get(ma_ho, {'XE_MAY': 0, 'O_TO': 0, 'XE_DAP_DIEN': 0})

            ratio = 1.0
            if apt['so_can_ho'] == 'B0403':
                ratio = 16.0 / 31.0

            phi_dv = round(12000 * dien_tich * ratio)
            phi_ql = round(7000 * dien_tich * ratio)
            phi_xm = xe['XE_MAY'] * 70000
            phi_oto = xe['O_TO'] * 1200000
            tien_dien = int(350000 + (dien_tich * 4500))
            tien_nuoc = int(90000 + (dien_tich * 1200))

            is_paid_full = ma_ho in (1, 2, 4, 6, 8, 10, 18, 20, 27, 29)
            is_paid_partial = ma_ho in (5, 9, 14, 23)

            da_nop_dv = phi_dv if is_paid_full else (round(phi_dv * 0.5) if is_paid_partial else 0)
            st_dv = 'DA_NOP_DU' if da_nop_dv >= phi_dv else ('NOP_THIEU' if da_nop_dv > 0 else 'CHUA_NOP')
            chi_tiet_records.append((2, ma_ho, 1, phi_dv, da_nop_dv, st_dv, 'Phí dịch vụ T11'))

            da_nop_ql = phi_ql if is_paid_full else 0
            st_ql = 'DA_NOP_DU' if da_nop_ql >= phi_ql else 'CHUA_NOP'
            chi_tiet_records.append((2, ma_ho, 2, phi_ql, da_nop_ql, st_ql, 'Phí quản lý T11'))

            if phi_xm > 0:
                da_nop_xm = phi_xm if (is_paid_full or is_paid_partial) else 0
                st_xm = 'DA_NOP_DU' if da_nop_xm >= phi_xm else 'CHUA_NOP'
                chi_tiet_records.append((2, ma_ho, 3, phi_xm, da_nop_xm, st_xm, f'Phí gửi {xe["XE_MAY"]} xe máy'))

            if phi_oto > 0:
                da_nop_oto = phi_oto if is_paid_full else 0
                st_oto = 'DA_NOP_DU' if da_nop_oto >= phi_oto else 'CHUA_NOP'
                chi_tiet_records.append((2, ma_ho, 4, phi_oto, da_nop_oto, st_oto, f'Phí gửi {xe["O_TO"]} ô tô'))

            da_nop_dien = tien_dien if is_paid_full else 0
            st_dien = 'DA_NOP_DU' if da_nop_dien >= tien_dien else 'CHUA_NOP'
            chi_tiet_records.append((2, ma_ho, 5, tien_dien, da_nop_dien, st_dien, 'Hóa đơn EVN T11'))

            da_nop_nuoc = tien_nuoc if is_paid_full else 0
            st_nuoc = 'DA_NOP_DU' if da_nop_nuoc >= tien_nuoc else 'CHUA_NOP'
            chi_tiet_records.append((2, ma_ho, 6, tien_nuoc, da_nop_nuoc, st_nuoc, 'Nước sạch T11'))

            if ma_ho % 2 == 0:
                chi_tiet_records.append((2, ma_ho, 7, 50000, 50000 if is_paid_full else 0, 'DA_NOP_DU' if is_paid_full else 'CHUA_NOP', 'Ủng hộ người nghèo'))

        cursor.executemany("INSERT INTO CHI_TIET_THU (ma_dot, ma_ho, ma_kt, so_tien_phai_nop, so_tien_da_nop, trang_thai, ghi_chu) VALUES (?, ?, ?, ?, ?, ?, ?)", chi_tiet_records)

        # Biên lai phiếu thu
        paid_details = cursor.execute("""
        SELECT ct.ma_ct, ct.so_tien_da_nop, ct.ghi_chu, h.so_can_ho, nk.ho_ten as ten_chu_ho
        FROM CHI_TIET_THU ct
        JOIN HO_KHAU h ON ct.ma_ho = h.ma_ho
        LEFT JOIN NHAN_KHAU nk ON h.ma_chu_ho = nk.ma_nk
        WHERE ct.so_tien_da_nop > 0
        """).fetchall()

        receipt_seq = 1
        receipt_records = []
        for p in paid_details:
            ma_phieu = f"PT-202611-{receipt_seq:04d}"
            receipt_seq += 1
            nguoi_nop = p['ten_chu_ho'] or f"Chủ hộ {p['so_can_ho']}"
            phuong_thuc = 'CHUYEN_KHOAN' if receipt_seq % 2 == 0 else 'TIEN_MAT'
            receipt_records.append((
                ma_phieu, p['ma_ct'], p['so_tien_da_nop'],
                f"2026-11-0{min(9, (receipt_seq % 7) + 2)} 09:{10 + (receipt_seq % 45)}:00",
                nguoi_nop, phuong_thuc, 4, p['ghi_chu'] or 'Thu phí kỳ tháng 11/2026'
            ))

        cursor.executemany("INSERT INTO PHIEU_THU (ma_phieu, ma_ct, so_tien, ngay_nop, nguoi_nop, phuong_thuc, ma_tk_thu, ghi_chu) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", receipt_records)

        conn.commit()
        print("[OK] Đã tự động khởi tạo cơ sở dữ liệu mở rộng Blue Moon (29 căn hộ, 80 cư dân, 49 xe)!")

    conn.close()

# ====================================================================
# BỘ XỬ LÝ YÊU CẦU HTTP (HTTP REQUEST HANDLER)
# ====================================================================
class BlueMoonRequestHandler(http.server.BaseHTTPRequestHandler):
    def end_headers(self):
        # Thiết lập CORS headers để hỗ trợ gọi API mượt mà
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status_code=200):
        """Hàm trợ giúp trả về phản hồi định dạng JSON UTF-8"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def get_post_data(self):
        """Đọc và giải mã dữ liệu JSON gửi lên từ Client"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body.decode('utf-8'))
        return {}

    def get_caller_role(self, body=None):
        """Xác định vai trò của người gọi API từ Header HTTP hoặc Request Payload"""
        role = self.headers.get('X-User-Role')
        if not role and body and isinstance(body, dict):
            role = body.get('caller_role') or body.get('user_role') or body.get('role')
        return (role or '').strip().upper()

    # ----------------------------------------------------------------
    # XỬ LÝ GET REQUEST
    # ----------------------------------------------------------------
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # 1. API: Danh sách Căn hộ / Hộ khẩu (UC02)
        if path == '/api/apartments':
            conn = get_db()
            cursor = conn.cursor()
            query = """
            SELECT h.*, 
                   nk.ho_ten AS ten_chu_ho, 
                   nk.so_dien_thoai AS sdt_chu_ho,
                   (SELECT COUNT(*) FROM NHAN_KHAU WHERE ma_ho = h.ma_ho) AS so_nhan_khau,
                   (SELECT COUNT(*) FROM PHUONG_TIEN WHERE ma_ho = h.ma_ho AND loai_xe = 'XE_MAY') AS so_xe_may,
                   (SELECT COUNT(*) FROM PHUONG_TIEN WHERE ma_ho = h.ma_ho AND loai_xe = 'O_TO') AS so_o_to
            FROM HO_KHAU h
            LEFT JOIN NHAN_KHAU nk ON h.ma_chu_ho = nk.ma_nk
            ORDER BY h.so_can_ho ASC
            """
            rows = cursor.execute(query).fetchall()
            apartments = [dict(r) for r in rows]
            conn.close()
            self.send_json({"success": True, "data": apartments})
            return

        # 2. API: Danh sách Cư dân / Nhân khẩu (UC03)
        elif path == '/api/residents':
            conn = get_db()
            cursor = conn.cursor()
            ma_ho = query_params.get('ma_ho', [None])[0]
            if ma_ho:
                rows = cursor.execute("""
                SELECT nk.*, h.so_can_ho 
                FROM NHAN_KHAU nk 
                JOIN HO_KHAU h ON nk.ma_ho = h.ma_ho 
                WHERE nk.ma_ho = ?
                ORDER BY nk.quan_he_chu_ho = 'Chủ hộ' DESC, nk.ho_ten ASC
                """, (ma_ho,)).fetchall()
            else:
                rows = cursor.execute("""
                SELECT nk.*, h.so_can_ho 
                FROM NHAN_KHAU nk 
                JOIN HO_KHAU h ON nk.ma_ho = h.ma_ho 
                ORDER BY h.so_can_ho ASC, nk.quan_he_chu_ho = 'Chủ hộ' DESC
                """).fetchall()
            residents = [dict(r) for r in rows]
            conn.close()
            self.send_json({"success": True, "data": residents})
            return

        # 3. API: Danh sách Tạm trú, Tạm vắng (UC04)
        elif path == '/api/temporary-residence':
            conn = get_db()
            cursor = conn.cursor()
            rows = cursor.execute("""
            SELECT ttv.*, nk.ho_ten, nk.so_cccd, h.so_can_ho 
            FROM TAM_TRU_TAM_VANG ttv
            JOIN NHAN_KHAU nk ON ttv.ma_nk = nk.ma_nk
            JOIN HO_KHAU h ON nk.ma_ho = h.ma_ho
            ORDER BY ttv.ma_ttv DESC
            """).fetchall()
            records = [dict(r) for r in rows]
            conn.close()
            self.send_json({"success": True, "data": records})
            return

        # 4. API: Danh sách Phương tiện gửi xe (UC05)
        elif path == '/api/vehicles':
            conn = get_db()
            cursor = conn.cursor()
            rows = cursor.execute("""
            SELECT pt.*, h.so_can_ho, nk.ho_ten as ten_chu_ho
            FROM PHUONG_TIEN pt
            JOIN HO_KHAU h ON pt.ma_ho = h.ma_ho
            LEFT JOIN NHAN_KHAU nk ON h.ma_chu_ho = nk.ma_nk
            ORDER BY h.so_can_ho ASC, pt.loai_xe DESC
            """).fetchall()
            vehicles = [dict(r) for r in rows]
            conn.close()
            self.send_json({"success": True, "data": vehicles})
            return

        # 5. API: Danh mục Khoản thu & Đơn giá (UC06)
        elif path == '/api/fees':
            conn = get_db()
            cursor = conn.cursor()
            rows = cursor.execute("SELECT * FROM KHOAN_THU ORDER BY loai ASC, ma_kt ASC").fetchall()
            fees = [dict(r) for r in rows]
            conn.close()
            self.send_json({"success": True, "data": fees})
            return

        # 6. API: Danh sách Đợt thu phí (UC07)
        elif path == '/api/periods':
            conn = get_db()
            cursor = conn.cursor()
            query = """
            SELECT d.*,
                   COUNT(DISTINCT c.ma_ho) AS tong_so_ho,
                   IFNULL(SUM(c.so_tien_phai_nop), 0) AS tong_phai_thu,
                   IFNULL(SUM(c.so_tien_da_nop), 0) AS tong_da_thu
            FROM DOT_THU d
            LEFT JOIN CHI_TIET_THU c ON d.ma_dot = c.ma_dot
            GROUP BY d.ma_dot
            ORDER BY d.thang_nam DESC
            """
            rows = cursor.execute(query).fetchall()
            periods = [dict(r) for r in rows]
            conn.close()
            self.send_json({"success": True, "data": periods})
            return

        # 7. API: Chi tiết đợt thu theo từng hộ (UC07, UC08, UC09)
        elif path.startswith('/api/periods/') and path.endswith('/details'):
            # Path dạng: /api/periods/<ma_dot>/details
            parts = path.split('/')
            ma_dot = int(parts[3])
            so_can_ho = query_params.get('so_can_ho', [None])[0]

            conn = get_db()
            cursor = conn.cursor()

            sql = """
            SELECT c.*, h.so_can_ho, h.dien_tich, nk.ho_ten AS ten_chu_ho, kt.ten_khoan_thu, kt.loai, kt.don_gia,
                   (c.so_tien_phai_nop - c.so_tien_da_nop) AS con_no
            FROM CHI_TIET_THU c
            JOIN HO_KHAU h ON c.ma_ho = h.ma_ho
            LEFT JOIN NHAN_KHAU nk ON h.ma_chu_ho = nk.ma_nk
            JOIN KHOAN_THU kt ON c.ma_kt = kt.ma_kt
            WHERE c.ma_dot = ?
            """
            params = [ma_dot]
            if so_can_ho:
                sql += " AND h.so_can_ho LIKE ?"
                params.append(f"%{so_can_ho}%")
            
            sql += " ORDER BY h.so_can_ho ASC, kt.ma_kt ASC"

            rows = cursor.execute(sql, params).fetchall()
            details = [dict(r) for r in rows]
            conn.close()
            self.send_json({"success": True, "data": details})
            return

        # 8. API: Lấy công nợ của 1 căn hộ cụ thể trong đợt thu (UC09)
        elif path == '/api/household-debt':
            ma_dot = query_params.get('ma_dot', [None])[0]
            so_can_ho = query_params.get('so_can_ho', [None])[0]

            if not so_can_ho:
                self.send_json({"success": False, "message": "Vui lòng truyền số căn hộ"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()

            # Lấy thông tin căn hộ
            ho = cursor.execute("""
            SELECT h.*, nk.ho_ten as ten_chu_ho, nk.so_dien_thoai
            FROM HO_KHAU h
            LEFT JOIN NHAN_KHAU nk ON h.ma_chu_ho = nk.ma_nk
            WHERE h.so_can_ho = ?
            """, (so_can_ho,)).fetchone()

            if not ho:
                conn.close()
                self.send_json({"success": False, "message": f"Không tìm thấy căn hộ {so_can_ho}"}, 404)
                return

            ho_dict = dict(ho)

            # Lấy các khoản nợ của căn hộ
            sql_debts = """
            SELECT c.*, kt.ten_khoan_thu, kt.loai, d.ten_dot, d.thang_nam,
                   (c.so_tien_phai_nop - c.so_tien_da_nop) AS con_no
            FROM CHI_TIET_THU c
            JOIN KHOAN_THU kt ON c.ma_kt = kt.ma_kt
            JOIN DOT_THU d ON c.ma_dot = d.ma_dot
            WHERE c.ma_ho = ? AND (c.so_tien_phai_nop - c.so_tien_da_nop) > 0
            """
            params_debts = [ho_dict['ma_ho']]
            if ma_dot:
                sql_debts += " AND c.ma_dot = ?"
                params_debts.append(ma_dot)

            sql_debts += " ORDER BY c.ma_dot DESC, kt.ma_kt ASC"
            debts = [dict(r) for r in cursor.execute(sql_debts, params_debts).fetchall()]

            conn.close()
            self.send_json({"success": True, "household": ho_dict, "debts": debts})
            return

        # 9. API: Danh sách Phiếu thu biên lai (UC09, in laser)
        elif path == '/api/receipts':
            conn = get_db()
            cursor = conn.cursor()
            rows = cursor.execute("""
            SELECT pt.*, h.so_can_ho, kt.ten_khoan_thu, d.ten_dot, d.thang_nam, nd.ho_ten as ten_thu_ngan
            FROM PHIEU_THU pt
            JOIN CHI_TIET_THU ct ON pt.ma_ct = ct.ma_ct
            JOIN HO_KHAU h ON ct.ma_ho = h.ma_ho
            JOIN KHOAN_THU kt ON ct.ma_kt = kt.ma_kt
            JOIN DOT_THU d ON ct.ma_dot = d.ma_dot
            LEFT JOIN NGUOI_DUNG nd ON pt.ma_tk_thu = nd.ma_tk
            ORDER BY pt.ngay_nop DESC
            LIMIT 100
            """).fetchall()
            receipts = [dict(r) for r in rows]
            conn.close()
            self.send_json({"success": True, "data": receipts})
            return

        # 10. API: Báo cáo Thống kê tổng quan (UC10)
        elif path == '/api/statistics':
            conn = get_db()
            cursor = conn.cursor()

            # Tổng quan căn hộ & dân cư
            total_apartments = cursor.execute("SELECT COUNT(*) AS c FROM HO_KHAU").fetchone()['c']
            occupied_apartments = cursor.execute("SELECT COUNT(*) AS c FROM HO_KHAU WHERE trang_thai = 'DANG_O'").fetchone()['c']
            total_residents = cursor.execute("SELECT COUNT(*) AS c FROM NHAN_KHAU").fetchone()['c']
            total_vehicles = cursor.execute("SELECT COUNT(*) AS c FROM PHUONG_TIEN").fetchone()['c']

            # Thống kê tài chính
            finance = cursor.execute("""
            SELECT IFNULL(SUM(so_tien_phai_nop), 0) AS tong_phai_thu,
                   IFNULL(SUM(so_tien_da_nop), 0) AS tong_da_thu
            FROM CHI_TIET_THU
            """).fetchone()

            tong_phai_thu = finance['tong_phai_thu']
            tong_da_thu = finance['tong_da_thu']
            tong_con_no = tong_phai_thu - tong_da_thu
            ty_le_thu = round((tong_da_thu / tong_phai_thu * 100), 1) if tong_phai_thu > 0 else 0

            # Thống kê theo từng loại khoản thu
            by_fee_rows = cursor.execute("""
            SELECT kt.ten_khoan_thu, kt.loai,
                   IFNULL(SUM(c.so_tien_phai_nop), 0) AS phai_thu,
                   IFNULL(SUM(c.so_tien_da_nop), 0) AS da_thu
            FROM KHOAN_THU kt
            LEFT JOIN CHI_TIET_THU c ON kt.ma_kt = c.ma_kt
            GROUP BY kt.ma_kt
            ORDER BY phai_thu DESC
            """).fetchall()
            by_fee = [dict(r) for r in by_fee_rows]

            # Top các căn hộ còn nợ nhiều nhất
            debtors_rows = cursor.execute("""
            SELECT h.so_can_ho, nk.ho_ten AS ten_chu_ho,
                   SUM(c.so_tien_phai_nop - c.so_tien_da_nop) AS tong_no
            FROM CHI_TIET_THU c
            JOIN HO_KHAU h ON c.ma_ho = h.ma_ho
            LEFT JOIN NHAN_KHAU nk ON h.ma_chu_ho = nk.ma_nk
            WHERE (c.so_tien_phai_nop - c.so_tien_da_nop) > 0
            GROUP BY h.ma_ho
            ORDER BY tong_no DESC
            LIMIT 10
            """).fetchall()
            debtors = [dict(r) for r in debtors_rows]

            conn.close()
            self.send_json({
                "success": True,
                "data": {
                    "overview": {
                        "total_apartments": total_apartments,
                        "occupied_apartments": occupied_apartments,
                        "total_residents": total_residents,
                        "total_vehicles": total_vehicles,
                        "tong_phai_thu": tong_phai_thu,
                        "tong_da_thu": tong_da_thu,
                        "tong_con_no": tong_con_no,
                        "ty_le_thu": ty_le_thu
                    },
                    "by_fee": by_fee,
                    "top_debtors": debtors
                }
            })
            return

        # 11. API: Danh sách Người dùng hệ thống (UC11)
        elif path == '/api/users':
            conn = get_db()
            cursor = conn.cursor()
            rows = cursor.execute("SELECT ma_tk, ten_dang_nhap, ho_ten, vai_tro, so_dien_thoai, trang_thai, ngay_tao FROM NGUOI_DUNG ORDER BY ma_tk ASC").fetchall()
            users = [dict(r) for r in rows]
            conn.close()
            self.send_json({"success": True, "data": users})
            return

        # 12. API: Sao lưu dữ liệu CSDL dạng JSON (UC12)
        elif path == '/api/backup':
            conn = get_db()
            cursor = conn.cursor()
            backup_data = {}
            tables = ['NGUOI_DUNG', 'HO_KHAU', 'NHAN_KHAU', 'TAM_TRU_TAM_VANG', 'PHUONG_TIEN', 'KHOAN_THU', 'DOT_THU', 'CHI_TIET_THU', 'PHIEU_THU']
            for t in tables:
                rows = cursor.execute(f"SELECT * FROM {t}").fetchall()
                backup_data[t] = [dict(r) for r in rows]
            conn.close()
            self.send_json({"success": True, "backup_date": datetime.now().isoformat(), "database": backup_data})
            return

        # 13. API: Dành riêng cho Cư dân / Chủ hộ (Xem công nợ, hạn nộp, thành viên, xe cộ)
        elif path == '/api/resident/portal':
            ma_ho = query_params.get('ma_ho', [1])[0]
            conn = get_db()
            cursor = conn.cursor()

            apartment = cursor.execute("""
            SELECT h.*, nk.ho_ten as ten_chu_ho, nk.so_dien_thoai as sdt_chu_ho
            FROM HO_KHAU h
            LEFT JOIN NHAN_KHAU nk ON h.ma_chu_ho = nk.ma_nk
            WHERE h.ma_ho = ?
            """, (ma_ho,)).fetchone()

            if not apartment:
                conn.close()
                self.send_json({"success": False, "message": "Không tìm thấy thông tin căn hộ"}, 404)
                return

            members = [dict(r) for r in cursor.execute("""
            SELECT * FROM NHAN_KHAU WHERE ma_ho = ? ORDER BY quan_he_chu_ho = 'Chủ hộ' DESC, ho_ten ASC
            """, (ma_ho,)).fetchall()]

            vehicles = [dict(r) for r in cursor.execute("""
            SELECT * FROM PHUONG_TIEN WHERE ma_ho = ? ORDER BY loai_xe DESC
            """, (ma_ho,)).fetchall()]

            bills = [dict(r) for r in cursor.execute("""
            SELECT c.*, kt.ten_khoan_thu, kt.loai, kt.don_gia,
                   d.ten_dot, d.thang_nam, d.han_nop, d.ngay_bat_dau,
                   (c.so_tien_phai_nop - c.so_tien_da_nop) AS con_no
            FROM CHI_TIET_THU c
            JOIN KHOAN_THU kt ON c.ma_kt = kt.ma_kt
            JOIN DOT_THU d ON c.ma_dot = d.ma_dot
            WHERE c.ma_ho = ?
            ORDER BY (c.so_tien_phai_nop - c.so_tien_da_nop) DESC, d.thang_nam DESC, kt.ma_kt ASC
            """, (ma_ho,)).fetchall()]

            receipts = [dict(r) for r in cursor.execute("""
            SELECT pt.*, kt.ten_khoan_thu, d.ten_dot, d.thang_nam
            FROM PHIEU_THU pt
            JOIN CHI_TIET_THU c ON pt.ma_ct = c.ma_ct
            JOIN KHOAN_THU kt ON c.ma_kt = kt.ma_kt
            JOIN DOT_THU d ON c.ma_dot = d.ma_dot
            WHERE c.ma_ho = ?
            ORDER BY pt.ngay_nop DESC
            """, (ma_ho,)).fetchall()]

            proposals = [dict(r) for r in cursor.execute("""
            SELECT yc.*, yc.ma_yc AS ma_kn, yc.phan_hoi AS phan_hoi_bqt 
            FROM YEU_CAU_KIEN_NGHI yc 
            WHERE yc.ma_ho = ? 
            ORDER BY yc.ma_yc DESC
            """, (ma_ho,)).fetchall()]

            conn.close()
            self.send_json({
                "success": True,
                "data": {
                    "apartment": dict(apartment),
                    "members": members,
                    "vehicles": vehicles,
                    "bills": bills,
                    "receipts": receipts,
                    "proposals": proposals
                }
            })
            return

        # 14. API: Danh sách Đề xuất & Kiến nghị cư dân gửi tới BQT / Admin
        elif path == '/api/proposals':
            conn = get_db()
            cursor = conn.cursor()
            ma_ho = query_params.get('ma_ho', [None])[0]
            if ma_ho:
                rows = cursor.execute("""
                SELECT yc.*, yc.ma_yc AS ma_kn, yc.phan_hoi AS phan_hoi_bqt, h.so_can_ho, nk.ho_ten as ten_chu_ho
                FROM YEU_CAU_KIEN_NGHI yc
                JOIN HO_KHAU h ON yc.ma_ho = h.ma_ho
                LEFT JOIN NHAN_KHAU nk ON h.ma_chu_ho = nk.ma_nk
                WHERE yc.ma_ho = ?
                ORDER BY yc.ma_yc DESC
                """, (ma_ho,)).fetchall()
            else:
                rows = cursor.execute("""
                SELECT yc.*, yc.ma_yc AS ma_kn, yc.phan_hoi AS phan_hoi_bqt, h.so_can_ho, nk.ho_ten as ten_chu_ho
                FROM YEU_CAU_KIEN_NGHI yc
                JOIN HO_KHAU h ON yc.ma_ho = h.ma_ho
                LEFT JOIN NHAN_KHAU nk ON h.ma_chu_ho = nk.ma_nk
                ORDER BY CASE yc.trang_thai WHEN 'CHO_DUYET' THEN 1 WHEN 'DANG_XU_LY' THEN 2 WHEN 'DA_DUYET' THEN 3 ELSE 4 END, yc.ma_yc DESC
                """).fetchall()
            proposals = [dict(r) for r in rows]
            conn.close()
            self.send_json({"success": True, "data": proposals})
            return

        # Mặc định: Phục vụ Static Files (Frontend HTML, CSS, JS)
        else:
            self.serve_static_file(path)

    # ----------------------------------------------------------------
    # XỬ LÝ POST REQUEST
    # ----------------------------------------------------------------
    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self.get_post_data()

        # 1. API: Đăng nhập (UC01)
        if path == '/api/auth/login':
            username = body.get('username', '').strip()
            password = body.get('password', '').strip()
            conn = get_db()
            cursor = conn.cursor()
            user = cursor.execute("""
            SELECT ma_tk, ten_dang_nhap, ho_ten, vai_tro, ma_ho, trang_thai 
            FROM NGUOI_DUNG 
            WHERE ten_dang_nhap = ? AND mat_khau = ?
            """, (username, password)).fetchone()
            conn.close()

            if user:
                if user['trang_thai'] == 'KHOA':
                    self.send_json({"success": False, "message": "Tài khoản của bạn đã bị khóa bởi Quản trị viên!"}, 403)
                else:
                    self.send_json({
                        "success": True,
                        "message": "Đăng nhập thành công!",
                        "user": dict(user)
                    })
            else:
                self.send_json({"success": False, "message": "Tên đăng nhập hoặc mật khẩu không chính xác!"}, 401)
            return

        # 1b. API: Đăng ký tài khoản mới (Dành cho Cư dân & Người dùng mới)
        elif path == '/api/auth/register':
            username = body.get('username', '').strip()
            password = body.get('password', '').strip()
            fullname = body.get('fullname', '').strip()
            phone = body.get('phone', '').strip()
            so_can_ho = body.get('so_can_ho', '').strip().upper()
            role = body.get('role', 'CU_DAN')
            so_cccd = body.get('so_cccd', '').strip() or None

            if not username or not password or not fullname:
                self.send_json({"success": False, "message": "Vui lòng nhập đầy đủ Tên đăng nhập, Mật khẩu và Họ tên!"}, 400)
                return

            if len(password) < 6:
                self.send_json({"success": False, "message": "Mật khẩu bảo mật phải có ít nhất 6 ký tự!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()

            existing = cursor.execute("SELECT ma_tk FROM NGUOI_DUNG WHERE ten_dang_nhap = ?", (username,)).fetchone()
            if existing:
                conn.close()
                self.send_json({"success": False, "message": f"Tên đăng nhập '{username}' đã được đăng ký! Vui lòng chọn tên khác."}, 400)
                return

            ma_ho = None
            if so_can_ho:
                ho = cursor.execute("SELECT ma_ho FROM HO_KHAU WHERE so_can_ho = ?", (so_can_ho,)).fetchone()
                if ho:
                    ma_ho = ho['ma_ho']
                else:
                    cursor.execute("""
                    INSERT INTO HO_KHAU (so_can_ho, dien_tich, so_tang, trang_thai, ngay_chuyen_den)
                    VALUES (?, ?, ?, 'DANG_O', CURRENT_DATE)
                    """, (so_can_ho, 75.0, 1))
                    ma_ho = cursor.lastrowid

            try:
                cursor.execute("""
                INSERT INTO NGUOI_DUNG (ten_dang_nhap, mat_khau, ho_ten, vai_tro, ma_ho, so_dien_thoai, trang_thai)
                VALUES (?, ?, ?, ?, ?, ?, 'HOAT_DONG')
                """, (username, password, fullname, role, ma_ho, phone))
                new_user_id = cursor.lastrowid

                # Tự động đồng bộ vào danh sách nhân khẩu nếu là cư dân
                if role == 'CU_DAN' and ma_ho:
                    nk = cursor.execute("SELECT ma_nk FROM NHAN_KHAU WHERE ma_ho = ? AND ho_ten = ?", (ma_ho, fullname)).fetchone()
                    if not nk:
                        cursor.execute("""
                        INSERT INTO NHAN_KHAU (ma_ho, ho_ten, ngay_sinh, gioi_tinh, so_cccd, quan_he_chu_ho, so_dien_thoai)
                        VALUES (?, ?, '1990-01-01', 'NAM', ?, 'Chủ hộ', ?)
                        """, (ma_ho, fullname, so_cccd, phone))
                        new_nk_id = cursor.lastrowid
                        cursor.execute("UPDATE HO_KHAU SET ma_chu_ho = ? WHERE ma_ho = ? AND (ma_chu_ho IS NULL OR ma_chu_ho = '')", (new_nk_id, ma_ho))

                conn.commit()
                created = cursor.execute("""
                SELECT ma_tk, ten_dang_nhap, ho_ten, vai_tro, ma_ho, so_dien_thoai, trang_thai
                FROM NGUOI_DUNG WHERE ma_tk = ?
                """, (new_user_id,)).fetchone()
                conn.close()

                self.send_json({
                    "success": True,
                    "message": f"Chúc mừng! Đăng ký tài khoản '{username}' thành công!",
                    "user": dict(created)
                }, 201)
            except Exception as e:
                conn.close()
                self.send_json({"success": False, "message": f"Lỗi đăng ký tài khoản: {str(e)}"}, 500)
            return

        # 2. API: Thêm Căn hộ mới (UC02 - BQT & Admin)
        elif path == '/api/apartments':
            caller_role = self.get_caller_role(body)
            if caller_role in ('KE_TOAN', 'CU_DAN'):
                self.send_json({"success": False, "message": "Thu ngân / Kế toán chỉ có quyền xem dữ liệu, không được thêm hoặc xóa căn hộ!"}, 403)
                return

            so_can_ho = body.get('so_can_ho', '').strip().upper()
            dien_tich = float(body.get('dien_tich', 0))
            so_tang = int(body.get('so_tang', 1))
            trang_thai = body.get('trang_thai', 'DANG_O')
            ngay_chuyen_den = body.get('ngay_chuyen_den', date.today().isoformat())

            if not so_can_ho or dien_tich <= 0:
                self.send_json({"success": False, "message": "Số căn hộ và diện tích > 0 là bắt buộc!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO HO_KHAU (so_can_ho, dien_tich, so_tang, trang_thai, ngay_chuyen_den)
                VALUES (?, ?, ?, ?, ?)
                """, (so_can_ho, dien_tich, so_tang, trang_thai, ngay_chuyen_den))
                conn.commit()
                new_id = cursor.lastrowid
                conn.close()
                self.send_json({"success": True, "message": f"Đã thêm căn hộ {so_can_ho} thành công!", "ma_ho": new_id})
            except sqlite3.IntegrityError:
                conn.close()
                self.send_json({"success": False, "message": f"Số căn hộ {so_can_ho} đã tồn tại!"}, 400)
            return

        # 3. API: Thêm Cư dân / Nhân khẩu (UC03 - BQT & Admin)
        elif path == '/api/residents':
            caller_role = self.get_caller_role(body)
            if caller_role in ('KE_TOAN', 'CU_DAN'):
                self.send_json({"success": False, "message": "Thu ngân / Kế toán chỉ có quyền xem dữ liệu, không được thêm cư dân!"}, 403)
                return

            ma_ho = body.get('ma_ho')
            ho_ten = body.get('ho_ten', '').strip()
            ngay_sinh = body.get('ngay_sinh')
            gioi_tinh = body.get('gioi_tinh', 'NAM')
            so_cccd = body.get('so_cccd', '').strip() or None
            quan_he_chu_ho = body.get('quan_he_chu_ho', 'Thành viên')
            so_dien_thoai = body.get('so_dien_thoai', '').strip()

            if not ma_ho or not ho_ten or not ngay_sinh:
                self.send_json({"success": False, "message": "Vui lòng nhập đầy đủ họ tên, căn hộ và ngày sinh!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO NHAN_KHAU (ma_ho, ho_ten, ngay_sinh, gioi_tinh, so_cccd, quan_he_chu_ho, so_dien_thoai)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ma_ho, ho_ten, ngay_sinh, gioi_tinh, so_cccd, quan_he_chu_ho, so_dien_thoai))
                new_id = cursor.lastrowid

                # Nếu quan hệ là 'Chủ hộ', tự động cập nhật làm chủ hộ cho HO_KHAU
                if quan_he_chu_ho == 'Chủ hộ':
                    cursor.execute("UPDATE HO_KHAU SET ma_chu_ho = ? WHERE ma_ho = ?", (new_id, ma_ho))

                conn.commit()
                conn.close()
                self.send_json({"success": True, "message": f"Đã khai báo cư dân {ho_ten} thành công!", "ma_nk": new_id})
            except sqlite3.IntegrityError as e:
                conn.close()
                self.send_json({"success": False, "message": f"Lỗi dữ liệu: Số CCCD có thể đã bị trùng ({str(e)})"}, 400)
            return

        # 4. API: Đăng ký Tạm trú, Tạm vắng (UC04 - Chỉ Ban Quản Trị)
        elif path == '/api/temporary-residence':
            caller_role = self.get_caller_role(body)
            if caller_role == 'ADMIN':
                self.send_json({"success": False, "message": "Quản trị viên (Admin) không có thẩm quyền đăng ký tạm trú / tạm vắng. Nghiệp vụ này do Ban Quản Trị trực tiếp phụ trách!"}, 403)
                return
            if caller_role in ('KE_TOAN', 'CU_DAN'):
                self.send_json({"success": False, "message": "Bạn không có thẩm quyền đăng ký biến động tạm trú / tạm vắng!"}, 403)
                return

            ma_nk = body.get('ma_nk')
            loai = body.get('loai', 'TAM_TRU')
            tu_ngay = body.get('tu_ngay')
            den_ngay = body.get('den_ngay')
            ly_do = body.get('ly_do', '')

            if not ma_nk or not tu_ngay or not den_ngay:
                self.send_json({"success": False, "message": "Vui lòng chọn nhân khẩu và khoảng thời gian!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO TAM_TRU_TAM_VANG (ma_nk, loai, tu_ngay, den_ngay, ly_do)
            VALUES (?, ?, ?, ?, ?)
            """, (ma_nk, loai, tu_ngay, den_ngay, ly_do))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": f"Đã ghi nhận đăng ký {loai} thành công!"})
            return

        # 5. API: Đăng ký Phương tiện gửi xe (UC05 - BQT & Admin)
        elif path == '/api/vehicles':
            caller_role = self.get_caller_role(body)
            if caller_role in ('KE_TOAN', 'CU_DAN'):
                self.send_json({"success": False, "message": "Thu ngân chỉ có quyền xem dữ liệu phương tiện do BQT quản lý!"}, 403)
                return

            ma_ho = body.get('ma_ho')
            loai_xe = body.get('loai_xe', 'XE_MAY')
            bien_so = body.get('bien_so', '').strip().upper()
            ten_xe = body.get('ten_xe', '').strip()

            if not ma_ho or not bien_so:
                self.send_json({"success": False, "message": "Vui lòng chọn căn hộ và nhập biển số xe!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO PHUONG_TIEN (ma_ho, loai_xe, bien_so, ten_xe)
                VALUES (?, ?, ?, ?)
                """, (ma_ho, loai_xe, bien_so, ten_xe))
                conn.commit()
                conn.close()
                self.send_json({"success": True, "message": f"Đã đăng ký phương tiện biển số {bien_so} thành công!"})
            except sqlite3.IntegrityError:
                conn.close()
                self.send_json({"success": False, "message": f"Biển số {bien_so} đã được đăng ký trong hệ thống!"}, 400)
            return

        # 6. API: Thêm / Sửa Khoản thu (UC06 - BQT & Admin)
        elif path == '/api/fees':
            caller_role = self.get_caller_role(body)
            if caller_role in ('CU_DAN', 'KE_TOAN'):
                self.send_json({"success": False, "message": "Chỉ Ban Quản Trị và Admin mới có quyền cấu hình danh mục khoản thu!"}, 403)
                return

            ten_khoan_thu = body.get('ten_khoan_thu', '').strip()
            loai = body.get('loai', 'BAT_BUOC')
            cach_tinh = body.get('cach_tinh', 'THEO_DIEN_TICH')
            don_gia = float(body.get('don_gia', 0))
            ghi_chu = body.get('ghi_chu', '')

            if not ten_khoan_thu:
                self.send_json({"success": False, "message": "Tên khoản thu không được để trống!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO KHOAN_THU (ten_khoan_thu, loai, cach_tinh, don_gia, ghi_chu)
            VALUES (?, ?, ?, ?, ?)
            """, (ten_khoan_thu, loai, cach_tinh, don_gia, ghi_chu))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": f"Đã thêm khoản thu '{ten_khoan_thu}' thành công!"})
            return

        # 7. API: TỰ ĐỘNG LẬP ĐỢT THU PHÍ THÁNG (UC07 + CR-003)
        # Tự động tính toán tiền dịch vụ, quản lý theo diện tích, phí gửi xe theo số lượng xe
        # Xử lý Change Request CR-003: Nếu căn hộ chuyển đến giữa tháng, tính theo tỷ lệ số ngày thực tế
        elif path == '/api/periods':
            ten_dot = body.get('ten_dot', '').strip()
            thang_nam = body.get('thang_nam', '').strip() # Định dạng 'YYYY-MM'
            ngay_bat_dau = body.get('ngay_bat_dau', f"{thang_nam}-01")
            han_nop = body.get('han_nop', f"{thang_nam}-25")
            selected_fee_ids = body.get('fees', []) # Danh sách ma_kt áp dụng

            if not ten_dot or not thang_nam:
                self.send_json({"success": False, "message": "Vui lòng nhập tên đợt thu và kỳ tháng/năm!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()

            # Kiểm tra xem kỳ thu đã tồn tại chưa (Alternative flow 6a)
            existing = cursor.execute("SELECT ma_dot FROM DOT_THU WHERE thang_nam = ?", (thang_nam,)).fetchone()
            if existing:
                conn.close()
                self.send_json({"success": False, "message": f"Đợt thu cho kỳ {thang_nam} đã tồn tại! Vui lòng chọn kỳ khác."}, 400)
                return

            # Tạo đợt thu mới
            cursor.execute("""
            INSERT INTO DOT_THU (ten_dot, thang_nam, ngay_bat_dau, han_nop, trang_thai)
            VALUES (?, ?, ?, ?, 'DANG_THU')
            """, (ten_dot, thang_nam, ngay_bat_dau, han_nop))
            ma_dot = cursor.lastrowid

            # Lấy danh sách khoản thu áp dụng
            if selected_fee_ids and len(selected_fee_ids) > 0:
                fee_placeholders = ','.join('?' for _ in selected_fee_ids)
                fees = cursor.execute(f"SELECT * FROM KHOAN_THU WHERE ma_kt IN ({fee_placeholders})", selected_fee_ids).fetchall()
            else:
                fees = cursor.execute("SELECT * FROM KHOAN_THU WHERE kich_hoat = 1").fetchall()

            # Lấy danh sách toàn bộ căn hộ đang ở hoặc cho thuê
            apartments = cursor.execute("SELECT * FROM HO_KHAU WHERE trang_thai IN ('DANG_O', 'CHO_THUE')").fetchall()

            count_records = 0
            # Phân tích năm và tháng của kỳ thu
            year, month = map(int, thang_nam.split('-'))
            days_in_month = 30 # Quy chuẩn tính toán

            for apt in apartments:
                ma_ho = apt['ma_ho']
                dien_tich = apt['dien_tich']
                ngay_chuyen_den_str = apt['ngay_chuyen_den']

                # Tính hệ số số ngày ở trong tháng theo yêu cầu CR-003
                ratio_days = 1.0
                ratio_note = ""
                if ngay_chuyen_den_str:
                    try:
                        move_date = datetime.strptime(ngay_chuyen_den_str, "%Y-%m-%d").date()
                        # Nếu chuyển đến trong chính tháng của kỳ thu
                        if move_date.year == year and move_date.month == month:
                            actual_days = max(1, days_in_month - move_date.day + 1)
                            ratio_days = actual_days / days_in_month
                            ratio_note = f" (Áp dụng CR-003: Ở {actual_days}/30 ngày)"
                    except Exception:
                        ratio_days = 1.0

                # Lấy số lượng xe của hộ
                so_xe_may = cursor.execute("SELECT COUNT(*) AS c FROM PHUONG_TIEN WHERE ma_ho = ? AND loai_xe = 'XE_MAY'", (ma_ho,)).fetchone()['c']
                so_o_to = cursor.execute("SELECT COUNT(*) AS c FROM PHUONG_TIEN WHERE ma_ho = ? AND loai_xe = 'O_TO'", (ma_ho,)).fetchone()['c']

                for f in fees:
                    cach_tinh = f['cach_tinh']
                    don_gia = f['don_gia']
                    so_tien = 0.0

                    if cach_tinh == 'THEO_DIEN_TICH':
                        so_tien = round(don_gia * dien_tich * ratio_days)
                    elif cach_tinh == 'THEO_XE_MAY':
                        so_tien = don_gia * so_xe_may
                    elif cach_tinh == 'THEO_O_TO':
                        so_tien = don_gia * so_o_to
                    elif cach_tinh == 'THEO_HO':
                        so_tien = don_gia
                    elif cach_tinh == 'NHAP_TAY':
                        # Khoản thu hộ điện nước sẽ nhập bổ sung sau ở UC08
                        so_tien = 0

                    # Chỉ lưu chi tiết thu nếu có phát sinh tiền hoặc là khoản bắt buộc/thu hộ
                    if so_tien > 0 or f['loai'] in ('BAT_BUOC', 'THU_HO'):
                        ghi_chu_ct = f"{f['ten_khoan_thu']}{ratio_note}" if ratio_note else None
                        cursor.execute("""
                        INSERT INTO CHI_TIET_THU (ma_dot, ma_ho, ma_kt, so_tien_phai_nop, so_tien_da_nop, trang_thai, ghi_chu)
                        VALUES (?, ?, ?, ?, 0, 'CHUA_NOP', ?)
                        """, (ma_dot, ma_ho, f['ma_kt'], so_tien, ghi_chu_ct))
                        count_records += 1

            conn.commit()
            conn.close()
            self.send_json({
                "success": True, 
                "message": f"Khởi tạo thành công đợt thu '{ten_dot}' với {count_records} khoản thu tự động!",
                "ma_dot": ma_dot
            })
            return

        # 8. API: Nhập tiền điện, nước thu hộ (UC08)
        elif path == '/api/utility-bills':
            ma_dot = body.get('ma_dot')
            ma_ho = body.get('ma_ho')
            ma_kt = body.get('ma_kt') # Mã khoản tiền điện hoặc nước
            so_tien = float(body.get('so_tien', 0))
            ghi_chu = body.get('ghi_chu', '')

            if not ma_dot or not ma_ho or not ma_kt:
                self.send_json({"success": False, "message": "Thiếu thông tin đợt thu, căn hộ hoặc loại tiền thu hộ!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()

            # Kiểm tra xem đã có bản ghi chi tiết chưa
            existing = cursor.execute("""
            SELECT ma_ct, so_tien_da_nop FROM CHI_TIET_THU WHERE ma_dot = ? AND ma_ho = ? AND ma_kt = ?
            """, (ma_dot, ma_ho, ma_kt)).fetchone()

            if existing:
                da_nop = existing['so_tien_da_nop']
                trang_thai = 'DA_NOP_DU' if da_nop >= so_tien else ('NOP_THIEU' if da_nop > 0 else 'CHUA_NOP')
                cursor.execute("""
                UPDATE CHI_TIET_THU 
                SET so_tien_phai_nop = ?, trang_thai = ?, ghi_chu = ?
                WHERE ma_ct = ?
                """, (so_tien, trang_thai, ghi_chu, existing['ma_ct']))
            else:
                cursor.execute("""
                INSERT INTO CHI_TIET_THU (ma_dot, ma_ho, ma_kt, so_tien_phai_nop, so_tien_da_nop, trang_thai, ghi_chu)
                VALUES (?, ?, ?, ?, 0, 'CHUA_NOP', ?)
                """, (ma_dot, ma_ho, ma_kt, so_tien, ghi_chu))

            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Đã cập nhật số tiền điện/nước thu hộ thành công!"})
            return

        # 9. API: GHI NHẬN NỘP TIỀN & XUẤT BIÊN LAI (UC09)
        # Sinh mã phiếu thu duy nhất, cập nhật số tiền đã nộp, trừ công nợ, xuất biên lai
        elif path == '/api/collect-fee':
            ma_ct = body.get('ma_ct')
            so_tien_nop = float(body.get('so_tien', 0))
            nguoi_nop = body.get('nguoi_nop', '').strip()
            phuong_thuc = body.get('phuong_thuc', 'TIEN_MAT')
            ma_tk_thu = body.get('ma_tk_thu', 1)
            ghi_chu = body.get('ghi_chu', '')

            if not ma_ct or so_tien_nop <= 0 or not nguoi_nop:
                self.send_json({"success": False, "message": "Vui lòng nhập đầy đủ khoản thu, người nộp và số tiền > 0!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()

            # Lấy thông tin khoản thu chi tiết
            ct = cursor.execute("SELECT * FROM CHI_TIET_THU WHERE ma_ct = ?", (ma_ct,)).fetchone()
            if not ct:
                conn.close()
                self.send_json({"success": False, "message": "Không tìm thấy khoản thu tương ứng!"}, 404)
                return

            phai_nop = ct['so_tien_phai_nop']
            da_nop_cu = ct['so_tien_da_nop']
            da_nop_moi = da_nop_cu + so_tien_nop

            # Cập nhật trạng thái
            if da_nop_moi >= phai_nop:
                trang_thai_moi = 'DA_NOP_DU'
            elif da_nop_moi > 0:
                trang_thai_moi = 'NOP_THIEU'
            else:
                trang_thai_moi = 'CHUA_NOP'

            # Sinh mã phiếu thu duy nhất dạng: PT-YYYYMMDD-XXXX
            today_str = datetime.now().strftime("%Y%m%d")
            random_seq = int(datetime.now().timestamp() * 1000) % 10000
            ma_phieu = f"PT-{today_str}-{random_seq:04d}"

            # Lưu phiếu thu
            cursor.execute("""
            INSERT INTO PHIEU_THU (ma_phieu, ma_ct, so_tien, nguoi_nop, phuong_thuc, ma_tk_thu, ghi_chu)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ma_phieu, ma_ct, so_tien_nop, nguoi_nop, phuong_thuc, ma_tk_thu, ghi_chu))

            # Cập nhật chi tiết thu
            cursor.execute("""
            UPDATE CHI_TIET_THU
            SET so_tien_da_nop = ?, trang_thai = ?
            WHERE ma_ct = ?
            """, (da_nop_moi, trang_thai_moi, ma_ct))

            conn.commit()

            # Lấy lại thông tin đầy đủ để trả về phục vụ in ấn biên lai laser tức thì
            receipt_detail = cursor.execute("""
            SELECT pt.*, h.so_can_ho, h.dien_tich, kt.ten_khoan_thu, d.ten_dot, d.thang_nam,
                   nd.ho_ten AS ten_thu_ngan,
                   ct.so_tien_phai_nop, ct.so_tien_da_nop,
                   (ct.so_tien_phai_nop - ct.so_tien_da_nop) AS con_no
            FROM PHIEU_THU pt
            JOIN CHI_TIET_THU ct ON pt.ma_ct = ct.ma_ct
            JOIN HO_KHAU h ON ct.ma_ho = h.ma_ho
            JOIN KHOAN_THU kt ON ct.ma_kt = kt.ma_kt
            JOIN DOT_THU d ON ct.ma_dot = d.ma_dot
            LEFT JOIN NGUOI_DUNG nd ON pt.ma_tk_thu = nd.ma_tk
            WHERE pt.ma_phieu = ?
            """, (ma_phieu,)).fetchone()

            conn.close()
            self.send_json({
                "success": True,
                "message": f"Đã ghi nhận nộp tiền thành công! Mã phiếu thu: {ma_phieu}",
                "receipt": dict(receipt_detail)
            })
            return

        # 10. API: Thêm Người dùng cán bộ (UC11)
        elif path == '/api/users':
            username = body.get('ten_dang_nhap', '').strip()
            password = body.get('mat_khau', '123456').strip()
            fullname = body.get('ho_ten', '').strip()
            role = body.get('vai_tro', 'KE_TOAN')
            phone = body.get('so_dien_thoai', '').strip()

            if not username or not fullname:
                self.send_json({"success": False, "message": "Tên đăng nhập và họ tên là bắt buộc!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO NGUOI_DUNG (ten_dang_nhap, mat_khau, ho_ten, vai_tro, so_dien_thoai)
                VALUES (?, ?, ?, ?, ?)
                """, (username, password, fullname, role, phone))
                conn.commit()
                conn.close()
                self.send_json({"success": True, "message": f"Đã tạo tài khoản cho {fullname} thành công!"})
            except sqlite3.IntegrityError:
                conn.close()
                self.send_json({"success": False, "message": f"Tên đăng nhập '{username}' đã tồn tại!"}, 400)
            return

        # 11. API: Khôi phục CSDL từ JSON (UC12)
        elif path == '/api/restore':
            backup = body.get('database')
            if not backup:
                self.send_json({"success": False, "message": "Dữ liệu phục hồi không hợp lệ!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            try:
                # Xóa sạch dữ liệu cũ
                for table in ['PHIEU_THU', 'CHI_TIET_THU', 'DOT_THU', 'KHOAN_THU', 'PHUONG_TIEN', 'TAM_TRU_TAM_VANG', 'NHAN_KHAU', 'HO_KHAU', 'NGUOI_DUNG']:
                    cursor.execute(f"DELETE FROM {table}")

                # Khôi phục theo thứ tự khóa ngoại
                for table in ['NGUOI_DUNG', 'HO_KHAU', 'NHAN_KHAU', 'TAM_TRU_TAM_VANG', 'PHUONG_TIEN', 'KHOAN_THU', 'DOT_THU', 'CHI_TIET_THU', 'PHIEU_THU']:
                    if table in backup and len(backup[table]) > 0:
                        records = backup[table]
                        columns = list(records[0].keys())
                        placeholders = ', '.join(['?'] * len(columns))
                conn.commit()
                conn.close()
                self.send_json({"success": True, "message": "Khôi phục dữ liệu hệ thống thành công!"})
            except Exception as e:
                conn.close()
                self.send_json({"success": False, "message": f"Lỗi trong quá trình khôi phục: {str(e)}"}, 500)
            return

        # 12. API: Cư dân đóng tiền Online (Quét mã VietQR / Chuyển khoản trực tuyến)
        elif path == '/api/resident/pay-online':
            ma_ct = body.get('ma_ct')
            so_tien = float(body.get('so_tien', 0))
            nguoi_nop = body.get('nguoi_nop', 'Chủ hộ').strip()
            phuong_thuc = body.get('phuong_thuc', 'CHUYEN_KHOAN')
            ghi_chu = body.get('ghi_chu', 'Thanh toán trực tuyến qua cổng VietQR/Ngân hàng')

            if not ma_ct or so_tien <= 0:
                self.send_json({"success": False, "message": "Số tiền thanh toán phải lớn hơn 0!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()

            ct = cursor.execute("SELECT * FROM CHI_TIET_THU WHERE ma_ct = ?", (ma_ct,)).fetchone()
            if not ct:
                conn.close()
                self.send_json({"success": False, "message": "Khoản thu không tồn tại!"}, 404)
                return

            phai_nop = ct['so_tien_phai_nop']
            da_nop_moi = ct['so_tien_da_nop'] + so_tien
            trang_thai_moi = 'DA_NOP_DU' if da_nop_moi >= phai_nop else 'NOP_THIEU'

            # Sinh mã phiếu thu điện tử online
            today_str = datetime.now().strftime("%Y%m%d")
            random_seq = int(datetime.now().timestamp() * 1000) % 10000
            ma_phieu = f"PT-ONLINE-{today_str}-{random_seq:04d}"

            cursor.execute("""
            INSERT INTO PHIEU_THU (ma_phieu, ma_ct, so_tien, nguoi_nop, phuong_thuc, ma_tk_thu, ghi_chu)
            VALUES (?, ?, ?, ?, ?, NULL, ?)
            """, (ma_phieu, ma_ct, so_tien, nguoi_nop, phuong_thuc, ghi_chu))

            cursor.execute("""
            UPDATE CHI_TIET_THU
            SET so_tien_da_nop = ?, trang_thai = ?
            WHERE ma_ct = ?
            """, (da_nop_moi, trang_thai_moi, ma_ct))

            conn.commit()

            # Lấy chi tiết để xuất biên lai điện tử
            receipt_detail = cursor.execute("""
            SELECT pt.*, h.so_can_ho, h.dien_tich, kt.ten_khoan_thu, d.ten_dot, d.thang_nam,
                   ct.so_tien_phai_nop, ct.so_tien_da_nop,
                   (ct.so_tien_phai_nop - ct.so_tien_da_nop) AS con_no
            FROM PHIEU_THU pt
            JOIN CHI_TIET_THU ct ON pt.ma_ct = ct.ma_ct
            JOIN HO_KHAU h ON ct.ma_ho = h.ma_ho
            JOIN KHOAN_THU kt ON ct.ma_kt = kt.ma_kt
            JOIN DOT_THU d ON ct.ma_dot = d.ma_dot
            WHERE pt.ma_phieu = ?
            """, (ma_phieu,)).fetchone()

            conn.close()
            self.send_json({
                "success": True,
                "message": f"Thanh toán trực tuyến thành công! Mã biên lai điện tử: {ma_phieu}",
                "receipt": dict(receipt_detail)
            })
            return

        # 13. API: Cư dân gửi Yêu cầu / Đề xuất kiến nghị mới tới BQT
        elif path == '/api/proposals':
            ma_ho = body.get('ma_ho') or 6
            tieu_de = body.get('tieu_de', '').strip()
            loai_yeu_cau = str(body.get('loai_yeu_cau', 'KHAC')).strip().upper()
            
            # Chuẩn hóa nếu truyền mã có dấu tiếng Việt
            loai_map = {
                'SỬA CHỮA': 'SUA_CHUA', 'KỸ THUẬT': 'SUA_CHUA', 'AN NINH': 'AN_NINH',
                'VỆ SINH': 'VE_SINH', 'THU PHÍ': 'THU_PHI', 'TIỆN ÍCH': 'TIEN_ICH'
            }
            loai_yeu_cau = loai_map.get(loai_yeu_cau, loai_yeu_cau)
            if loai_yeu_cau not in ['SUA_CHUA', 'AN_NINH', 'VE_SINH', 'THU_PHI', 'TIEN_ICH', 'KHAC']:
                loai_yeu_cau = 'KHAC'

            noi_dung = body.get('noi_dung', '').strip()
            nguoi_gui = body.get('nguoi_gui', '').strip() or 'Cư dân'

            if not tieu_de or not noi_dung:
                self.send_json({"success": False, "message": "Vui lòng nhập đầy đủ tiêu đề và nội dung kiến nghị!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO YEU_CAU_KIEN_NGHI (ma_ho, tieu_de, loai_yeu_cau, noi_dung, nguoi_gui, trang_thai)
            VALUES (?, ?, ?, ?, ?, 'CHO_DUYET')
            """, (ma_ho, tieu_de, loai_yeu_cau, noi_dung, nguoi_gui))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            self.send_json({"success": True, "message": "Đã gửi đề xuất / kiến nghị tới Ban Quản Trị thành công!", "ma_yc": new_id, "ma_kn": new_id}, 201)
            return

        # 14. API: Admin / BQT duyệt & phản hồi Đề xuất kiến nghị
        elif path == '/api/proposals/review':
            ma_yc = body.get('ma_yc') or body.get('ma_kn')
            trang_thai = body.get('trang_thai')
            if trang_thai == 'HOAN_THANH':
                trang_thai = 'DA_XU_LY'
            phan_hoi = (body.get('phan_hoi') or body.get('phan_hoi_bqt') or '').strip()
            nguoi_duyet = (body.get('nguoi_duyet') or 'Admin Quản Trị').strip()

            if not ma_yc or not trang_thai:
                self.send_json({"success": False, "message": "Thiếu mã yêu cầu hoặc trạng thái duyệt!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE YEU_CAU_KIEN_NGHI
            SET trang_thai = ?, phan_hoi = ?, nguoi_duyet = ?, ngay_duyet = CURRENT_TIMESTAMP
            WHERE ma_yc = ?
            """, (trang_thai, phan_hoi, nguoi_duyet, ma_yc))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": f"Đã cập nhật trạng thái đề xuất #{ma_yc} thành công!"})
            return

        # 15. API: Cư dân đăng ký thêm Thành viên gia đình
        elif path == '/api/resident/members':
            ma_ho = body.get('ma_ho')
            ho_ten = body.get('ho_ten', '').strip()
            ngay_sinh = body.get('ngay_sinh', '').strip()
            gioi_tinh = body.get('gioi_tinh', 'NAM')
            so_cccd = body.get('so_cccd', '').strip() or None
            quan_he_chu_ho = body.get('quan_he_chu_ho', 'Thành viên')
            so_dien_thoai = body.get('so_dien_thoai', '').strip()

            if not ma_ho or not ho_ten or not ngay_sinh:
                self.send_json({"success": False, "message": "Vui lòng nhập đầy đủ họ tên và ngày sinh của thành viên!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO NHAN_KHAU (ma_ho, ho_ten, ngay_sinh, gioi_tinh, so_cccd, quan_he_chu_ho, so_dien_thoai)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (ma_ho, ho_ten, ngay_sinh, gioi_tinh, so_cccd, quan_he_chu_ho, so_dien_thoai))
                conn.commit()
                new_id = cursor.lastrowid
                conn.close()
                self.send_json({"success": True, "message": f"Đã đăng ký thành viên '{ho_ten}' vào hộ gia đình thành công!", "ma_nk": new_id}, 201)
            except sqlite3.IntegrityError:
                conn.close()
                self.send_json({"success": False, "message": f"Số CCCD '{so_cccd}' đã tồn tại trong hệ thống!"}, 400)
            return

        # 16. API: Cư dân đăng ký gửi Xe (Ô tô / Xe máy)
        elif path == '/api/resident/vehicles':
            ma_ho = body.get('ma_ho')
            loai_xe = body.get('loai_xe', 'XE_MAY')
            bien_so = body.get('bien_so', '').strip().upper()
            ten_xe = body.get('ten_xe', '').strip()

            if not ma_ho or not bien_so:
                self.send_json({"success": False, "message": "Vui lòng nhập biển số xe đăng ký!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO PHUONG_TIEN (ma_ho, loai_xe, bien_so, ten_xe, ngay_dang_ky)
                VALUES (?, ?, ?, ?, CURRENT_DATE)
                """, (ma_ho, loai_xe, bien_so, ten_xe))
                conn.commit()
                new_id = cursor.lastrowid
                conn.close()
                self.send_json({"success": True, "message": f"Đã đăng ký gửi xe {bien_so} cho căn hộ thành công!", "ma_pt": new_id}, 201)
            except sqlite3.IntegrityError:
                conn.close()
                self.send_json({"success": False, "message": f"Biển số {bien_so} đã được đăng ký trong hệ thống!"}, 400)
            return

        # 17. API: Cư dân cập nhật thông tin Căn hộ
        elif path == '/api/resident/apartment':
            ma_ho = body.get('ma_ho')
            sdt_chu_ho = body.get('sdt_chu_ho', '').strip()
            ten_chu_ho = body.get('ten_chu_ho', '').strip()

            if not ma_ho:
                self.send_json({"success": False, "message": "Thiếu mã căn hộ!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            ho = cursor.execute("SELECT ma_chu_ho FROM HO_KHAU WHERE ma_ho = ?", (ma_ho,)).fetchone()
            if ho and ho['ma_chu_ho']:
                if sdt_chu_ho or ten_chu_ho:
                    cursor.execute("""
                    UPDATE NHAN_KHAU 
                    SET so_dien_thoai = COALESCE(NULLIF(?, ''), so_dien_thoai),
                        ho_ten = COALESCE(NULLIF(?, ''), ho_ten)
                    WHERE ma_nk = ?
                    """, (sdt_chu_ho, ten_chu_ho, ho['ma_chu_ho']))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Đã cập nhật thông tin liên hệ của căn hộ thành công!"})
            return

        else:
            self.send_json({"success": False, "message": "Endpoint không tồn tại"}, 404)

    # ----------------------------------------------------------------
    # XỬ LÝ PUT VÀ DELETE REQUEST
    # ----------------------------------------------------------------
    def do_PUT(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self.get_post_data()

        # Khóa / Mở khóa tài khoản (UC11)
        if path.startswith('/api/users/') and path.endswith('/toggle'):
            parts = path.split('/')
            ma_tk = int(parts[3])
            conn = get_db()
            cursor = conn.cursor()
            user = cursor.execute("SELECT trang_thai FROM NGUOI_DUNG WHERE ma_tk = ?", (ma_tk,)).fetchone()
            if not user:
                conn.close()
                self.send_json({"success": False, "message": "Không tìm thấy người dùng"}, 404)
                return
            new_status = 'KHOA' if user['trang_thai'] == 'HOAT_DONG' else 'HOAT_DONG'
            cursor.execute("UPDATE NGUOI_DUNG SET trang_thai = ? WHERE ma_tk = ?", (new_status, ma_tk))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": f"Đã chuyển trạng thái tài khoản sang {new_status}"})
            return

        self.send_json({"success": False, "message": "Endpoint không hỗ trợ"}, 404)

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        caller_role = self.get_caller_role()

        conn = get_db()
        cursor = conn.cursor()

        if path.startswith('/api/apartments/'):
            if caller_role in ('KE_TOAN', 'CU_DAN'):
                conn.close()
                self.send_json({"success": False, "message": "Thu ngân / Cư dân không có thẩm quyền xóa căn hộ!"}, 403)
                return
            ma_ho = int(path.split('/')[-1])
            cursor.execute("DELETE FROM HO_KHAU WHERE ma_ho = ?", (ma_ho,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Đã xóa căn hộ thành công!"})
            return

        elif path.startswith('/api/residents/'):
            if caller_role in ('KE_TOAN', 'CU_DAN'):
                conn.close()
                self.send_json({"success": False, "message": "Thu ngân / Cư dân không có thẩm quyền xóa nhân khẩu!"}, 403)
                return
            ma_nk = int(path.split('/')[-1])
            cursor.execute("DELETE FROM NHAN_KHAU WHERE ma_nk = ?", (ma_nk,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Đã xóa nhân khẩu thành công!"})
            return

        elif path.startswith('/api/vehicles/'):
            if caller_role in ('KE_TOAN', 'CU_DAN'):
                conn.close()
                self.send_json({"success": False, "message": "Thu ngân không có thẩm quyền hủy gửi xe của BQT!"}, 403)
                return
            ma_pt = int(path.split('/')[-1])
            cursor.execute("DELETE FROM PHUONG_TIEN WHERE ma_pt = ?", (ma_pt,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Đã xóa phương tiện gửi xe!"})
            return

        elif path.startswith('/api/temporary-residence/'):
            if caller_role in ('ADMIN', 'KE_TOAN', 'CU_DAN'):
                conn.close()
                self.send_json({"success": False, "message": "Nghiệp vụ tạm trú / tạm vắng do Ban Quản Trị trực tiếp phụ trách!"}, 403)
                return
            ma_ttv = int(path.split('/')[-1])
            cursor.execute("DELETE FROM TAM_TRU_TAM_VANG WHERE ma_ttv = ?", (ma_ttv,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Đã xóa bản ghi tạm trú/tạm vắng!"})
            return

        conn.close()
        self.send_json({"success": False, "message": "Endpoint không hỗ trợ"}, 404)

    # ----------------------------------------------------------------
    # HÀM PHỤC VỤ STATIC FILES (HTML, CSS, JS, ICONS)
    # ----------------------------------------------------------------
    def serve_static_file(self, req_path):
        if req_path == '/' or req_path == '':
            req_path = '/index.html'

        # Chuyển đổi đường dẫn URL thành đường dẫn tệp trên ổ đĩa
        clean_path = req_path.lstrip('/')
        file_path = os.path.join(STATIC_DIR, clean_path)

        if not os.path.isfile(file_path):
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"<h1>404 Not Found - Khong tim thay tep giao dien!</h1>")
            return

        # Xác định MIME Type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'

        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Length', str(os.path.getsize(file_path)))
        self.end_headers()

        with open(file_path, 'rb') as f:
            self.wfile.write(f.read())


# ====================================================================
# ĐIỂM KHỞI CHẠY CHÍNH (ENTRY POINT)
# ====================================================================
if __name__ == '__main__':
    print("====================================================================")
    print("    HỆ THỐNG QUẢN LÝ THU PHÍ CHUNG CƯ BLUE MOON (BMFM WEB APP)      ")
    print("              Nhóm 12 - Môn Kỹ thuật phần mềm (KTPM 2026)           ")
    print("====================================================================")
    
    # Khởi tạo CSDL
    init_database()
    
    # Khởi động Web Server Đa luồng (ThreadingHTTPServer)
    handler = BlueMoonRequestHandler
    with http.server.ThreadingHTTPServer(("", PORT), handler) as httpd:
        httpd.daemon_threads = True
        print(f"\n[OK] Máy chủ Web đang chạy tại: http://localhost:{PORT}")
        print(f"[OK] Mở trình duyệt web và truy cập địa chỉ trên để sử dụng.")
        print(f"[OK] Nhấn phím Ctrl + C để dừng máy chủ.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Đã dừng máy chủ Blue Moon.")
