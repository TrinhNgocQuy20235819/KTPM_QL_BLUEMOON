/**
 * ====================================================================
 * DỰ ÁN QUẢN LÝ THU PHÍ CHUNG CƯ BLUE MOON (BMFM)
 * File: app.js
 * Mô tả: Toàn bộ Logic điều khiển giao diện Frontend Single Page Application
 *        Xử lý 12 Use-Case, Chuyển tab, Quản lý Modal, Gọi REST API,
 *        Vẽ biểu đồ Chart.js và Định dạng biên lai in laser (UC09)
 * ====================================================================
 */

// ====================================================================
// TRẠNG THÁI ỨNG DỤNG TOÀN CỤC (APP STATE & SESSION)
// ====================================================================
let initialUser = null;
try {
    const stored = localStorage.getItem('bmfm_user');
    if (stored) initialUser = JSON.parse(stored);
} catch (e) {
    console.error("Lỗi đọc session user:", e);
}

const state = {
    currentUser: initialUser || {
        ma_tk: 4,
        ten_dang_nhap: 'ketoan_minh',
        ho_ten: 'Kế toán Nguyễn Hồng Minh',
        vai_tro: 'KE_TOAN',
        role: 'KE_TOAN',
        fullname: 'Kế toán Nguyễn Hồng Minh'
    },
    apartments: [],
    residents: [],
    fees: [],
    periods: [],
    currentPeriodDetails: [],
    chartInstance: null
};

// Đồng bộ các thuộc tính tên gọi
function syncUserProperties(u) {
    if (!u) return u;
    if (u.vai_tro && !u.role) u.role = u.vai_tro;
    if (u.role && !u.vai_tro) u.vai_tro = u.role;
    if (u.ho_ten && !u.fullname) u.fullname = u.ho_ten;
    if (u.fullname && !u.ho_ten) u.ho_ten = u.fullname;
    return u;
}
syncUserProperties(state.currentUser);

// ====================================================================
// MA TRẬN PHÂN QUYỀN HỆ THỐNG (ROLE-BASED ACCESS CONTROL - RBAC)
// ====================================================================
const ROLE_PERMISSIONS = {
    ADMIN: {
        name: 'Quản trị viên (Admin)',
        badgeClass: 'role-admin',
        badgeText: '👑 VAI TRÒ: QUẢN TRỊ VIÊN HỆ THỐNG (ADMIN)',
        description: '<strong>Phạm vi quản trị:</strong> Toàn quyền quản trị hệ thống: Duyệt các đề xuất & kiến nghị của cư dân các phòng, Phân quyền cán bộ (UC11), Sao lưu & Phục hồi CSDL (UC12), Quản lý Căn hộ, Nhân khẩu, Phương tiện, Lập đợt thu và Báo cáo tài chính. <em>(Lưu ý: Nghiệp vụ đăng ký biến động tạm trú / tạm vắng do Ban Quản Trị trực tiếp phụ trách theo quy định).</em>',
        allowedTabs: ['tab-dashboard', 'tab-apartments', 'tab-residents', 'tab-temporary', 'tab-vehicles', 'tab-fees', 'tab-periods', 'tab-utilities', 'tab-collection', 'tab-reports', 'tab-proposals', 'tab-users', 'tab-system', 'tab-resident-portal'],
        defaultTab: 'tab-dashboard'
    },
    BAN_QUAN_TRI: {
        name: 'Ban Quản Trị (BQT)',
        badgeClass: 'role-bqt',
        badgeText: '🏢 VAI TRÒ: BAN QUẢN TRỊ (BQT)',
        description: '<strong>Phạm vi Ban Quản Trị:</strong> Quản lý toàn bộ Căn hộ & Hộ khẩu (UC02), Nhân khẩu cư dân (UC03), Trực tiếp thực hiện nghiệp vụ Đăng ký Tạm trú / Tạm vắng (UC04), Phương tiện gửi xe (UC05), Cấu hình danh mục khoản thu & đơn giá (UC06), Duyệt các đề xuất kiến nghị của cư dân các phòng gửi lên, Xem thống kê báo cáo (UC10) và Hỗ trợ cư dân qua Cổng cư dân.',
        allowedTabs: ['tab-dashboard', 'tab-apartments', 'tab-residents', 'tab-temporary', 'tab-vehicles', 'tab-fees', 'tab-proposals', 'tab-reports', 'tab-resident-portal'],
        defaultTab: 'tab-dashboard'
    },
    KE_TOAN: {
        name: 'Kế toán / Thu ngân',
        badgeClass: '',
        badgeText: '💼 VAI TRÒ: KẾ TOÁN / THU NGÂN',
        description: '<strong>Phạm vi Kế toán / Thu ngân:</strong> Quản lý các nội dung tài chính: Lập đợt thu tự động theo diện tích sàn, số xe & số ngày thực tế (UC07), Nhập tiền điện nước thu hộ (UC08), Thu tiền phí & In biên lai laser chuẩn (UC09), Xem công nợ và Báo cáo tài chính (UC10). <em>(Thu ngân có quyền xem các bảng Căn hộ, Phương tiện, Đơn giá do Ban Quản Trị quản lý; không có quyền thêm/sửa/xóa căn hộ hay cư dân).</em>',
        allowedTabs: ['tab-dashboard', 'tab-apartments', 'tab-vehicles', 'tab-fees', 'tab-periods', 'tab-utilities', 'tab-collection', 'tab-reports'],
        defaultTab: 'tab-dashboard'
    },
    CU_DAN: {
        name: 'Cư dân / Chủ hộ',
        badgeClass: 'role-cudan',
        badgeText: '🏡 VAI TRÒ: CƯ DÂN / CHỦ HỘ',
        description: '<strong>Phạm vi Cư dân / Chủ hộ:</strong> Xem thông tin căn hộ, Cập nhật thông tin liên hệ căn hộ, Đăng ký thành viên gia đình, Đăng ký phương tiện (ô tô, xe máy), Gửi đề xuất/kiến nghị tới Ban Quản Trị, Tra cứu hóa đơn các khoản phí, Nộp tiền online qua VietQR 24/7 và Xuất hóa đơn điện tử online chuẩn VAT.',
        allowedTabs: ['tab-resident-portal', 'tab-fees'],
        defaultTab: 'tab-resident-portal'
    }
};

