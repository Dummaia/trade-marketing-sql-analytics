\set ON_ERROR_STOP on
BEGIN;
-- A carga exige tabelas vazias; erros revertem a transação inteira.
\copy clients (client_id,client_name,segment) FROM 'data/raw/clients.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
SELECT setval(pg_get_serial_sequence('clients', 'client_id'), (SELECT MAX(client_id) FROM clients));
\copy brands (brand_id,client_id,brand_name) FROM 'data/raw/brands.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
SELECT setval(pg_get_serial_sequence('brands', 'brand_id'), (SELECT MAX(brand_id) FROM brands));
\copy products (product_id,brand_id,product_name,category,sku,cost_price,sale_price) FROM 'data/raw/products.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
SELECT setval(pg_get_serial_sequence('products', 'product_id'), (SELECT MAX(product_id) FROM products));
\copy retailers (retailer_id,retailer_name,channel) FROM 'data/raw/retailers.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
SELECT setval(pg_get_serial_sequence('retailers', 'retailer_id'), (SELECT MAX(retailer_id) FROM retailers));
\copy stores (store_id,retailer_id,store_name,city,state) FROM 'data/raw/stores.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
SELECT setval(pg_get_serial_sequence('stores', 'store_id'), (SELECT MAX(store_id) FROM stores));
\copy sell_out (sale_date,store_id,product_id,quantity,unit_price) FROM 'data/raw/sell_out.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')
COMMIT;
ANALYZE;
