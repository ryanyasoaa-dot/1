/**
 * product-form.js — Multi-step product creation
 * Steps: 1 Basic Info → 2 Variants → 3 Images → 4 Review → Submit
 */

// ── State ─────────────────────────────────────────────────────
let pfStep    = 1;
let pfVariants = [];   // [{ id, color, hex, price, stock }]
let pfImages   = {};   // { variantId: File, 'general': File[] }
let pfVarIdSeq = 0;

// ── Color name from hex ──────────────────────────────────────
const COLOR_MAP = [
    { name: 'Black',     hex: '#1a1a1a' },
    { name: 'White',     hex: '#ffffff' },
    { name: 'Red',       hex: '#e74c3c' },
    { name: 'Pink',      hex: '#FF6BCE' },
    { name: 'Blue',      hex: '#3498db' },
    { name: 'Navy',      hex: '#1a2a5e' },
    { name: 'Green',     hex: '#2ecc71' },
    { name: 'Yellow',    hex: '#f1c40f' },
    { name: 'Orange',    hex: '#e67e22' },
    { name: 'Purple',    hex: '#9b59b6' },
    { name: 'Brown',     hex: '#795548' },
    { name: 'Gray',      hex: '#95a5a6' },
    { name: 'Beige',     hex: '#f5f0e8' },
    { name: 'Maroon',    hex: '#800000' },
    { name: 'Teal',      hex: '#009688' },
    { name: 'Lavender',  hex: '#e6e6fa' },
    { name: 'Coral',     hex: '#ff6b6b' },
    { name: 'Mint',      hex: '#98ff98' },
    { name: 'Cream',     hex: '#fffdd0' },
    { name: 'Charcoal',  hex: '#36454f' },
];

function hexToRgb(hex) {
    const h = hex.replace('#', '');
    const full = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
    return {
        r: parseInt(full.slice(0,2), 16),
        g: parseInt(full.slice(2,4), 16),
        b: parseInt(full.slice(4,6), 16)
    };
}

function colorNameFromHex(hex) {
    const rgb = hexToRgb(hex);
    let best = COLOR_MAP[0], bestDist = Infinity;
    for (const c of COLOR_MAP) {
        const cr = hexToRgb(c.hex);
        const dist = Math.sqrt(
            (rgb.r - cr.r) ** 2 +
            (rgb.g - cr.g) ** 2 +
            (rgb.b - cr.b) ** 2
        );
        if (dist < bestDist) { bestDist = dist; best = c; }
    }
    return best.name;
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    pfImages['general'] = [];
    pfGoTo(1);
});

// ── Step navigation ───────────────────────────────────────────
function pfGoTo(step) {
    if (step > pfStep) {
        if (!pfValidate(pfStep)) return;
    }
    if (step === 3) pfBuildImageSections();
    if (step === 4) pfBuildReview();

    document.querySelectorAll('[id^="pfStep"]').forEach(el => el.style.display = 'none');
    document.getElementById(`pfStep${step}`).style.display = 'block';

    for (let i = 1; i <= 4; i++) {
        const ind  = document.getElementById(`pf-ind${i}`);
        const circ = ind.querySelector('.pf-step-circle');
        ind.classList.remove('active', 'done');
        if (i < step)  { ind.classList.add('done');   circ.textContent = '✓'; }
        if (i === step) { ind.classList.add('active'); circ.textContent = i; }
        if (i > step)   circ.textContent = i;
    }
    document.querySelectorAll('.pf-step-line').forEach((l, i) => l.classList.toggle('done', i + 1 < step));

    pfStep = step;
    window.scrollTo({ top: 0, behavior: 'smooth' });
    pfHideError();
}

// ── Validation ────────────────────────────────────────────────
function pfValidate(step) {
    if (step === 1) {
        if (!pfVal('pfName'))      return pfShowError('Product name is required.');
        if (!pfVal('pfBasePrice') || parseFloat(pfVal('pfBasePrice')) <= 0)
                                   return pfShowError('Base price must be greater than 0.');
        if (!pfVal('pfCategory'))  return pfShowError('Category is missing. Please contact support.');
        return true;
    }
    if (step === 2) {
        if (pfVariants.length === 0) return pfShowError('Add at least one variant.');
        for (const v of pfVariants) {
            if (!v.color)              return pfShowError('All variants must have a color name.');
            if (v.price <= 0)          return pfShowError(`Price for ${v.color} must be greater than 0.`);
            if (v.stock < 0)           return pfShowError(`Stock for ${v.color} cannot be negative.`);
        }
        return true;
    }
    if (step === 3) {
        for (const v of pfVariants) {
            if (!pfImages[v.id]) return pfShowError(`Please upload an image for the "${v.color}" variant.`);
        }
        return true;
    }
    return true;
}

