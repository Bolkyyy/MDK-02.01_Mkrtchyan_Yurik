import datetime
import json
import mimetypes
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, unquote, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.realpath(os.path.join(BASE_DIR, "static"))
DB_PATH = os.path.join(BASE_DIR, "shop.db")
DISCOUNT = 0.25
LOW_STOCK = 3
STAFF = ("Менеджер", "Администратор")

mimetypes.add_type("text/html", ".html")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def api_login(query):
    login = query.get("login", [""])[0].strip()
    if not login:
        return 400, {"error": "Не указан логин"}
    conn = db()
    row = conn.execute(
        "SELECT u.id, u.full_name, r.name AS role FROM Users u "
        "JOIN Roles r ON r.id = u.role_id WHERE u.login = ?", (login,)).fetchone()
    conn.close()
    if not row:
        return 404, {"error": "Пользователь с логином «{}» не найден".format(login)}
    return 200, dict(row)

def ordered_last_month(conn):
    first_cur = datetime.date.today().replace(day=1)
    first_prev = (first_cur - datetime.timedelta(days=1)).replace(day=1)
    rows = conn.execute(
        "SELECT DISTINCT oi.product_id FROM OrderItems oi JOIN Orders o ON o.id = oi.order_id "
        "WHERE o.order_date >= ? AND o.order_date < ?", (first_prev.isoformat(), first_cur.isoformat()))
    return {r[0] for r in rows}

def add_price(product, ordered):
    if product["id"] in ordered:
        product["discount"] = 0
        product["price_final"] = product["price"]
    else:
        product["discount"] = int(DISCOUNT * 100)
        product["price_final"] = round(product["price"] * (1 - DISCOUNT), 2)

def api_products(query):
    category = query.get("category", [""])[0].strip()
    search = query.get("search", [""])[0].strip().lower()
    sort = query.get("sort", [""])[0].strip()
    if sort not in ("", "price_asc", "price_desc"):
        return 400, {"error": "Недопустимое значение sort: " + sort}
    sql = ("SELECT p.id, p.name, c.name AS category, m.name AS manufacturer, p.description, "
           "p.price, p.image, "
           "COALESCE((SELECT SUM(s.quantity) FROM Stock s WHERE s.product_id = p.id), 0) AS stock "
           "FROM Products p "
           "JOIN Categories c ON c.id = p.category_id "
           "JOIN Manufacturers m ON m.id = p.manufacturer_id")
    params = []
    if category:
        sql += " WHERE c.name = ?"
        params.append(category)
    conn = db()
    products = [dict(r) for r in conn.execute(sql + " ORDER BY p.id", params)]
    ordered = ordered_last_month(conn)
    conn.close()
    if search:
        products = [p for p in products if search in p["name"].lower()]
    for p in products:
        add_price(p, ordered)
        p["stock_level"] = "мало" if p["stock"] <= LOW_STOCK else "много"
    if sort:
        products.sort(key=lambda p: p["price_final"], reverse=(sort == "price_desc"))
    return 200, products

def check_role(conn, headers, roles):
    login = unquote(headers.get("X-User-Login", "")).strip()
    row = conn.execute(
        "SELECT r.name FROM Users u JOIN Roles r ON r.id = u.role_id WHERE u.login = ?",
        (login,)).fetchone()
    if not row:
        return 401, {"error": "Требуется вход в систему"}
    if row[0] not in roles:
        return 403, {"error": "Недостаточно прав: нужна роль " + " или ".join(roles)}
    return None

def load_order(conn, order_id):
    head = conn.execute(
        "SELECT o.id, o.order_num, o.order_date, u.full_name FROM Orders o "
        "JOIN Users u ON u.id = o.user_id WHERE o.id = ?", (order_id,)).fetchone()
    if not head:
        return None
    order = dict(head)
    order["items"] = [dict(r) for r in conn.execute(
        "SELECT oi.id, p.name AS product, z.value AS size, oi.quantity, oi.unit_price, "
        "oi.quantity * oi.unit_price AS sum FROM OrderItems oi "
        "JOIN Products p ON p.id = oi.product_id "
        "JOIN Sizes z ON z.id = oi.size_id "
        "WHERE oi.order_id = ? ORDER BY oi.id", (order_id,))]
    order["total"] = sum(i["sum"] for i in order["items"])
    return order

