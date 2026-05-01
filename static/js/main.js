// ── Carousel ──────────────────────────────────────────────────
let currentSlide = 0;
const slides     = document.querySelectorAll('.hero-slide');
const dots       = document.querySelectorAll('.carousel-dot');

function showSlide(n) {
    slides.forEach(s => s.classList.remove('active'));
    dots.forEach(d => d.classList.remove('active'));
    slides[n].classList.add('active');
    dots[n].classList.add('active');
}

function nextSlide() { currentSlide = (currentSlide + 1) % slides.length; showSlide(currentSlide); }
function prevSlide() { currentSlide = (currentSlide - 1 + slides.length) % slides.length; showSlide(currentSlide); }

let autoSlide = setInterval(nextSlide, 6000);

document.getElementById('nextBtn')?.addEventListener('click', () => { clearInterval(autoSlide); nextSlide(); autoSlide = setInterval(nextSlide, 6000); });
document.getElementById('prevBtn')?.addEventListener('click', () => { clearInterval(autoSlide); prevSlide(); autoSlide = setInterval(nextSlide, 6000); });
dots.forEach((dot, i) => dot.addEventListener('click', () => { clearInterval(autoSlide); currentSlide = i; showSlide(i); autoSlide = setInterval(nextSlide, 6000); }));

// ── Hamburger ─────────────────────────────────────────────────
const hamburger = document.getElementById('hamburger');
const navLinks  = document.getElementById('navLinks');
hamburger?.addEventListener('click', () => {
    hamburger.classList.toggle('active');
    navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
});

// ── Search ────────────────────────────────────────────────────
function navDoSearch() {
    const q = document.getElementById('navSearch')?.value?.trim();
    if (q) window.location.href = `/buyer/market?search=${encodeURIComponent(q)}`;
}

// ── Product card builder ──────────────────────────────────────
function buildProductCard(p) {
    const price    = parseFloat(p.price || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
    const imgSrc   = p.image ? `/${p.image}` : '';
    const imgEl    = imgSrc
        ? `<img src="${imgSrc}" alt="${p.name}" style="width:100%;height:100%;object-fit:cover">`
        : `<span style="font-size:48px">👗</span>`;
    const seller   = p.seller ? `${p.seller.first_name || ''} ${p.seller.last_name || ''}`.trim() : '';
    const stock    = p.total_stock ?? 0;
    const variants = (p.product_variants || []);
    const colorDots = variants.slice(0, 5).map(v => {
        const hex = v.sku?.includes('#') ? v.sku : '#ccc';
        return `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${hex};border:1px solid #ddd;margin-right:2px"></span>`;
    }).join('');

    const card = document.createElement('div');
    card.className = 'product-card';
    card.style.cursor = 'pointer';
    card.onclick = () => window.location.href = `/buyer/market`;
    card.innerHTML = `
        <div class="product-image-wrapper">${imgEl}</div>
        <h3 class="product-name">${p.name}</h3>
        ${seller ? `<div style="font-size:11px;color:#999;margin-bottom:4px">by ${seller}</div>` : ''}
        <div class="product-price">
            <span class="current">₱${price}</span>
        </div>
        <div style="font-size:11px;color:#999;margin-bottom:8px">${stock > 0 ? `${stock} in stock` : '<span style="color:#e74c3c">Out of stock</span>'}</div>
        ${colorDots ? `<div style="margin-bottom:8px">${colorDots}</div>` : ''}
        <a href="/buyer/market" class="quick-add-btn" style="text-align:center;display:block;text-decoration:none">View Product</a>`;
    return card;
}

// ── Render grid ───────────────────────────────────────────────
function renderGrid(gridId, products) {
    const grid = document.getElementById(gridId);
    if (!grid) return;
    grid.innerHTML = '';

    if (!products.length) {
        grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;color:#999">
            <div style="font-size:40px;margin-bottom:12px">🛍️</div>
            <p>No products available yet.</p>
            <a href="/register" style="color:#FF2BAC;font-weight:600">Become a seller →</a>
        </div>`;
        return;
    }
    products.forEach(p => grid.appendChild(buildProductCard(p)));
}

// ── Fetch & display products ──────────────────────────────────
async function loadHomeProducts() {
    try {
        const res      = await fetch('/api/products');
        const products = await res.json();

        if (!Array.isArray(products)) {
            renderGrid('featuredGrid', []);
            renderGrid('newArrivalsGrid', []);
            return;
        }

        // Featured = first 6
        renderGrid('featuredGrid', products.slice(0, 6));

        // New arrivals = next 6 (or same if fewer than 6)
        const arrivals = products.length > 6 ? products.slice(6, 12) : products.slice(0, 6);
        renderGrid('newArrivalsGrid', arrivals);

        // Update cart badge if logged in
        loadCartCount();
    } catch (e) {
        renderGrid('featuredGrid', []);
        renderGrid('newArrivalsGrid', []);
    }
}

async function loadCartCount() {
    try {
        const res  = await fetch('/buyer/api/cart');
        if (!res.ok) return;
        const data = await res.json();
        const badge = document.getElementById('cartBadge');
        if (badge && Array.isArray(data) && data.length > 0) {
            badge.textContent = data.length;
            badge.style.display = 'flex';
        }
    } catch { /* not logged in */ }
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', loadHomeProducts);