const TEST_ACCOUNTS = {
    'ADMIN': { username: 'admin', pass: 'admin123' },
    'BAN_QUAN_TRI': { username: 'bqt_truongban', pass: 'bqt123' },
    'KE_TOAN': { username: 'ketoan_minh', pass: 'ketoan123' },
    'cudan_a1205': { username: 'cudan_a1205', pass: '123456' },
    'cudan_b1104': { username: 'cudan_b1104', pass: '123456' },
    'cudan_b0402': { username: 'cudan_b0402', pass: '123456' },
    'cudan_a1801': { username: 'cudan_a1801', pass: '123456' }
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
    result = result.charAt(0).toUpperCase() + result.slice(1) + ' đồng chẵn.';
    return result;
}

/**
 * Hiển thị thông báo nổi Toast Notification
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
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
// XỬ LÝ PHÂN QUYỀN VAI TRÒ & ĐIỀU HƯỚNG TAB
// ====================================================================

/**
 * Áp dụng phân quyền RBAC lên toàn bộ giao diện
 */
function applyRolePermissions(role) {
    syncUserProperties(state.currentUser);
    const userRole = role || state.currentUser.role || 'KE_TOAN';
    state.currentUser.role = userRole;
    state.currentUser.vai_tro = userRole;

    const perm = ROLE_PERMISSIONS[userRole] || ROLE_PERMISSIONS['KE_TOAN'];

    // 1. Ẩn/Hiện Menu Sidebar & các nút hành động phân quyền trên toàn trang
    document.querySelectorAll('[data-roles]').forEach(el => {
        const rolesAttr = el.getAttribute('data-roles') || '';
        const rolesList = rolesAttr.split(',').map(s => s.trim());
        if (rolesList.includes(userRole)) {
            el.style.display = '';
        } else {
            el.style.display = 'none';
        }
    });

    // 2. Cập nhật Thẻ hiển thị thông tin người dùng ở góc dưới Sidebar
    const avatarEl = document.getElementById('user-avatar');
    const nameEl = document.getElementById('user-name');
    const badgeEl = document.getElementById('user-role-badge');

    if (avatarEl) {
        if (userRole === 'ADMIN') avatarEl.textContent = 'AD';
        else if (userRole === 'BAN_QUAN_TRI') avatarEl.textContent = 'BQT';
        else if (userRole === 'KE_TOAN') avatarEl.textContent = 'KT';
        else avatarEl.textContent = 'CD';
    }

    if (nameEl) {
        nameEl.textContent = state.currentUser.fullname || state.currentUser.ho_ten || 'Người dùng';
    }

    if (badgeEl) {
        badgeEl.textContent = perm.name;
    }

    // 3. Cập nhật Role Permission Banner
    const banner = document.getElementById('role-permission-banner');
    const bannerBadge = document.getElementById('banner-role-badge');
    const bannerDesc = document.getElementById('banner-role-desc');

    if (banner) {
        banner.classList.remove('role-admin', 'role-bqt', 'role-cudan');
        if (perm.badgeClass) banner.classList.add(perm.badgeClass);
    }
    if (bannerBadge) {
        bannerBadge.textContent = perm.badgeText;
    }
    if (bannerDesc) {
        bannerDesc.innerHTML = perm.description;
    }

    // 4. Đồng bộ nút Topbar Auth
    const btnAuth = document.getElementById('btn-topbar-auth');
    if (btnAuth) {
        btnAuth.textContent = `👤 ${state.currentUser.ten_dang_nhap || state.currentUser.username}`;
    }

    // 5. Kiểm tra nếu Tab đang hiển thị không hợp lệ với quyền -> Chuyển sang Tab mặc định
    const currentActivePane = document.querySelector('.tab-pane.active');
    const currentTabId = currentActivePane ? currentActivePane.id : '';

    if (!perm.allowedTabs.includes(currentTabId)) {
        switchTab(perm.defaultTab);
    } else {
        // Tải lại dữ liệu cho tab hiện tại
        loadTabData(currentTabId);
    }
}

/**
 * Chuyển tab có kiểm tra phân quyền chặt chẽ
 */
