/**
 * product-form.js — Product creation form logic
 * Handles dynamic variants, image uploads, and validation
 */

let uploadedImages = [];
let removedImages = [];
let currentVariantId = 0;

// Default variant values by category
const defaultVariants = {
    'Dresses & Skirts': ['Red', 'Blue', 'Black', 'White', 'Green', 'Yellow'],
    'Tops & Blouses': ['Red', 'Blue', 'Black', 'White', 'Pink', 'Gray'],
    'Activewear & Yoga Pants': ['Black', 'Navy', 'Gray', 'Purple', 'Pink'],
    'Lingerie & Sleepwear': ['Black', 'White', 'Pink', 'Beige', 'Red'],
    'Jackets & Coats': ['Black', 'Blue', 'Brown', 'Green', 'Beige'],
    'Shoes & Accessories': ['36', '37', '38', '39', '40', '41', '42']
};

// Variant type mapping
const variantTypes = {
    'Dresses & Skirts': 'color',
    'Tops & Blouses': 'color',
    'Activewear & Yoga Pants': 'color',
    'Lingerie & Sleepwear': 'color',
    'Jackets & Coats': 'color',
    'Shoes & Accessories': 'size'
};

const variantLabels = {
    'color': 'Color',
    'size': 'Size'
};

// Initialize form when page loads
document.addEventListener('DOMContentLoaded', () => {
    const categorySelect = document.getElementById('productCategory');
    categorySelect.addEventListener('change', onCategoryChange);

    // Add initial variants based on category or default to color
    const initialCategory = categorySelect.value || 'Dresses & Skirts';
    onCategoryChange({ target: categorySelect });
    initializeVariants(initialCategory);
});

function onCategoryChange(event) {
    const category = event.target.value;
    const variantType = category ? variantTypes[category] : 'color';
    const label = variantType === 'color' ? 'Color' : 'Size';

    document.getElementById('variantTypeLabel').textContent = label + ' variants';
    document.getElementById('variantTypeDescription').textContent = label.toLowerCase();

    // Clear existing variants
    document.getElementById('variantsContainer').innerHTML = '';
    currentVariantId = 0;

    // Add initial variants
    if (category && defaultVariants[category]) {
        defaultVariants[category].forEach(val => {
            addVariant(val);
        });
    } else {
        addVariant();
    }
}

function initializeVariants(category) {
    if (defaultVariants[category]) {
        defaultVariants[category].forEach(val => {
            addVariant(val);
        });
    }
}

function addVariant(initialValue = '') {
    const container = document.getElementById('variantsContainer');
    const category = document.getElementById('productCategory').value;
    const variantType = category ? variantTypes[category] : 'color';
    const label = variantType === 'color' ? 'Color' : 'Size';
    const inputType = variantType === 'color' ? 'text' : 'number';
    const placeholder = variantType === 'color' ? 'e.g., Red, Blue' : 'e.g., 38';
    const step = variantType === 'size' ? '1' : null;
    const min = variantType === 'size' ? '0' : null;

    const div = document.createElement('div');
    div.className = 'variant-item';
    div.id = `variant-${currentVariantId}`;

    const input = document.createElement('input');
    input.type = inputType;
    input.placeholder = placeholder;
    input.value = initialValue;
    input.step = step;
    input.min = min;
    input.setAttribute('aria-label', label);

    const stockInput = document.createElement('input');
    stockInput.type = 'number';
    stockInput.placeholder = 'Stock';
    stockInput.min = '0';
    stockInput.value = '0';
    stockInput.style.maxWidth = '120px';

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'variant-remove';
    removeBtn.innerHTML = '×';
    removeBtn.title = 'Remove variant';
    removeBtn.setAttribute('aria-label', 'Remove variant');
    removeBtn.onclick = () => {
        div.remove();
    };

    div.appendChild(input);
    div.appendChild(stockInput);
    div.appendChild(removeBtn);
    container.appendChild(div);
    currentVariantId++;

    // Focus on the new input
    input.focus();
}

function setBulkStock() {
    const stock = parseInt(document.getElementById('bulkStockInput').value) || 0;
    document.querySelectorAll('#variantsContainer input[type="number"]').forEach(input => {
        input.value = stock;
    });
}

function handleImageSelect(event) {
    const files = Array.from(event.target.files);
    const previewGrid = document.getElementById('imagePreviewGrid');

    files.forEach(file => {
        if (file.type.startsWith('image/')) {
            const reader = new Image();
            reader.onload = (e) => {
                const imgData = {
                    id: Date.now() + Math.random(),
                    file: file,
                    url: e.target.result,
                    isPrimary: uploadedImages.length === 0
                };
                uploadedImages.push(imgData);
                renderImagePreviews();
            };
            reader.readAsDataURL(file);
        }
    });

    event.target.value = '';
}

