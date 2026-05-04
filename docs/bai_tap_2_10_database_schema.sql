-- ============================================================
-- BÀI TẬP 2.10 — DATABASE SCHEMA TOÀN BỘ HỆ THỐNG
-- Microservices E-Commerce Platform
-- Môn học: Kiến trúc & Thiết kế Phần mềm
-- ============================================================

-- ============================================================
-- 1. PRODUCT SERVICE DATABASE — PostgreSQL (productdb)
-- Lý do chọn PostgreSQL:
--   - Hỗ trợ JSON field mạnh (specifications của Electronics)
--   - Phù hợp dữ liệu phức tạp, quan hệ nhiều bảng
--   - Hỗ trợ full-text search cho catalog sản phẩm
--   - Index đa dạng (B-tree, GIN cho JSONB)
-- ============================================================

-- Table: category
-- Mapping: Class Category → Table category
CREATE TABLE category (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    slug        VARCHAR(120) UNIQUE,
    description TEXT         DEFAULT '',
    is_active   BOOLEAN      DEFAULT TRUE,
    created_at  TIMESTAMP    DEFAULT NOW()
);

-- Table: product  (base class)
-- Mapping: Class Product → Table product
-- Association: Product → Category (FK category_id)
CREATE TABLE product (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255)   NOT NULL,
    description TEXT           DEFAULT '',
    price       FLOAT          NOT NULL,
    stock       INT            DEFAULT 0,
    image_url   VARCHAR(500)   DEFAULT '',
    is_active   BOOLEAN        DEFAULT TRUE,
    created_at  TIMESTAMP      DEFAULT NOW(),
    updated_at  TIMESTAMP      DEFAULT NOW(),
    -- Association: Product → Category (1..* many-to-one)
    category_id INT            NOT NULL REFERENCES category(id) ON DELETE CASCADE
);

CREATE INDEX idx_product_category ON product(category_id, is_active);
CREATE INDEX idx_product_price    ON product(price);
CREATE INDEX idx_product_name     ON product(name);

-- Table: book  (sub-class of Product — Table-per-Type inheritance)
-- Mapping: Class Book extends Product → Table book with FK = PK
CREATE TABLE book (
    product_id  INT          PRIMARY KEY REFERENCES product(id) ON DELETE CASCADE,
    author      VARCHAR(255) NOT NULL,
    publisher   VARCHAR(255) DEFAULT '',
    isbn        VARCHAR(20)  UNIQUE DEFAULT '',
    pages       INT,
    language    VARCHAR(50)  DEFAULT 'Vietnamese'
);

-- Table: electronics  (sub-class of Product)
-- Mapping: Class Electronics extends Product → Table electronics
CREATE TABLE electronics (
    product_id     INT          PRIMARY KEY REFERENCES product(id) ON DELETE CASCADE,
    brand          VARCHAR(100) NOT NULL,
    warranty       INT          NOT NULL,  -- tháng
    model_number   VARCHAR(100) DEFAULT '',
    specifications JSONB        DEFAULT '{}'
);

-- Table: fashion  (sub-class of Product)
-- Mapping: Class Fashion extends Product → Table fashion
CREATE TABLE fashion (
    product_id  INT          PRIMARY KEY REFERENCES product(id) ON DELETE CASCADE,
    size        VARCHAR(10)  NOT NULL,
    color       VARCHAR(50)  NOT NULL,
    material    VARCHAR(100) DEFAULT '',
    gender      CHAR(1)      DEFAULT 'U' CHECK (gender IN ('M', 'F', 'U'))
);

-- ============================================================
-- 2. USER SERVICE DATABASE — MySQL (userdb)
-- Lý do chọn MySQL:
--   - Phổ biến, ổn định cho authentication/user management
--   - Hỗ trợ tốt utf8mb4 (tiếng Việt)
--   - Tích hợp dễ với Django AbstractUser
-- ============================================================
-- (Chạy trên MySQL 8.0)

CREATE DATABASE IF NOT EXISTS userdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE userdb;