function switchTab(targetTab) {
    const role = state.currentUser.role || 'KE_TOAN';
    const perm = ROLE_PERMISSIONS[role] || ROLE_PERMISSIONS['KE_TOAN'];
    const navItems = document.querySelectorAll('.sidebar-menu .nav-item');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const pageHeading = document.getElementById('page-heading');

    // Nếu tab không nằm trong danh sách quyền -> Báo lỗi Access Denied
    if (!perm.allowedTabs.includes(targetTab)) {
        tabPanes.forEach(pane => pane.classList.remove('active'));
        const deniedPane = document.getElementById('tab-access-denied');
        if (deniedPane) deniedPane.classList.add('active');
        if (pageHeading) pageHeading.textContent = 'Truy Cập Bị Từ Chối (403)';

        const msgEl = document.getElementById('access-denied-message');
        if (msgEl) {
            msgEl.innerHTML = `Tài khoản của bạn hiện đang đăng nhập với vai trò <strong>${perm.name}</strong>. Phân hệ chức năng này không nằm trong phạm vi quyền hạn được cấp phép. Bạn chỉ có quyền truy cập: <em>${perm.allowedTabs.join(', ')}</em>.`;
        }
        navItems.forEach(i => i.classList.remove('active'));
        return;
    }

    // Cập nhật trạng thái active trên sidebar
    navItems.forEach(i => {
        if (i.getAttribute('data-tab') === targetTab) {
            i.classList.add('active');
            const titleSpan = i.querySelector('span:last-child');
            if (titleSpan && pageHeading) {
                pageHeading.textContent = titleSpan.textContent;
            }
        } else {
            i.classList.remove('active');
        }
    });

    // Chuyển tab hiển thị
    tabPanes.forEach(pane => {
        pane.classList.remove('active');
        if (pane.id === targetTab) {
            pane.classList.add('active');
        }
    });

    // Gọi tải dữ liệu tương ứng
    loadTabData(targetTab);
}

/**
 * Khởi tạo điều hướng thanh Sidebar và Topbar
 */
