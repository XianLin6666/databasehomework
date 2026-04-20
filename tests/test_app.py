import unittest
import sqlite3

import app as market_app


class MarketAppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.db_uri = "file:market_test?mode=memory&cache=shared"
        self.keepalive = sqlite3.connect(self.db_uri, uri=True)
        market_app.app.config.update(TESTING=True)
        market_app.app.config["DATABASE"] = self.db_uri

        with market_app.app.app_context():
            market_app.init_db()

        self.client = market_app.app.test_client()

    def tearDown(self) -> None:
        self.keepalive.close()
        market_app.app.config.pop("DATABASE", None)

    def login_admin(self) -> None:
        self.client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )

    def test_viewer_cannot_write_items(self) -> None:
        response = self.client.post(
            "/items",
            data={
                "action": "add_item",
                "item_name": "TestBook",
                "category": "Book",
                "price": "12",
                "seller_id": "u001",
            },
            follow_redirects=True,
        )
        self.assertIn("写操作已禁止".encode("utf-8"), response.data)

    def test_admin_can_add_item(self) -> None:
        self.login_admin()
        self.client.post(
            "/items",
            data={
                "action": "add_item",
                "item_name": "TestBook",
                "category": "Book",
                "price": "12",
                "seller_id": "u001",
            },
            follow_redirects=True,
        )

        with market_app.app.app_context():
            row = market_app.safe_exec("SELECT COUNT(*) AS c FROM item WHERE item_name='TestBook'")[0]
            self.assertEqual(row["c"], 1)

    def test_cannot_purchase_own_item_in_app_layer(self) -> None:
        self.login_admin()
        response = self.client.post(
            "/items",
            data={"action": "purchase", "buyer_id": "u001", "item_id": "i001"},
            follow_redirects=True,
        )
        self.assertIn("不能购买自己发布的商品".encode("utf-8"), response.data)

    def test_cannot_purchase_own_item_in_db_layer(self) -> None:
        conn = sqlite3.connect(self.db_uri, uri=True)
        conn.execute("PRAGMA foreign_keys = ON;")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO orders(order_id, item_id, buyer_id, order_date) VALUES (?, ?, ?, ?)",
                ("o999", "i001", "u001", "2026-04-16"),
            )
        conn.close()

    def test_cannot_delete_sold_item(self) -> None:
        self.login_admin()
        response = self.client.post(
            "/items",
            data={"action": "delete_unsold", "item_id": "i002"},
            follow_redirects=True,
        )
        self.assertIn("只能删除未售出的商品".encode("utf-8"), response.data)

    def test_reset_db_requires_admin(self) -> None:
        response = self.client.post("/admin/reset-db", follow_redirects=True)
        self.assertIn("需要管理员权限".encode("utf-8"), response.data)


if __name__ == "__main__":
    unittest.main()
