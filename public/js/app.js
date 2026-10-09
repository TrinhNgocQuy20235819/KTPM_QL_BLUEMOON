/**
 * ====================================================================
 * DỰ ÁN QUẢN LÝ THU PHÍ CHUNG CƯ BLUE MOON (BMFM)
 * File: app.js
 * Mô tả: Toàn bộ Logic điều khiển giao diện Frontend Single Page Application
 *        Xử lý 12 Use-Case, Chuyển tab, Quản lý Modal, Gọi REST API,
 *        Vẽ biểu đồ Chart.js và Định dạng biên lai in laser (UC09)
 * ====================================================================
 */

// Trạng thái ứng dụng toàn cục (App State)
const state = {
    currentUser: {
        id: 3,
        username: 'ketoan_minh',
        fullname: 'Nguyễn Hồng Minh',
        role: 'KE_TOAN'
    },
    apartments: [],
    residents: [],
    fees: [],
    periods: [],
    currentPeriodDetails: [],
    chartInstance: null
};

// ====================================================================
// HÀM TIỆN ÍCH TRỢ GIÚP (HELPER FUNCTIONS)
// ====================================================================

/**
 * Định dạng số thành tiền tệ Việt Nam Đồng (VNĐ)
 */
function formatVND(amount) {
    if (isNaN(amount) || amount === null) return '0 đ';
    return new Intl.NumberFormat('vi-VN').format(Math.round(amount)) + ' đ';
}

/**
 * Chuyển đổi số tiền thành chữ tiếng Việt chuẩn (phục vụ in biên lai UC09)
 */
function numberToVietnameseWords(num) {
    if (!num || num === 0) return 'Không đồng chẵn.';
    const units = ['', 'nghìn', 'triệu', 'tỷ', 'nghìn tỷ', 'triệu tỷ'];
    const digits = ['không', 'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín'];

    function readGroup(n) {
        let h = Math.floor(n / 100);
        let t = Math.floor((n % 100) / 10);
        let u = n % 10;
        let str = '';

        if (h > 0) str += digits[h] + ' trăm ';
        else if (n >= 100) str += 'không trăm ';

        if (t > 1) {
            str += digits[t] + ' mươi ';
            if (u === 1) str += 'mốt ';
            else if (u === 5) str += 'lăm ';
            else if (u > 0) str += digits[u] + ' ';
        } else if (t === 1) {
            str += 'mười ';
            if (u === 5) str += 'lăm ';
            else if (u > 0) str += digits[u] + ' ';
        } else if (u > 0) {
            if (h > 0 || n >= 100) str += 'lẻ ' + digits[u] + ' ';
            else str += digits[u] + ' ';
        }
        return str.trim();
    }

    let n = Math.abs(Math.round(num));
    let groups = [];
    while (n > 0) {
        groups.push(n % 1000);
        n = Math.floor(n / 1000);
    }

    let words = [];
    for (let i = groups.length - 1; i >= 0; i--) {
        let g = groups[i];
        if (g > 0) {
            words.push(readGroup(g) + ' ' + units[i]);
        }
    }

    let result = words.join(' ').trim();
    // Viết hoa chữ cái đầu và thêm đuôi đồng chẵn
    result = result.charAt(0).toUpperCase() + result.slice(1) + ' đồng chẵn.';
    return result;
}

