@echo off
chcp 65001 > nul
title Hệ Thống Quản Lý Thu Phí Chung Cư Blue Moon (BMFM)
echo ====================================================================
echo     HỆ THỐNG QUẢN LÝ THU PHÍ CHUNG CƯ BLUE MOON (BMFM WEB APP)
echo               Nhóm 12 - Môn Kỹ thuật phần mềm (KTPM 2026)
echo ====================================================================
echo Đang khởi động máy chủ Web Server tại cổng 8000...
echo Tự động mở trình duyệt web tại: http://localhost:8000
echo.

start "" "http://localhost:8000"
py server.py

if errorlevel 1 (
    echo.
    echo [LƯU Ý] Lệnh py không khả dụng, đang thử lệnh python...
    python server.py
)
pause
