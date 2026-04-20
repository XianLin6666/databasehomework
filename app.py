import sqlite3
import os
from functools import wraps
from datetime import date
from pathlib import Path
from typing import Any, Callable

from flask import Flask, flash, g, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "campus_market.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "database-homework-secret")

DEMO_ACCOUNTS = {
    "admin": {
        "password": "admin123",
        "role": "admin",
        "display_name": "管理员",
    },
    "viewer": {
        "password": "viewer123",
        "role": "viewer",
        "display_name": "普通用户",
    },
}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        database = app.config.get("DATABASE", str(DB_PATH))
        use_uri = isinstance(database, str) and database.startswith("file:")
        conn = sqlite3.connect(database, uri=use_uri)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    database = app.config.get("DATABASE", str(DB_PATH))
    use_uri = isinstance(database, str) and database.startswith("file:")
    conn = sqlite3.connect(database, uri=use_uri)
    try:
        conn.executescript((BASE_DIR / "schema.sql").read_text(encoding="utf-8"))
        conn.executescript((BASE_DIR / "seed.sql").read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def generate_next_id(prefix: str, table: str, id_col: str) -> str:
    db = get_db()
    row = db.execute(
        f"SELECT {id_col} FROM {table} WHERE {id_col} LIKE ? ORDER BY {id_col} DESC LIMIT 1",
        (f"{prefix}%",),
    ).fetchone()
    if not row:
        return f"{prefix}001"
    current = row[id_col]
    num = int(current[1:]) + 1
    return f"{prefix}{num:03d}"


def safe_exec(query: str, params: tuple[Any, ...] = ()):
    return get_db().execute(query, params).fetchall()


def get_current_user() -> dict[str, str] | None:
    username = session.get("username")
    role = session.get("role")
    if not username or not role:
        return None
    account = DEMO_ACCOUNTS.get(username)
    if not account:
        return None
    return {
        "username": username,
        "role": role,
        "display_name": account["display_name"],
    }


def is_admin() -> bool:
    user = get_current_user()
    return bool(user and user["role"] == "admin")


def admin_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any):
        if not is_admin():
            flash("需要管理员权限才能执行该操作")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_auth_info() -> dict[str, Any]:
    return {
        "current_user": get_current_user(),
        "is_admin": is_admin(),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        account = DEMO_ACCOUNTS.get(username)

        if not account or account["password"] != password:
            flash("登录失败：用户名或密码错误")
            return redirect(url_for("login"))

        session["username"] = username
        session["role"] = account["role"]
        flash(f"登录成功：{account['display_name']}")
        next_url = request.args.get("next", "").strip()
        if next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("你已退出登录")
    return redirect(url_for("home"))


@app.route("/")
def home():
    stats = {
        "item_total": safe_exec("SELECT COUNT(*) AS c FROM item")[0]["c"],
        "order_total": safe_exec("SELECT COUNT(*) AS c FROM orders")[0]["c"],
        "unsold_total": safe_exec("SELECT COUNT(*) AS c FROM item WHERE status=0")[0]["c"],
        "avg_price": safe_exec("SELECT ROUND(COALESCE(AVG(price), 0), 2) AS a FROM item")[0]["a"],
    }
    return render_template("home.html", stats=stats)


@app.route("/users")
def users_page():
    users = safe_exec("SELECT * FROM user ORDER BY user_id")
    return render_template("users.html", users=users)


@app.route("/items", methods=["GET", "POST"])
def items_page():
    db = get_db()
    if request.method == "POST":
        if not is_admin():
            flash("写操作已禁止：请使用管理员账号登录")
            return redirect(url_for("login", next=url_for("items_page")))

        action = request.form.get("action", "")
        try:
            if action == "add_item":
                item_id = generate_next_id("i", "item", "item_id")
                db.execute(
                    """
                    INSERT INTO item (item_id, item_name, category, price, status, seller_id)
                    VALUES (?, ?, ?, ?, 0, ?)
                    """,
                    (
                        item_id,
                        request.form["item_name"].strip(),
                        request.form["category"].strip(),
                        float(request.form["price"]),
                        request.form["seller_id"].strip(),
                    ),
                )
                db.commit()
                flash(f"新增商品成功：{item_id}")

            elif action == "update_price":
                result = db.execute(
                    "UPDATE item SET price = ? WHERE item_id = ?",
                    (float(request.form["new_price"]), request.form["item_id"].strip()),
                )
                if result.rowcount == 0:
                    raise ValueError("商品不存在")
                db.commit()
                flash("商品价格修改成功")

            elif action == "delete_unsold":
                item_id = request.form["item_id"].strip()
                row = db.execute("SELECT status FROM item WHERE item_id=?", (item_id,)).fetchone()
                if not row:
                    raise ValueError("商品不存在")
                if row["status"] == 1:
                    raise ValueError("只能删除未售出的商品")
                db.execute("DELETE FROM item WHERE item_id=?", (item_id,))
                db.commit()
                flash("删除未售商品成功")

            elif action == "purchase":
                buyer_id = request.form["buyer_id"].strip()
                item_id = request.form["item_id"].strip()
                purchase_item(buyer_id, item_id)
                flash("购买成功，订单与商品状态已自动更新")

            else:
                raise ValueError("未知操作类型")

        except ValueError as exc:
            db.rollback()
            flash(f"操作失败：{exc}")
        except sqlite3.IntegrityError as exc:
            db.rollback()
            flash(f"操作失败（约束冲突）：{exc}")
        except sqlite3.DatabaseError as exc:
            db.rollback()
            flash(f"操作失败（数据库错误）：{exc}")
        except Exception:
            db.rollback()
            flash("操作失败：发生了未预期错误，请稍后重试")

        return redirect(url_for("items_page"))

    items = safe_exec(
        """
        SELECT i.*, u.user_name AS seller_name
        FROM item i JOIN user u ON i.seller_id = u.user_id
        ORDER BY i.item_id
        """
    )
    users = safe_exec("SELECT * FROM user ORDER BY user_id")
    return render_template("items.html", items=items, users=users)


def purchase_item(buyer_id: str, item_id: str) -> None:
    db = get_db()
    db.execute("BEGIN IMMEDIATE")

    item = db.execute(
        "SELECT item_id, seller_id, status FROM item WHERE item_id = ?",
        (item_id,),
    ).fetchone()
    if not item:
        raise ValueError("商品不存在")
    if item["status"] == 1:
        raise ValueError("该商品已售出，不能重复购买")
    if item["seller_id"] == buyer_id:
        raise ValueError("不能购买自己发布的商品")

    buyer = db.execute("SELECT 1 FROM user WHERE user_id=?", (buyer_id,)).fetchone()
    if not buyer:
        raise ValueError("买家不存在")

    existing = db.execute("SELECT 1 FROM orders WHERE item_id=?", (item_id,)).fetchone()
    if existing:
        raise ValueError("该商品已有订单")

    order_id = generate_next_id("o", "orders", "order_id")
    db.execute(
        "INSERT INTO orders(order_id, item_id, buyer_id, order_date) VALUES (?, ?, ?, ?)",
        (order_id, item_id, buyer_id, date.today().isoformat()),
    )
    db.commit()


@app.route("/orders")
def orders_page():
    orders = safe_exec(
        """
        SELECT o.order_id, o.item_id, i.item_name, o.buyer_id, u.user_name AS buyer_name, o.order_date
        FROM orders o
        JOIN item i ON i.item_id = o.item_id
        JOIN user u ON u.user_id = o.buyer_id
        ORDER BY o.order_id
        """
    )
    return render_template("orders.html", orders=orders)


@app.route("/queries")
def queries_page():
    users = safe_exec("SELECT user_id, user_name FROM user ORDER BY user_id")
    categories = safe_exec("SELECT DISTINCT category FROM item ORDER BY category")

    try:
        price_threshold = float(request.args.get("price_gt", "30"))
    except ValueError:
        price_threshold = 30.0
    if price_threshold < 0:
        price_threshold = 30.0

    category_default = "DailyGoods"
    category = request.args.get("category", category_default).strip()
    available_categories = [r["category"] for r in categories]
    if not category or category not in available_categories:
        category = category_default if category_default in available_categories else (
            available_categories[0] if available_categories else ""
        )

    seller_id = request.args.get("seller_id", "u001").strip()
    user_ids = [u["user_id"] for u in users]
    if seller_id not in user_ids:
        seller_id = "u001" if "u001" in user_ids else (user_ids[0] if user_ids else "")

    basic = {
        "unsold_items": safe_exec("SELECT * FROM item WHERE status = 0 ORDER BY item_id"),
        "price_dynamic": safe_exec(
            "SELECT * FROM item WHERE price > ? ORDER BY item_id",
            (price_threshold,),
        ),
        "category_dynamic": safe_exec(
            "SELECT * FROM item WHERE category = ? ORDER BY item_id",
            (category,),
        ),
        "seller_dynamic": safe_exec(
            "SELECT * FROM item WHERE seller_id = ? ORDER BY item_id",
            (seller_id,),
        ),
    }

    joins = {
        "sold_with_buyer": safe_exec(
            """
            SELECT i.item_id, i.item_name, o.buyer_id, u.user_name AS buyer_name
            FROM item i
            JOIN orders o ON i.item_id = o.item_id
            JOIN user u ON u.user_id = o.buyer_id
            ORDER BY i.item_id
            """
        ),
        "order_detail": safe_exec(
            """
            SELECT o.order_id, i.item_name, u.user_name AS buyer_name, o.order_date
            FROM orders o
            JOIN item i ON i.item_id = o.item_id
            JOIN user u ON u.user_id = o.buyer_id
            ORDER BY o.order_id
            """
        ),
        "u001_items_purchased": safe_exec(
            """
            SELECT i.item_id, i.item_name,
                   CASE WHEN o.order_id IS NULL THEN '未购买' ELSE '已购买' END AS purchase_status
            FROM item i
            LEFT JOIN orders o ON o.item_id = i.item_id
            WHERE i.seller_id = 'u001'
            ORDER BY i.item_id
            """
        ),
    }

    aggs = {
        "item_total": safe_exec("SELECT COUNT(*) AS total_items FROM item"),
        "category_count": safe_exec(
            "SELECT category, COUNT(*) AS category_total FROM item GROUP BY category ORDER BY category"
        ),
        "avg_price": safe_exec("SELECT ROUND(AVG(price), 2) AS avg_price FROM item"),
        "top_seller": safe_exec(
            """
            WITH seller_counts AS (
                SELECT u.user_id, u.user_name, COUNT(i.item_id) AS item_count
                FROM user u
                JOIN item i ON i.seller_id = u.user_id
                GROUP BY u.user_id, u.user_name
            )
            SELECT user_id, user_name, item_count
            FROM seller_counts
            WHERE item_count = (SELECT MAX(item_count) FROM seller_counts)
            ORDER BY user_id
            """
        ),
    }

    views = {
        "sold_view": safe_exec("SELECT * FROM sold_items_view ORDER BY item_id"),
        "unsold_view": safe_exec("SELECT * FROM unsold_items_view ORDER BY item_id"),
    }

    sold_count = safe_exec("SELECT COUNT(*) AS c FROM item WHERE status = 1")[0]["c"]
    unsold_count = safe_exec("SELECT COUNT(*) AS c FROM item WHERE status = 0")[0]["c"]

    chart_data = {
        "category_labels": [row["category"] for row in aggs["category_count"]],
        "category_counts": [row["category_total"] for row in aggs["category_count"]],
        "price_labels": [row["item_name"] for row in safe_exec("SELECT item_name FROM item ORDER BY item_id")],
        "price_values": [row["price"] for row in safe_exec("SELECT price FROM item ORDER BY item_id")],
        "status_labels": ["已售出", "未售出"],
        "status_values": [sold_count, unsold_count],
    }

    filters = {
        "price_threshold": price_threshold,
        "category": category,
        "seller_id": seller_id,
        "categories": available_categories,
        "users": users,
    }

    context = {
        "basic": basic,
        "joins": joins,
        "aggs": aggs,
        "views": views,
        "chart_data": chart_data,
        "filters": filters,
    }
    if request.args.get("partial") == "1":
        return render_template("_queries_content.html", **context)
    return render_template("queries.html", **context)


@app.route("/admin/reset-db", methods=["POST"])
@admin_required
def reset_db():
    init_db()
    flash("数据库已重建并恢复初始数据")
    return redirect(url_for("home"))


if __name__ == "__main__":
    if not DB_PATH.exists():
        init_db()
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
