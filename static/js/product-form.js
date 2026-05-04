/**
 * product-form.js — Multi-step product creation
 * Steps: 1 Basic Info → 2 Variants → 3 Images → 4 Review → Submit
 */

// ── State ─────────────────────────────────────────────────────
let pfStep    = 1;
let pfVariants = [];   // [{ id, color, hex, price, stock }]
let pfImages   = {};   // { variantId: File, 'general': File[] }
let pfVarIdSeq = 0;

// ── Predefined colors and sizes (hardcoded for simplicity)
const pfPredefinedColors = [
    { name: 'Black', hex: '#000000' },
    { name: 'White', hex: '#FFFFFF' },
    { name: 'Red', hex: '#FF0000' },
    { name: 'Blue', hex: '#0000FF' },
    { name: 'Green', hex: '#008000' },
    { name: 'Yellow', hex: '#FFFF00' },
    { name: 'Orange', hex: '#FFA500' },
    { name: 'Purple', hex: '#800080' },
    { name: 'Pink', hex: '#FFC0CB' },
    { name: 'Brown', hex: '#A52A2A' },
    { name: 'Gray', hex: '#808080' },
    { name: 'Navy', hex: '#000080' },
    { name: 'Maroon', hex: '#800000' },
    { name: 'Olive', hex: '#808000' },
    { name: 'Teal', hex: '#008080' },
    { name: 'Silver', hex: '#C0C0C0' }
];

const pfPredefinedSizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL', 'One Size'];

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
    
    // Set up product discount event listeners
    const productDiscountType = document.getElementById('pfProductDiscountType');
    const productDiscountValue = document.getElementById('pfProductDiscountValue');
    
    if (productDiscountType) {
        productDiscountType.addEventListener('change', pfUpdateProductDiscount);
    }
    if (productDiscountValue) {
        productDiscountValue.addEventListener('input', pfUpdateProductDiscount);
    }
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
function pfAddVariant(color = null, hex = null, size = null) {
    if (pfVariants.length >= 10) return pfShowError('Maximum 10 variants allowed.');

    // Prevent duplicate by size + color combination
    const variantKey = `${size || 'One Size'}-${color || 'Default'}`;
    if (pfVariants.some(v => `${v.size || 'One Size'}-${v.color || 'Default'}` === variantKey)) {
        return pfShowError(`A variant with this size and color combination already exists.`);
    }

    const id = ++pfVarIdSeq;
    pfVariants.push({ 
        id, 
        color: color || 'Default', 
        hex: hex || '#808080',
        size: size || 'One Size',
        price: 0, 
        stock: 0,
        discount_type: 'none',
        discount_value: 0
    });
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
            <div class="pf-empty">No variants yet. Choose a size and color below or add custom ones.</div>
            <div class="pf-variant-creator" id="pfVariantCreator"></div>`;
        pfRenderVariantCreator();
        document.getElementById('pfAddVariantBtn').style.display = 'none';
        return;
    }

    list.innerHTML = `
        <div class="pf-variant-creator" id="pfVariantCreator"></div>
        <div class="pf-variant-list" id="pfVarItems"></div>`;

    pfRenderVariantCreator();

    const items = document.getElementById('pfVarItems');
    pfVariants.forEach(v => {
        const row = document.createElement('div');
        row.className = 'pf-variant-row';
        row.id = `pfVar-${v.id}`;
        row.innerHTML = `
            <div class="pf-var-preview">
                <div class="pf-var-color-preview" style="background:${v.hex}" title="${v.color}"></div>
                <div class="pf-var-size-label">${v.size || 'One Size'}</div>
            </div>
            <div class="pf-var-fields">
                <div class="pf-var-field">
                    <label class="pf-label-sm">Size</label>
                    <select class="pf-input-sm" id="pfSize-${v.id}" onchange="pfUpdateVariant(${v.id}, 'size', this.value)">
                        ${pfPredefinedSizes.map(size => 
                            `<option value="${size}" ${v.size === size ? 'selected' : ''}>${size}</option>`
                        ).join('')}
                        <option value="custom">Custom Size</option>
                    </select>
                    <input type="text" class="pf-input-sm" id="pfCustomSize-${v.id}" placeholder="Custom size" 
                           style="display:none; margin-top:4px;" onchange="pfUpdateVariant(${v.id}, 'size', this.value)">
                </div>
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
                <div class="pf-var-field">
                    <label class="pf-label-sm">Variant Discount</label>
                    <select class="pf-input-sm" id="pfDiscountType-${v.id}" onchange="pfUpdateVariantDiscount(${v.id})">
                        <option value="none" ${v.discount_type === 'none' ? 'selected' : ''}>No Discount</option>
                        <option value="percentage" ${v.discount_type === 'percentage' ? 'selected' : ''}>Percentage (%)</option>
                        <option value="fixed_amount" ${v.discount_type === 'fixed_amount' ? 'selected' : ''}>Fixed Amount (₱)</option>
                    </select>
                    <input type="number" class="pf-input-sm" id="pfDiscountValue-${v.id}" 
                           placeholder="0.00" min="0" step="0.01" value="${v.discount_value}"
                           style="display:${v.discount_type === 'none' ? 'none' : 'block'}; margin-top:4px;"
                           onchange="pfUpdateVariantDiscount(${v.id})">
                    <small class="pf-discount-preview" id="pfDiscountPreview-${v.id}" style="display:block; margin-top:2px; color:#28a745;"></small>
                </div>
            </div>
            <button type="button" class="pf-var-remove" onclick="pfRemoveVariant(${v.id})" title="Remove">×</button>`;
        items.appendChild(row);
    });

    document.getElementById('pfAddVariantBtn').style.display = pfVariants.length >= 10 ? 'none' : 'inline-flex';
}

function pfRenderVariantCreator() {
    const creator = document.getElementById('pfVariantCreator');
    if (!creator) return;
    
    const usedHexes = pfVariants.map(v => v.hex.toLowerCase());
    const usedSizes = pfVariants.map(v => v.size || 'One Size');
    
    creator.innerHTML = `
        <div class="pf-creator-section">
            <div class="pf-creator-group">
                <label class="pf-label-sm">Select Size</label>
                <select id="pfCreatorSize" class="pf-input-sm" style="width: 100%;">
                    <option value="">Choose size...</option>
                    ${pfPredefinedSizes.map(size => 
                        `<option value="${size}" ${usedSizes.includes(size) ? 'disabled' : ''}>${size} ${usedSizes.includes(size) ? '(used)' : ''}</option>`
                    ).join('')}
                    <option value="custom">Custom Size</option>
                </select>
                <input type="text" id="pfCreatorCustomSize" placeholder="Enter custom size" 
                       class="pf-input-sm" style="width: 100%; margin-top: 4px; display: none;">
            </div>
            
            <div class="pf-creator-group">
                <label class="pf-label-sm">Select Color</label>
                <div class="pf-color-grid">
                    ${pfPredefinedColors.map(color => {
                        const used = usedHexes.includes(color.hex.toLowerCase());
                        return `<button type="button" class="pf-color-swatch ${used ? 'used' : ''}"
                                    style="background:${color.hex}" title="${color.name}"
                                    onclick="${used ? '' : `pfSelectCreatorColor('${color.name}', '${color.hex}')`}"
                                    ${used ? 'disabled' : ''}>
                                    ${used ? '✓' : ''}
                                </button>`;
                    }).join('')}
                </div>
                <div class="pf-custom-color" style="margin-top: 8px;">
                    <label class="pf-label-sm">Custom Color</label>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <input type="color" id="pfCreatorCustomColor" value="#808080">
                        <input type="text" id="pfCreatorCustomColorName" placeholder="Color name" class="pf-input-sm" style="flex: 1;">
                    </div>
                </div>
            </div>
            
            <button type="button" class="pf-add-btn" onclick="pfAddVariantFromCreator()" style="width: 100%; margin-top: 12px;">
                + Add Variant
            </button>
        </div>
    `;
    
    // Handle size selection change
    const sizeSelect = document.getElementById('pfCreatorSize');
    const customSizeInput = document.getElementById('pfCreatorCustomSize');
    if (sizeSelect) {
        sizeSelect.addEventListener('change', function() {
            customSizeInput.style.display = this.value === 'custom' ? 'block' : 'none';
        });
    }
}

function pfSelectCreatorColor(name, hex) {
    document.getElementById('pfCreatorCustomColor').value = hex;
    document.getElementById('pfCreatorCustomColorName').value = name;
}

function pfAddVariantFromCreator() {
    const sizeSelect = document.getElementById('pfCreatorSize');
    const customSizeInput = document.getElementById('pfCreatorCustomSize');
    const customColorInput = document.getElementById('pfCreatorCustomColor');
    const customColorName = document.getElementById('pfCreatorCustomColorName');
    
    let size = sizeSelect.value;
    if (size === 'custom') {
        size = customSizeInput.value.trim();
        if (!size) {
            return pfShowError('Please enter a custom size.');
        }
    } else if (!size) {
        return pfShowError('Please select a size.');
    }
    
    const colorName = customColorName.value.trim() || 'Custom Color';
    const colorHex = customColorInput.value;
    
    pfAddVariant(colorName, colorHex, size);
}

function pfUpdateVariant(id, field, value) {
    const v = pfVariants.find(v => v.id === id);
    if (!v) return;
    v[field] = value;
    
    // Handle custom size display
    if (field === 'size' && value === 'custom') {
        const customInput = document.getElementById(`pfCustomSize-${id}`);
        const sizeSelect = document.getElementById(`pfSize-${id}`);
        customInput.style.display = 'block';
        sizeSelect.style.display = 'none';
    } else if (field === 'size' && value !== 'custom') {
        const customInput = document.getElementById(`pfCustomSize-${id}`);
        const sizeSelect = document.getElementById(`pfSize-${id}`);
        customInput.style.display = 'none';
        sizeSelect.style.display = 'block';
    }
}

function pfUpdateVariantDiscount(id) {
    const v = pfVariants.find(v => v.id === id);
    if (!v) return;
    
    const typeSelect = document.getElementById(`pfDiscountType-${id}`);
    const valueInput = document.getElementById(`pfDiscountValue-${id}`);
    const preview = document.getElementById(`pfDiscountPreview-${id}`);
    
    v.discount_type = typeSelect.value;
    v.discount_value = parseFloat(valueInput.value) || 0;
    
    // Show/hide value input based on type
    valueInput.style.display = v.discount_type === 'none' ? 'none' : 'block';
    
    // Calculate and show discounted price
    if (v.discount_type !== 'none' && v.discount_value > 0 && v.price > 0) {
        let finalPrice = v.price;
        if (v.discount_type === 'percentage') {
            finalPrice = v.price * (1 - v.discount_value / 100);
        } else if (v.discount_type === 'fixed_amount') {
            finalPrice = Math.max(0, v.price - v.discount_value);
        }
        
        preview.textContent = `Final price: ₱${finalPrice.toLocaleString('en-PH', {minimumFractionDigits: 2})}`;
        preview.style.display = 'block';
    } else {
        preview.textContent = '';
    }
}

function pfUpdateProductDiscount() {
    const typeSelect = document.getElementById('pfProductDiscountType');
    const valueInput = document.getElementById('pfProductDiscountValue');
    const preview = document.getElementById('pfProductDiscountPreview');
    
    // Show/hide value input based on type
    valueInput.style.display = typeSelect.value === 'none' ? 'none' : 'block';
    
    // Calculate preview for all variants
    const discountType = typeSelect.value;
    const discountValue = parseFloat(valueInput.value) || 0;
    
    if (discountType !== 'none' && discountValue > 0) {
        let previewText = `Product discount: ${discountType === 'percentage' ? discountValue + '%' : '₱' + discountValue}`;
        
        // Show impact on variants
        const variantPrices = pfVariants.map(v => {
            if (v.price > 0) {
                let finalPrice = v.price;
                if (discountType === 'percentage') {
                    finalPrice = v.price * (1 - discountValue / 100);
                } else if (discountType === 'fixed_amount') {
                    finalPrice = Math.max(0, v.price - discountValue);
                }
                return `₱${finalPrice.toLocaleString('en-PH', {minimumFractionDigits: 2})}`;
            }
            return null;
        }).filter(p => p !== null);
        
        if (variantPrices.length > 0) {
            previewText += ` | Variant prices: ${variantPrices.join(', ')}`;
        }
        
        preview.textContent = previewText;
        preview.style.display = 'block';
    } else {
        preview.textContent = '';
    }
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
        const imgHtml = hasImg ? `<img src="${URL.createObjectURL(pfImages[v.id])}" class="pf-review-variant-img" alt="${v.color}">` : '<span class="pf-review-img-missing">⚠️ Missing</span>';
        
        // Calculate final price after discount
        let finalPrice = price;
        let discountInfo = '';
        if (v.discount_type !== 'none' && v.discount_value > 0) {
            if (v.discount_type === 'percentage') {
                finalPrice = price * (1 - v.discount_value / 100);
                discountInfo = ` (${v.discount_value}% off)`;
            } else if (v.discount_type === 'fixed_amount') {
                finalPrice = Math.max(0, price - v.discount_value);
                discountInfo = ` (-₱${v.discount_value})`;
            }
        }
        
        return `
        <div class="pf-review-variant">
            <span class="pf-review-variant-info">
                <span class="pf-var-dot" style="background:${v.hex};display:inline-block;vertical-align:middle;margin-right:6px"></span>
                ${v.size} - ${v.color}
            </span>
            <span class="pf-review-price">
                ₱${finalPrice.toLocaleString('en-PH', {minimumFractionDigits:2})}
                ${discountInfo ? `<small style="color:#28a745">${discountInfo}</small>` : ''}
            </span>
            <span class="pf-review-stock">${stock} pcs</span>
            <span class="pf-review-img">${imgHtml}</span>
        </div>`;
    }).join('');

    el.innerHTML = `
        <div class="pf-review-section">
            <div class="pf-review-title">📝 Basic Info</div>
            <div class="pf-review-row"><span>Name</span><strong>${pfVal('pfName')}</strong></div>
            <div class="pf-review-row"><span>Category</span><strong>${pfVal('pfCategory')}</strong></div>
            <div class="pf-review-row"><span>Description</span><strong>${pfVal('pfDesc') || '—'}</strong></div>
        </div>
        <div class="pf-review-section">
            <div class="pf-review-title">🎨 Variants (${pfVariants.length})</div>
            <div class="pf-review-variant-header">
                <span>Variant</span><span>Final Price</span><span>Stock</span><span>Image</span>
            </div>
            ${varRows}
        </div>
        ${(() => {
            const productDiscountType = document.getElementById('pfProductDiscountType')?.value || 'none';
            const productDiscountValue = parseFloat(document.getElementById('pfProductDiscountValue')?.value || 0);
            
            if (productDiscountType !== 'none' && productDiscountValue > 0) {
                return `
                <div class="pf-review-section">
                    <div class="pf-review-title">🏷️ Product Discount</div>
                    <div class="pf-review-row">
                        <span>Discount Type</span>
                        <strong>${productDiscountType === 'percentage' ? productDiscountValue + '%' : '₱' + productDiscountValue}</strong>
                    </div>
                </div>`;
            }
            return '';
        })()}
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

    pfVariants.forEach((v, i) => {
        fd.append(`variants[${i}][type]`,         'color');
        fd.append(`variants[${i}][value]`,        v.color);
        fd.append(`variants[${i}][hex]`,          v.hex);
        fd.append(`variants[${i}][size]`,         v.size || 'One Size');
        fd.append(`variants[${i}][price]`,        v.price);
        fd.append(`variants[${i}][stock]`,        v.stock);
        fd.append(`variants[${i}][discount_type]`, v.discount_type || 'none');
        fd.append(`variants[${i}][discount_value]`, v.discount_value || 0);
        if (pfImages[v.id]) fd.append(`variant_image_${i}`, pfImages[v.id]);
    });
    
    // Add product discount information
    const productDiscountType = document.getElementById('pfProductDiscountType')?.value || 'none';
    const productDiscountValue = parseFloat(document.getElementById('pfProductDiscountValue')?.value || 0);
    fd.append('discount_type', productDiscountType);
    fd.append('discount_value', productDiscountValue);

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
