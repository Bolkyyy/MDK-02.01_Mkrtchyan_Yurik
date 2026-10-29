-- Active: 1793296056299@@127.0.0.1@3306
PRAGMA foreign_keys = ON;

CREATE TABLE Roles (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT    NOT NULL UNIQUE
          CHECK (name IN ('Клиент', 'Менеджер', 'Администратор'))
);

CREATE TABLE Users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name  TEXT    NOT NULL,
    login      TEXT    NOT NULL UNIQUE,
    role_id    INTEGER NOT NULL,
    FOREIGN KEY (role_id) REFERENCES Roles(id) ON DELETE RESTRICT
);

CREATE TABLE Categories (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT    NOT NULL UNIQUE
);

CREATE TABLE Manufacturers (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT    NOT NULL UNIQUE
);

CREATE TABLE Sizes (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    value  REAL    NOT NULL UNIQUE CHECK (value BETWEEN 15 AND 50)
);

CREATE TABLE Products (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    category_id      INTEGER NOT NULL,
    manufacturer_id  INTEGER NOT NULL,
    description      TEXT,
    price            REAL    NOT NULL CHECK (price > 0),
    image            TEXT,
    UNIQUE (name, manufacturer_id),
    FOREIGN KEY (category_id)     REFERENCES Categories(id)    ON DELETE RESTRICT,
    FOREIGN KEY (manufacturer_id) REFERENCES Manufacturers(id) ON DELETE RESTRICT
);

CREATE TABLE Stock (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL,
    size_id     INTEGER NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    UNIQUE (product_id, size_id),
    FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE,
    FOREIGN KEY (size_id)    REFERENCES Sizes(id)    ON DELETE RESTRICT
);

CREATE TABLE Orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_num   TEXT    NOT NULL UNIQUE,
    order_date  TEXT    NOT NULL CHECK (date(order_date) IS NOT NULL),
    user_id     INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE RESTRICT
);

CREATE TABLE OrderItems (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL,
    product_id  INTEGER NOT NULL,
    size_id     INTEGER NOT NULL,
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  REAL    NOT NULL CHECK (unit_price >= 0),
    FOREIGN KEY (order_id)   REFERENCES Orders(id)   ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE RESTRICT,
    FOREIGN KEY (size_id)    REFERENCES Sizes(id)    ON DELETE RESTRICT
);

CREATE INDEX idx_products_category     ON Products(category_id);
CREATE INDEX idx_products_manufacturer ON Products(manufacturer_id);
CREATE INDEX idx_products_name         ON Products(name);
CREATE INDEX idx_stock_product         ON Stock(product_id);
CREATE INDEX idx_orders_date           ON Orders(order_date);
CREATE INDEX idx_orders_user           ON Orders(user_id);
CREATE INDEX idx_orderitems_order      ON OrderItems(order_id);
CREATE INDEX idx_orderitems_product    ON OrderItems(product_id);
