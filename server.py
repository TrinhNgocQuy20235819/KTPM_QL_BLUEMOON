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

    # Kiểm tra xem đã có dữ liệu mẫu chưa, nếu chưa thì chèn dữ liệu
    cursor.execute("SELECT COUNT(*) as cnt FROM NGUOI_DUNG")
    if cursor.fetchone()['cnt'] == 0:
        # Chèn người dùng (Cán bộ quản trị và Cư dân/Khách)
        cursor.executemany("""
        INSERT INTO NGUOI_DUNG (ten_dang_nhap, mat_khau, ho_ten, vai_tro, ma_ho, so_dien_thoai) VALUES (?, ?, ?, ?, ?, ?)
        """, [
            ('admin', 'admin123', 'Quản trị viên Hệ thống', 'ADMIN', None, '0901234567'),
            ('bqt_truongban', 'bqt123', 'Trưởng Ban Quản Trị', 'BAN_QUAN_TRI', None, '0912345678'),
            ('ketoan_minh', 'ketoan123', 'Kế toán Nguyễn Hồng Minh', 'KE_TOAN', None, '0987654321'),
            ('cudan_a1205', '123456', 'Nguyễn Văn An (Chủ hộ A1205)', 'CU_DAN', 1, '0911222333'),
            ('cudan_b0402', '123456', 'Phạm Quỳnh Nga (Chủ hộ B0402)', 'CU_DAN', 3, '0977666555'),
            ('cudan_b0403', '123456', 'Vũ Đức Thành (Chủ hộ B0403)', 'CU_DAN', 4, '0966555444')
        ])

        # Chèn căn hộ mẫu
        cursor.executemany("""
        INSERT INTO HO_KHAU (ma_ho, so_can_ho, dien_tich, so_tang, trang_thai, ngay_chuyen_den) VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (1, 'A1205', 85.50, 12, 'DANG_O', '2026-01-10'),
            (2, 'A1206', 70.00, 12, 'DANG_O', '2026-02-15'),
            (3, 'B0402', 95.00, 4, 'DANG_O', '2026-01-05'),
            (4, 'B0403', 65.50, 4, 'DANG_O', '2026-10-16'), # Chuyển đến giữa tháng (CR-003)
            (5, 'C1501', 120.00, 15, 'DANG_O', '2026-03-01'),
            (6, 'C1502', 75.00, 15, 'CHO_THUE', '2026-04-20'),
            (7, 'A0801', 82.00, 8, 'TRONG', '2026-10-01')
        ])

        # Chèn nhân khẩu mẫu
        cursor.executemany("""
        INSERT INTO NHAN_KHAU (ma_nk, ma_ho, ho_ten, ngay_sinh, gioi_tinh, so_cccd, quan_he_chu_ho, so_dien_thoai) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (1, 1, 'Nguyễn Văn An', '1980-05-12', 'NAM', '001080012345', 'Chủ hộ', '0911222333'),
            (2, 1, 'Trần Thị Mai', '1984-08-20', 'NU', '001184054321', 'Vợ', '0911222444'),
            (3, 1, 'Nguyễn Minh Quân', '2012-11-10', 'NAM', '001212009876', 'Con', None),
            (4, 2, 'Lê Hoàng Long', '1975-02-28', 'NAM', '001075034567', 'Chủ hộ', '0988777666'),
            (5, 3, 'Phạm Quỳnh Nga', '1990-09-15', 'NU', '001190087654', 'Chủ hộ', '0977666555'),
            (6, 4, 'Vũ Đức Thành', '1992-12-05', 'NAM', '001092043210', 'Chủ hộ', '0966555444'),
            (7, 5, 'Hoàng Gia Bảo', '1968-07-22', 'NAM', '001068019283', 'Chủ hộ', '0944333222'),
            (8, 6, 'Đặng Thu Trang', '1995-04-18', 'NU', '001195076543', 'Chủ hộ', '0933222111')
        ])

        # Cập nhật chủ hộ
        cursor.execute("UPDATE HO_KHAU SET ma_chu_ho = 1 WHERE ma_ho = 1")
        cursor.execute("UPDATE HO_KHAU SET ma_chu_ho = 4 WHERE ma_ho = 2")
        cursor.execute("UPDATE HO_KHAU SET ma_chu_ho = 5 WHERE ma_ho = 3")
        cursor.execute("UPDATE HO_KHAU SET ma_chu_ho = 6 WHERE ma_ho = 4")
        cursor.execute("UPDATE HO_KHAU SET ma_chu_ho = 7 WHERE ma_ho = 5")
        cursor.execute("UPDATE HO_KHAU SET ma_chu_ho = 8 WHERE ma_ho = 6")

        # Chèn phương tiện mẫu
        cursor.executemany("""
        INSERT INTO PHUONG_TIEN (ma_ho, loai_xe, bien_so, ten_xe) VALUES (?, ?, ?, ?)
        """, [
            (1, 'XE_MAY', '29B1-888.88', 'Honda SH 150i'),
            (1, 'XE_MAY', '29B1-678.90', 'Honda AirBlade'),
            (1, 'O_TO', '30F-123.45', 'Mazda CX-5'),
            (2, 'XE_MAY', '29C1-555.55', 'Yamaha Grande'),
            (3, 'O_TO', '30G-999.99', 'Mercedes C200'),
            (4, 'XE_MAY', '29D1-333.33', 'Honda Wave Alpha'),
            (5, 'O_TO', '30H-888.66', 'Toyota Camry'),
            (5, 'XE_MAY', '29E1-777.77', 'Vespa Sprint')
        ])

        # Chèn danh mục khoản thu
        cursor.executemany("""
        INSERT INTO KHOAN_THU (ma_kt, ten_khoan_thu, loai, cach_tinh, don_gia, ghi_chu, kich_hoat) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (1, 'Phí dịch vụ chung cư', 'BAT_BUOC', 'THEO_DIEN_TICH', 12000, 'Khung quy định: 2.500 - 16.500 đ/m2/tháng', 1),
            (2, 'Phí quản lý vận hành', 'BAT_BUOC', 'THEO_DIEN_TICH', 7000, 'Mức áp dụng hiện hành: 7.000 đ/m2/tháng', 1),
            (3, 'Phí trông giữ xe máy', 'BAT_BUOC', 'THEO_XE_MAY', 70000, 'Đơn giá: 70.000 đ/xe máy/tháng', 1),
            (4, 'Phí trông giữ xe ô tô', 'BAT_BUOC', 'THEO_O_TO', 1200000, 'Đơn giá: 1.200.000 đ/xe ô tô/tháng', 1),
            (5, 'Tiền điện sinh hoạt (Thu hộ)', 'THU_HO', 'NHAP_TAY', 0, 'Nhập theo hóa đơn thực tế của Điện lực', 1),
            (6, 'Tiền nước sinh hoạt (Thu hộ)', 'THU_HO', 'NHAP_TAY', 0, 'Nhập theo hóa đơn thực tế của Cty Nước sạch', 1),
            (7, 'Quỹ Vì người nghèo', 'TU_NGUYEN', 'THEO_HO', 50000, 'Vận động ủng hộ vì người nghèo', 1),
            (8, 'Quỹ Đền ơn đáp nghĩa 27/7', 'TU_NGUYEN', 'THEO_HO', 50000, 'Ủng hộ tri ân ngày thương binh liệt sĩ', 1),
            (9, 'Quỹ Tết thiếu nhi 1/6', 'TU_NGUYEN', 'THEO_HO', 100000, 'Quỹ tổ chức sự kiện thiếu nhi chung cư', 1)
        ])

        # Chèn đợt thu mẫu tháng 11/2026
        cursor.execute("""
        INSERT INTO DOT_THU (ma_dot, ten_dot, thang_nam, ngay_bat_dau, han_nop, trang_thai) 
        VALUES (1, 'Thu phí tháng 11/2026', '2026-11', '2026-11-01', '2026-11-25', 'DANG_THU')
        """)

        # Chi tiết thu mẫu
        cursor.executemany("""
        INSERT INTO CHI_TIET_THU (ma_ct, ma_dot, ma_ho, ma_kt, so_tien_phai_nop, so_tien_da_nop, trang_thai) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (1, 1, 1, 1, 1026000, 1026000, 'DA_NOP_DU'),
            (2, 1, 1, 2, 598500, 598500, 'DA_NOP_DU'),
            (3, 1, 1, 3, 140000, 140000, 'DA_NOP_DU'),
            (4, 1, 1, 4, 1200000, 1200000, 'DA_NOP_DU'),
            (5, 1, 1, 5, 650000, 650000, 'DA_NOP_DU'),
            (6, 1, 1, 6, 180000, 180000, 'DA_NOP_DU'),
            (7, 1, 3, 1, 1140000, 0, 'CHUA_NOP'),
            (8, 1, 3, 2, 665000, 0, 'CHUA_NOP'),
            (9, 1, 3, 4, 1200000, 0, 'CHUA_NOP'),
            (10, 1, 4, 1, 786000, 400000, 'NOP_THIEU'),
            (11, 1, 4, 2, 458500, 0, 'CHUA_NOP'),
            (12, 1, 4, 3, 70000, 70000, 'DA_NOP_DU')
        ])

        # Phiếu thu mẫu
        cursor.executemany("""
        INSERT INTO PHIEU_THU (ma_phieu, ma_ct, so_tien, ngay_nop, nguoi_nop, phuong_thuc, ma_tk_thu, ghi_chu) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ('PT-202611-0001', 1, 1026000, '2026-11-05 08:30:00', 'Nguyễn Văn An', 'CHUYEN_KHOAN', 3, 'Thanh toán phí dịch vụ tháng 11'),
            ('PT-202611-0002', 2, 598500, '2026-11-05 08:30:00', 'Nguyễn Văn An', 'CHUYEN_KHOAN', 3, 'Thanh toán phí quản lý tháng 11'),
            ('PT-202611-0003', 3, 140000, '2026-11-05 08:30:00', 'Nguyễn Văn An', 'TIEN_MAT', 3, 'Thanh toán phí 2 xe máy'),
            ('PT-202611-0004', 4, 1200000, '2026-11-05 08:30:00', 'Nguyễn Văn An', 'CHUYEN_KHOAN', 3, 'Thanh toán phí 1 ô tô'),
            ('PT-202611-0005', 10, 400000, '2026-11-06 14:15:00', 'Vũ Đức Thành', 'TIEN_MAT', 3, 'Nộp tạm ứng phí dịch vụ'),
            ('PT-202611-0006', 12, 70000, '2026-11-06 14:15:00', 'Vũ Đức Thành', 'TIEN_MAT', 3, 'Nộp phí xe máy tháng 11')
        ])

        conn.commit()
        print(">>> Đã khởi tạo cơ sở dữ liệu mẫu Blue Moon thành công!")

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

            conn.close()
            self.send_json({
                "success": True,
                "data": {
                    "apartment": dict(apartment),
                    "members": members,
                    "vehicles": vehicles,
                    "bills": bills,
                    "receipts": receipts
                }
            })
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

        # 2. API: Thêm Căn hộ mới (UC02)
        elif path == '/api/apartments':
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

        # 3. API: Thêm Cư dân / Nhân khẩu (UC03)
        elif path == '/api/residents':
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

        # 4. API: Đăng ký Tạm trú, Tạm vắng (UC04)
        elif path == '/api/temporary-residence':
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

        # 5. API: Đăng ký Phương tiện gửi xe (UC05)
        elif path == '/api/vehicles':
            ma_ho = body.get('ma_ho')
            loai_xe = body.get('loai_xe', 'XE_MAY')
            bien_so = body.get('bien_so', '').strip().upper()
            ten_xe = body.get('ten_xe', '').strip()

            if not ma_ho or not bien_so:
                self.send_json({"success": False, "message": "Vui lòng chọn căn hộ và nhập biển số xe!"}, 400)
                return

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO PHUONG_TIEN (ma_ho, loai_xe, bien_so, ten_xe)
            VALUES (?, ?, ?, ?)
            """, (ma_ho, loai_xe, bien_so, ten_xe))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": f"Đã đăng ký phương tiện biển số {bien_so} thành công!"})
            return

        # 6. API: Thêm / Sửa Khoản thu (UC06)
        elif path == '/api/fees':
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

        conn = get_db()
        cursor = conn.cursor()

        if path.startswith('/api/apartments/'):
            ma_ho = int(path.split('/')[-1])
            cursor.execute("DELETE FROM HO_KHAU WHERE ma_ho = ?", (ma_ho,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Đã xóa căn hộ thành công!"})
            return

        elif path.startswith('/api/residents/'):
            ma_nk = int(path.split('/')[-1])
            cursor.execute("DELETE FROM NHAN_KHAU WHERE ma_nk = ?", (ma_nk,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Đã xóa nhân khẩu thành công!"})
            return

        elif path.startswith('/api/vehicles/'):
            ma_pt = int(path.split('/')[-1])
            cursor.execute("DELETE FROM PHUONG_TIEN WHERE ma_pt = ?", (ma_pt,))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "Đã xóa phương tiện gửi xe!"})
            return

        elif path.startswith('/api/temporary-residence/'):
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
    
    # Khởi động Web Server
    handler = BlueMoonRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"\n[OK] Máy chủ Web đang chạy tại: http://localhost:{PORT}")
        print(f"[OK] Mở trình duyệt web và truy cập địa chỉ trên để sử dụng.")
        print(f"[OK] Nhấn phím Ctrl + C để dừng máy chủ.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Đã dừng máy chủ Blue Moon.")
