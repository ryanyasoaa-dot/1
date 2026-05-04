#!/usr/bin/env python3
"""
E-Commerce System - Flutter Integration Readiness Audit
=======================================================
Checks what's needed for production Flutter app integration.
"""

import os, json, re
os.environ['SUPABASE_URL'] = 'https://opusrotqhtkhmeefvydh.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wdXNyb3RxaHRraG1lZWZ2eWRoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NzU1NTczMywiZXhwIjoyMDkzMTMxNzMzfQ.GYBLr1o5eH5iR0VA52Wab9B8Tysp9393Two7b7LvYdk'
from supabase import create_client
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print('='*60)
print('  E-COMMERCE FLUTTER INTEGRATION - READINESS AUDIT       ')
print('='*60)
print()

# ── 1. DATABASE CHECK ───────────────────────────────────────────────
print('📦 DATABASE TABLES')
print('-'*60)
tables = {
    'users': 'Users (all roles)',
    'products': 'Products',
    'orders': 'Orders',
    'order_items': 'Order Items',
    'cart_items': 'Cart Items',
    'addresses': 'Addresses',
    'conversations': 'Conversations',
    'messages': 'Messages',
    'notifications': 'Notifications',
    'reviews': 'Reviews',
    'applications': 'Seller/Rider Applications',
    'admin_settings': 'Admin Settings',
    'rider_earnings': 'Rider Earnings',
}
for tbl, desc in tables.items():
    try:
        r = sb.table(tbl).select('id').limit(0).execute()
        print(f'   ✓ {tbl:25s} - {desc}')
    except Exception as e:
        print(f'   ✗ {tbl:25s} - MISSING - {desc}')

# ── 2. FLUTTER ENDPOINTS CHECK ─────────────────────────────────────
print()
print('🌐 FLUTTER-READY ENDPOINTS (JSON API)')
print('-'*60)

flutter_endpoints = {
    'Auth & User': [
        ('POST   /api/auth/login', 'Login with email/password'),
        ('POST   /api/auth/register', 'Register new user'),
        ('POST   /api/auth/logout', 'Logout'),
        ('GET    /api/auth/user', 'Get current user profile'),
        ('PUT    /api/auth/user', 'Update user profile'),
        ('POST   /api/auth/password', 'Change password'),
        ('POST   /api/auth/forgot-password', 'Send reset email'),
    ],
    'Products': [
        ('GET    /api/products', 'List all products (with filters)'),
        ('GET    /api/products/{id}', 'Get product detail'),
        ('GET    /api/products/search', 'Search products'),
        ('GET    /api/categories', 'Get product categories'),
    ],
    'Cart': [
        ('GET    /api/cart', 'Get cart items'),
        ('POST   /api/cart', 'Add to cart'),
        ('PUT    /api/cart/{id}', 'Update cart item'),
        ('DELETE /api/cart/{id}', 'Remove from cart'),
    ],
    'Addresses': [
        ('GET    /api/addresses', 'List addresses'),
        ('POST   /api/addresses', 'Create address'),
        ('PUT    /api/addresses/{id}', 'Update address'),
        ('DELETE /api/addresses/{id}', 'Delete address'),
        ('POST   /api/addresses/{id}/default', 'Set default'),
    ],
    'Orders': [
        ('GET    /api/orders', 'List user orders'),
        ('GET    /api/orders/{id}', 'Get order detail'),
        ('POST   /api/checkout', 'Create order from cart'),
        ('POST   /api/orders/{id}/cancel', 'Cancel order'),
        ('GET    /api/orders/stats', 'Order statistics'),
    ],
    'Payments': [
        ('POST   /api/payments/create', 'Create payment intent'),
        ('POST   /api/payments/webhook', 'Payment webhook'),
        ('GET    /api/payments/methods', 'Available payment methods'),
    ],
    'Reviews': [
        ('GET    /api/reviews', 'Get reviews (product or user)'),
        ('POST   /api/reviews', 'Create review'),
        ('PUT    /api/reviews/{id}', 'Update review'),
        ('DELETE /api/reviews/{id}', 'Delete review'),
    ],
    'Notifications': [
        ('GET    /api/notifications', 'List notifications'),
        ('POST   /api/notifications/{id}/read', 'Mark as read'),
        ('POST   /api/notifications/read-all', 'Mark all as read'),
    ],
    'Messaging': [
        ('GET    /api/conversations', 'List conversations'),
        ('POST   /api/conversations/start', 'Start conversation'),
        ('GET    /api/conversations/find', 'Find conversation'),
        ('GET    /api/messages', 'Get messages (conversation_id)'),
        ('POST   /api/messages', 'Send message'),
    ],
    'Seller': [
        ('GET    /api/seller/stats', 'Seller dashboard stats'),
        ('GET    /api/seller/orders', 'Seller orders'),
        ('POST   /api/seller/orders/{id}/status', 'Update order status'),
        ('GET    /api/seller/products', 'Seller products'),
        ('POST   /api/seller/products', 'Create product'),
    ],
    'Rider': [
        ('GET    /api/rider/dashboard', 'Rider dashboard'),
        ('GET    /api/rider/deliveries', 'Available deliveries'),
        ('POST   /api/rider/deliveries/{id}/accept', 'Accept delivery'),
        ('POST   /api/rider/deliveries/{id}/status', 'Update status'),
        ('GET    /api/rider/earnings', 'Rider earnings history'),
    ],
    'Admin': [
        ('GET    /api/admin/stats', 'Admin dashboard stats'),
        ('GET    /api/admin/users', 'List all users'),
        ('GET    /api/admin/orders', 'List all orders'),
        ('GET    /api/admin/products', 'List all products'),
        ('POST   /api/admin/products/{id}/status', 'Update product status'),
        ('POST   /api/admin/orders/{id}/status', 'Update order status'),
        ('POST   /api/admin/orders/{id}/cancel', 'Cancel order'),
    ],
}

