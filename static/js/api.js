/**
 * api.js — Centralized REST API layer
 * All state-changing requests include X-CSRF-Token automatically.
 */

// ── CSRF helpers ──────────────────────────────────────────────
function _csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

function _post(url, body) {
    const token = _csrfToken();
    console.log('POST', url, 'CSRF token:', token ? 'present (' + token.length + ' chars)' : 'MISSING');
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
        body: JSON.stringify(body),
    }).then(r => r.json());
}

function _put(url, body) {
    return fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': _csrfToken() },
        body: JSON.stringify(body),
    }).then(r => r.json());
}

function _delete(url) {
    return fetch(url, {
        method: 'DELETE',
        headers: { 'X-CSRF-Token': _csrfToken() },
    }).then(r => r.json());
}

function _get(url) {
    return fetch(url).then(r => r.json());
}

const API = {

    // ── Admin: Applications ───────────────────────────────────
    applications: {
        getAll:       ()                       => _get('/admin/api/applications'),
        getOne:       (id)                     => _get(`/admin/api/applications/${encodeURIComponent(id)}`),
        updateStatus: (id, status, notes = '') => _post(`/admin/api/applications/${encodeURIComponent(id)}/status`, { status, notes }),
    },

    // ── Auth ──────────────────────────────────────────────────
    auth: {
        login: (email, password) =>
            fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': _csrfToken() },
                body: JSON.stringify({ email, password }),
            }).then(async r => ({ ok: r.ok, data: await r.json() })),

        register: (formData) => {
            formData.append('csrf_token', _csrfToken());
            return fetch('/register', {
                method: 'POST',
                headers: { 'X-CSRF-Token': _csrfToken() },
                body: formData,
            }).then(async r => ({ ok: r.ok, data: await r.json() }));
        },
    },

    // ── Seller ────────────────────────────────────────────────
    seller: {
        getProducts:       ()             => _get('/seller/api/products'),
        getOrders:         ()             => _get('/seller/api/orders'),
        updateOrderStatus: (id, status)   => _post(`/seller/api/orders/${encodeURIComponent(id)}/status`, { status }),
        getEarnings:       ()             => _get('/seller/api/earnings'),
        getShipping:       ()             => _get('/seller/api/shipping'),
        getReviews:        ()             => _get('/seller/api/reviews'),
        getStore:          ()             => _get('/seller/api/store'),
        updateStore:       (data)         => _post('/seller/api/store', data),
        // Enhanced Analytics Endpoints
        getDashboardSummary: ()           => _get('/seller/api/dashboard-summary'),
        getSalesAnalytics: (period)      => _get(`/seller/api/sales-analytics?period=${encodeURIComponent(period || 'daily')}`),
        getRecentOrders:   (limit)       => _get(`/seller/api/recent-orders?limit=${encodeURIComponent(limit || 10)}`),
        getTopProducts:    (limit)       => _get(`/seller/api/top-products?limit=${encodeURIComponent(limit || 5)}`),
        getLowStock:       (threshold)   => _get(`/seller/api/low-stock?threshold=${encodeURIComponent(threshold || 10)}`),
    },

    // ── Buyer ─────────────────────────────────────────────────
    buyer: {
        getCart:        ()              => _get('/buyer/api/cart'),
        addToCart:      (payload)       => _post('/buyer/api/cart', payload),
        updateCartItem: (id, quantity)  => _put(`/buyer/api/cart/${encodeURIComponent(id)}`, { quantity }),
        removeCartItem: (id)            => _delete(`/buyer/api/cart/${encodeURIComponent(id)}`),
        checkout:       (payload)       => _post('/buyer/api/checkout', payload),
        getOrders:      ()              => _get('/buyer/api/orders'),
        getProfile:     ()              => _get('/buyer/api/profile'),
        getAddresses:   ()              => _get('/buyer/api/addresses'),
        createAddress:  (payload)       => _post('/buyer/api/addresses', payload),
        setDefault:     (id)            => _post(`/buyer/api/addresses/${encodeURIComponent(id)}/default`, {}),
        deleteAddress:  (id)            => _delete(`/buyer/api/addresses/${encodeURIComponent(id)}`),
        updateProfile:  (payload)       => _put('/buyer/api/profile', payload),
        changePassword: (payload)       => _put('/buyer/api/password', payload),
    },

    // ── Rider ─────────────────────────────────────────────────
    rider: {
        getDeliveries:  ()              => _get('/rider/api/deliveries'),
        acceptDelivery: (id)            => _post(`/rider/api/deliveries/${encodeURIComponent(id)}/accept`, {}),
        updateStatus:   (id, status)    => _post(`/rider/api/deliveries/${encodeURIComponent(id)}/status`, { status }),
        getLocations:   (id)            => _get(`/rider/api/deliveries/${encodeURIComponent(id)}/locations`),
        getDashboard:   ()              => _get('/rider/api/dashboard'),
        getEarnings:    ()              => _get('/rider/api/earnings'),
    },

    // ── Public (shop) ─────────────────────────────────────────
    shop: {
        getProducts: (params = '') => _get(`/buyer/api/products${params ? '?' + params : ''}`),
        getProduct:  (id)          => _get(`/buyer/api/products/${encodeURIComponent(id)}`),
    },

    // ── Admin: Orders ─────────────────────────────────────────
    admin: {
        getOrders:         (status = '') => _get(`/admin/api/orders${status ? '?status=' + encodeURIComponent(status) : ''}`),
        updateOrderStatus: (id, status, rider_id = '') => _post(`/admin/api/orders/${encodeURIComponent(id)}/status`, { status, rider_id }),
        getDashboard:      ()            => _get('/admin/api/dashboard'),
        getEarnings:       ()            => _get('/admin/api/earnings'),
        getCommission:     ()            => _get('/admin/api/commission'),
        setCommission:     (data)        => _post('/admin/api/commission', data),
        getSalesAnalytics: (period)      => _get(`/admin/api/sales-analytics?period=${encodeURIComponent(period || 'daily')}`),
        getRecentOrders:   (limit)       => _get(`/admin/api/recent-orders?limit=${encodeURIComponent(limit || 10)}`),
        getEarningsDetail: (params = {}) => {
            const qs = new URLSearchParams(params).toString();
            return _get(`/admin/api/earnings-detail${qs ? '?' + qs : ''}`);
        },
        exportEarnings:    (format, params = {}) => {
            params.format = format;
            const qs = new URLSearchParams(params).toString();
            return `/admin/api/earnings-export?${qs}`;
        },
    },

    // ── Admin: Products ───────────────────────────────────────
    adminProducts: {
        getAll:       (status = '')              => _get(`/admin/api/products${status ? '?status=' + encodeURIComponent(status) : ''}`),
        getOne:       (id)                       => _get(`/admin/api/products/${encodeURIComponent(id)}`),
        updateStatus: (id, status, reason = '')  => _post(`/admin/api/products/${encodeURIComponent(id)}/status`, { status, reason }),
    },

    // ── Messages ──────────────────────────────────────────────
    messages: {
        getConversations:  ()                       => _get('/messages/api/conversations'),
        startConversation: (userId, orderId = null) => _post('/messages/api/conversations/start', { user_id: userId, order_id: orderId }),
        findConversation:  (otherId, orderId = null) => _get(`/messages/api/conversations/find?user_id=${encodeURIComponent(otherId)}${orderId ? '&order_id=' + encodeURIComponent(orderId) : ''}`),
        getMessages:       (convId, after = null)   => _get(`/messages/api/conversations/${encodeURIComponent(convId)}/messages${after ? '?after=' + encodeURIComponent(after) : ''}`),
        sendMessage:       (convId, content)        => _post(`/messages/api/conversations/${encodeURIComponent(convId)}/messages`, { content }),
        markRead:          (convId)                 => _post(`/messages/api/conversations/${encodeURIComponent(convId)}/read`, {}),
        getUnreadCount:    ()                       => _get('/messages/api/unread-count'),
        quickMessage:      (otherId, orderId, sendAuto) => _post('/messages/api/quick-message', { other_id: otherId, order_id: orderId, send_auto: sendAuto }),
    },
};