function pfVal(id) { return document.getElementById(id)?.value?.trim() || ''; }

function pfShowError(msg) {
    const el = document.getElementById('pfError');
    el.textContent = msg;
    el.style.display = 'block';
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return false;
}

function pfHideError() {
    const el = document.getElementById('pfError');
    if (el) el.style.display = 'none';
}

// ── Step 2: Variants ──────────────────────────────────────────
function pfAddVariant(presetColor = null) {
    if (pfVariants.length >= 10) return pfShowError('Maximum 10 variants allowed.');

    const hex   = presetColor?.hex || '#cccccc';
    const color = colorNameFromHex(hex);

    // Prevent duplicate by hex
    const normalHex = hex.toLowerCase();
    if (pfVariants.some(v => v.hex.toLowerCase() === normalHex)) {
        return pfShowError(`A variant with this color already exists.`);
    }

    const id = ++pfVarIdSeq;
    pfVariants.push({ id, color, hex, price: parseFloat(pfVal('pfBasePrice')) || 0, stock: 0 });
    pfImages[id] = null;
    pfRenderVariants();
}

function pfRemoveVariant(id) {
    pfVariants = pfVariants.filter(v => v.id !== id);
    delete pfImages[id];
    pfRenderVariants();
}

function pfRenderVariants() {
    const list = document.getElementById('pfVariantList');
    if (!list) return;

    if (pfVariants.length === 0) {
        list.innerHTML = `
            <div class="pf-empty">No variants yet. Choose a color below or add a custom one.</div>
            <div class="pf-color-palette" id="pfPalette"></div>`;
        pfRenderPalette();
        document.getElementById('pfAddVariantBtn').style.display = 'inline-flex';
        return;
    }

    list.innerHTML = `
        <div class="pf-color-palette" id="pfPalette"></div>
        <div class="pf-variant-list" id="pfVarItems"></div>`;

    pfRenderPalette();

    const items = document.getElementById('pfVarItems');
    pfVariants.forEach(v => {
        const row = document.createElement('div');
        row.className = 'pf-variant-row';
        row.id = `pfVar-${v.id}`;
        row.innerHTML = `
            <div class="pf-var-color-preview" style="background:${v.hex}" title="${v.color}"></div>
            <div class="pf-var-fields">
                <div class="pf-var-field">
                    <label class="pf-label-sm">Color Name</label>
                    <input class="pf-input-sm" type="text" value="${v.color}" readonly
                           style="background:#f8f9fa;cursor:not-allowed;color:#666">
                </div>
                <div class="pf-var-field">
                    <label class="pf-label-sm">Hex Color</label>
                    <div class="pf-color-input-wrap">
                        <input type="color" value="${v.hex}"
                               oninput="pfOnHexChange(${v.id}, this.value)">
                        <span class="pf-hex-text" id="pfHexText-${v.id}">${v.hex}</span>
                    </div>
                </div>
                <div class="pf-var-field">
                    <label class="pf-label-sm">Price (₱)</label>
                    <input class="pf-input-sm" type="number" min="0" step="0.01" value="${v.price}"
                           onchange="pfUpdateVariant(${v.id},'price',parseFloat(this.value)||0)">
                </div>
                <div class="pf-var-field">
                    <label class="pf-label-sm">Stock</label>
                    <input class="pf-input-sm" type="number" min="0" value="${v.stock}"
                           onchange="pfUpdateVariant(${v.id},'stock',parseInt(this.value)||0)">
                </div>
            </div>
            <button type="button" class="pf-var-remove" onclick="pfRemoveVariant(${v.id})" title="Remove">×</button>`;
        items.appendChild(row);
    });

    document.getElementById('pfAddVariantBtn').style.display = pfVariants.length >= 10 ? 'none' : 'inline-flex';
}

function pfRenderPalette() {
    const palette = document.getElementById('pfPalette');
    if (!palette) return;
    const usedHexes = pfVariants.map(v => v.hex.toLowerCase());
    palette.innerHTML = COLOR_MAP.map(c => {
        const used = usedHexes.includes(c.hex.toLowerCase());
        return `<button type="button" class="pf-palette-swatch ${used ? 'used' : ''}"
                    style="background:${c.hex}" title="${c.name}"
                    onclick="${used ? '' : `pfAddVariant({name:'${c.name}',hex:'${c.hex}'})`}"
                    ${used ? 'disabled' : ''}>
                    ${used ? '✓' : ''}
                </button>`;
    }).join('');
}

