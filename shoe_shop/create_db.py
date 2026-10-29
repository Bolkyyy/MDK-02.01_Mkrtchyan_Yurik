import logging
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
DEFAULT_DB = os.path.join(BASE_DIR, "shop.db")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(BASE_DIR, "create_db.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger("create_db")



def create_database(db_path):
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError("Нет файла сземы: " + SCHEMA_PATH)

    with open(SCHEMA_PATH, encoding="utf-8") as f:
        script = f.read()
    log.info("Прочитан скрипт схемы: %s (%d байт)", SCHEMA_PATH, len(script))

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(script)
        conn.commit()
        log.info("Скрипт выполнен, БД: %s", db_path)

        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        indexes = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'index' AND name LIKE 'idx_%' ORDER BY name")]
        fk_on = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        return tables, indexes, fk_on
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()



def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    log.info("Начинаем создание БД")
    try:
        tables, indexes, fk_on = create_database(db_path)
    except (sqlite3.Error, OSError) as e:
        log.error("Ошибка: %s", e)
        return 1

    expected = {"Roles", "Users", "Categories", "Manufacturers", "Sizes",
                "Products", "Stock", "Orders", "OrderItems"}
    log.info("Создано таблиц: %d (%s)", len(tables), ", ".join(tables))
    log.info("Создано индексов: %d", len(indexes))
    log.info("Внешние ключи: %s", "включены" if fk_on else "выключены")

    missing = expected - set(tables)
    if missing:
        log.error("Не хватает таблиц: %s", ", ".join(sorted(missing)))
        return 1
    log.info("Все %d таблиц на местн", len(expected))
    return 0


if __name__ == "__main__":
    sys.exit(main())

