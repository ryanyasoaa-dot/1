-- ============================================
-- LUXE E-COMMERCE - SUPABASE SQL SCHEMA
-- Run this entire file in Supabase SQL Editor
-- ============================================ 

-- Drop old tables if they exist (clean slate)
drop table if exists application_documents cascade;
drop table if exists applications          cascade;
drop table if exists addresses             cascade;
drop table if exists product_images        cascade;
drop table if exists product_variants      cascade;
drop table if exists products              cascade;
drop table if exists cart_items            cascade;
drop table if exists profiles              cascade;
drop table if exists users                 cascade;

-- ============================================
-- USERS TABLE
-- ============================================
create table users (
    id          uuid        not null references auth.users(id) on delete cascade,
    first_name  text        not null,
    middle_name text,
    last_name   text        not null,
    phone       text        not null,
    gender      text        check (gender in ('male', 'female', 'other')),
    birthdate   date,
    role        text        not null default 'user' check (role in ('user', 'admin')),
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now(),
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
    reviewed_by       uuid        references auth.users(id),
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
    status            text        not null default 'pending' check (status in ('pending', 'active', 'rejected')),
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
    stock             integer     not null default 0 check (stock >= 0),
    sku               text        unique,
    created_at        timestamptz not null default now(),
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
    status          text        not null default 'pending' check (status in ('pending', 'processing', 'ready_for_pickup', 'in_transit', 'delivered')),
    payment_method  text        not null default 'cod' check (payment_method in ('cod', 'card', 'bank_transfer', 'gcash')),
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
-- POLICIES - Application Documents
-- ============================================
create policy "Service role full access on app_documents" on application_documents
    for all using (true) with check (true);

create policy "Users can view own documents" on application_documents
    for select using (application_id in (
        select id from applications where user_id = auth.uid()
    ));

-- ============================================
-- POLICIES - Products
-- ============================================
create policy "Service role full access on products" on products
    for all using (true) with check (true);

create policy "Sellers can view own products" on products
    for select using (seller_id = auth.uid());

create policy "Sellers can insert own products" on products
    for insert with check (seller_id = auth.uid());

create policy "Sellers can update own products" on products
    for update using (seller_id = auth.uid());

create policy "Sellers can delete own products" on products
    for delete using (seller_id = auth.uid());

create policy "Buyers can view active products" on products
    for select using (status = 'active');

-- ============================================
-- POLICIES - Product Variants
-- ============================================
create policy "Service role full access on variants" on product_variants
    for all using (true) with check (true);

create policy "Sellers can manage own variants" on product_variants
    for all using (product_id in (
        select id from products where seller_id = auth.uid()
    ));

-- ============================================
-- POLICIES - Product Images
-- ============================================
create policy "Service role full access on images" on product_images
    for all using (true) with check (true);

create policy "Sellers can manage own images" on product_images
    for all using (product_id in (
        select id from products where seller_id = auth.uid()
    ));

create policy "Buyers can view product images" on product_images
    for select using (product_id in (
        select id from products where status = 'active'
    ));

-- ============================================
-- POLICIES - Cart
-- ============================================
create policy "Service role full access on cart items" on cart_items
    for all using (true) with check (true);

create policy "Users can manage own cart items" on cart_items
    for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- ============================================
-- POLICIES - Orders
-- ============================================
create policy "Service role full access on orders" on orders
    for all using (true) with check (true);

create policy "Users can view own orders" on orders
    for select using (buyer_id = auth.uid());

create policy "Users can create own orders" on orders
    for insert with check (buyer_id = auth.uid());

create policy "Sellers can view orders for their products" on orders
    for select using (id in (
        select order_id from order_items oi
        join products p on oi.product_id = p.id
        where p.seller_id = auth.uid()
    ));

create policy "Riders can view available and assigned deliveries" on orders
    for select using (
        status = 'ready_for_pickup'
        or rider_id = auth.uid()
    );

-- ============================================
-- POLICIES - Order Items
-- ============================================
create policy "Service role full access on order items" on order_items
    for all using (true) with check (true);

create policy "Users can view own order items" on order_items
    for select using (order_id in (
        select id from orders where buyer_id = auth.uid()
    ));

-- ============================================
-- INDEXES
-- ============================================
create index idx_addresses_user_id       on addresses(user_id);
create index idx_applications_user_id    on applications(user_id);
create index idx_applications_status     on applications(status);
create index idx_app_docs_application_id on application_documents(application_id);
create index idx_products_seller_id      on products(seller_id);
create index idx_products_category       on products(category);
create index idx_products_status         on products(status);
create index idx_variants_product_id     on product_variants(product_id);
create index idx_images_product_id       on product_images(product_id);
create index idx_images_variant_id       on product_images(variant_id);
create index idx_cart_items_user_id      on cart_items(user_id);
create index idx_cart_items_product_id   on cart_items(product_id);
create index idx_orders_buyer_id         on orders(buyer_id);
create index idx_orders_rider_id         on orders(rider_id);
create index idx_orders_status           on orders(status);
create index idx_items_order_id          on order_items(order_id);
create index idx_items_product_id        on order_items(product_id);

-- ============================================
-- ALTER-ONLY MIGRATION BLOCK (NO RESET)
-- Run this block on existing databases only.
-- ============================================
/*
alter table orders
    add column if not exists rider_id uuid references users(id) on delete set null;

do $$
begin
    alter table orders drop constraint if exists orders_status_check;
exception
    when undefined_object then null;
end $$;

alter table orders
    add constraint orders_status_check
    check (status in ('pending', 'processing', 'ready_for_pickup', 'in_transit', 'delivered'));

do $$
begin
    alter table orders drop constraint if exists orders_payment_method_check;
exception
    when undefined_object then null;
end $$;

alter table orders
    add constraint orders_payment_method_check
    check (payment_method in ('cod', 'card', 'bank_transfer', 'gcash'));

update orders
set status = case
    when status = 'shipped' then 'in_transit'
    when status = 'cancelled' then 'pending'
    else status
end
where status in ('shipped', 'cancelled');

create index if not exists idx_orders_rider_id on orders(rider_id);

drop policy if exists "Riders can view available and assigned deliveries" on orders;
create policy "Riders can view available and assigned deliveries" on orders
    for select using (
        status = 'ready_for_pickup'
        or rider_id = auth.uid()
    );
*/
