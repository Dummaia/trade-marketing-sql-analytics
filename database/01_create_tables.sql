-- Execute em um banco vazio. Falha sem alterar tabelas existentes.
BEGIN;
CREATE TABLE clients (
    client_id BIGSERIAL PRIMARY KEY,
    client_name VARCHAR(120) NOT NULL,
    segment VARCHAR(80),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
);

CREATE TABLE brands (
    brand_id BIGSERIAL PRIMARY KEY,
    client_id BIGINT NOT NULL,
    brand_name VARCHAR(120) NOT NULL,

    FOREIGN KEY (client_id)
        REFERENCES clients(client_id)
);

CREATE TABLE products (

    product_id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    category VARCHAR(100),
    sku VARCHAR(50),
    cost_price NUMERIC(10,2),
    sale_price NUMERIC(10,2),

    FOREIGN KEY (brand_id)
        REFERENCES brands(brand_id) 
);

CREATE TABLE retailers (
    retailer_id BIGSERIAL PRIMARY KEY,
    retailer_name VARCHAR(120) NOT NULL,
    channel VARCHAR(80)
);

CREATE TABLE stores (
    store_id BIGSERIAL PRIMARY KEY,
    retailer_id BIGINT NOT NULL,
    store_name VARCHAR(150) NOT NULL,
    city VARCHAR(100),
    state CHAR(2),

    FOREIGN KEY (retailer_id)
        REFERENCES retailers(retailer_id)
);

CREATE TABLE sell_out (
    sell_out_id BIGSERIAL PRIMARY KEY,
    sale_date DATE NOT NULL,
    store_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),

    FOREIGN KEY (store_id)
        REFERENCES stores(store_id),

    FOREIGN KEY (product_id)
        REFERENCES products(product_id)
);

COMMIT;
