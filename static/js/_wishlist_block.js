// -- Wishlist page ------------------------------------------
function buildWishlistCard(p) {
    var sellerObj  = p.seller || {};
    var seller     = ((sellerObj.first_name || '') + ' ' + (sellerObj.last_name || '')).trim() || (p.seller_name || '');
    var stock      = p.total_stock != null ? p.total_stock : (p.stock != null ? p.stock : 0);
    var price      = parseFloat(p.price || 0).toLocaleString('en-PH', { minimumFractionDigits: 2 });
    var outOfStock = stock <= 0;
    var imgSrc     = p.image ? (p.image.startsWith('/') ? p.image : '/' + p.image) : '';
    var imgHtml    = imgSrc
        ? '<img src="' + imgSrc + '" alt="' + p.name + '" style="width:100%;height:100%;object-fit:cover" onerror="this.style.display=\'none\'">'
        : '<div class="wc-image-placeholder">&#128717;</div>';
    var sellerHtml = seller ? '<div class="wc-seller">by Seller: ' + seller + '</div>' : '';
    var stockHtml  = '<div class="wc-stock ' + (outOfStock ? 'out-stock' : 'in-stock') + '">' + (outOfStock ? 'Out of stock' : stock + ' in stock') + '</div>';
    var cartBtn    = outOfStock
        ? '<button class="wc-btn-cart" disabled>Out of Stock</button>'
        : '<button class="wc-btn-cart" onclick="addToCart({id:\'' + p.id + '\',name:\'' + p.name.replace(/'/g, '') + '\'})">&#128722; Add to Cart</button>';
    var removeBtn  = '<button class="wc-btn-remove" onclick="removeFromWishlist(\'' + p.id + '\')">&#10084;&#65039; Remove</button>';
    return '<div class="wishlist-card" id="wc-' + p.id + '">'
        + '<div class="wc-image" onclick="window.location=\'/buyer/product?id=' + p.id + '\'">'
        + imgHtml
        + '<button class="wc-remove" onclick="event.stopPropagation();removeFromWishlist(\'' + p.id + '\')" title="Remove">&#10084;&#65039;</button>'
        + '</div>'
        + '<div class="wc-body">'
        + '<div class="wc-name" onclick="window.location=\'/buyer/product?id=' + p.id + '\'" style="cursor:pointer">' + p.name + '</div>'
        + sellerHtml
        + '<div class="wc-price">&#8369;' + price + '</div>'
        + stockHtml
        + '<div class="wc-actions">' + cartBtn + removeBtn + '</div>'
        + '</div></div>';
}

function removeFromWishlist(productId) {
    var list = getWishlist().filter(function(i) { return i.id !== productId; });
    localStorage.setItem('luxe_wishlist', JSON.stringify(list));
    var card = document.getElementById('wc-' + productId);
    if (card) card.remove();
    var remaining = document.querySelectorAll('#wishlistGrid .wishlist-card').length;
    var badge = document.getElementById('wishlistCount');
    if (badge) badge.textContent = remaining;
    if (!remaining) loadWishlist();
    showToast('Removed from wishlist.');
}

function loadWishlist() {
    var grid = document.getElementById('wishlistGrid');
    if (!grid) return;
    var list  = getWishlist();
    var badge = document.getElementById('wishlistCount');
    if (badge) badge.textContent = list.length;
    if (!list.length) {
        grid.innerHTML = '<div class="wishlist-empty"><div class="empty-heart">&#10084;&#65039;</div><h3>Your wishlist is empty &#10084;&#65039;</h3><p>Save items you love to buy them later.</p><a href="/buyer/market" class="btn-browse">Browse Products</a></div>';
        return;
    }
    grid.innerHTML = list.map(function(p) { return buildWishlistCard(p); }).join('');
}