function renderImagePreviews() {
    const previewGrid = document.getElementById('imagePreviewGrid');
    previewGrid.innerHTML = '';

    uploadedImages.forEach((img, index) => {
        const preview = document.createElement('div');
        preview.className = 'image-preview';

        const imgEl = document.createElement('img');
        imgEl.src = img.url;
        imgEl.alt = 'Product image';

        const actions = document.createElement('div');
        actions.className = 'image-preview-actions';

        if (img.isPrimary) {
            const badge = document.createElement('span');
            badge.className = 'primary-badge';
            badge.textContent = 'Primary';
            actions.appendChild(badge);
        }

        const btnGroup = document.createElement('div');

        const primaryBtn = document.createElement('button');
        primaryBtn.type = 'button';
        primaryBtn.innerHTML = img.isPrimary ? '★' : '☆';
        primaryBtn.title = 'Set as primary';
        primaryBtn.onclick = (e) => {
            e.stopPropagation();
            setPrimaryImage(img.id);
        };
        btnGroup.appendChild(primaryBtn);

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.innerHTML = '×';
        removeBtn.className = 'remove-image';
        removeBtn.title = 'Remove image';
        removeBtn.onclick = (e) => {
            e.stopPropagation();
            uploadedImages = uploadedImages.filter(i => i.id !== img.id);
            removedImages.push(img);
            renderImagePreviews();
        };
        btnGroup.appendChild(removeBtn);

        actions.appendChild(btnGroup);
        preview.appendChild(imgEl);
        preview.appendChild(actions);
        previewGrid.appendChild(preview);
    });
}

function setPrimaryImage(imgId) {
    uploadedImages.forEach(img => {
        img.isPrimary = img.id === imgId;
    });
    renderImagePreviews();
}

function validateForm() {
    let isValid = true;

    // Validate name
    const name = document.getElementById('productName').value.trim();
    if (!name) {
        document.getElementById('nameError').classList.add('show');
        isValid = false;
    } else {
        document.getElementById('nameError').classList.remove('show');
    }

    // Validate price
    const price = parseFloat(document.getElementById('productPrice').value);
    if (!price || price <= 0) {
        document.getElementById('priceError').classList.add('show');
        isValid = false;
    } else {
        document.getElementById('priceError').classList.remove('show');
    }

    // Validate category
    const category = document.getElementById('productCategory').value;
    if (!category) {
        document.getElementById('categoryError').classList.add('show');
        isValid = false;
    } else {
        document.getElementById('categoryError').classList.remove('show');
    }

    // Validate images
    if (uploadedImages.length === 0) {
        document.getElementById('imageError').style.display = 'block';
        isValid = false;
    } else {
        document.getElementById('imageError').style.display = 'none';
    }

    // Validate variants
    const variantItems = document.querySelectorAll('.variant-item');
    if (variantItems.length === 0) {
        document.getElementById('variantError').style.display = 'block';
        isValid = false;
    } else {
        // Check if any variant has value
        let hasValue = false;
        variantItems.forEach(item => {
            const input = item.querySelector('input[type="text"], input[type="number"]');
            if (input && input.value.trim()) {
                hasValue = true;
            }
        });
        if (!hasValue) {
            document.getElementById('variantError').style.display = 'block';
            isValid = false;
        } else {
            document.getElementById('variantError').style.display = 'none';
        }
    }

    return isValid;
}

function collectVariantData() {
    const variantItems = document.querySelectorAll('.variant-item');
    const category = document.getElementById('productCategory').value;
    const variantType = category ? variantTypes[category] : 'color';
    const variants = [];

    variantItems.forEach(item => {
        const input = item.querySelector('input[type="text"], input[type="number"]');
        const stockInput = item.querySelectorAll('input[type="number"]')[1];

        if (input && input.value.trim()) {
            let value = input.value.trim();
            if (variantType === 'size') {
                value = parseInt(value).toString();
            }
            variants.push({
                variant_type: variantType,
                value: value,
                stock: parseInt(stockInput.value) || 0
            });
        }
    });

    return variants;
}

function showToast(message, type) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.style.background = type === 'success' ? 'var(--pink)' : '#e74c3c';
    toast.style.display = 'block';
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

async function submitProduct(event) {
    event.preventDefault();

    if (!validateForm()) {
        showToast('Please fix the errors in the form', 'error');
        return false;
    }

    const submitBtn = event.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating...';

    const form = event.target;
    const formData = new FormData();

    // Basic product data
    formData.append('name', document.getElementById('productName').value.trim());
    formData.append('description', document.getElementById('productDescription').value.trim());
    formData.append('category', document.getElementById('productCategory').value);
    formData.append('price', document.getElementById('productPrice').value);

    // Append images
    uploadedImages.forEach(img => {
        if (img.file) {
            formData.append('images[]', img.file);
        }
    });

    // Append variants
    const variants = collectVariantData();
    variants.forEach((v, i) => {
        formData.append(`variants[${i}][type]`, v.variant_type);
        formData.append(`variants[${i}][value]`, v.value);
        formData.append(`variants[${i}][stock]`, v.stock);
    });

    try {
        const response = await fetch('/seller/api/products', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showToast(data.message || 'Product submitted for approval!', 'success');
            setTimeout(() => {
                window.location.href = '/seller/products';
            }, 1500);
        } else {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Create Product';
            showToast(data.error || 'Failed to create product', 'error');
        }
    } catch (error) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Product';
        showToast('Network error. Please try again.', 'error');
        console.error('Error:', error);
    }

    return false;
}