def api_orders(headers):
    conn = db()
    try:
        error = check_role(conn, headers, STAFF)
        if error:
            return error
        rows = conn.execute(
            "SELECT o.id, o.order_num, o.order_date, u.full_name FROM Orders o "
            "JOIN Users u ON u.id = o.user_id ORDER BY o.id").fetchall()
        return 200, [dict(r) for r in rows]
    finally:
        conn.close()

def api_order(query, headers):
    conn = db()
    try:
        error = check_role(conn, headers, STAFF)
        if error:
            return error
        try:
            order_id = int(query.get("id", [""])[0])
        except ValueError:
            return 400, {"error": "Параметр id должен быть числом"}
        order = load_order(conn, order_id)
        if not order:
            return 404, {"error": "Заказ id={} не найден".format(order_id)}
        return 200, order
    finally:
        conn.close()

def api_order_update(body, headers):
    conn = db()
    try:
        error = check_role(conn, headers, ("Администратор",))
        if error:
            return error
        try:
            order_id = int(body.get("id"))
        except (TypeError, ValueError):
            return 400, {"error": "Не указан id заказа"}
        if not load_order(conn, order_id):
            return 404, {"error": "Заказ id={} не найден".format(order_id)}
        new_date = str(body.get("order_date") or "").strip()
        if new_date:
            try:
                new_date = datetime.date.fromisoformat(new_date).isoformat()
            except ValueError:
                return 400, {"error": "Дата должна быть в формате ГГГГ-ММ-ДД"}
            conn.execute("UPDATE Orders SET order_date = ? WHERE id = ?", (new_date, order_id))
        for item_id in body.get("delete_items") or []:
            row = conn.execute(
                "SELECT product_id, size_id, quantity FROM OrderItems WHERE id = ? AND order_id = ?",
                (item_id, order_id)).fetchone()
            if not row:
                return 404, {"error": "Позиция id={} не найдена в заказе".format(item_id)}
            conn.execute(
                "INSERT INTO Stock(product_id, size_id, quantity) VALUES (?, ?, ?) "
                "ON CONFLICT(product_id, size_id) DO UPDATE SET quantity = quantity + excluded.quantity",
                (row["product_id"], row["size_id"], row["quantity"]))
            conn.execute("DELETE FROM OrderItems WHERE id = ?", (item_id,))
        conn.commit()
        return 200, load_order(conn, order_id)
    finally:
        conn.close()

def api_users(headers):
    conn = db()
    try:
        error = check_role(conn, headers, STAFF)
        if error:
            return error
        rows = conn.execute(
            "SELECT u.id, u.full_name, r.name AS role FROM Users u "
            "JOIN Roles r ON r.id = u.role_id ORDER BY u.full_name").fetchall()
        return 200, [dict(r) for r in rows]
    finally:
        conn.close()

def api_product(query):
    try:
        product_id = int(query.get("id", [""])[0])
    except ValueError:
        return 400, {"error": "Параметр id должен быть числом"}
    conn = db()
    try:
        row = conn.execute("SELECT id, name, price FROM Products WHERE id = ?", (product_id,)).fetchone()
        if not row:
            return 404, {"error": "Товар id={} не найден".format(product_id)}
        product = dict(row)
        add_price(product, ordered_last_month(conn))
        product["sizes"] = [dict(r) for r in conn.execute(
            "SELECT s.size_id, z.value AS size, s.quantity FROM Stock s "
            "JOIN Sizes z ON z.id = s.size_id "
            "WHERE s.product_id = ? AND s.quantity > 0 ORDER BY z.value", (product_id,))]
        return 200, product
    finally:
        conn.close()