/**
 * Hiển thị thông báo nổi Toast Notification
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

/**
 * Mở hộp thoại Modal
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
    }
}

/**
 * Đóng hộp thoại Modal
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
    }
}

// ====================================================================
// ĐIỀU HƯỚNG TAB & PHÂN QUYỀN (ROLES & TABS)
// ====================================================================

function initNavigation() {
    const navItems = document.querySelectorAll('.sidebar-menu .nav-item');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const pageHeading = document.getElementById('page-heading');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');

            // Cập nhật trạng thái active trên sidebar
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            // Chuyển tab hiển thị
            tabPanes.forEach(pane => {
                pane.classList.remove('active');
                if (pane.id === targetTab) {
                    pane.classList.add('active');
                }
            });

            // Cập nhật tiêu đề Topbar
            const titleSpan = item.querySelector('span:last-child');
            if (titleSpan) {
                pageHeading.textContent = titleSpan.textContent;
            }

            // Gọi tải lại dữ liệu của tab tương ứng
            loadTabData(targetTab);
        });
    });

    // Xử lý chuyển đổi vai trò (Role Switcher)
    const roleSwitcher = document.getElementById('role-switcher');
    roleSwitcher.addEventListener('change', (e) => {
        const val = e.target.value;
        state.currentUser.role = val;
        const roleNames = {
            'ADMIN': 'Quản trị viên (Admin)',
            'BAN_QUAN_TRI': 'Ban quản trị (BQT)',
            'KE_TOAN': 'Kế toán / Thu ngân',
            'CU_DAN': 'Cư dân / Chủ hộ (A1205)'
        };
        document.getElementById('user-role-badge').textContent = roleNames[val] || val;

        if (val === 'CU_DAN') {
            state.currentUser.id = 4;
            state.currentUser.fullname = 'Nguyễn Văn An (Chủ hộ A1205)';
            state.currentUser.ma_ho = 1;
            document.getElementById('user-name').textContent = 'Nguyễn Văn An (A1205)';
            document.getElementById('user-avatar').textContent = 'AN';

            // Ẩn bớt các mục quản trị hệ thống, chuyển sang tab Cổng cư dân
            document.querySelectorAll('[data-role-section]').forEach(el => el.style.display = 'none');
            const portalNav = document.getElementById('nav-resident-portal');
            if (portalNav) portalNav.click();
            showToast('Đã chuyển sang Cổng Thông Tin Dành Cho Cư Dân (A1205)!', 'success');
        } else {
            // Hiện lại toàn bộ menu quản trị
            document.querySelectorAll('[data-role-section]').forEach(el => el.style.display = '');
            if (val === 'ADMIN') {
                state.currentUser.fullname = 'Quản trị viên Hệ thống';
                document.getElementById('user-avatar').textContent = 'AD';
            } else if (val === 'BAN_QUAN_TRI') {
                state.currentUser.fullname = 'Trưởng Ban Quản Trị';
                document.getElementById('user-avatar').textContent = 'BQT';
            } else {
                state.currentUser.fullname = 'Kế toán Nguyễn Hồng Minh';
                document.getElementById('user-avatar').textContent = 'KT';
            }
            document.getElementById('user-name').textContent = state.currentUser.fullname;
            showToast(`Đã chuyển sang vai trò: ${roleNames[val]}`, 'info');
        }
    });

    // Theme toggle (Dark / Light)
    const themeBtn = document.getElementById('theme-toggle');
    themeBtn.addEventListener('click', () => {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', newTheme);
        showToast(`Đã chuyển sang giao diện ${newTheme === 'dark' ? 'Tối (Dark)' : 'Sáng (Light)'}`, 'info');
    });
}

function loadTabData(tabId) {
    switch (tabId) {
        case 'tab-resident-portal':
            loadResidentPortal(state.currentUser.ma_ho || 1);
            break;
        case 'tab-dashboard':
            loadDashboard();
            break;
        case 'tab-apartments':
            loadApartments();
            break;
        case 'tab-residents':
            loadResidents();
            break;
        case 'tab-temporary':
            loadTemporaryResidence();
            break;
        case 'tab-vehicles':
            loadVehicles();
            break;
        case 'tab-fees':
            loadFees();
            break;
        case 'tab-periods':
            loadPeriods();
            break;
        case 'tab-utilities':
            loadUtilities();
            break;
        case 'tab-collection':
            loadCollectionHistory();
            break;
        case 'tab-reports':
            loadReports();
            break;
        case 'tab-users':
            loadUsers();
            break;
        case 'tab-system':
            // Sẵn sàng cho thao tác backup/restore
            break;
    }
}

// ====================================================================
// 1. DASHBOARD TỔNG QUAN (UC10)
// ====================================================================
async function loadDashboard() {
    try {
        const res = await API.statistics.getOverview();
        if (!res.success) return;
        const data = res.data;

        // Thống kê thẻ số liệu
        document.getElementById('stat-apartments').textContent = data.overview.total_apartments;
        document.getElementById('stat-occupied-sub').textContent = `Đang ở: ${data.overview.occupied_apartments} căn`;

        document.getElementById('stat-residents').textContent = data.overview.total_residents;
        document.getElementById('stat-vehicles-sub').textContent = `Phương tiện: ${data.overview.total_vehicles} xe`;

        document.getElementById('stat-collected').textContent = formatVND(data.overview.tong_da_thu);
        document.getElementById('stat-collected-rate').textContent = `Tỷ lệ: ${data.overview.ty_le_thu}%`;

        document.getElementById('stat-debt').textContent = formatVND(data.overview.tong_con_no);

        // Nạp danh sách top nợ nhiều nhất
        const tbodyDebtors = document.getElementById('top-debtors-tbody');
        tbodyDebtors.innerHTML = '';
        if (data.top_debtors && data.top_debtors.length > 0) {
            data.top_debtors.forEach(d => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${d.so_can_ho}</strong></td>
                    <td>${d.ten_chu_ho || '<span style="color:var(--text-muted)">Chưa có</span>'}</td>
                    <td style="color: var(--danger); font-weight: 700;">${formatVND(d.tong_no)}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="quickCollectDebt('${d.so_can_ho}')">Thu tiền</button>
                    </td>
                `;
                tbodyDebtors.appendChild(tr);
            });
        } else {
            tbodyDebtors.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">Không có căn hộ nợ đọng!</td></tr>`;
        }

        // Vẽ biểu đồ Chart.js
        renderChart(data.by_fee);

    } catch (e) {
        showToast(`Lỗi nạp Dashboard: ${e.message}`, 'error');
    }
}

function renderChart(byFeeData) {
    const ctx = document.getElementById('chart-fees');
    if (!ctx) return;

    if (state.chartInstance) {
        state.chartInstance.destroy();
    }

    const labels = byFeeData.map(f => f.ten_khoan_thu);
    const phaiThu = byFeeData.map(f => f.phai_thu);
    const daThu = byFeeData.map(f => f.da_thu);

    state.chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Phải thu',
                    data: phaiThu,
                    backgroundColor: 'rgba(37, 99, 235, 0.6)',
                    borderColor: '#2563eb',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Đã thu',
                    data: daThu,
                    backgroundColor: 'rgba(16, 185, 129, 0.7)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: ${formatVND(ctx.raw)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (v) => formatVND(v)
                    }
                }
            }
        }
    });
}

function quickCollectDebt(soCanHo) {
    // Chuyển sang tab thu tiền và điền số căn hộ
    const navCollect = document.querySelector('[data-tab="tab-collection"]');
    if (navCollect) navCollect.click();
    document.getElementById('collect-search-apt').value = soCanHo;
    document.getElementById('btn-find-debt').click();
}

// ====================================================================
// 2. QUẢN LÝ CĂN HỘ / HỘ KHẨU (UC02)
// ====================================================================
async function loadApartments() {
    try {
        const res = await API.apartments.getAll();
        state.apartments = res.data;
        renderApartmentsTable(state.apartments);
        populateApartmentDropdowns(state.apartments);
    } catch (e) {
        showToast(`Lỗi nạp căn hộ: ${e.message}`, 'error');
    }
}

function renderApartmentsTable(apartments) {
    const tbody = document.getElementById('apartments-tbody');
    tbody.innerHTML = '';
    apartments.forEach(apt => {
        const tr = document.createElement('tr');
        const badgeClass = apt.trang_thai === 'DANG_O' ? 'badge-success' : (apt.trang_thai === 'CHO_THUE' ? 'badge-warning' : 'badge-neutral');
        const statusText = apt.trang_thai === 'DANG_O' ? 'Đang ở' : (apt.trang_thai === 'CHO_THUE' ? 'Cho thuê' : 'Còn trống');

        tr.innerHTML = `
            <td><strong>${apt.so_can_ho}</strong></td>
            <td>${apt.dien_tich} m²</td>
            <td>Tầng ${apt.so_tang}</td>
            <td>${apt.ten_chu_ho || '<span style="color:var(--text-muted)">Chưa gán</span>'}</td>
            <td><span class="badge badge-primary">${apt.so_nhan_khau} người</span></td>
            <td>🛵 ${apt.so_xe_may} xe máy | 🚗 ${apt.so_o_to} ô tô</td>
            <td>${apt.ngay_chuyen_den || '2026-01-01'}</td>
            <td><span class="badge ${badgeClass}">${statusText}</span></td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="deleteApartment(${apt.ma_ho}, '${apt.so_can_ho}')">Xóa</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function populateApartmentDropdowns(apartments) {
    const residentSelect = document.getElementById('resident-select-apt');
    const vehicleSelect = document.getElementById('vehicle-select-apt');
    const utilAptSelect = document.getElementById('util-modal-apt');

    const options = apartments.map(a => `<option value="${a.ma_ho}">Căn hộ ${a.so_can_ho} (${a.dien_tich}m² - Chủ: ${a.ten_chu_ho || 'Chưa gán'})</option>`).join('');

    if (residentSelect) residentSelect.innerHTML = options;
    if (vehicleSelect) vehicleSelect.innerHTML = options;
    if (utilAptSelect) utilAptSelect.innerHTML = options;
}

async function deleteApartment(id, code) {
    if (!confirm(`Bạn có chắc muốn xóa căn hộ ${code}? Toàn bộ nhân khẩu và xe cộ của căn hộ sẽ bị xóa!`)) return;
    try {
        await API.apartments.delete(id);
        showToast(`Đã xóa căn hộ ${code}`, 'success');
        loadApartments();
    } catch (e) {
        showToast(`Lỗi: ${e.message}`, 'error');
    }
}

// ====================================================================
// 3. QUẢN LÝ NHÂN KHẨU (UC03)
// ====================================================================
async function loadResidents() {
    try {
        const res = await API.residents.getAll();
        state.residents = res.data;
        renderResidentsTable(state.residents);
        populateResidentDropdowns(state.residents);
    } catch (e) {
        showToast(`Lỗi nạp cư dân: ${e.message}`, 'error');
    }
}

function renderResidentsTable(residents) {
    const tbody = document.getElementById('residents-tbody');
    tbody.innerHTML = '';
    residents.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${r.ho_ten}</strong></td>
            <td><span class="badge badge-primary">Căn ${r.so_can_ho}</span></td>
            <td><code>${r.so_cccd || '---'}</code></td>
            <td>${r.ngay_sinh}</td>
            <td>${r.gioi_tinh === 'NAM' ? 'Nam' : 'Nữ'}</td>
            <td><span class="badge ${r.quan_he_chu_ho === 'Chủ hộ' ? 'badge-success' : 'badge-neutral'}">${r.quan_he_chu_ho}</span></td>
            <td>${r.so_dien_thoai || '---'}</td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="deleteResident(${r.ma_nk}, '${r.ho_ten}')">Xóa</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function populateResidentDropdowns(residents) {
    const tempResidentSelect = document.getElementById('temp-select-resident');
    if (tempResidentSelect) {
        tempResidentSelect.innerHTML = residents.map(r => `<option value="${r.ma_nk}">${r.ho_ten} (Căn ${r.so_can_ho} - CCCD: ${r.so_cccd || 'Chưa có'})</option>`).join('');
    }
}

async function deleteResident(id, name) {
    if (!confirm(`Xác nhận xóa cư dân: ${name}?`)) return;
    try {
        await API.residents.delete(id);
        showToast(`Đã xóa cư dân ${name}`, 'success');
        loadResidents();
        loadApartments();
    } catch (e) {
        showToast(`Lỗi: ${e.message}`, 'error');
    }
}

// ====================================================================
// 4. QUẢN LÝ TẠM TRÚ / TẠM VẮNG (UC04)
// ====================================================================
async function loadTemporaryResidence() {
    try {
        const res = await API.temporary.getAll();
        const tbody = document.getElementById('temporary-tbody');
        tbody.innerHTML = '';
        if (res.data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">Chưa có bản ghi tạm trú / tạm vắng nào.</td></tr>`;
            return;
        }
        res.data.forEach(item => {
            const tr = document.createElement('tr');
            const isTT = item.loai === 'TAM_TRU';
            tr.innerHTML = `
                <td><strong>${item.ho_ten}</strong> (CCCD: ${item.so_cccd || '---'})</td>
                <td><span class="badge badge-primary">Căn ${item.so_can_ho}</span></td>
                <td><span class="badge ${isTT ? 'badge-success' : 'badge-warning'}">${isTT ? 'Tạm Trú' : 'Tạm Vắng'}</span></td>
                <td>${item.tu_ngay} ➔ ${item.den_ngay}</td>
                <td>${item.ly_do || '---'}</td>
                <td>${item.ngay_tao ? item.ngay_tao.split(' ')[0] : '---'}</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="deleteTemporary(${item.ma_ttv})">Xóa</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        showToast(`Lỗi nạp tạm trú/tạm vắng: ${e.message}`, 'error');
    }
}

async function deleteTemporary(id) {
    if (!confirm('Xác nhận xóa bản ghi cư trú này?')) return;
    try {
        await API.temporary.delete(id);
        showToast('Đã xóa bản ghi cư trú', 'success');
        loadTemporaryResidence();
    } catch (e) {
        showToast(`Lỗi: ${e.message}`, 'error');
    }
}

// ====================================================================
// 5. QUẢN LÝ PHƯƠNG TIỆN GỬI XE (UC05)
// ====================================================================
async function loadVehicles() {
    try {
        const res = await API.vehicles.getAll();
        const tbody = document.getElementById('vehicles-tbody');
        tbody.innerHTML = '';
        res.data.forEach(v => {
            const tr = document.createElement('tr');
            const isCar = v.loai_xe === 'O_TO';
            const price = isCar ? '1.200.000 đ/tháng' : (v.loai_xe === 'XE_MAY' ? '70.000 đ/tháng' : '40.000 đ/tháng');
            const typeText = isCar ? '🚗 Ô tô' : (v.loai_xe === 'XE_MAY' ? '🛵 Xe máy' : '🚲 Xe đạp điện');

            tr.innerHTML = `
                <td><code><strong>${v.bien_so}</strong></code></td>
                <td>${typeText}</td>
                <td>${v.ten_xe || '---'}</td>
                <td><span class="badge badge-primary">Căn ${v.so_can_ho}</span></td>
                <td>${v.ten_chu_ho || '---'}</td>
                <td><strong style="color:var(--primary);">${price}</strong></td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="deleteVehicle(${v.ma_pt}, '${v.bien_so}')">Hủy gửi xe</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        showToast(`Lỗi nạp phương tiện: ${e.message}`, 'error');
    }
}

async function deleteVehicle(id, license) {
    if (!confirm(`Hủy đăng ký gửi xe biển số: ${license}?`)) return;
    try {
        await API.vehicles.delete(id);
        showToast(`Đã hủy gửi xe ${license}`, 'success');
        loadVehicles();
        loadApartments();
    } catch (e) {
        showToast(`Lỗi: ${e.message}`, 'error');
    }
}

// ====================================================================
// 6. DANH MỤC KHOẢN THU (UC06)
// ====================================================================
async function loadFees() {
    try {
        const res = await API.fees.getAll();
        state.fees = res.data;
        const tbody = document.getElementById('fees-tbody');
        tbody.innerHTML = '';

        state.fees.forEach(f => {
            const tr = document.createElement('tr');
            const badgeType = f.loai === 'BAT_BUOC' ? 'badge-danger' : (f.loai === 'TU_NGUYEN' ? 'badge-success' : 'badge-warning');
            const typeText = f.loai === 'BAT_BUOC' ? 'Bắt buộc' : (f.loai === 'TU_NGUYEN' ? 'Tự nguyện' : 'Thu hộ');

            let calcText = '';
            if (f.cach_tinh === 'THEO_DIEN_TICH') calcText = 'Theo m² diện tích căn hộ';
            else if (f.cach_tinh === 'THEO_XE_MAY') calcText = 'Theo số xe máy đăng ký';
            else if (f.cach_tinh === 'THEO_O_TO') calcText = 'Theo số ô tô đăng ký';
            else if (f.cach_tinh === 'THEO_HO') calcText = 'Theo định mức từng hộ';
            else calcText = 'Nhập hóa đơn thực tế';

            tr.innerHTML = `
                <td><code>KT-${f.ma_kt}</code></td>
                <td><strong>${f.ten_khoan_thu}</strong></td>
                <td><span class="badge ${badgeType}">${typeText}</span></td>
                <td>${calcText}</td>
                <td><strong>${f.don_gia > 0 ? formatVND(f.don_gia) : 'Theo hóa đơn'}</strong></td>
                <td style="color:var(--text-secondary); font-size:12.5px;">${f.ghi_chu || '---'}</td>
                <td><span class="badge badge-success">Đang áp dụng</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        showToast(`Lỗi nạp danh mục khoản thu: ${e.message}`, 'error');
    }
}

// ====================================================================
// 7. LẬP ĐỢT THU PHÍ (UC07 + CR-003)
// ====================================================================
async function loadPeriods() {
    try {
        const res = await API.periods.getAll();
        state.periods = res.data;
        const tbody = document.getElementById('periods-tbody');
        tbody.innerHTML = '';

        // Cập nhật dropdown đợt thu ở tab Điện nước
        const utilSelect = document.getElementById('select-utility-period');
        const utilModalSelect = document.getElementById('util-modal-period');
        if (utilSelect) {
            utilSelect.innerHTML = state.periods.map(p => `<option value="${p.ma_dot}">${p.ten_dot} (${p.thang_nam})</option>`).join('');
        }
        if (utilModalSelect) {
            utilModalSelect.innerHTML = utilSelect.innerHTML;
        }

        state.periods.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${p.ten_dot}</strong></td>
                <td><code>${p.thang_nam}</code></td>
                <td>${p.ngay_bat_dau} ➔ ${p.han_nop}</td>
                <td><span class="badge badge-primary">${p.tong_so_ho} hộ</span></td>
                <td style="font-weight:700;">${formatVND(p.tong_phai_thu)}</td>
                <td style="color:var(--success); font-weight:700;">${formatVND(p.tong_da_thu)}</td>
                <td><span class="badge badge-success">Đang mở thu</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="viewPeriodDetails(${p.ma_dot}, '${p.ten_dot}')">Xem bảng kê chi tiết</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        showToast(`Lỗi nạp đợt thu: ${e.message}`, 'error');
    }
}

async function viewPeriodDetails(maDot, tenDot) {
    try {
        const res = await API.periods.getDetails(maDot);
        state.currentPeriodDetails = res.data;
        document.getElementById('period-detail-title').textContent = `Bảng Kê Chi Tiết: ${tenDot}`;

        const tbody = document.getElementById('period-details-tbody');
        tbody.innerHTML = '';

        res.data.forEach(item => {
            const tr = document.createElement('tr');
            const badgeClass = item.trang_thai === 'DA_NOP_DU' ? 'badge-success' : (item.trang_thai === 'NOP_THIEU' ? 'badge-warning' : 'badge-danger');
            const statusText = item.trang_thai === 'DA_NOP_DU' ? 'Đã nộp đủ' : (item.trang_thai === 'NOP_THIEU' ? 'Nộp thiếu' : 'Chưa nộp');

            tr.innerHTML = `
                <td><strong>${item.so_can_ho}</strong></td>
                <td>${item.ten_chu_ho || '---'}</td>
                <td>${item.ten_khoan_thu}</td>
                <td><strong>${formatVND(item.so_tien_phai_nop)}</strong></td>
                <td style="color:var(--success);">${formatVND(item.so_tien_da_nop)}</td>
                <td style="color:var(--danger); font-weight:700;">${formatVND(item.con_no)}</td>
                <td><span class="badge ${badgeClass}">${statusText}</span></td>
                <td style="font-size:12px; color:var(--text-muted);">${item.ghi_chu || ''}</td>
            `;
            tbody.appendChild(tr);
        });

        openModal('modal-period-details');
    } catch (e) {
        showToast(`Lỗi nạp chi tiết đợt: ${e.message}`, 'error');
    }
}

// ====================================================================
// 8. ĐIỆN NƯỚC THU HỘ (UC08)
// ====================================================================
async function loadUtilities() {
    const periodSelect = document.getElementById('select-utility-period');
    const maDot = periodSelect ? periodSelect.value : 1;
    if (!maDot) return;

    try {
        const res = await API.periods.getDetails(maDot);
        const utilities = res.data.filter(d => d.loai === 'THU_HO');
        const tbody = document.getElementById('utilities-tbody');
        tbody.innerHTML = '';

        if (utilities.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">Chưa có hóa đơn điện nước thu hộ nào trong đợt này. Nhấn nút "Nhập hóa đơn" để thêm!</td></tr>`;
            return;
        }

        utilities.forEach(u => {
            const tr = document.createElement('tr');
            const badgeClass = u.trang_thai === 'DA_NOP_DU' ? 'badge-success' : 'badge-danger';
            tr.innerHTML = `
                <td><strong>${u.so_can_ho}</strong></td>
                <td>${u.ten_chu_ho || '---'}</td>
                <td>Thu phí tháng</td>
                <td><span class="badge badge-warning">${u.ten_khoan_thu}</span></td>
                <td><strong>${formatVND(u.so_tien_phai_nop)}</strong></td>
                <td>${formatVND(u.so_tien_da_nop)}</td>
                <td><span class="badge ${badgeClass}">${u.trang_thai === 'DA_NOP_DU' ? 'Đã thu' : 'Chưa thu'}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        showToast(`Lỗi nạp điện nước: ${e.message}`, 'error');
    }
}

// ====================================================================
// 9. THU PHÍ & IN BIÊN LAI (UC09)
// ====================================================================
async function findApartmentDebt() {
    const aptInput = document.getElementById('collect-search-apt').value.trim().toUpperCase();
    if (!aptInput) {
        showToast('Vui lòng nhập số căn hộ (ví dụ: A1205)', 'error');
        return;
    }

    try {
        const res = await API.collection.getDebt(aptInput);
        if (!res.success) {
            showToast(res.message, 'error');
            return;
        }

        const ho = res.household;
        const debts = res.debts;

        // Cập nhật thông tin chủ hộ
        document.getElementById('debt-apt-number').textContent = `Căn hộ: ${ho.so_can_ho} (Diện tích: ${ho.dien_tich} m²)`;
        document.getElementById('debt-owner-info').textContent = `Chủ hộ: ${ho.ten_chu_ho || 'Chưa gán'} - SĐT: ${ho.so_dien_thoai || 'Chưa có'}`;

        let totalDebt = debts.reduce((sum, d) => sum + d.con_no, 0);
        document.getElementById('debt-total-amount').textContent = formatVND(totalDebt);

        const tbody = document.getElementById('debt-list-tbody');
        tbody.innerHTML = '';

        if (debts.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--success); font-weight:600; padding:20px;">🎉 Căn hộ này đã hoàn thành toàn bộ nghĩa vụ nộp phí! Không còn khoản nợ nào.</td></tr>`;
        } else {
            debts.forEach((d, idx) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${idx + 1}</td>
                    <td><code>${d.ten_dot}</code></td>
                    <td><strong>${d.ten_khoan_thu}</strong></td>
                    <td>${formatVND(d.so_tien_phai_nop)}</td>
                    <td>${formatVND(d.so_tien_da_nop)}</td>
                    <td style="color:var(--danger); font-weight:700;">${formatVND(d.con_no)}</td>
                    <td>
                        <button class="btn btn-sm btn-success" onclick="openPayModal(${d.ma_ct}, '${d.ten_khoan_thu}', ${d.con_no}, '${ho.ten_chu_ho || ''}')">
                            💰 Nộp khoản này
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        document.getElementById('debt-result-container').style.display = 'block';

    } catch (e) {
        showToast(`Lỗi tìm công nợ: ${e.message}`, 'error');
    }
}

function openPayModal(maCt, feeName, debtAmount, defaultPayer) {
    document.getElementById('pay-ma-ct').value = maCt;
    document.getElementById('pay-fee-name').value = feeName;
    document.getElementById('pay-fee-debt').value = formatVND(debtAmount);
    document.getElementById('pay-fee-input').value = debtAmount;
    document.getElementById('pay-payer-name').value = defaultPayer || '';
    openModal('modal-collect-pay');
}

async function loadCollectionHistory() {
    try {
        const res = await API.collection.getReceipts();
        const tbody = document.getElementById('receipts-tbody');
        tbody.innerHTML = '';

        res.data.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><code><strong>${r.ma_phieu}</strong></code></td>
                <td><span class="badge badge-primary">Căn ${r.so_can_ho}</span></td>
                <td>${r.ten_khoan_thu}</td>
                <td style="font-weight:700; color:var(--success);">${formatVND(r.so_tien)}</td>
                <td>${r.nguoi_nop}</td>
                <td>${r.phuong_thuc === 'CHUYEN_KHOAN' ? 'Chuyển khoản' : 'Tiền mặt'}</td>
                <td>${r.ten_thu_ngan || 'Kế toán'}</td>
                <td>${r.ngay_nop}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="previewReceipt(${JSON.stringify(r).replace(/"/g, '&quot;')})">
                        🖨️ In Laser
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        showToast(`Lỗi nạp biên lai: ${e.message}`, 'error');
    }
}

/**
 * Hiển thị Modal Mẫu Biên Lai In Laser Chuẩn Cư Dân (UC09)
 */