total_endpoints = sum(len(v) for v in flutter_endpoints.values())
print(f'Total Flutter endpoints needed: {total_endpoints}')
print()

for category, endpoints in flutter_endpoints.items():
    print(f'  {category}:')
    for method_path, desc in endpoints:
        print(f'    {method_path:45s} - {desc}')
    print()

# ── 3. CURRENT IMPLEMENTATION STATUS ────────────────────────────────
print()
print('3. CURRENTLY IMPLEMENTED ENDPOINTS')
print('-'*60)

with open('routes/buyer_routes.py') as f:
    buyer_routes = f.read()
with open('routes/seller_routes.py') as f:
    seller_routes = f.read()
with open('routes/admin_routes.py') as f:
    admin_routes = f.read()
with open('routes/messages_routes.py') as f:
    msg_routes = f.read()

implemented = {
    'Auth (Session-based)': [
        'POST /auth/register (HTML form)',
        'POST /auth/login (HTML form)',
        'POST /auth/logout',
    ],
    'Buyer (JSON API)': [
        'GET /api/products',
        'GET /api/products/{id}',
        'GET /api/cart',
        'POST /api/cart',
        'PUT /api/cart/{id}',
        'DELETE /api/cart/{id}',
        'GET /api/addresses',
        'POST /api/addresses',
        'PUT /api/addresses/{id}',
        'DELETE /api/addresses/{id}',
        'POST /api/addresses/{id}/default',
        'POST /api/checkout',
        'GET /api/orders',
        'GET /api/orders/{id}',
        'POST /api/orders/{id}/cancel',
        'GET /api/reviews',
        'POST /api/reviews',
        'PUT /api/reviews/{id}',
        'DELETE /api/reviews/{id}',
        'GET /api/notifications',
        'POST /api/notifications/{id}/read',
        'POST /api/notifications/read-all',
        'POST /api/profile',
        'POST /api/password',
    ],
    'Seller (HTML + JSON)': [
        'GET /seller/orders',
        'POST /api/orders/{id}/status',
        'GET /seller/products (HTML)',
        'POST /api/seller/products',
    ],
    'Rider (HTML + JSON)': [
        'GET /api/deliveries',
        'POST /api/deliveries/{id}/accept',
    ],
    'Admin (HTML + JSON)': [
        'GET /admin/orders',
        'GET /admin/products',
        'POST /api/admin/orders/{id}/status',
        'POST /api/admin/products/{id}/status',
    ],
    'Messaging (JSON)': [
        'GET /api/conversations',
        'POST /api/conversations/start',
        'GET /api/conversations/find',
        'GET /api/conversations/{id}/messages',
        'POST /api/conversations/{id}/messages',
        'POST /api/conversations/{id}/read',
        'GET /api/unread-count',
        'POST /api/quick-message',
        'GET /api/messages?conversation_id=',
        'POST /api/messages',
    ],
}