function initNavigation() {
    const navItems = document.querySelectorAll('.sidebar-menu .nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });

    // Nút quay lại từ màn hình Access Denied
    document.getElementById('btn-back-to-allowed')?.addEventListener('click', () => {
        const role = state.currentUser.role || 'KE_TOAN';
        const perm = ROLE_PERMISSIONS[role] || ROLE_PERMISSIONS['KE_TOAN'];
        switchTab(perm.defaultTab);
    });

    // Xử lý chuyển đổi vai trò (Role Switcher trên Topbar để test nhanh)
    const roleSwitcher = document.getElementById('role-switcher');
    roleSwitcher?.addEventListener('change', async (e) => {
        const val = e.target.value;
        const targetAcc = TEST_ACCOUNTS[val];
        if (targetAcc) {
            await quickLogin(targetAcc.username, targetAcc.pass);
        } else {
            state.currentUser.role = val;
            state.currentUser.vai_tro = val;
            applyRolePermissions(val);
            showToast(`Đã chuyển sang vai trò: ${ROLE_PERMISSIONS[val]?.name || val}`, 'info');
        }
    });

    // Theme toggle (Dark / Light)
    const themeBtn = document.getElementById('theme-toggle');
    themeBtn?.addEventListener('click', () => {
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
            loadResidentPortal(state.currentUser.ma_ho || 6);
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
        case 'tab-proposals':
            loadAdminProposals();
            break;
        case 'tab-users':
            loadUsers();
            break;
        case 'tab-system':
            break;
    }
}

// ====================================================================
// XỬ LÝ ĐĂNG NHẬP, ĐĂNG KÝ VÀ PHIÊN LÀM VIỆC (AUTH CONTROLLER)
// ====================================================================

function openAuthModal(tab = 'login') {
    openModal('modal-auth');
    switchAuthTab(tab);
    loadApartmentsForRegister();
}

function switchAuthTab(tab) {
    const btnLogin = document.getElementById('btn-tab-login');
    const btnReg = document.getElementById('btn-tab-register');
    const contentLogin = document.getElementById('auth-content-login');
    const contentReg = document.getElementById('auth-content-register');

    if (tab === 'login') {
        btnLogin?.classList.add('active');
        btnReg?.classList.remove('active');
        contentLogin?.classList.add('active');
        contentReg?.classList.remove('active');
    } else {
        btnReg?.classList.add('active');
        btnLogin?.classList.remove('active');
        contentReg?.classList.add('active');
        contentLogin?.classList.remove('active');
        loadApartmentsForRegister();
    }
}

function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (input) {
        input.type = input.type === 'password' ? 'text' : 'password';
    }
}

/**
 * Xử lý đăng nhập bằng tài khoản & mật khẩu
 */
async function handleLoginSubmit() {
    const username = document.getElementById('login-username')?.value.trim();
    const password = document.getElementById('login-password')?.value.trim();

    if (!username || !password) {
        showToast('Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!', 'error');
        return;
    }

    try {
        const res = await API.auth.login(username, password);
        if (res.success) {
            state.currentUser = syncUserProperties(res.user);
            localStorage.setItem('bmfm_user', JSON.stringify(res.user));
            closeModal('modal-auth');
            applyRolePermissions(res.user.vai_tro || res.user.role);
            showToast(`Đăng nhập thành công! Chào mừng ${res.user.ho_ten}`, 'success');
        } else {
            showToast(res.message || 'Đăng nhập thất bại!', 'error');
        }
    } catch (err) {
        showToast(err.message || 'Lỗi kết nối máy chủ!', 'error');
    }
}

/**
 * Đăng nhập nhanh 1-Click phục vụ kiểm thử
 */
async function quickLogin(username, password) {
    const uInput = document.getElementById('login-username');
    const pInput = document.getElementById('login-password');
    if (uInput) uInput.value = username;
    if (pInput) pInput.value = password;
    await handleLoginSubmit();
}

/**
 * Xử lý đăng ký tài khoản cư dân mới
 */
async function handleRegisterSubmit() {
    const username = document.getElementById('reg-username')?.value.trim();
    const fullname = document.getElementById('reg-fullname')?.value.trim();
    const password = document.getElementById('reg-password')?.value.trim();
    const confirmPassword = document.getElementById('reg-password-confirm')?.value.trim();
    const soCanHo = document.getElementById('reg-apartment')?.value;
    const phone = document.getElementById('reg-phone')?.value.trim();
    const cccd = document.getElementById('reg-cccd')?.value.trim();

    if (!username || !fullname || !password || !soCanHo || !phone) {
        showToast('Vui lòng điền đầy đủ các thông tin bắt buộc (*)!', 'error');
        return;
    }

    if (password.length < 6) {
        showToast('Mật khẩu bảo mật phải có ít nhất 6 ký tự!', 'error');
        return;
    }

    if (password !== confirmPassword) {
        showToast('Mật khẩu nhập lại không trùng khớp!', 'error');
        return;
    }

    try {
        const res = await API.auth.register({
            username,
            password,
            fullname,
            phone,
            so_can_ho: soCanHo,
            so_cccd: cccd,
            role: 'CU_DAN'
        });

        if (res.success) {
            state.currentUser = syncUserProperties(res.user);
            localStorage.setItem('bmfm_user', JSON.stringify(res.user));
            closeModal('modal-auth');
            applyRolePermissions('CU_DAN');
            showToast(`Đăng ký thành công! Chào mừng Cư dân ${fullname} (Căn ${soCanHo})`, 'success');
        } else {
            showToast(res.message || 'Đăng ký không thành công!', 'error');
        }
    } catch (err) {
        showToast(err.message || 'Lỗi kết nối khi đăng ký!', 'error');
    }
}

/**
 * Đăng xuất tài khoản
 */
function handleLogout() {
    localStorage.removeItem('bmfm_user');
    showToast('Đã đăng xuất khỏi hệ thống.', 'info');
    openAuthModal('login');
}

/**
 * Tải danh sách căn hộ vào dropdown đăng ký
 */
async function loadApartmentsForRegister() {
    const select = document.getElementById('reg-apartment');
    if (!select) return;
    try {
        const res = await API.apartments.getAll();
        if (res.success && res.data) {
            select.innerHTML = '<option value="">-- Vui lòng chọn căn hộ cư trú --</option>' +
                res.data.map(a => `<option value="${a.so_can_ho}">Căn ${a.so_can_ho} (Tầng ${a.so_tang} • ${a.dien_tich} m² • ${a.trang_thai === 'DANG_O' ? 'Đang ở' : 'Trống/Thuê'})</option>`).join('');
        }
    } catch (e) {
        console.error("Lỗi nạp căn hộ cho đăng ký:", e);
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

        const actionBtn = (state.currentUser.role === 'KE_TOAN') 
            ? `<span class="badge badge-neutral" title="Thu ngân chỉ xem dữ liệu do Ban Quản Trị quản lý">👁️ Chỉ xem</span>`
            : `<button class="btn btn-sm btn-danger" onclick="deleteApartment(${apt.ma_ho}, '${apt.so_can_ho}')">Xóa</button>`;

        tr.innerHTML = `
            <td><strong>${apt.so_can_ho}</strong></td>
            <td>${apt.dien_tich} m²</td>
            <td>Tầng ${apt.so_tang}</td>
            <td>${apt.ten_chu_ho || '<span style="color:var(--text-muted)">Chưa gán</span>'}</td>
            <td><span class="badge badge-primary">${apt.so_nhan_khau} người</span></td>
            <td>🛵 ${apt.so_xe_may} xe máy | 🚗 ${apt.so_o_to} ô tô</td>
            <td>${apt.ngay_chuyen_den || '2026-01-01'}</td>
            <td><span class="badge ${badgeClass}">${statusText}</span></td>
            <td>${actionBtn}</td>
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

            const actionBtn = (state.currentUser.role === 'KE_TOAN') 
                ? `<span class="badge badge-neutral" title="Thu ngân chỉ xem dữ liệu do Ban Quản Trị quản lý">👁️ Chỉ xem</span>`
                : `<button class="btn btn-sm btn-danger" onclick="deleteVehicle(${v.ma_pt}, '${v.bien_so}')">Hủy gửi xe</button>`;

            tr.innerHTML = `
                <td><code><strong>${v.bien_so}</strong></code></td>
                <td>${typeText}</td>
                <td>${v.ten_xe || '---'}</td>
                <td><span class="badge badge-primary">Căn ${v.so_can_ho}</span></td>
                <td>${v.ten_chu_ho || '---'}</td>
                <td><strong style="color:var(--primary);">${price}</strong></td>
                <td>${actionBtn}</td>
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
                    ? `<button class="btn btn-sm btn-info" onclick="exportOnlineInvoiceFromBill(${JSON.stringify(b).replace(/"/g, '&quot;')})">🧾 Hóa đơn điện tử</button>`
                    : `<button class="btn btn-sm btn-success" onclick="openOnlinePayment(${b.ma_ct}, '${b.ten_khoan_thu}', ${b.con_no}, '${apt.so_can_ho}')">
                         📲 Nộp tiền Online
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

        // Bảng lịch sử phiếu thu & Hóa đơn điện tử online
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
                        <div style="display:flex; gap:6px;">
                            <button class="btn btn-sm btn-primary" onclick="previewReceipt(${JSON.stringify(r).replace(/"/g, '&quot;')})">
                                📄 Biên lai
                            </button>
                            <button class="btn btn-sm btn-info" onclick="previewInvoice(${JSON.stringify(r).replace(/"/g, '&quot;')})">
                                🧾 Hóa Đơn Online
                            </button>
                        </div>
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

        // Bảng kiến nghị & đề xuất của căn hộ gửi tới Ban Quản Trị
        const tbodyProposals = document.getElementById('res-proposals-tbody');
        if (tbodyProposals) {
            tbodyProposals.innerHTML = '';
            const proposals = data.proposals || [];
            if (proposals.length === 0) {
                tbodyProposals.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:16px;">Căn hộ chưa gửi đề xuất, kiến nghị nào tới Ban Quản Trị.</td></tr>`;
            } else {
                proposals.forEach(p => {
                    const tr = document.createElement('tr');
                    let badgeClass = 'badge-pending';
                    let statusText = 'Chờ BQT duyệt';
                    if (p.trang_thai === 'DA_DUYET') { badgeClass = 'badge-approved'; statusText = 'Đã duyệt'; }
                    else if (p.trang_thai === 'DANG_XU_LY') { badgeClass = 'badge-processing'; statusText = 'Đang xử lý'; }
                    else if (p.trang_thai === 'HOAN_THANH') { badgeClass = 'badge-completed'; statusText = 'Đã hoàn thành'; }
                    else if (p.trang_thai === 'TU_CHOI') { badgeClass = 'badge-rejected'; statusText = 'Từ chối'; }

                    tr.innerHTML = `
                        <td><code>KN-${p.ma_kn}</code></td>
                        <td><strong>${p.tieu_de}</strong></td>
                        <td><span class="badge badge-neutral">${p.loai_yeu_cau}</span></td>
                        <td><span class="badge ${badgeClass}">${statusText}</span></td>
                        <td>${p.ngay_gui}</td>
                        <td>
                            <div style="font-size:12.5px;">${p.phan_hoi_bqt || '<span style="color:var(--text-muted)">BQT chưa phản hồi</span>'}</div>
                            ${p.nguoi_duyet ? `<div style="font-size:11px; color:var(--primary); margin-top:2px;">Duyệt bởi: <strong>${p.nguoi_duyet}</strong> (${p.ngay_duyet || ''})</div>` : ''}
                        </td>
                    `;
                    tbodyProposals.appendChild(tr);
                });
            }
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
// CHỨC NĂNG CƯ DÂN: CẬP NHẬT CĂN HỘ, THÀNH VIÊN, XE, ĐỀ XUẤT
// ====================================================================

function openResidentApartmentModal() {
    if (!currentResidentPortalData || !currentResidentPortalData.apartment) return;
    const apt = currentResidentPortalData.apartment;
    const codeEl = document.getElementById('res-apt-code');
    const areaEl = document.getElementById('res-apt-area');
    const ownerEl = document.getElementById('res-apt-owner');
    const phoneEl = document.getElementById('res-apt-phone');

    if (codeEl) codeEl.value = apt.so_can_ho || '';
    if (areaEl) areaEl.value = apt.dien_tich || '';
    if (ownerEl) ownerEl.value = apt.ten_chu_ho || '';
    if (phoneEl) phoneEl.value = apt.sdt_chu_ho || '';
    openModal('modal-resident-apartment');
}

async function handleUpdateResidentApartment() {
    const phone = document.getElementById('res-apt-phone')?.value.trim();
    const owner = document.getElementById('res-apt-owner')?.value.trim();

    try {
        const res = await API.resident.updateApartment({
            so_dien_thoai: phone,
            ten_chu_ho: owner
        });
        showToast(res.message, 'success');
        closeModal('modal-resident-apartment');
        loadResidentPortal(state.currentUser.ma_ho || 6);
        loadApartments();
    } catch (e) {
        showToast(`Lỗi cập nhật căn hộ: ${e.message}`, 'error');
    }
}

function openResidentMemberModal() {
    document.getElementById('form-resident-member')?.reset();
    openModal('modal-resident-member');
}

async function handleAddResidentMember() {
    const hoTen = document.getElementById('res-mem-name')?.value.trim();
    const quanHe = document.getElementById('res-mem-relation')?.value;
    const gioiTinh = document.getElementById('res-mem-gender')?.value;
    const ngaySinh = document.getElementById('res-mem-dob')?.value;
    const soCccd = document.getElementById('res-mem-cccd')?.value.trim();
    const sdt = document.getElementById('res-mem-phone')?.value.trim();

    if (!hoTen || !quanHe || !ngaySinh) {
        showToast('Vui lòng nhập họ tên, quan hệ và ngày sinh!', 'error');
        return;
    }

    try {
        const res = await API.resident.addMember({
            ho_ten: hoTen,
            quan_he_chu_ho: quanHe,
            gioi_tinh: gioiTinh,
            ngay_sinh: ngaySinh,
            so_cccd: soCccd,
            so_dien_thoai: sdt
        });
        showToast(res.message, 'success');
        closeModal('modal-resident-member');
        document.getElementById('form-resident-member')?.reset();
        loadResidentPortal(state.currentUser.ma_ho || 6);
        loadApartments();
        loadResidents();
    } catch (e) {
        showToast(`Lỗi thêm thành viên: ${e.message}`, 'error');
    }
}

function openResidentVehicleModal() {
    document.getElementById('form-resident-vehicle')?.reset();
    openModal('modal-resident-vehicle');
}

async function handleAddResidentVehicle() {
    const loaiXe = document.getElementById('res-veh-type')?.value;
    const bienSo = document.getElementById('res-veh-plate')?.value.trim().toUpperCase();
    const tenXe = document.getElementById('res-veh-model')?.value.trim();

    if (!bienSo || !loaiXe) {
        showToast('Vui lòng nhập biển số và chọn loại phương tiện!', 'error');
        return;
    }

    try {
        const res = await API.resident.addVehicle({
            loai_xe: loaiXe,
            bien_so: bienSo,
            ten_xe: tenXe
        });
        showToast(res.message, 'success');
        closeModal('modal-resident-vehicle');
        document.getElementById('form-resident-vehicle')?.reset();
        loadResidentPortal(state.currentUser.ma_ho || 6);
        loadVehicles();
        loadApartments();
    } catch (e) {
        showToast(`Lỗi đăng ký xe: ${e.message}`, 'error');
    }
}

function openResidentProposalModal() {
    document.getElementById('form-resident-proposal')?.reset();
    const senderEl = document.getElementById('res-prop-sender');
    if (senderEl) {
        senderEl.value = (currentResidentPortalData?.apartment?.ten_chu_ho || state.currentUser.fullname || '') + 
                         ` (Căn ${currentResidentPortalData?.apartment?.so_can_ho || ''})`;
    }
    openModal('modal-resident-proposal');
}

async function handleAddResidentProposal() {
    const tieuDe = document.getElementById('res-prop-title')?.value.trim();
    const loaiYeuCau = document.getElementById('res-prop-type')?.value;
    const noiDung = document.getElementById('res-prop-content')?.value.trim();

    if (!tieuDe || !noiDung) {
        showToast('Vui lòng nhập tiêu đề và nội dung kiến nghị/đề xuất!', 'error');
        return;
    }

    try {
        const res = await API.proposals.create({
            tieu_de: tieuDe,
            loai_yeu_cau: loaiYeuCau,
            noi_dung: noiDung,
            nguoi_gui: currentResidentPortalData?.apartment?.ten_chu_ho || state.currentUser.fullname,
            sdt_nguoi_gui: currentResidentPortalData?.apartment?.sdt_chu_ho || state.currentUser.so_dien_thoai
        });
        showToast(res.message, 'success');
        closeModal('modal-resident-proposal');
        document.getElementById('form-resident-proposal')?.reset();
        loadResidentPortal(state.currentUser.ma_ho || 6);
    } catch (e) {
        showToast(`Lỗi gửi đề xuất: ${e.message}`, 'error');
    }
}

// ====================================================================
// QUẢN LÝ DUYỆT ĐỀ XUẤT & KIẾN NGHỊ DÀNH CHO ADMIN & BAN QUẢN TRỊ
// ====================================================================
let adminProposalsList = [];
let currentFilterProposalStatus = 'ALL';

async function loadAdminProposals() {
    try {
        const res = await API.proposals.getAll();
        adminProposalsList = res.data || [];
        filterAdminProposals(currentFilterProposalStatus);
    } catch (e) {
        showToast(`Lỗi nạp danh sách đề xuất: ${e.message}`, 'error');
    }
}

function filterAdminProposals(status) {
    currentFilterProposalStatus = status;
    document.querySelectorAll('.filter-group .btn').forEach(b => b.classList.remove('active'));
    if (status === 'ALL') document.getElementById('filter-proposals-all')?.classList.add('active');
    else if (status === 'CHO_DUYET') document.getElementById('filter-proposals-pending')?.classList.add('active');
    else if (status === 'DA_DUYET') document.getElementById('filter-proposals-approved')?.classList.add('active');
    else if (status === 'TU_CHOI') document.getElementById('filter-proposals-rejected')?.classList.add('active');

    let filtered = adminProposalsList;
    if (status !== 'ALL') {
        filtered = adminProposalsList.filter(p => p.trang_thai === status);
    }
    renderAdminProposals(filtered);
}

function renderAdminProposals(list) {
    const tbody = document.getElementById('admin-proposals-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:24px;">Không có đề xuất hoặc kiến nghị nào phù hợp với bộ lọc.</td></tr>`;
        return;
    }

    list.forEach(p => {
        const tr = document.createElement('tr');
        let badgeClass = 'badge-pending';
        let statusText = 'Chờ BQT duyệt';
        if (p.trang_thai === 'DA_DUYET') { badgeClass = 'badge-approved'; statusText = 'Đã duyệt'; }
        else if (p.trang_thai === 'DANG_XU_LY') { badgeClass = 'badge-processing'; statusText = 'Đang xử lý'; }
        else if (p.trang_thai === 'DA_XU_LY' || p.trang_thai === 'HOAN_THANH') { badgeClass = 'badge-completed'; statusText = 'Đã xử lý'; }
        else if (p.trang_thai === 'TU_CHOI') { badgeClass = 'badge-rejected'; statusText = 'Từ chối'; }

        const idVal = p.ma_yc || p.ma_kn;
        const replyVal = p.phan_hoi || p.phan_hoi_bqt;

        tr.innerHTML = `
            <td><code>KN-${idVal}</code></td>
            <td>
                <strong>Căn ${p.so_can_ho}</strong>
                <div style="font-size:12px; color:var(--text-muted);">${p.nguoi_gui || ''} ${p.sdt_nguoi_gui ? `(${p.sdt_nguoi_gui})` : ''}</div>
            </td>
            <td>
                <strong>${p.tieu_de}</strong>
                <div style="font-size:12.5px; color:var(--text-secondary); margin-top:3px; max-width:320px; white-space:normal; line-height:1.4;">${p.noi_dung}</div>
            </td>
            <td><span class="badge badge-neutral">${p.loai_yeu_cau}</span></td>
            <td>${p.ngay_gui}</td>
            <td><span class="badge ${badgeClass}">${statusText}</span></td>
            <td>
                <div style="font-size:12.5px;">${replyVal || '<span style="color:var(--text-muted)">Chưa có phản hồi</span>'}</div>
                ${p.nguoi_duyet ? `<div style="font-size:11px; color:var(--primary); margin-top:2px;">Duyệt: <strong>${p.nguoi_duyet}</strong></div>` : ''}
            </td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="openReviewProposalModal(${JSON.stringify(p).replace(/"/g, '&quot;')})">
                    ✍️ Duyệt & Trả lời
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function openReviewProposalModal(proposal) {
    const idEl = document.getElementById('rev-prop-id');
    const aptEl = document.getElementById('rev-prop-apt');
    const senderEl = document.getElementById('rev-prop-sender');
    const dateEl = document.getElementById('rev-prop-date');
    const titleEl = document.getElementById('rev-prop-title');
    const contentEl = document.getElementById('rev-prop-content');
    const statusEl = document.getElementById('rev-prop-status');
    const replyEl = document.getElementById('rev-prop-reply');

    if (idEl) idEl.value = proposal.ma_yc || proposal.ma_kn;
    if (aptEl) aptEl.textContent = proposal.so_can_ho || 'A1205';
    if (senderEl) senderEl.textContent = `${proposal.nguoi_gui || ''} ${proposal.sdt_nguoi_gui ? `(${proposal.sdt_nguoi_gui})` : ''}`;
    if (dateEl) dateEl.textContent = proposal.ngay_gui || '';
    if (titleEl) titleEl.textContent = proposal.tieu_de || '';
    if (contentEl) contentEl.textContent = proposal.noi_dung || '';
    if (statusEl) statusEl.value = proposal.trang_thai;
    if (replyEl) replyEl.value = proposal.phan_hoi || proposal.phan_hoi_bqt || '';

    openModal('modal-review-proposal');
}

async function handleSaveProposalReview() {
    const maKn = document.getElementById('rev-prop-id')?.value;
    const status = document.getElementById('rev-prop-status')?.value;
    const reply = document.getElementById('rev-prop-reply')?.value.trim();

    if (!reply) {
        showToast('Vui lòng nhập nội dung ý kiến hoặc giải pháp phản hồi cho cư dân!', 'error');
        return;
    }

    try {
        const res = await API.proposals.review({
            ma_yc: maKn,
            ma_kn: maKn,
            trang_thai: status,
            phan_hoi: reply,
            phan_hoi_bqt: reply,
            nguoi_duyet: state.currentUser.fullname || 'Admin Quản Trị'
        });
        showToast(res.message, 'success');
        closeModal('modal-review-proposal');
        loadAdminProposals();
    } catch (e) {
        showToast(`Lỗi duyệt đề xuất: ${e.message}`, 'error');
    }
}

// ====================================================================
// HÓA ĐƠN ĐIỆN TỬ ONLINE CHUẨN VAT (E-INVOICE VIEWER & PRINT)
// ====================================================================
function previewInvoice(data) {
    const invCode = data.ma_phieu ? `INV-2026-${String(data.ma_phieu).padStart(6, '0')}` : `INV-2026-${Math.floor(100000 + Math.random() * 900000)}`;
    const lookupCode = (data.ma_phieu ? `BM${data.ma_phieu}` : `BM${Date.now()}`).toUpperCase().slice(0, 10);
    const amount = Number(data.so_tien || data.so_tien_phai_nop || data.so_tien_da_nop || 0);
    const aptNumber = data.so_can_ho || (currentResidentPortalData?.apartment?.so_can_ho) || 'A1205';
    const customerName = data.nguoi_nop || (currentResidentPortalData?.apartment?.ten_chu_ho) || state.currentUser.fullname || 'Cư dân Blue Moon';
    const feeName = data.ten_khoan_thu || 'Phí quản lý & dịch vụ vận hành chung cư';
    const paymentMethod = data.phuong_thuc === 'CHUYEN_KHOAN' ? 'Chuyển khoản (VietQR Napas 24/7)' : 'Tiền mặt';
    const dateStr = data.ngay_nop || new Date().toISOString().slice(0, 10);

    // Điền dữ liệu vào Hóa Đơn Điện Tử
    document.getElementById('inv-code').textContent = invCode;
    document.getElementById('inv-lookup-code').textContent = lookupCode;
    document.getElementById('inv-date').textContent = dateStr;
    document.getElementById('inv-customer-name').textContent = customerName;
    document.getElementById('inv-customer-apt').textContent = `Căn hộ ${aptNumber} - Chung cư cao cấp Blue Moon`;
    document.getElementById('inv-payment-method').textContent = paymentMethod;

    document.getElementById('inv-item-name').textContent = feeName;
    document.getElementById('inv-item-unit').textContent = 'Tháng / Gói';
    document.getElementById('inv-item-qty').textContent = '1';
    document.getElementById('inv-item-price').textContent = formatVND(amount);
    document.getElementById('inv-item-amount').textContent = formatVND(amount);

    document.getElementById('inv-subtotal').textContent = formatVND(amount);
    document.getElementById('inv-tax-amount').textContent = '0 đ (KCT - Không chịu thuế GTGT)';
    document.getElementById('inv-total').textContent = formatVND(amount);
    document.getElementById('inv-words').textContent = numberToVietnameseWords(amount);

    document.getElementById('inv-signer-name').textContent = 'BAN QUẢN TRỊ CHUNG CƯ BLUE MOON';
    document.getElementById('inv-sign-date').textContent = dateStr;

    openModal('modal-invoice-preview');
}

function exportOnlineInvoiceFromBill(bill) {
    previewInvoice({
        ma_phieu: bill.ma_ct,
        ten_khoan_thu: bill.ten_khoan_thu,
        so_tien: bill.so_tien_da_nop > 0 ? bill.so_tien_da_nop : bill.so_tien_phai_nop,
        nguoi_nop: currentResidentPortalData?.apartment?.ten_chu_ho || state.currentUser.fullname,
        so_can_ho: currentResidentPortalData?.apartment?.so_can_ho,
        phuong_thuc: 'CHUYEN_KHOAN',
        ngay_nop: new Date().toISOString().slice(0, 10)
    });
}

function printInvoice() {
    window.print();
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

    // 12. Nghiệp vụ Cổng Cư Dân: Cập nhật căn hộ, Thêm thành viên, Xe & Kiến nghị
    document.getElementById('btn-res-edit-apartment')?.addEventListener('click', openResidentApartmentModal);
    document.getElementById('btn-save-res-apartment')?.addEventListener('click', handleUpdateResidentApartment);

    document.getElementById('btn-res-add-member')?.addEventListener('click', openResidentMemberModal);
    document.getElementById('btn-save-res-member')?.addEventListener('click', handleAddResidentMember);

    document.getElementById('btn-res-add-vehicle')?.addEventListener('click', openResidentVehicleModal);
    document.getElementById('btn-save-res-vehicle')?.addEventListener('click', handleAddResidentVehicle);

    document.getElementById('btn-res-add-proposal')?.addEventListener('click', openResidentProposalModal);
    document.getElementById('btn-save-res-proposal')?.addEventListener('click', handleAddResidentProposal);

    // 13. Nghiệp vụ Duyệt Đề Xuất & Kiến Nghị (Admin & BQT)
    document.getElementById('filter-proposals-all')?.addEventListener('click', () => filterAdminProposals('ALL'));
    document.getElementById('filter-proposals-pending')?.addEventListener('click', () => filterAdminProposals('CHO_DUYET'));
    document.getElementById('filter-proposals-approved')?.addEventListener('click', () => filterAdminProposals('DA_DUYET'));
    document.getElementById('filter-proposals-rejected')?.addEventListener('click', () => filterAdminProposals('TU_CHOI'));
    document.getElementById('btn-save-review-proposal')?.addEventListener('click', handleSaveProposalReview);

    // 14. In hóa đơn điện tử online
    document.getElementById('btn-print-invoice')?.addEventListener('click', printInvoice);
}

// ====================================================================
// ĐIỂM KHỞI ĐỘNG ỨNG DỤNG (INITIALIZATION)
// ====================================================================
document.addEventListener('DOMContentLoaded', () => {
    console.log(">>> Khởi tạo ứng dụng Web Quản lý thu phí chung cư Blue Moon...");
    initNavigation();
    initFormListeners();

    // 1. Đồng bộ và áp dụng ma trận phân quyền RBAC
    applyRolePermissions(state.currentUser.role);

    // 2. Tải dữ liệu ban đầu phù hợp với quyền hạn của vai trò
    if (state.currentUser.role === 'CU_DAN') {
        loadResidentPortal(state.currentUser.ma_ho || 6);
        loadFees();
    } else {
        loadDashboard();
        loadApartments();
        loadResidents();
        loadFees();
        loadPeriods();
    }
});