function pfUpdateVariant(id, field, value) {
    const v = pfVariants.find(v => v.id === id);
    if (!v) return;
    v[field] = value;
}

function pfOnHexChange(id, hex) {
    const v = pfVariants.find(v => v.id === id);
    if (!v) return;
    // Prevent duplicate hex
    if (pfVariants.some(other => other.id !== id && other.hex.toLowerCase() === hex.toLowerCase())) {
        pfShowError('A variant with this color already exists.');
        return;
    }
    v.hex   = hex;
    v.color = colorNameFromHex(hex);
    // Update preview dot and read-only name field
    const row = document.getElementById(`pfVar-${id}`);
    if (row) {
        row.querySelector('.pf-var-color-preview').style.background = hex;
        row.querySelector('input[readonly]').value = v.color;
        const hexText = document.getElementById(`pfHexText-${id}`);
        if (hexText) hexText.textContent = hex;
    }
}

// ── Step 3: Images ────────────────────────────────────────────
function pfBuildImageSections() {
    const container = document.getElementById('pfImageSections');
    if (!container) return;
    container.innerHTML = '';

    // Per-variant image sections
    pfVariants.forEach(v => {
        const sec = document.createElement('div');
        sec.className = 'pf-img-section';
        sec.innerHTML = `
            <div class="pf-img-section-title">
                <span class="pf-var-dot" style="background:${v.hex}"></span>
                ${v.color} Variant Image <span class="pf-req">*</span>
            </div>
            <div class="pf-upload-area" id="pfUploadArea-${v.id}" onclick="document.getElementById('pfFileInput-${v.id}').click()">
                <div class="pf-upload-icon">🖼️</div>
                <div class="pf-upload-text">Click to upload image for <strong>${v.color}</strong></div>
                <div class="pf-upload-hint">JPG, PNG, WEBP — 1 image per variant</div>
            </div>
            <input type="file" id="pfFileInput-${v.id}" accept="image/*" style="display:none"
                   onchange="pfHandleVariantImage(${v.id}, this)">
            <div class="pf-img-preview" id="pfImgPreview-${v.id}"></div>`;
        container.appendChild(sec);

        // Restore existing preview if already uploaded
        if (pfImages[v.id]) pfShowVariantPreview(v.id, pfImages[v.id]);
    });

    // General images section
    const gen = document.createElement('div');
    gen.className = 'pf-img-section';
    gen.innerHTML = `
        <div class="pf-img-section-title">📦 General Product Images <span style="font-weight:400;color:#999">(optional)</span></div>
        <div class="pf-upload-area" onclick="document.getElementById('pfGenInput').click()">
            <div class="pf-upload-icon">📷</div>
            <div class="pf-upload-text">Click to upload general product images</div>
            <div class="pf-upload-hint">Multiple images allowed</div>
        </div>
        <input type="file" id="pfGenInput" accept="image/*" multiple style="display:none"
               onchange="pfHandleGeneralImages(this)">
        <div class="pf-img-grid" id="pfGenPreview"></div>`;
    container.appendChild(gen);

    pfRenderGeneralPreviews();
}

function pfHandleVariantImage(variantId, input) {
    const file = input.files[0];
    if (!file) return;
    pfImages[variantId] = file;
    pfShowVariantPreview(variantId, file);
}

function pfShowVariantPreview(variantId, file) {
    const preview = document.getElementById(`pfImgPreview-${variantId}`);
    const area    = document.getElementById(`pfUploadArea-${variantId}`);
    if (!preview) return;
    const url = URL.createObjectURL(file);
    preview.innerHTML = `
        <div class="pf-img-thumb">
            <img src="${url}" alt="variant image">
            <button type="button" class="pf-img-remove" onclick="pfRemoveVariantImage(${variantId})">×</button>
        </div>`;
    if (area) area.style.display = 'none';
}

function pfRemoveVariantImage(variantId) {
    pfImages[variantId] = null;
    const preview = document.getElementById(`pfImgPreview-${variantId}`);
    const area    = document.getElementById(`pfUploadArea-${variantId}`);
    if (preview) preview.innerHTML = '';
    if (area)    area.style.display = 'flex';
    const input = document.getElementById(`pfFileInput-${variantId}`);
    if (input) input.value = '';
}

function pfHandleGeneralImages(input) {
    Array.from(input.files).forEach(f => pfImages['general'].push(f));
    pfRenderGeneralPreviews();
    input.value = '';
}

