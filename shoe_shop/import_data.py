import datetime
import logging
import os
import sqlite3
import sys
from read_excel import read_xlsx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMPORTS_DIR = os.path.join(BASE_DIR, "..", "imports")
DB_PATH = os.path.join(BASE_DIR, "shop.db")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",datefmt="%H:%M:%S")
log = logging.getLogger("import")

ROLES = {"Авторизованный пользователь": "Клиент"}


def load(name):
    rows = read_xlsx(os.path.join(IMPORTS_DIR, name))
    log.info("%-24s %3d строк", name, len(rows) - 1)
    return rows[1:]


def clean(text):
    return " ".join(str(text).replace("\xa0", " ").split())


def excel_date(value):
    return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(value)))).isoformat()


def get_or_create(cur, table, name):
    cur.execute("INSERT OR IGNORE INTO {}(name) VALUES (?)".format(table), (name,))
    return cur.execute("SELECT id FROM {} WHERE name = ?".format(table), (name,)).fetchone()[0]


def import_users(cur):
    for last, first, middle, login, role in load("Users_import.xlsx"):
        role_id = get_or_create(cur, "Roles", ROLES.get(clean(role), clean(role)))
        full_name = " ".join([clean(last), clean(first), clean(middle)])
        cur.execute("INSERT OR IGNORE INTO Users(full_name, login, role_id) VALUES (?,?,?)",(full_name, clean(login), role_id))


def import_sizes(cur):
    for (value,) in load("Sizes_import.xlsx"):
        cur.execute("INSERT OR IGNORE INTO Sizes(value) VALUES (?)", (float(value),))


def import_products(cur):
    for category, _subcat, image, name, manufacturer, description, _sostav, price in load("Products_import.xlsx"):
        cur.execute(
            "INSERT INTO Products(name, category_id, manufacturer_id, description, price, image) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(name, manufacturer_id) "
            "DO UPDATE SET price = excluded.price, image = excluded.image",
            (clean(name), get_or_create(cur, "Categories", clean(category)),
             get_or_create(cur, "Manufacturers", clean(manufacturer)),
             clean(description), float(price), "uploads/" + clean(image)))


def find_product(cur, name, manufacturer):
    name, manufacturer = clean(name), clean(manufacturer)
    rows = cur.execute("SELECT p.id, p.name FROM Products p JOIN Manufacturers m "
                       "ON m.id = p.manufacturer_id WHERE m.name = ?", (manufacturer,)).fetchall()
    for pid, p_name in rows:
        if p_name == name:
            return pid
    for pid, p_name in rows:
        if p_name.startswith(name + " "):
            return pid
    return None


def size_id(cur, value):
    row = cur.execute("SELECT id FROM Sizes WHERE value = ?", (float(value),)).fetchone()
    return row[0] if row else None


def import_stock(cur):
    for name, manufacturer, size, qty in load("Stock_Items_import.xlsx"):
        pid, sid = find_product(cur, name, manufacturer), size_id(cur, size)
        if not pid or not sid:
            log.warning("Склад: пропущена строка «%s» (%s) р. %s", name, manufacturer, size)
            continue
        cur.execute("INSERT INTO Stock(product_id, size_id, quantity) VALUES (?,?,?) "
                    "ON CONFLICT(product_id, size_id) DO UPDATE SET quantity = excluded.quantity",
                    (pid, sid, int(float(qty))))


def import_orders(cur):
    order_ids = {}
    for num, date, fio, _cat, name, manufacturer, size, qty, price in load("Orders_import.xlsx"):
        user = cur.execute("SELECT id FROM Users WHERE full_name = ?", (clean(fio),)).fetchone()
        pid, sid = find_product(cur, name, manufacturer), size_id(cur, size)
        if not user or not pid or not sid:
            log.warning("Заказ %s: пропущена строка «%s» (%s)", num, name, fio)
            continue
        num = clean(num)
        if num not in order_ids:
            cur.execute("INSERT INTO Orders(order_num, order_date, user_id) VALUES (?,?,?)",
                        (num, excel_date(date), user[0]))
            order_ids[num] = cur.lastrowid
        cur.execute("INSERT INTO OrderItems(order_id, product_id, size_id, quantity, unit_price) "
                    "VALUES (?,?,?,?,?)", (order_ids[num], pid, sid, int(float(qty)), float(price)))


def main():
    if not os.path.exists(DB_PATH):
        log.error("Нет файла shop.db — сначала выполните python create_db.py")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    try:
        import_users(cur)
        import_sizes(cur)
        import_products(cur)
        import_stock(cur)
        import_orders(cur)
        conn.commit()
    except (sqlite3.Error, OSError, ValueError, KeyError) as e:
        conn.rollback()
        log.error("Ошибка импорта: %s", e)
        return 1
    finally:
        for t in ("Roles", "Users", "Categories", "Manufacturers", "Sizes",
                  "Products", "Stock", "Orders", "OrderItems"):
            log.info("%-14s %3d записей", t, conn.execute("SELECT COUNT(*) FROM " + t).fetchone()[0])
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())