import os
import re
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def split_queries(text):
    parts = re.split(r"^-- (\d+\. .+)$", text, flags=re.M)
    return [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def print_table(headers, rows):
    cells = [[("" if v is None else str(v)) for v in r] for r in rows]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(headers)]
    line = "-+-".join("-" * w for w in widths)
    print(" | ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print(line)
    for r in cells:
        print(" | ".join(v.ljust(w) for v, w in zip(r, widths)))
    print("({} строк)\n".format(len(rows)))


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE_DIR, "shop.db")
    with open(os.path.join(BASE_DIR, "queries.sql"), encoding="utf-8") as f:
        queries = split_queries(f.read())
    conn = sqlite3.connect(db)
    try:
        for title, sql in queries:
            print("=== " + title)
            cur = conn.execute(sql)
            print_table([d[0] for d in cur.description], cur.fetchall())
    except sqlite3.Error as e:
        print("Ошибка SQL:", e)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())