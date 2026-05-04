-- ============================================
-- COMPREHENSIVE ECOMMERCE DATABASE SCHEMA
-- Updated with all implemented features including:
-- - User management and authentication
-- - Product variants with size/color attributes
-- - Discount system for products and variants
-- - Inventory management with low stock alerts
-- - Order management with reserved stock
-- - Notifications and reviews
-- - Rider delivery system
-- ============================================

-- ============================================
-- USERS TABLE
-- ============================================
create table users (
    id              uuid        not null default gen_random_uuid(),
    first_name      text        not null,
    middle_name     text,
    last_name       text        not null,
    phone           text        not null,
    gender          text        check (gender in ('male', 'female', 'other')),
    birthdate       date,
    role            text        not null default 'user' check (role in ('user', 'admin', 'buyer', 'seller', 'rider')),
    profile_picture text,
    password        text,  -- In production, this should be hashed
    email           text        not null unique,
    failed_attempts integer     not null default 0,
    lock_until      timestamptz,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- ACTIVITY LOGS TABLE
-- ============================================
create table activity_logs (
    id          uuid        not null default gen_random_uuid(),
    user_id     uuid        references users(id) on delete set null,
    action      text        not null,
    ip_address  text        not null,
    user_agent  text,
    created_at  timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- ADDRESSES TABLE
-- ============================================
create table addresses (
    id         uuid        not null default gen_random_uuid(),
    user_id    uuid        not null references users(id) on delete cascade,
    label      text        default 'Home',
    region     text,
    city       text,
    barangay   text,
    street     text,
    zip_code   text,
    latitude   numeric(10, 7),
    longitude  numeric(10, 7),
    is_default boolean     not null default false,
    created_at timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- APPLICATIONS TABLE
-- ============================================
create table applications (
    id                uuid        not null default gen_random_uuid(),
    user_id           uuid        not null references users(id) on delete cascade,
    role              text        not null check (role in ('buyer', 'seller', 'rider')),
    status            text        not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
    -- Seller fields
    store_name        text,
    store_category    text        check (store_category in ('Dresses & Skirts', 'Tops & Blouses', 'Activewear & Yoga Pants', 'Lingerie & Sleepwear', 'Jackets & Coats', 'Shoes & Accessories')),
    store_description text,
    -- Rider fields
    vehicle_type      text,
    license_number    text,
    -- Admin review
    reviewed_by       uuid        references users(id) on delete set null,
    reviewed_at       timestamptz,
    reject_reason     text,
    created_at        timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- APPLICATION DOCUMENTS TABLE
-- ============================================
create table application_documents (
    id             uuid        not null default gen_random_uuid(),
    application_id uuid        not null references applications(id) on delete cascade,
    doc_type       text        not null,
    file_path      text        not null,
    created_at     timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- PRODUCT MANAGEMENT TABLES
-- ============================================
create table products (
    id                uuid        not null default gen_random_uuid(),
    seller_id         uuid        not null references users(id) on delete cascade,
    name              text        not null,
    description       text,
    category          text        not null check (category in ('Dresses & Skirts', 'Tops & Blouses', 'Activewear & Yoga Pants', 'Lingerie & Sleepwear', 'Jackets & Coats', 'Shoes & Accessories')),
    price             numeric(10, 2) not null check (price >= 0),
    total_stock       integer     not null default 0 check (total_stock >= 0),
    reserved_stock    integer     not null default 0 check (reserved_stock >= 0),
    status            text        not null default 'pending' check (status in ('pending', 'active', 'rejected')),
    -- Discount fields
    discount_type     text        default 'none' check (discount_type in ('percentage', 'fixed_amount', 'none')),
    discount_value    numeric(10, 2) default 0.00 check (discount_value >= 0),
    -- Inventory management fields
    low_stock_threshold integer default 10 check (low_stock_threshold >= 0),
    reorder_point      integer default 5 check (reorder_point >= 0),
    reorder_quantity   integer default 20 check (reorder_quantity >= 0),
    -- Admin review
    reviewed_by       uuid        references users(id),
    reviewed_at       timestamptz,
    reject_reason     text,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now(),
    primary key (id)
);

create table product_variants (
    id                uuid        not null default gen_random_uuid(),
    product_id        uuid        not null references products(id) on delete cascade,
    variant_type      text        not null check (variant_type in ('color', 'size')),
    value             text        not null,
    -- Enhanced variant attributes
    size              text,
    color             text,
    color_hex         text,
    stock             integer     not null default 0 check (stock >= 0),
    reserved_stock    integer     not null default 0 check (reserved_stock >= 0),
    price             numeric(10, 2) not null check (price >= 0),
    sku               text        unique,
    -- Discount fields
    discount_type     text        default 'none' check (discount_type in ('percentage', 'fixed_amount', 'none')),
    discount_value    numeric(10, 2) default 0.00 check (discount_value >= 0),
    -- Inventory management fields
    low_stock_threshold integer default 10 check (low_stock_threshold >= 0),
    reorder_point      integer default 5 check (reorder_point >= 0),
    reorder_quantity   integer default 20 check (reorder_quantity >= 0),
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now(),
    primary key (id),
    unique (product_id, variant_type, value)
);

create table product_images (
    id                uuid        not null default gen_random_uuid(),
    product_id        uuid        not null references products(id) on delete cascade,
    image_url         text        not null,
    is_primary        boolean     not null default false,
    variant_id        uuid        references product_variants(id) on delete set null,
    display_order     integer     not null default 0,
    created_at        timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- CART TABLE
-- ============================================
create table cart_items (
    id             uuid        not null default gen_random_uuid(),
    user_id        uuid        not null references users(id) on delete cascade,
    product_id     uuid        not null references products(id) on delete cascade,
    variant_id     uuid        references product_variants(id) on delete set null,
    quantity       integer     not null default 1 check (quantity > 0),
    price_snapshot numeric(10, 2) not null check (price_snapshot >= 0),
    created_at     timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- ORDERS TABLE
-- ============================================
create table orders (
    id              uuid        not null default gen_random_uuid(),
    buyer_id        uuid        not null references users(id) on delete cascade,
    rider_id        uuid        references users(id) on delete set null,
    total_amount    numeric(10, 2) not null check (total_amount >= 0),
    shipping_address jsonb       not null,
    status          text        not null default 'pending' check (status in ('pending', 'processing', 'ready_for_pickup', 'in_transit', 'delivered', 'cancelled')),
    payment_method  text        not null default 'cod' check (payment_method in ('cod', 'card', 'bank_transfer', 'gcash')),
    stock_reserved_at timestamptz, -- When stock was reserved for this order
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    primary key (id)
);

create table order_items (
    id          uuid        not null default gen_random_uuid(),
    order_id    uuid        not null references orders(id) on delete cascade,
    product_id  uuid        not null references products(id) on delete cascade,
    variant_id  uuid        references product_variants(id) on delete set null,
    quantity    integer     not null check (quantity > 0),
    unit_price  numeric(10, 2) not null check (unit_price >= 0),
    total_price numeric(10, 2) not null check (total_price >= 0),
    created_at  timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- NOTIFICATIONS TABLE
-- ============================================
create table notifications (
    id          uuid        not null default gen_random_uuid(),
    user_id     uuid        not null references users(id) on delete cascade,
    type        text        not null check (type in ('order', 'promo', 'delivery', 'system', 'inventory')),
    title       text        not null,
    message     text        not null,
    is_read     boolean     not null default false,
    action_url  text,
    created_at  timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- REVIEWS TABLE
-- ============================================
create table reviews (
    id          uuid        not null default gen_random_uuid(),
    user_id     uuid        not null references users(id) on delete cascade,
    product_id  uuid        not null references products(id) on delete cascade,
    order_id    uuid        not null references orders(id) on delete cascade,
    rating      integer     not null check (rating >= 1 and rating <= 5),
    comment     text,
    image_url   text,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
    primary key (id),
    unique (user_id, product_id, order_id)
);

-- ============================================
-- PASSWORD RESET TOKENS TABLE
-- ============================================
create table password_reset_tokens (
    id          uuid        not null default gen_random_uuid(),
    user_id     uuid        not null references users(id) on delete cascade,
    token       text        not null unique,
    expires_at  timestamptz not null,
    created_at  timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- EMAIL OTP TABLE
-- ============================================
create table email_otp (
    id          uuid        not null default gen_random_uuid(),
    email       text        not null,
    otp         text        not null,
    expires_at  timestamptz not null,
    created_at  timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- CONVERSATIONS TABLE
-- ============================================
create table conversations (
    id          uuid        not null default gen_random_uuid(),
    user1_id    uuid        not null references users(id) on delete cascade,
    user2_id    uuid        not null references users(id) on delete cascade,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
    primary key (id),
    unique (user1_id, user2_id),
    check (user1_id < user2_id)
);

-- ============================================
-- MESSAGES TABLE
-- ============================================
create table messages (
    id              uuid        not null default gen_random_uuid(),
    conversation_id uuid        not null references conversations(id) on delete cascade,
    sender_id       uuid        not null references users(id) on delete cascade,
    receiver_id     uuid        not null references users(id) on delete cascade,
    content         text        not null,
    is_read         boolean     not null default false,
    created_at      timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- RIDER EARNINGS TABLE
-- ============================================
create table rider_earnings (
    id          uuid        not null default gen_random_uuid(),
    rider_id    uuid        not null references users(id) on delete cascade,
    order_id    uuid        not null references orders(id) on delete cascade,
    amount      numeric(10, 2) not null check (amount >= 0),
    status      text        not null default 'pending' check (status in ('pending', 'paid', 'cancelled')),
    created_at  timestamptz not null default now(),
    paid_at     timestamptz,
    primary key (id)
);

-- ============================================
-- ADMIN SETTINGS TABLE
-- ============================================
create table admin_settings (
    id          uuid        not null default gen_random_uuid(),
    key         text        not null unique,
    value       text,
    description text,
    updated_by  uuid        not null references users(id),
    updated_at  timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- INVENTORY MANAGEMENT TABLES
-- ============================================
create table low_stock_alerts (
    id            uuid        not null default gen_random_uuid(),
    seller_id     uuid        not null references users(id) on delete cascade,
    product_id    uuid        not null references products(id) on delete cascade,
    variant_id    uuid        references product_variants(id) on delete set null,
    current_stock integer     not null,
    threshold     integer     not null check (threshold >= 0),
    is_resolved   boolean     not null default false,
    created_at    timestamptz not null default now(),
    resolved_at   timestamptz,
    resolved_by   uuid        references users(id) on delete set null,
    primary key (id)
);

create table inventory_settings (
    id                  uuid        not null default gen_random_uuid(),
    seller_id           uuid        not null references users(id) on delete cascade,
    low_stock_threshold integer     not null default 10 check (low_stock_threshold >= 0),
    out_of_stock_threshold integer not null default 0 check (out_of_stock_threshold >= 0),
    auto_reorder        boolean     not null default false,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    primary key (id),
    unique (seller_id)
);

create table inventory_snapshots (
    id            uuid        not null default gen_random_uuid(),
    seller_id     uuid        not null references users(id) on delete cascade,
    product_id    uuid        references products(id) on delete cascade,
    variant_id    uuid        references product_variants(id) on delete set null,
    stock_level   integer     not null,
    reserved_stock integer     not null default 0,
    total_value   numeric(10, 2) not null default 0.00,
    snapshot_date timestamptz not null default now(),
    created_at    timestamptz not null default now(),
    primary key (id)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Users indexes
create index idx_users_email on users(email);
create index idx_users_role on users(role);
create index idx_users_created_at on users(created_at);

-- Products indexes
create index idx_products_seller_id on products(seller_id);
create index idx_products_category on products(category);
create index idx_products_status on products(status);
create index idx_products_created_at on products(created_at);
create index idx_products_low_stock_threshold on products(low_stock_threshold);

-- Product variants indexes
create index idx_product_variants_product_id on product_variants(product_id);
create index idx_product_variants_size on product_variants(size);
create index idx_product_variants_color on product_variants(color);
create index idx_product_variants_stock on product_variants(stock);
create index idx_product_variants_discount_type on product_variants(discount_type);
create index idx_product_variants_low_stock_threshold on product_variants(low_stock_threshold);

-- Orders indexes
create index idx_orders_buyer_id on orders(buyer_id);
create index idx_orders_status on orders(status);
create index idx_orders_created_at on orders(created_at);
create index idx_orders_stock_reserved_at on orders(stock_reserved_at);

-- Order items indexes
create index idx_order_items_order_id on order_items(order_id);
create index idx_order_items_product_id on order_items(product_id);
create index idx_order_items_variant_id on order_items(variant_id);

-- Cart items indexes
create index idx_cart_items_user_id on cart_items(user_id);
create index idx_cart_items_product_id on cart_items(product_id);

-- Notifications indexes
create index idx_notifications_user_id on notifications(user_id);
create index idx_notifications_is_read on notifications(is_read);
create index idx_notifications_created_at on notifications(created_at);
create index idx_notifications_type on notifications(type);

-- Reviews indexes
create index idx_reviews_product_id on reviews(product_id);
create index idx_reviews_user_id on reviews(user_id);
create index idx_reviews_order_id on reviews(order_id);
create index idx_reviews_rating on reviews(rating);

-- Inventory management indexes
create index idx_low_stock_alerts_seller_id on low_stock_alerts(seller_id);
create index idx_low_stock_alerts_product_id on low_stock_alerts(product_id);
create index idx_low_stock_alerts_is_resolved on low_stock_alerts(is_resolved);
create index idx_inventory_settings_seller_id on inventory_settings(seller_id);
create index idx_inventory_snapshots_seller_id on inventory_snapshots(seller_id);
create index idx_inventory_snapshots_product_id on inventory_snapshots(product_id);
create index idx_inventory_snapshots_snapshot_date on inventory_snapshots(snapshot_date);

-- Messaging indexes
create index idx_conversations_user1_id on conversations(user1_id);
create index idx_conversations_user2_id on conversations(user2_id);
create index idx_messages_conversation_id on messages(conversation_id);
create index idx_messages_sender_id on messages(sender_id);
create index idx_messages_receiver_id on messages(receiver_id);
create index idx_messages_created_at on messages(created_at);

-- ============================================
-- DATABASE FUNCTIONS
-- ============================================

-- Function to calculate final price with discount
create or replace function calculate_final_price(
    base_price numeric,
    discount_type text,
    discount_value numeric
) returns numeric as $$
begin
    return case 
        when discount_type = 'percentage' and discount_value > 0 
        then base_price * (1 - discount_value / 100)
        when discount_type = 'fixed_amount' and discount_value > 0 
        then greatest(0, base_price - discount_value)
        else base_price
    end;
end;
$$ language plpgsql;

-- Function to get lowest variant price (considering discounts)
create or replace function get_lowest_variant_price(product_uuid uuid) returns numeric as $$
declare
    lowest_price numeric;
begin
    select min(calculate_final_price(price, discount_type, discount_value)) into lowest_price
    from product_variants 
    where product_id = product_uuid and stock > 0;
    
    return coalesce(lowest_price, 0);
end;
$$ language plpgsql;

-- Function to check and create low stock alerts
create or replace function check_low_stock()
returns void as $$
declare
    alert_record record;
begin
    -- Check products with low stock
    for alert_record in 
        select p.id as product_id, p.seller_id, null::uuid as variant_id, 
               p.total_stock as current_stock, p.low_stock_threshold as threshold
        from products p
        where p.status = 'active'
        and p.total_stock <= p.low_stock_threshold
        and p.low_stock_threshold > 0
        
        union all
        
        select pv.product_id, p.seller_id, pv.id as variant_id,
               pv.stock as current_stock, pv.low_stock_threshold as threshold
        from product_variants pv
        join products p on pv.product_id = p.id
        where p.status = 'active'
        and pv.stock <= pv.low_stock_threshold
        and pv.low_stock_threshold > 0
    loop
        -- Insert alert if it doesn't exist and isn't resolved
        insert into low_stock_alerts (seller_id, product_id, variant_id, current_stock, threshold)
        values (alert_record.seller_id, alert_record.product_id, alert_record.variant_id, 
                alert_record.current_stock, alert_record.threshold)
        on conflict (seller_id, product_id, variant_id, is_resolved) 
        do nothing;
    end loop;
end;
$$ language plpgsql;

-- Function to create daily inventory snapshots
create or replace function create_inventory_snapshot()
returns void as $$
declare
    snapshot_date timestamptz := now();
begin
    -- Create snapshots for all active products
    insert into inventory_snapshots (seller_id, product_id, variant_id, stock_level, reserved_stock, total_value, snapshot_date)
    select 
        p.seller_id,
        p.id,
        null::uuid,
        p.total_stock,
        p.reserved_stock,
        coalesce(p.total_stock * p.price, 0),
        snapshot_date
    from products p
    where p.status = 'active'
    
    union all
    
    select 
        p.seller_id,
        pv.product_id,
        pv.id,
        pv.stock,
        pv.reserved_stock,
        coalesce(pv.stock * pv.price, 0),
        snapshot_date
    from product_variants pv
    join products p on pv.product_id = p.id
    where p.status = 'active';
end;
$$ language plpgsql;

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================
alter table users                 enable row level security;
alter table addresses             enable row level security;
alter table applications          enable row level security;
alter table application_documents enable row level security;
alter table products              enable row level security;
alter table product_variants      enable row level security;
alter table product_images        enable row level security;
alter table cart_items            enable row level security;
alter table orders                enable row level security;
alter table order_items           enable row level security;
alter table notifications         enable row level security;
alter table reviews               enable row level security;
alter table conversations         enable row level security;
alter table messages              enable row level security;
alter table rider_earnings        enable row level security;
alter table low_stock_alerts      enable row level security;
alter table inventory_settings    enable row level security;
alter table inventory_snapshots    enable row level security;

-- ============================================
-- POLICIES - Users
-- ============================================
create policy "Service role full access on users" on users
    for all using (true) with check (true);

create policy "Users can view own record" on users
    for select using (auth.uid() = id);

create policy "Users can update own record" on users
    for update using (auth.uid() = id);

-- ============================================
-- POLICIES - Addresses
-- ============================================
create policy "Service role full access on addresses" on addresses
    for all using (true) with check (true);

create policy "Users can manage own addresses" on addresses
    for all using (auth.uid() = user_id);

-- ============================================
-- POLICIES - Applications
-- ============================================
create policy "Service role full access on applications" on applications
    for all using (true) with check (true);

create policy "Users can view own applications" on applications
    for select using (auth.uid() = user_id);

-- ============================================
-- POLICIES - Products
-- ============================================
create policy "Service role full access on products" on products
    for all using (true) with check (true);

create policy "Sellers can manage own products" on products
    for all using (auth.uid() = seller_id);

create policy "Buyers can view active products" on products
    for select using (status = 'active');

-- ============================================
-- POLICIES - Product Variants
-- ============================================
create policy "Service role full access on product_variants" on product_variants
    for all using (true) with check (true);

create policy "Sellers can manage own product variants" on product_variants
    for all using (auth.uid() in (select seller_id from products where id = product_variants.product_id));

create policy "Buyers can view active product variants" on product_variants
    for select using (exists (select 1 from products where id = product_variants.product_id and status = 'active'));

-- ============================================
-- POLICIES - Orders
-- ============================================
create policy "Service role full access on orders" on orders
    for all using (true) with check (true);

create policy "Buyers can view own orders" on orders
    for select using (auth.uid() = buyer_id);

create policy "Sellers can view orders for their products" on orders
    for select using (exists (
        select 1 from order_items oi 
        join products p on oi.product_id = p.id 
        where oi.order_id = orders.id and p.seller_id = auth.uid()
    ));

create policy "Riders can view assigned orders" on orders
    for select using (auth.uid() = rider_id);

-- ============================================
-- POLICIES - Cart Items
-- ============================================
create policy "Service role full access on cart_items" on cart_items
    for all using (true) with check (true);

create policy "Users can manage own cart items" on cart_items
    for all using (auth.uid() = user_id);

-- ============================================
-- POLICIES - Notifications
-- ============================================
create policy "Service role full access on notifications" on notifications
    for all using (true) with check (true);

create policy "Users can manage own notifications" on notifications
    for all using (auth.uid() = user_id);

-- ============================================
-- POLICIES - Reviews
-- ============================================
create policy "Service role full access on reviews" on reviews
    for all using (true) with check (true);

create policy "Users can manage own reviews" on reviews
    for all using (auth.uid() = user_id);

-- ============================================
-- POLICIES - Messages
-- ============================================
create policy "Service role full access on messages" on messages
    for all using (true) with check (true);

create policy "Users can view own conversations" on messages
    for select using (auth.uid() in (select user1_id from conversations where id = conversation_id) 
                    or auth.uid() in (select user2_id from conversations where id = conversation_id));

-- ============================================
-- POLICIES - Inventory Management
-- ============================================
create policy "Service role full access on inventory tables" on low_stock_alerts
    for all using (true) with check (true);

create policy "Sellers can manage own inventory alerts" on low_stock_alerts
    for all using (auth.uid() = seller_id);

create policy "Service role full access on inventory_settings" on inventory_settings
    for all using (true) with check (true);

create policy "Sellers can manage own settings" on inventory_settings
    for all using (auth.uid() = seller_id);

-- ============================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================

-- Trigger to update updated_at timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Apply updated_at trigger to relevant tables
create trigger update_users_updated_at before update on users
    for each row execute function update_updated_at_column();

create trigger update_products_updated_at before update on products
    for each row execute function update_updated_at_column();

create trigger update_product_variants_updated_at before update on product_variants
    for each row execute function update_updated_at_column();

create trigger update_orders_updated_at before update on orders
    for each row execute function update_updated_at_column();

create trigger update_reviews_updated_at before update on reviews
    for each row execute function update_updated_at_column();

create trigger update_conversations_updated_at before update on conversations
    for each row execute function update_updated_at_column();

create trigger update_inventory_settings_updated_at before update on inventory_settings
    for each row execute function update_updated_at_column();

-- ============================================
-- INITIAL DATA
-- ============================================

-- Insert default admin settings
insert into admin_settings (key, value, description, updated_by) values
('platform_name', 'Grande', 'Platform name', (select id from users where role = 'admin' limit 1)),
('platform_email', 'admin@grande.com', 'Platform email', (select id from users where role = 'admin' limit 1)),
('maintenance_mode', 'false', 'Maintenance mode flag', (select id from users where role = 'admin' limit 1)),
('max_products_per_seller', '100', 'Maximum products per seller', (select id from users where role = 'admin' limit 1));

-- Initialize inventory settings for existing sellers (if any)
insert into inventory_settings (seller_id, low_stock_threshold, out_of_stock_threshold)
select distinct seller_id, 10, 0 from products
where seller_id is not null
on conflict (seller_id) do nothing;

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Product listings view for buyers
create view product_listings as
select 
    p.id,
    p.name,
    p.description,
    p.category,
    p.status,
    p.discount_type as product_discount_type,
    p.discount_value as product_discount_value,
    get_lowest_variant_price(p.id) as lowest_variant_price,
    case 
        when p.discount_type != 'none' then calculate_final_price(p.price, p.discount_type, p.discount_value)
        else get_lowest_variant_price(p.id)
    end as display_price,
    p.total_stock,
    p.created_at,
    p.updated_at
from products p
where p.status = 'active';

-- Order summary view for sellers
create view seller_order_summary as
select 
    p.seller_id,
    o.id as order_id,
    o.status,
    o.created_at,
    o.total_amount,
    count(oi.id) as item_count,
    sum(oi.quantity) as total_quantity
from orders o
join order_items oi on o.id = oi.order_id
join products p on oi.product_id = p.id
group by p.seller_id, o.id, o.status, o.created_at, o.total_amount;
