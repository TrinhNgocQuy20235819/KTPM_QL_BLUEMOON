/**
 * ====================================================================
 * DỰ ÁN QUẢN LÝ THU PHÍ CHUNG CƯ BLUE MOON (BMFM)
 * File: api.js
 * Mô tả: Lớp trừu tượng giao tiếp với REST API Backend (server.py)
 *        Sử dụng Fetch API chuẩn với cú pháp Async/Await hiện đại
 * ====================================================================
 */

const API_BASE_URL = window.location.origin;

const API = {
    /**
     * Hàm gọi HTTP chung có xử lý lỗi tự động
     */
    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        let userRole = '';
        try {
            const u = JSON.parse(localStorage.getItem('bmfm_user') || '{}');
            userRole = u.vai_tro || u.role || '';
        } catch(e) {}

        const headers = {
            'Content-Type': 'application/json',
            ...(userRole ? { 'X-User-Role': userRole } : {}),
            ...(options.headers || {})
        };

        try {
            const response = await fetch(url, { ...options, headers });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || `Lỗi máy chủ (${response.status})`);
            }
            return data;
        } catch (error) {
            console.error(`[API Error] ${endpoint}:`, error);
            throw error;
        }
    },

    // ----------------------------------------------------------------
    // 1. XÁC THỰC & ĐĂNG NHẬP (UC01)
    // ----------------------------------------------------------------
    auth: {
        login: (username, password) => 
            API.request('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ username, password })
            }),
        register: (data) =>
            API.request('/api/auth/register', {
                method: 'POST',
                body: JSON.stringify(data)
            })
    },

    // ----------------------------------------------------------------
    // 2. QUẢN LÝ CĂN HỘ / HỘ KHẨU (UC02)
    // ----------------------------------------------------------------
    apartments: {
        getAll: () => API.request('/api/apartments'),
        create: (data) => API.request('/api/apartments', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        delete: (id) => API.request(`/api/apartments/${id}`, {
            method: 'DELETE'
        })
    },

    // ----------------------------------------------------------------
    // 3. QUẢN LÝ NHÂN KHẨU / CƯ DÂN (UC03)
    // ----------------------------------------------------------------
    residents: {
        getAll: (ma_ho = null) => {
            const query = ma_ho ? `?ma_ho=${ma_ho}` : '';
            return API.request(`/api/residents${query}`);
        },
        create: (data) => API.request('/api/residents', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        delete: (id) => API.request(`/api/residents/${id}`, {
            method: 'DELETE'
        })
    },

    // ----------------------------------------------------------------
    // 4. QUẢN LÝ TẠM TRÚ, TẠM VẮNG (UC04)
    // ----------------------------------------------------------------
    temporary: {
        getAll: () => API.request('/api/temporary-residence'),
        create: (data) => API.request('/api/temporary-residence', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        delete: (id) => API.request(`/api/temporary-residence/${id}`, {
            method: 'DELETE'
        })
    },

    // ----------------------------------------------------------------
    // 5. QUẢN LÝ PHƯƠNG TIỆN GỬI XE (UC05)
    // ----------------------------------------------------------------
    vehicles: {
        getAll: () => API.request('/api/vehicles'),
        create: (data) => API.request('/api/vehicles', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        delete: (id) => API.request(`/api/vehicles/${id}`, {
            method: 'DELETE'
        })
    },

    // ----------------------------------------------------------------
    // 6. QUẢN LÝ DANH MỤC KHOẢN THU (UC06)
    // ----------------------------------------------------------------
    fees: {
        getAll: () => API.request('/api/fees'),
        create: (data) => API.request('/api/fees', {
            method: 'POST',
            body: JSON.stringify(data)
        })
    },

    // ----------------------------------------------------------------
    // 7. LẬP ĐỢT THU PHÍ ĐỊNH KỲ (UC07 + CR-003)
    // ----------------------------------------------------------------
    periods: {
        getAll: () => API.request('/api/periods'),
        create: (data) => API.request('/api/periods', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        getDetails: (ma_dot, so_can_ho = '') => {
            const query = so_can_ho ? `?so_can_ho=${encodeURIComponent(so_can_ho)}` : '';
            return API.request(`/api/periods/${ma_dot}/details${query}`);
        }
    },

    // ----------------------------------------------------------------
    // 8. NHẬP TIỀN ĐIỆN NƯỚC THU HỘ (UC08)
    // ----------------------------------------------------------------
    utility: {
        save: (data) => API.request('/api/utility-bills', {
            method: 'POST',
            body: JSON.stringify(data)
        })
    },

    // ----------------------------------------------------------------
    // 9. THU PHÍ & TRA CỨU CÔNG NỢ & XUẤT BIÊN LAI (UC09)
    // ----------------------------------------------------------------
    collection: {
        getDebt: (so_can_ho, ma_dot = '') => {
            const query = `?so_can_ho=${encodeURIComponent(so_can_ho)}${ma_dot ? `&ma_dot=${ma_dot}` : ''}`;
            return API.request(`/api/household-debt${query}`);
        },
        collect: (data) => API.request('/api/collect-fee', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        getReceipts: () => API.request('/api/receipts')
    },

    // ----------------------------------------------------------------
    // 10. THỐNG KÊ & BÁO CÁO (UC10)
    // ----------------------------------------------------------------
    statistics: {
        getOverview: () => API.request('/api/statistics')
    },

    // ----------------------------------------------------------------
    // 11. TÀI KHOẢN & PHÂN QUYỀN (UC11)
    // ----------------------------------------------------------------
    users: {
        getAll: () => API.request('/api/users'),
        create: (data) => API.request('/api/users', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        toggleStatus: (id) => API.request(`/api/users/${id}/toggle`, {
            method: 'PUT'
        })
    },

    // ----------------------------------------------------------------
    // 12. SAO LƯU & PHỤC HỒI CSDL (UC12)
    // ----------------------------------------------------------------
    system: {
        backup: () => API.request('/api/backup'),
        restore: (data) => API.request('/api/restore', {
            method: 'POST',
            body: JSON.stringify(data)
        })
    },

    // ----------------------------------------------------------------
    // 13. CỔNG THÔNG TIN CƯ DÂN & ĐÓNG TIỀN ONLINE (VAI TRÒ KHÁCH/CHỦ HỘ)
    // ----------------------------------------------------------------
    resident: {
        getPortal: (ma_ho = 1) => API.request(`/api/resident/portal?ma_ho=${ma_ho}`),
        payOnline: (data) => API.request('/api/resident/pay-online', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        addMember: (data) => API.request('/api/resident/members', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        addVehicle: (data) => API.request('/api/resident/vehicles', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        updateApartment: (data) => API.request('/api/resident/apartment', {
            method: 'POST',
            body: JSON.stringify(data)
        })
    },

    // ----------------------------------------------------------------
    // 14. ĐỀ XUẤT & KIẾN NGHỊ CƯ DÂN (GỬI & DUYỆT ĐỀ XUẤT)
    // ----------------------------------------------------------------
    proposals: {
        getAll: (ma_ho = '') => {
            const query = ma_ho ? `?ma_ho=${ma_ho}` : '';
            return API.request(`/api/proposals${query}`);
        },
        create: (data) => API.request('/api/proposals', {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        review: (data) => API.request('/api/proposals/review', {
            method: 'POST',
            body: JSON.stringify(data)
        })
    }
};