function pfRenderGeneralPreviews() {
    const grid = document.getElementById('pfGenPreview');
    if (!grid) return;
    grid.innerHTML = pfImages['general'].map((f, i) => `
        <div class="pf-img-thumb">
            <img src="${URL.createObjectURL(f)}" alt="general">
            <button type="button" class="pf-img-remove" onclick="pfRemoveGeneral(${i})">×</button>
        </div>`).join('');
}

function pfRemoveGeneral(idx) {
    pfImages['general'].splice(idx, 1);
    pfRenderGeneralPreviews();
}

// ── Step 4: Review ────────────────────────────────────────────
function pfBuildReview() {
    const el = document.getElementById('pfReviewContent');
    if (!el) return;

    const varRows = pfVariants.map(v => {
        const price = parseFloat(v.price);
        const stock = parseInt(v.stock);
        const hasImg = !!pfImages[v.id];
        return `
        <div class="pf-review-variant">
            <span class="pf-review-color">
                <span class="pf-var-dot" style="background:${v.hex};display:inline-block;vertical-align:middle;margin-right:6px"></span>
                ${v.color}
            </span>
            <span class="pf-review-price">₱${price.toLocaleString('en-PH', {minimumFractionDigits:2})}</span>
            <span class="pf-review-stock">${stock} pcs</span>
            <span class="pf-review-img">${hasImg ? '🖼️ Set' : '⚠️ Missing'}</span>
        </div>`;
    }).join('');

    el.innerHTML = `
        <div class="pf-review-section">
            <div class="pf-review-title">📝 Basic Info</div>
            <div class="pf-review-row"><span>Name</span><strong>${pfVal('pfName')}</strong></div>
            <div class="pf-review-row"><span>Category</span><strong>${pfVal('pfCategory')}</strong></div>
            <div class="pf-review-row"><span>Base Price</span><strong>₱${parseFloat(pfVal('pfBasePrice')).toLocaleString('en-PH',{minimumFractionDigits:2})}</strong></div>
            <div class="pf-review-row"><span>Description</span><strong>${pfVal('pfDesc') || '—'}</strong></div>
        </div>
        <div class="pf-review-section">
            <div class="pf-review-title">🎨 Variants (${pfVariants.length})</div>
            <div class="pf-review-variant-header">
                <span>Color</span><span>Price</span><span>Stock</span><span>Image</span>
            </div>
            ${varRows}
        </div>
        <div class="pf-review-section">
            <div class="pf-review-title">📷 General Images</div>
            <div class="pf-img-grid">
                ${pfImages['general'].map(f => `<div class="pf-img-thumb"><img src="${URL.createObjectURL(f)}"></div>`).join('') || '<span style="color:#999;font-size:13px">None</span>'}
            </div>
        </div>`;
}

// ── Submit ────────────────────────────────────────────────────
async function pfSubmit() {
    if (!pfValidate(3)) return;

    const btn = document.getElementById('pfSubmitBtn');
    btn.disabled    = true;
    btn.textContent = '⏳ Submitting...';

    const fd = new FormData();
    fd.append('name',        pfVal('pfName'));
    fd.append('description', pfVal('pfDesc'));
    fd.append('category',    pfVal('pfCategory'));
    fd.append('price',       pfVal('pfBasePrice'));

    pfVariants.forEach((v, i) => {
        fd.append(`variants[${i}][type]`,  'color');
        fd.append(`variants[${i}][value]`, v.color);
        fd.append(`variants[${i}][hex]`,   v.hex);
        fd.append(`variants[${i}][price]`, v.price);
        fd.append(`variants[${i}][stock]`, v.stock);
        if (pfImages[v.id]) fd.append(`variant_image_${i}`, pfImages[v.id]);
    });

    pfImages['general'].forEach(f => fd.append('images[]', f));

    try {
        const res  = await fetch('/seller/api/products', { method: 'POST', body: fd });
        const data = await res.json();
        if (res.ok) {
            pfShowToast('Product submitted for approval! ✅', 'success');
            setTimeout(() => window.location.href = '/seller/products', 1800);
        } else {
            pfShowError(data.error || 'Failed to create product.');
            btn.disabled    = false;
            btn.textContent = '🚀 Submit for Approval';
        }
    } catch {
        pfShowError('Network error. Please try again.');
        btn.disabled    = false;
        btn.textContent = '🚀 Submit for Approval';
    }
}

// ── Toast ─────────────────────────────────────────────────────
function pfShowToast(msg, type = 'success') {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent  = msg;
    t.style.background = type === 'success' ? '#2ecc71' : '#e74c3c';
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}