function previewReceipt(receipt) {
    document.getElementById('rec-code').textContent = receipt.ma_phieu;
    document.getElementById('rec-apt').textContent = receipt.so_can_ho;
    document.getElementById('rec-area').textContent = receipt.dien_tich || '80';
    document.getElementById('rec-payer').textContent = receipt.nguoi_nop;
    document.getElementById('rec-date').textContent = receipt.ngay_nop || new Date().toLocaleDateString('vi-VN');
    document.getElementById('rec-period').textContent = receipt.ten_dot || 'Kỳ thu hiện hành';
    document.getElementById('rec-cashier').textContent = receipt.ten_thu_ngan || state.currentUser.fullname;

    document.getElementById('rec-fee-name').textContent = receipt.ten_khoan_thu;
    document.getElementById('rec-fee-due').textContent = formatVND(receipt.so_tien_phai_nop || receipt.so_tien);
    document.getElementById('rec-fee-paid').textContent = formatVND(receipt.so_tien);
    document.getElementById('rec-fee-remain').textContent = formatVND(receipt.con_no || 0);

    document.getElementById('rec-amount-num').textContent = formatVND(receipt.so_tien);
    document.getElementById('rec-amount-words').textContent = numberToVietnameseWords(receipt.so_tien);
    document.getElementById('rec-method').textContent = receipt.phuong_thuc === 'CHUYEN_KHOAN' ? 'Chuyển khoản ngân hàng' : 'Tiền mặt tại văn phòng BQT';

    document.getElementById('rec-sign-payer').textContent = receipt.nguoi_nop;
    document.getElementById('rec-sign-cashier').textContent = receipt.ten_thu_ngan || state.currentUser.fullname;

    openModal('modal-receipt-print');
}