for category, endpoints in implemented.items():
    print(f'  {category}: {len(endpoints)} endpoints')
    for ep in endpoints:
        print(f'    ✓ {ep}')
    print()

# ── 4. MISSING FOR FLUTTER ──────────────────────────────────────────
print()
print('4. MISSING ENDPOINTS (Needed for Flutter)')
print('-'*60)

missing = [
    ('POST   /api/auth/login', 'JSON login (currently HTML form only)'),
    ('POST   /api/auth/register', 'JSON register (currently HTML form only)'),
    ('GET    /api/auth/user', 'Get current user profile (JSON)'),
    ('POST   /api/auth/forgot-password', 'Send password reset email'),
    ('GET    /api/products/search?q=', 'Search endpoint (currently client-side)'),
    ('GET    /api/categories', 'Get product categories list'),
    ('GET    /api/products/{id}/reviews', 'Get reviews for specific product'),
    ('POST   /api/payments/create', 'Create payment (Stripe/Gcash/etc)'),
    ('GET    /api/orders/stats', 'User order statistics'),
    ('GET    /api/seller/stats', 'Seller statistics (JSON)'),
    ('GET    /api/rider/dashboard', 'Rider dashboard (JSON)'),
    ('GET    /api/rider/earnings', 'Rider earnings history'),
    ('POST   /api/rider/deliveries/{id}/status', 'Rider update status'),
    ('POST   /api/rider/earnings', 'Get rider earnings detail'),
    ('GET    /api/admin/stats', 'Admin statistics (JSON)'),
    ('GET    /api/admin/users', 'List all users (admin)'),
    ('GET    /api/admin/products', 'List all products (admin)'),
    ('POST   /api/products', 'Create product (admin/seller)'),
    ('PUT    /api/products/{id}', 'Update product'),
    ('DELETE /api/products/{id}', 'Delete product'),
    ('POST   /api/images/upload', 'Upload product/profile images'),
]

for ep, desc in missing:
    print(f'    {ep:45s} - {desc}')

print()

# ⚠️ 5. SECURITY GAPS ⚠️
print()
print('5. SECURITY GAPS (Critical for Production)')
print('-'*60)
security_gaps = [
    'No rate limiting on auth endpoints (brute force risk)',
    'No account lockout after failed login attempts',
    'No 2FA support',
    'Session security (no SameSite/Secure flags visible)',
    'No request size limits (DoS risk)',
    'No API key authentication for Flutter (session-based only)',
    'No OAuth/Social login options',
    'Password policy is basic (only 8 chars min)',
    'No email verification on registration',
    'No phone verification',
    'No CAPTCHA on auth forms (bot risk)',
    'CSRF protection exists but Flutter needs token-based auth',
]

for i, gap in enumerate(security_gaps, 1):
    print(f'   {i:2d}. {gap}')

print()

# 🔧 6. DATA VALIDATION GAPS 🔧
print()
print('6. DATA VALIDATION GAPS')
print('-'*60)
validation_gaps = [
    'Phone number format/enforcement',
    'Email domain validation',
    'Address coordinate bounds (Philippines)',
    'Product name duplicate checks',
    'Order status transition validation',
    'Rider assignment validation',
    'Stock reservation timeout (no expiry)',
    'Product price change history (none)',
    'Order cancellation time limit (none)',
]

