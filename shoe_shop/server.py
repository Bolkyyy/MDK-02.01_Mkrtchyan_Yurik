import json
import mimetypes
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.realpath(os.path.join(BASE_DIR, "static"))
DB_PATH = os.path.join(BASE_DIR, "shop.db")

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
        if path != "/api/echo":
            self.send_json(404, {"error": "Неизвестный метод API: " + path})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            self.send_json(400, {"error": "Некорректный JSON"})
            return
        self.send_json(200, {"received": data})

if __name__ == "__main__":
    HTTPServer.allow_reuse_address = False
    server = HTTPServer(("127.0.0.1", 8000), Handler)
    print("Сервер запущен: http://localhost:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Сервер остановлен")
    server.server_close()
