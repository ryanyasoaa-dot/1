/**
 * api.js — Centralized REST API layer
 * All fetch calls go through here.
 * Flutter: replace fetch() calls with Dart http/dio using same endpoints.
 *
 * Base URL for Flutter: const BASE = 'https://yourdomain.com';
 */

const API = {

    // ── Admin: Applications ───────────────────────────────────
    applications: {
        getAll: () =>
            fetch('/admin/api/applications').then(r => r.json()),

        getOne: (id) =>
            fetch(`/admin/api/applications/${id}`).then(r => r.json()),

        updateStatus: (id, status, notes = '') =>
            fetch(`/admin/api/applications/${id}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status, notes }),
            }).then(r => r.json()),
    },

    // ── Auth ──────────────────────────────────────────────────
    auth: {
        login: (email, password) =>
            fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            }).then(async r => ({ ok: r.ok, data: await r.json() })),

        register: (formData) =>
            fetch('/api/register', {
                method: 'POST',
                body: formData,
            }).then(async r => ({ ok: r.ok, data: await r.json() })),
    },

    // ── Seller ────────────────────────────────────────────────
    seller: {
        getProducts:  () => fetch('/seller/api/products').then(r => r.json()),
        getOrders:    () => fetch('/seller/api/orders').then(r => r.json()),
        updateOrderStatus: (id, status) => fetch(`/seller/api/orders/${id}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status }),
        }).then(r => r.json()),
        getEarnings:  () => fetch('/seller/api/earnings').then(r => r.json()),
        getShipping:  () => fetch('/seller/api/shipping').then(r => r.json()),
        getReviews:   () => fetch('/seller/api/reviews').then(r => r.json()),
        getStore:     () => fetch('/seller/api/store').then(r => r.json()),
        updateStore:  (data) => fetch('/seller/api/store', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        }).then(r => r.json()),
    },

    // ── Buyer ─────────────────────────────────────────────────
    buyer: {
        getCart:       () => fetch('/buyer/api/cart').then(r => r.json()),
        addToCart:     (payload) => fetch('/buyer/api/cart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }).then(r => r.json()),
        updateCartItem: (id, quantity) => fetch(`/buyer/api/cart/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quantity }),
        }).then(r => r.json()),
        removeCartItem: (id) => fetch(`/buyer/api/cart/${id}`, { method: 'DELETE' }).then(r => r.json()),
        checkout:      (payload) => fetch('/buyer/api/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }).then(r => r.json()),
        getOrders:     () => fetch('/buyer/api/orders').then(r => r.json()),
        getProfile:    () => fetch('/buyer/api/profile').then(r => r.json()),
        getWishlist:   () => fetch('/buyer/api/wishlist').then(r => r.json()),
        getAddresses:  () => fetch('/buyer/api/addresses').then(r => r.json()),
    },

    // ── Rider ─────────────────────────────────────────────────
    rider: {
        getDeliveries: () => fetch('/rider/api/deliveries').then(r => r.json()),
        acceptDelivery: (id) => fetch(`/rider/api/deliveries/${id}/accept`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        }).then(r => r.json()),
        getEarnings:   () => fetch('/rider/api/earnings').then(r => r.json()),
        updateStatus:  (id, status) => fetch(`/rider/api/deliveries/${id}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status }),
        }).then(r => r.json()),
    },

    // ── Public (shop) ─────────────────────────────────────────
    shop: {
        getProducts:   (params = '') => fetch(`/buyer/api/products?${params}`).then(r => r.json()),
        getCategories: () => fetch('/api/categories').then(r => r.json()),
        getProduct:    (id) => fetch(`/buyer/api/products/${id}`).then(r => r.json()),
    },

    // ── Admin: Product moderation ─────────────────────────────
    adminProducts: {
        getAll: (status = '') =>
            fetch(`/admin/api/products${status ? `?status=${encodeURIComponent(status)}` : ''}`).then(r => r.json()),
        getOne: (id) =>
            fetch(`/admin/api/products/${id}`).then(r => r.json()),
        updateStatus: (id, status, reason = '') =>
            fetch(`/admin/api/products/${id}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status, reason }),
            }).then(r => r.json()),
    },
};