for i, gap in enumerate(validation_gaps, 1):
    print(f'   {i:2d}. {gap}')

print()

# 🚀 7. BUSINESS LOGIC GAPS 🚀
print()
print('7. MISSING BUSINESS FEATURES')
print('-'*60)
business_gaps = [
    'Payment gateway integration (COD only)',
    'Refund/cancellation automation',
    'Shipping rate calculation (zones)',
    'Promo codes/coupons system',
    'Bulk product upload (CSV) for sellers',
    'Product variants pricing (different prices per variant)',
    'Wishlist (redirects to orders - needs actual wishlist table)',
    'Gift wrapping/not a gift option',
    'Delivery time slots',
    'Seller store page (currently just product list)',
    'Product recommendations (related items)',
    'Search autocomplete',
    'Recently viewed products',
    'Bulk order for B2B buyers',
    'Invoice generation',
]

for i, gap in enumerate(business_gaps, 1):
    print(f'   {i:2d}. {gap}')

print()

# 📱 8. IMAGE/FILE UPLOAD 📱
print()
print('8. IMAGE & FILE UPLOAD')
print('-'*60)
print('   Current: Products have images via Supabase Storage')
print('   Missing:')
print('     - Direct upload endpoint for Flutter (needs presigned URL)')
print('     - Product image upload API (only via form/multipart)')
print('     - Profile picture upload endpoint')
print('     - Review image upload endpoint')
print('     - Image compression/resize on upload')
print('     - CDN configuration check')
print()
print('9. ANALYTICS & REPORTS')
print('-'*60)
print('   Current: Products have images via Supabase Storage')
print('   Missing:',)
print('     - Direct upload endpoint for Flutter (needs presigned URL)')
print('     - Product image upload API (only via form/multipart)')
print('     - Profile picture upload endpoint')
print('     - Review image upload endpoint')
print('     - Image compression/resize on upload')
print('     - CDN configuration check')
print()

# 📊 9. ANALYTICS & REPORTS 📊
print()
print('📊 ANALYTICS & REPORTS')
print('-'*60)
analytics_gaps = [
    'Sales reports (daily/weekly/monthly)',
    'Best sellers report',
    'Customer analytics (retention, LTV)',
    'Seller performance metrics',
    'Rider performance metrics',
    'Product performance (views, conversions)',
    'Cart abandonment rate',
    'Revenue by category',
]

for i, gap in enumerate(analytics_gaps, 1):
    print(f'   {i:2d}. {gap}')

print()
print('='*60)
print('  SUMMARY: ACTION ITEMS FOR FLUTTER INTEGRATION            ')
print('='*60)
print()
print('CRITICAL (Must have for production):')
print('  1. Add JSON authentication endpoints (login/register via API)')
print('  2. Implement token-based auth (JWT) for Flutter')
print('  3. Add rate limiting on auth endpoints')
print('  4. Add payment gateway integration')
print('  5. Create missing Flutter API endpoints (see list above)')
print('  6. Image upload endpoints for Flutter')
print()
print('HIGH (Should have before launch):')
print('  7. Account verification (email/phone)')
print('  8. Wishlist table and API')
print('  9. Promo codes system')
print(' 10. Return/refund policy and workflow')
print(' 11. Shipping rate calculation')
print()
print('MEDIUM (Nice to have):')
print(' 12. Search endpoint (server-side)')
print(' 13. Bulk product upload for sellers')
print(' 14. Product recommendations')
print(' 15. Analytics dashboard API')
print()
print('LOW (Can add later):')
print(' 16. Social login (Google, Facebook)')
print(' 17. 2FA support')
print(' 18. Bulk order for B2B')
print(' 19. Gift wrapping options')
print(' 20. Delivery time slots')
print()