def api_order_create(body, headers):
    conn = db()
    try:
        error = check_role(conn, headers, STAFF)
        if error:
            return error
        try:
            user_id = int(body.get("user_id"))
            items = [(int(i["product_id"]), int(i["size_id"]), int(i["quantity"]))
                     for i in body.get("items") or []]
        except (TypeError, ValueError, KeyError):
            return 400, {"error": "Неверные данные заказа"}
        if not items:
            return 400, {"error": "В заказе нет позиций"}
        if not conn.execute("SELECT 1 FROM Users WHERE id = ?", (user_id,)).fetchone():
            return 404, {"error": "Клиент id={} не найден".format(user_id)}
        ordered = ordered_last_month(conn)
        prices = []
        for product_id, size_id, quantity in items:
            if quantity <= 0:
                return 400, {"error": "Количество должно быть больше нуля"}
            row = conn.execute(
                "SELECT p.id, p.name, p.price, s.quantity FROM Stock s "
                "JOIN Products p ON p.id = s.product_id "
                "WHERE s.product_id = ? AND s.size_id = ?", (product_id, size_id)).fetchone()
            if not row:
                return 404, {"error": "Товара id={} нужного размера нет на складе".format(product_id)}
            if row["quantity"] < quantity:
                return 409, {"error": "Недостаточно товара «{}»: на складе {} шт.".format(
                    row["name"], row["quantity"])}
            product = dict(row)
            add_price(product, ordered)
            prices.append(product["price_final"])
        last = conn.execute("SELECT MAX(CAST(order_num AS INTEGER)) FROM Orders").fetchone()[0] or 0
        cur = conn.execute(
            "INSERT INTO Orders(order_num, order_date, user_id) VALUES (?, ?, ?)",
            (str(last + 1), datetime.date.today().isoformat(), user_id))
        order_id = cur.lastrowid
        for (product_id, size_id, quantity), price in zip(items, prices):
            conn.execute(
                "INSERT INTO OrderItems(order_id, product_id, size_id, quantity, unit_price) "
                "VALUES (?, ?, ?, ?, ?)", (order_id, product_id, size_id, quantity, price))
            conn.execute(
                "UPDATE Stock SET quantity = quantity - ? WHERE product_id = ? AND size_id = ?",
                (quantity, product_id, size_id))
        conn.commit()
        return 200, load_order(conn, order_id)
    finally:
        conn.close()

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == "/api/login":
            self.send_json(*api_login(query))
        elif url.path == "/api/products":
            self.send_json(*api_products(query))
        elif url.path == "/api/orders":
            self.send_json(*api_orders(self.headers))
        elif url.path == "/api/order":
            self.send_json(*api_order(query, self.headers))
        elif url.path == "/api/users":
            self.send_json(*api_users(self.headers))
        elif url.path == "/api/product":
            self.send_json(*api_product(query))
        else:
            self.send_static(url.path)

    def send_static(self, path):
        if path == "/":
            path = "/index.html"
        file_path = os.path.realpath(os.path.join(STATIC_DIR, path.lstrip("/")))
        if not file_path.startswith(STATIC_DIR + os.sep) or not os.path.isfile(file_path):
            self.send_json(404, {"error": "Файл не найден: " + path})
            return
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type += "; charset=utf-8"
        with open(file_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/echo", "/api/order/update", "/api/order/create"):
            self.send_json(404, {"error": "Неизвестный метод API: " + path})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            self.send_json(400, {"error": "Некорректный JSON"})
            return
        if path == "/api/echo":
            self.send_json(200, {"received": data})
        elif not isinstance(data, dict):
            self.send_json(400, {"error": "Ожидается JSON-объект"})
        elif path == "/api/order/update":
            self.send_json(*api_order_update(data, self.headers))
        elif path == "/api/order/create":
            self.send_json(*api_order_create(data, self.headers))

if __name__ == "__main__":
    HTTPServer.allow_reuse_address = False
    server = HTTPServer(("127.0.0.1", 8000), Handler)
    print("Сервер запущен: http://localhost:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Сервер остановлен")
    server.server_close()