-- Table: user
-- Mapping: Class User → Table user
-- Ghi chú: Django AbstractUser tạo thêm các cột: last_login, is_superuser,
--          first_name, last_name, email, is_staff, is_active, date_joined
CREATE TABLE `user` (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    username     VARCHAR(150)  NOT NULL UNIQUE,
    email        VARCHAR(254)  NOT NULL UNIQUE,
    password     VARCHAR(128)  NOT NULL,  -- Django hashed password
    first_name   VARCHAR(150)  DEFAULT '',
    last_name    VARCHAR(150)  DEFAULT '',
    phone        VARCHAR(15)   DEFAULT '',
    address      TEXT          DEFAULT '',
    -- Enum role: RBAC (Role-Based Access Control)
    role         VARCHAR(20)   NOT NULL DEFAULT 'customer'
                               CHECK (role IN ('admin', 'staff', 'customer')),
    is_active    BOOLEAN       DEFAULT TRUE,
    is_staff     BOOLEAN       DEFAULT FALSE,
    is_superuser BOOLEAN       DEFAULT FALSE,
    date_joined  DATETIME      DEFAULT NOW(),
    last_login   DATETIME      NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_user_role ON `user`(role);

-- ============================================================
-- 3. CART SERVICE DATABASE — MySQL (cartdb)
-- Mapping: Class Cart + CartItem → Tables cart + cart_item
-- ============================================================

CREATE DATABASE IF NOT EXISTS cartdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cartdb;

-- Table: cart
-- Mapping: Class Cart → Table cart
-- Tham chiếu logic user_id → user-service (không FK vật lý giữa service)
CREATE TABLE cart (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT       NOT NULL UNIQUE,  -- logical ref to user-service
    created_at DATETIME  DEFAULT NOW(),
    updated_at DATETIME  DEFAULT NOW() ON UPDATE NOW()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table: cart_item
-- Mapping: Class CartItem → Table cart_item
-- Composition: Cart *-- CartItem (Composition, cascade delete)
-- Tham chiếu logic product_id → product-service
CREATE TABLE cart_item (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    cart_id    INT NOT NULL,
    product_id INT NOT NULL,    -- logical ref to product-service
    quantity   INT NOT NULL DEFAULT 1,
    added_at   DATETIME DEFAULT NOW(),
    UNIQUE KEY uq_cart_product (cart_id, product_id),
    FOREIGN KEY (cart_id) REFERENCES cart(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 4. ORDER SERVICE DATABASE — MySQL (orderdb)
-- Mapping: Class Order + OrderItem → Tables orders + order_item
-- ============================================================

CREATE DATABASE IF NOT EXISTS orderdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE orderdb;

-- Table: orders  (không dùng tên 'order' vì là reserved word trong SQL)
-- Mapping: Class Order → Table orders
-- Tham chiếu logic user_id → user-service
CREATE TABLE orders (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT           NOT NULL,  -- logical ref to user-service
    total_price FLOAT         NOT NULL DEFAULT 0,
    status      VARCHAR(50)   NOT NULL DEFAULT 'Pending'
                              CHECK (status IN ('Pending','Processing','Shipped','Delivered','Cancelled')),
    created_at  DATETIME      DEFAULT NOW(),
    updated_at  DATETIME      DEFAULT NOW() ON UPDATE NOW()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_orders_user   ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);

-- Table: order_item
-- Mapping: Class OrderItem → Table order_item
-- Composition: Order *-- OrderItem
-- Tham chiếu logic product_id → product-service
CREATE TABLE order_item (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    order_id   INT   NOT NULL,
    product_id INT   NOT NULL,  -- logical ref to product-service
    quantity   INT   NOT NULL DEFAULT 1,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 5. PAYMENT SERVICE DATABASE — PostgreSQL (paymentdb)
-- Lý do chọn PostgreSQL: nhất quán với product-service,
-- cần lưu trữ giao dịch với độ chính xác cao
-- Tham chiếu logic order_id → order-service
-- ============================================================

-- (Chạy trên PostgreSQL 15)

-- Table: payment
-- Mapping: Class Payment → Table payment
CREATE TABLE payment (
    id         SERIAL PRIMARY KEY,
    order_id   INT           NOT NULL,  -- logical ref to order-service
    amount     FLOAT         NOT NULL,
    status     VARCHAR(50)   NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP     DEFAULT NOW()
);

CREATE INDEX idx_payment_order  ON payment(order_id);
CREATE INDEX idx_payment_status ON payment(status);

-- ============================================================
-- 6. SHIPPING SERVICE DATABASE — MySQL (shippingdb)
-- Tham chiếu logic order_id → order-service
-- ============================================================

CREATE DATABASE IF NOT EXISTS shippingdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE shippingdb;

-- Table: shipment
-- Mapping: Class Shipment → Table shipment
CREATE TABLE shipment (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    order_id   INT           NOT NULL,  -- logical ref to order-service
    address    TEXT          NOT NULL,
    status     VARCHAR(50)   NOT NULL DEFAULT 'Processing'
                             CHECK (status IN ('Processing','Shipped','Delivered','Returned')),
    created_at DATETIME      DEFAULT NOW(),
    updated_at DATETIME      DEFAULT NOW() ON UPDATE NOW()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_shipment_order  ON shipment(order_id);
CREATE INDEX idx_shipment_status ON shipment(status);

-- ============================================================
-- TỔNG KẾT MAPPING CLASS DIAGRAM → DATABASE
-- ============================================================
-- Class          → Table          | Database        | Engine
-- ─────────────────────────────────────────────────────────────
-- Category       → category       | productdb (PG)  | PostgreSQL
-- Product        → product        | productdb (PG)  | PostgreSQL
-- Book           → book           | productdb (PG)  | PostgreSQL
-- Electronics    → electronics    | productdb (PG)  | PostgreSQL
-- Fashion        → fashion        | productdb (PG)  | PostgreSQL
-- User           → user           | userdb    (MY)  | MySQL
-- Cart           → cart           | cartdb    (MY)  | MySQL
-- CartItem       → cart_item      | cartdb    (MY)  | MySQL
-- Order          → orders         | orderdb   (MY)  | MySQL
-- OrderItem      → order_item     | orderdb   (MY)  | MySQL
-- Payment        → payment        | paymentdb (PG)  | PostgreSQL
-- Shipment       → shipment       | shippingdb(MY)  | MySQL
-- ============================================================