// ====================================================================
// 10. THỐNG KÊ & BÁO CÁO (UC10)
// ====================================================================
async function loadReports() {
    try {
        const res = await API.statistics.getOverview();
        const tbody = document.getElementById('report-fees-tbody');
        tbody.innerHTML = '';

        res.data.by_fee.forEach(f => {
            const tr = document.createElement('tr');
            const conNo = f.phai_thu - f.da_thu;
            const rate = f.phai_thu > 0 ? ((f.da_thu / f.phai_thu) * 100).toFixed(1) : 100;

            tr.innerHTML = `
                <td><strong>${f.ten_khoan_thu}</strong></td>
                <td><span class="badge ${f.loai === 'BAT_BUOC' ? 'badge-danger' : 'badge-success'}">${f.loai}</span></td>
                <td>${formatVND(f.phai_thu)}</td>
                <td style="color:var(--success); font-weight:600;">${formatVND(f.da_thu)}</td>
                <td style="color:var(--danger); font-weight:600;">${formatVND(conNo)}</td>
                <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-weight:700;">${rate}%</span>
                        <div style="flex:1; height:6px; background-color:var(--bg-subtle); border-radius:3px; overflow:hidden;">
                            <div style="width:${rate}%; height:100%; background-color:var(--success);"></div>
                        </div>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        showToast(`Lỗi nạp báo cáo: ${e.message}`, 'error');
    }
}

// ====================================================================
// 11. TÀI KHOẢN & PHÂN QUYỀN (UC11)
// ====================================================================
async function loadUsers() {
    try {
        const res = await API.users.getAll();
        const tbody = document.getElementById('users-tbody');
        tbody.innerHTML = '';

        res.data.forEach(u => {
            const tr = document.createElement('tr');
            const isLocked = u.trang_thai === 'KHOA';
            const roleBadge = u.vai_tro === 'ADMIN' ? 'badge-danger' : (u.vai_tro === 'BAN_QUAN_TRI' ? 'badge-primary' : 'badge-warning');

            tr.innerHTML = `
                <td><code>TK-${u.ma_tk}</code></td>
                <td><strong>${u.ten_dang_nhap}</strong></td>
                <td>${u.ho_ten}</td>
                <td><span class="badge ${roleBadge}">${u.vai_tro}</span></td>
                <td>${u.so_dien_thoai || '---'}</td>
                <td><span class="badge ${isLocked ? 'badge-danger' : 'badge-success'}">${isLocked ? 'Bị khóa' : 'Hoạt động'}</span></td>
                <td>
                    <button class="btn btn-sm ${isLocked ? 'btn-success' : 'btn-danger'}" onclick="toggleUser(${u.ma_tk})">
                        ${isLocked ? 'Mở khóa' : 'Khóa tài khoản'}
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        showToast(`Lỗi nạp người dùng: ${e.message}`, 'error');
    }
}

async function toggleUser(id) {
    try {
        await API.users.toggleStatus(id);
        showToast('Đã cập nhật trạng thái tài khoản', 'success');
        loadUsers();
    } catch (e) {
        showToast(`Lỗi: ${e.message}`, 'error');
    }
}

// ====================================================================
// 12. SAO LƯU & PHỤC HỒI CSDL (UC12)
// ====================================================================
async function downloadBackup() {
    try {
        const res = await API.system.backup();
        const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bluemoon_backup_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        showToast('Đã tải xuống bản sao lưu CSDL thành công!', 'success');
    } catch (e) {
        showToast(`Lỗi sao lưu: ${e.message}`, 'error');
    }
}

async function executeRestore() {
    const fileInput = document.getElementById('file-restore');
    if (!fileInput.files || fileInput.files.length === 0) {
        showToast('Vui lòng chọn tệp tin JSON sao lưu!', 'error');
        return;
    }

    if (!confirm('CẢNH BÁO: Thao tác này sẽ ghi đè toàn bộ dữ liệu hiện tại bằng dữ liệu trong bản sao lưu! Bạn có chắc chắn muốn khôi phục?')) return;

    const file = fileInput.files[0];
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const data = JSON.parse(e.target.result);
            const res = await API.system.restore(data);
            showToast(res.message, 'success');
            loadDashboard();
            loadApartments();
        } catch (err) {
            showToast(`Lỗi phục hồi: ${err.message}`, 'error');
        }
    };
    reader.readAsText(file);
}

