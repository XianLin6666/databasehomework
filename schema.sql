PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS sold_items_view;
DROP VIEW IF EXISTS unsold_items_view;
DROP TRIGGER IF EXISTS trg_orders_check_item;
DROP TRIGGER IF EXISTS trg_orders_set_item_sold;
DROP TRIGGER IF EXISTS trg_item_prevent_reset_status;
DROP TRIGGER IF EXISTS trg_item_prevent_delete_sold;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS item;
DROP TABLE IF EXISTS user;

CREATE TABLE user (
    user_id TEXT PRIMARY KEY,
    user_name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE
);

CREATE TABLE item (
    item_id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL CHECK (price > 0),
    status INTEGER NOT NULL CHECK (status IN (0, 1)),
    seller_id TEXT NOT NULL,
    FOREIGN KEY (seller_id) REFERENCES user(user_id)
);

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL UNIQUE,
    buyer_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES item(item_id),
    FOREIGN KEY (buyer_id) REFERENCES user(user_id)
);

CREATE TRIGGER trg_orders_check_item
BEFORE INSERT ON orders
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NOT EXISTS (SELECT 1 FROM item WHERE item_id = NEW.item_id) THEN
            RAISE(ABORT, '商品不存在')
        WHEN NEW.buyer_id = (SELECT seller_id FROM item WHERE item_id = NEW.item_id) THEN
            RAISE(ABORT, '买家不能购买自己发布的商品')
        WHEN EXISTS (SELECT 1 FROM orders WHERE item_id = NEW.item_id) THEN
            RAISE(ABORT, '每个商品只能交易一次')
        WHEN (SELECT status FROM item WHERE item_id = NEW.item_id) = 1 THEN
            RAISE(ABORT, '已售商品不能再次购买')
    END;
END;

CREATE TRIGGER trg_orders_set_item_sold
AFTER INSERT ON orders
FOR EACH ROW
BEGIN
    UPDATE item SET status = 1 WHERE item_id = NEW.item_id;
END;

CREATE TRIGGER trg_item_prevent_reset_status
BEFORE UPDATE OF status ON item
FOR EACH ROW
WHEN NEW.status = 0 AND EXISTS (SELECT 1 FROM orders WHERE item_id = NEW.item_id)
BEGIN
    SELECT RAISE(ABORT, '已成交商品状态不能改回未售出');
END;

CREATE TRIGGER trg_item_prevent_delete_sold
BEFORE DELETE ON item
FOR EACH ROW
WHEN EXISTS (SELECT 1 FROM orders WHERE item_id = OLD.item_id)
BEGIN
    SELECT RAISE(ABORT, '已成交商品不能删除');
END;

CREATE VIEW sold_items_view AS
SELECT i.item_id, i.item_name, o.buyer_id
FROM item i
JOIN orders o ON o.item_id = i.item_id;

CREATE VIEW unsold_items_view AS
SELECT item_id, item_name, category, price, seller_id
FROM item
WHERE status = 0;