// ====================================================================
// 13. CỔNG CƯ DÂN & ĐÓNG TIỀN ONLINE (VAI TRÒ KHÁCH/CHỦ HỘ)
// ====================================================================
let currentResidentPortalData = null;

async function loadResidentPortal(maHo = 1) {
    try {
        const res = await API.resident.getPortal(maHo);
        if (!res.success) {
            showToast(res.message, 'error');
            return;
        }

        const data = res.data;
        currentResidentPortalData = data;
        const apt = data.apartment;

        // Banner thông tin căn hộ
        document.getElementById('res-apt-title').textContent = `Căn hộ: ${apt.so_can_ho}`;
        document.getElementById('res-apt-desc').textContent = `Chủ hộ: ${apt.ten_chu_ho || 'Chưa gán'} • SĐT: ${apt.sdt_chu_ho || 'Chưa có'} • Diện tích: ${apt.dien_tich} m² • Tầng: ${apt.so_tang}`;

        // Thống kê nợ
        const totalDebt = data.bills.reduce((sum, b) => sum + b.con_no, 0);
        const unpaidBills = data.bills.filter(b => b.con_no > 0);

        document.getElementById('res-banner-debt').textContent = formatVND(totalDebt);
        document.getElementById('res-stat-debt').textContent = formatVND(totalDebt);
        document.getElementById('res-stat-count').textContent = `${unpaidBills.length} khoản chưa thanh toán`;

        // Hạn nộp gần nhất
        let nearestDeadline = '25/11/2026';
        if (unpaidBills.length > 0 && unpaidBills[0].han_nop) {
            nearestDeadline = unpaidBills[0].han_nop;
        }
        document.getElementById('res-stat-deadline').textContent = nearestDeadline;

        // Bảng hóa đơn các khoản phí & Hạn nộp
        const tbodyBills = document.getElementById('res-bills-tbody');
        tbodyBills.innerHTML = '';

        if (data.bills.length === 0) {
            tbodyBills.innerHTML = `<tr><td colspan="9" style="text-align:center; color:var(--text-muted); padding:20px;">Chưa phát sinh hóa đơn nào cho căn hộ này.</td></tr>`;
        } else {
            data.bills.forEach((b, idx) => {
                const tr = document.createElement('tr');
                const isPaid = b.con_no <= 0;
                const statusBadge = isPaid 
                    ? '<span class="badge badge-success">Đã nộp đủ</span>' 
                    : (b.so_tien_da_nop > 0 ? '<span class="badge badge-warning">Nộp thiếu</span>' : '<span class="badge badge-danger">Chưa nộp</span>');

                // Deadline indicator
                let deadlineBadge = `<span class="badge badge-neutral">${b.han_nop || 'Định kỳ'}</span>`;
                if (!isPaid && b.han_nop) {
                    const today = new Date().toISOString().slice(0, 10);
                    if (today > b.han_nop) {
                        deadlineBadge = `<span class="badge badge-danger">⚠️ Quá hạn (${b.han_nop})</span>`;
                    } else {
                        deadlineBadge = `<span class="badge badge-warning">⏰ Hạn nộp: ${b.han_nop}</span>`;
                    }
                }

                const payBtn = isPaid 
                    ? `<button class="btn btn-sm btn-secondary" disabled>Đã xong</button>`
                    : `<button class="btn btn-sm btn-success" onclick="openOnlinePayment(${b.ma_ct}, '${b.ten_khoan_thu}', ${b.con_no}, '${apt.so_can_ho}')">
                         📲 Đóng Online
                       </button>`;

                tr.innerHTML = `
                    <td>${idx + 1}</td>
                    <td><strong>${b.ten_khoan_thu}</strong></td>
                    <td><code>${b.ten_dot}</code></td>
                    <td>${deadlineBadge}</td>
                    <td>${formatVND(b.so_tien_phai_nop)}</td>
                    <td style="color:var(--success);">${formatVND(b.so_tien_da_nop)}</td>
                    <td style="color:var(--danger); font-weight:700;">${formatVND(b.con_no)}</td>
                    <td>${statusBadge}</td>
                    <td>${payBtn}</td>
                `;
                tbodyBills.appendChild(tr);
            });
        }

        // Bảng lịch sử phiếu thu
        const tbodyReceipts = document.getElementById('res-receipts-tbody');
        tbodyReceipts.innerHTML = '';
        if (data.receipts.length === 0) {
            tbodyReceipts.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:16px;">Chưa có giao dịch thanh toán nào được ghi nhận.</td></tr>`;
        } else {
            data.receipts.forEach(r => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><code><strong>${r.ma_phieu}</strong></code></td>
                    <td>${r.ten_khoan_thu}</td>
                    <td>${r.ten_dot}</td>
                    <td style="color:var(--success); font-weight:700;">${formatVND(r.so_tien)}</td>
                    <td>${r.ngay_nop}</td>
                    <td><span class="badge badge-primary">${r.phuong_thuc === 'CHUYEN_KHOAN' ? 'Chuyển khoản VietQR' : 'Tiền mặt'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="previewReceipt(${JSON.stringify(r).replace(/"/g, '&quot;')})">
                            📄 Xem biên lai
                        </button>
                    </td>
                `;
                tbodyReceipts.appendChild(tr);
            });
        }

        // Bảng thành viên gia đình
        const tbodyMembers = document.getElementById('res-members-tbody');
        tbodyMembers.innerHTML = '';
        data.members.forEach(m => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${m.ho_ten}</strong></td>
                <td><span class="badge ${m.quan_he_chu_ho === 'Chủ hộ' ? 'badge-success' : 'badge-neutral'}">${m.quan_he_chu_ho}</span></td>
                <td>${m.ngay_sinh}</td>
                <td><code>${m.so_cccd || '---'}</code></td>
            `;
            tbodyMembers.appendChild(tr);
        });

        // Bảng xe cộ
        const tbodyVehicles = document.getElementById('res-vehicles-tbody');
        tbodyVehicles.innerHTML = '';
        if (data.vehicles.length === 0) {
            tbodyVehicles.innerHTML = `<tr><td colspan="3" style="text-align:center; color:var(--text-muted);">Căn hộ chưa đăng ký gửi phương tiện nào.</td></tr>`;
        } else {
            data.vehicles.forEach(v => {
                const tr = document.createElement('tr');
                const isCar = v.loai_xe === 'O_TO';
                tr.innerHTML = `
                    <td><code><strong>${v.bien_so}</strong></code></td>
                    <td>${isCar ? '🚗 Ô tô (1.200.000 đ)' : '🛵 Xe máy (70.000 đ)'}</td>
                    <td>${v.ten_xe || '---'}</td>
                `;
                tbodyVehicles.appendChild(tr);
            });
        }

    } catch (e) {
        showToast(`Lỗi nạp thông tin cư dân: ${e.message}`, 'error');
    }
}

function openOnlinePayment(maCt, feeTitle, amount, soCanHo) {
    document.getElementById('online-pay-ma-ct').value = maCt;
    document.getElementById('online-pay-fee-title').textContent = feeTitle;
    document.getElementById('online-pay-amount').textContent = formatVND(amount);
    
    // Tạo nội dung chuyển khoản tự động
    const cleanFee = feeTitle.replace(/[^a-zA-Z0-9 ]/g, '').slice(0, 15);
    const memo = `BMFM ${soCanHo} ${cleanFee}`.toUpperCase();
    document.getElementById('online-pay-memo').textContent = memo;

    // Sinh mã QR ngân hàng chuẩn VietQR
    const qrUrl = `https://img.vietqr.io/image/970422-0987654321-compact2.png?amount=${Math.round(amount)}&addInfo=${encodeURIComponent(memo)}&accountName=BAN%20QUAN%20TRI%20CHUNG%20CU%20BLUE%20MOON`;
    document.getElementById('vietqr-img').src = qrUrl;

    openModal('modal-resident-pay');
}

// ====================================================================
// KHỞI TẠO CÁC SỰ KIỆN SUBMIT FORM
// ====================================================================
function initFormListeners() {
    // 1. Thêm Căn hộ
    document.getElementById('btn-add-apartment')?.addEventListener('click', () => openModal('modal-apartment'));
    document.getElementById('btn-save-apartment')?.addEventListener('click', async () => {
        const form = document.getElementById('form-apartment');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const res = await API.apartments.create(data);
            showToast(res.message, 'success');
            closeModal('modal-apartment');
            form.reset();
            loadApartments();
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    // 2. Thêm Nhân khẩu
    document.getElementById('btn-add-resident')?.addEventListener('click', () => openModal('modal-resident'));
    document.getElementById('btn-save-resident')?.addEventListener('click', async () => {
        const form = document.getElementById('form-resident');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const res = await API.residents.create(data);
            showToast(res.message, 'success');
            closeModal('modal-resident');
            form.reset();
            loadResidents();
            loadApartments();
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    // 3. Đăng ký Tạm trú/Tạm vắng
    document.getElementById('btn-add-temporary')?.addEventListener('click', () => openModal('modal-temporary-add'));
    document.getElementById('btn-save-temp')?.addEventListener('click', async () => {
        const form = document.getElementById('form-temporary-add');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const res = await API.temporary.create(data);
            showToast(res.message, 'success');
            closeModal('modal-temporary-add');
            form.reset();
            loadTemporaryResidence();
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    // 4. Đăng ký Xe
    document.getElementById('btn-add-vehicle')?.addEventListener('click', () => openModal('modal-vehicle'));
    document.getElementById('btn-save-vehicle')?.addEventListener('click', async () => {
        const form = document.getElementById('form-vehicle');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const res = await API.vehicles.create(data);
            showToast(res.message, 'success');
            closeModal('modal-vehicle');
            form.reset();
            loadVehicles();
            loadApartments();
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    // 5. Thêm Đợt thu phí
    document.getElementById('btn-add-period')?.addEventListener('click', () => openModal('modal-period'));
    document.getElementById('btn-save-period')?.addEventListener('click', async () => {
        const form = document.getElementById('form-period');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const res = await API.periods.create(data);
            showToast(res.message, 'success');
            closeModal('modal-period');
            form.reset();
            loadPeriods();
            loadDashboard();
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    // 6. Nhập tiền điện nước
    document.getElementById('btn-add-utility')?.addEventListener('click', () => openModal('modal-utility'));
    document.getElementById('btn-save-utility')?.addEventListener('click', async () => {
        const form = document.getElementById('form-utility');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const res = await API.utility.save(data);
            showToast(res.message, 'success');
            closeModal('modal-utility');
            form.reset();
            loadUtilities();
            loadPeriods();
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    // 7. Tra cứu & Thu tiền
    document.getElementById('btn-find-debt')?.addEventListener('click', findApartmentDebt);
    document.getElementById('btn-confirm-pay')?.addEventListener('click', async () => {
        const form = document.getElementById('form-collect-pay');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        data.ma_tk_thu = state.currentUser.id;

        try {
            const res = await API.collection.collect(data);
            showToast(res.message, 'success');
            closeModal('modal-collect-pay');
            form.reset();

            // Tải lại công nợ căn hộ
            findApartmentDebt();
            loadCollectionHistory();
            loadDashboard();

            // Tự động mở xem trước biên lai in Laser
            if (res.receipt) {
                previewReceipt(res.receipt);
            }
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    // 8. Tạo cán bộ mới
    document.getElementById('btn-add-user')?.addEventListener('click', () => openModal('modal-user'));
    document.getElementById('btn-save-user')?.addEventListener('click', async () => {
        const form = document.getElementById('form-user');
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            const res = await API.users.create(data);
            showToast(res.message, 'success');
            closeModal('modal-user');
            form.reset();
            loadUsers();
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    // 9. Backup & Restore
    document.getElementById('btn-download-backup')?.addEventListener('click', downloadBackup);
    document.getElementById('btn-exec-restore')?.addEventListener('click', executeRestore);

    // 10. Xuất file CSV
    document.getElementById('btn-export-csv')?.addEventListener('click', () => {
        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "Khoản Thu,Phân Loại,Phải Thu,Đã Thu,Còn Nợ\n";
        const rows = document.querySelectorAll('#report-fees-tbody tr');
        rows.forEach(r => {
            const cols = r.querySelectorAll('td');
            if (cols.length >= 5) {
                const row = [cols[0].innerText, cols[1].innerText, cols[2].innerText.replace(/[^0-9]/g,''), cols[3].innerText.replace(/[^0-9]/g,''), cols[4].innerText.replace(/[^0-9]/g,'')].join(",");
                csvContent += row + "\r\n";
            }
        });
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `bao_cao_thu_phi_${new Date().toISOString().slice(0,10)}.csv`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        showToast('Đã xuất báo cáo CSV thành công!', 'success');
    });

    // 11. Cư dân đóng tiền Online VietQR
    document.getElementById('btn-confirm-online-paid')?.addEventListener('click', async () => {
        const maCt = document.getElementById('online-pay-ma-ct').value;
        const feeTitle = document.getElementById('online-pay-fee-title').textContent;
        const amountText = document.getElementById('online-pay-amount').textContent;
        const amount = parseFloat(amountText.replace(/[^0-9]/g, '')) || 0;
        const payerName = state.currentUser.fullname || 'Nguyễn Văn An';

        if (!maCt || amount <= 0) {
            showToast('Không tìm thấy thông tin khoản thu cần thanh toán!', 'error');
            return;
        }

        try {
            const res = await API.resident.payOnline({
                ma_ct: maCt,
                so_tien: amount,
                nguoi_nop: payerName,
                phuong_thuc: 'CHUYEN_KHOAN',
                ghi_chu: `Thanh toán Online VietQR 24/7 (${feeTitle})`
            });

            showToast(res.message, 'success');
            closeModal('modal-resident-pay');

            // Tải lại dữ liệu trang Cư dân & Dashboard
            loadResidentPortal(state.currentUser.ma_ho || 1);
            loadDashboard();

            // Mở biên lai điện tử
            if (res.receipt) {
                previewReceipt(res.receipt);
            }
        } catch (e) {
            showToast(`Lỗi thanh toán: ${e.message}`, 'error');
        }
    });

    // Nút đóng toàn bộ tiền bằng VietQR
    document.getElementById('btn-resident-pay-all')?.addEventListener('click', () => {
        if (!currentResidentPortalData || !currentResidentPortalData.bills) return;
        const unpaidBills = currentResidentPortalData.bills.filter(b => b.con_no > 0);
        if (unpaidBills.length === 0) {
            showToast('Căn hộ của bạn không còn khoản nợ nào cần thanh toán!', 'success');
            return;
        }
        // Chọn khoản nợ đầu tiên để thanh toán
        const first = unpaidBills[0];
        openOnlinePayment(first.ma_ct, first.ten_khoan_thu, first.con_no, currentResidentPortalData.apartment.so_can_ho);
    });

    // Tìm kiếm nhanh căn hộ
    document.getElementById('search-apartment')?.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = state.apartments.filter(a => 
            a.so_can_ho.toLowerCase().includes(term) || 
            (a.ten_chu_ho && a.ten_chu_ho.toLowerCase().includes(term))
        );
        renderApartmentsTable(filtered);
    });

    // Tìm kiếm nhanh cư dân
    document.getElementById('search-resident')?.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = state.residents.filter(r => 
            r.ho_ten.toLowerCase().includes(term) || 
            (r.so_cccd && r.so_cccd.includes(term)) ||
            r.so_can_ho.toLowerCase().includes(term)
        );
        renderResidentsTable(filtered);
    });
}

// ====================================================================
// ĐIỂM KHỞI ĐỘNG ỨNG DỤNG (INITIALIZATION)
// ====================================================================
document.addEventListener('DOMContentLoaded', () => {
    console.log(">>> Khởi tạo ứng dụng Web Quản lý thu phí chung cư Blue Moon...");
    initNavigation();
    initFormListeners();

    // Hiển thị thông tin người dùng mẫu
    document.getElementById('user-name').textContent = state.currentUser.fullname;

    // Nạp dữ liệu ban đầu
    loadDashboard();
    loadApartments();
    loadResidents();
    loadFees();
    loadPeriods();
});
