import json
import os
import tempfile
import uuid
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request, abort
from flask_httpauth import HTTPBasicAuth


def load_books(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    if isinstance(data, list):
        return [b for b in data if isinstance(b, dict)]
    return []


def save_books(file_path: str, books: List[Dict[str, Any]]) -> None:
    d = os.path.dirname(os.path.abspath(file_path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="books_", suffix=".json", dir=d, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(books, tmp)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_path, file_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _non_empty_str(v: Any) -> str:
    if not isinstance(v, str):
        raise ValueError
    s = v.strip()
    if not s:
        raise ValueError
    return s


def _year_int(v: Any) -> int:
    if not isinstance(v, int):
        raise ValueError
    if v < 1000 or v > 9999:
        raise ValueError
    return v


def _validate_book_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError
    title = _non_empty_str(payload.get("title"))
    author = _non_empty_str(payload.get("author"))
    year = _year_int(payload.get("year"))
    return {"title": title, "author": author, "year": year}


def create_app(data_file: str, users: Dict[str, str]) -> Flask:
    app = Flask(__name__)
    auth = HTTPBasicAuth()

    store: List[Dict[str, Any]] = load_books(data_file)
    app.config["DATA_FILE"] = data_file
    app.config["USERS"] = users
    app.config["ITEM_STORE"] = store

    @auth.verify_password
    def _verify(username: str, password: str) -> Optional[str]:
        if username in users and users[username] == password:
            return username
        return None

    @auth.error_handler
    def _auth_error(_status):
        return jsonify({"error": "Unauthorized"}), 401

    def _parse_json_or_400():
        if not request.is_json:
            abort(400, description="invalid JSON")
        data = request.get_json(silent=True)
        if data is None:
            abort(400, description="invalid JSON")
        return data

    def _persist_or_500():
        try:
            save_books(data_file, store)
        except Exception:
            abort(500, description="file I/O error")

    def _find(book_id: str) -> Optional[Dict[str, Any]]:
        for b in store:
            if b.get("id") == book_id:
                return b
        return None

    @app.route("/books", methods=["GET"])
    @auth.login_required
    def list_books():
        return jsonify(store), 200

    @app.route("/books/<string:book_id>", methods=["GET"])
    @auth.login_required
    def get_book(book_id: str):
        book = _find(book_id)
        if not book:
            abort(404, description="not found")
        return jsonify(book), 200

    @app.route("/books", methods=["POST"])
    @auth.login_required
    def create_book():
        payload = _parse_json_or_400()
        try:
            fields = _validate_book_payload(payload)
        except ValueError:
            abort(400, description="bad request")
        book = {"id": str(uuid.uuid4()), **fields}
        store.append(book)
        _persist_or_500()
        return jsonify(book), 201

    @app.route("/books/<string:book_id>", methods=["PUT"])
    @auth.login_required
    def update_book(book_id: str):
        payload = _parse_json_or_400()
        try:
            fields = _validate_book_payload(payload)
        except ValueError:
            abort(400, description="bad request")
        book = _find(book_id)
        if not book:
            abort(404, description="not found")
        book.update(fields)
        _persist_or_500()
        return jsonify(book), 200

    @app.route("/books/<string:book_id>", methods=["DELETE"])
    @auth.login_required
    def delete_book(book_id: str):
        before = len(store)
        store[:] = [b for b in store if b.get("id") != book_id]
        if len(store) == before:
            abort(404, description="not found")
        _persist_or_500()
        return ("", 204)

    @app.errorhandler(400)
    def _bad_request(err):
        return jsonify({"error": getattr(err, "description", "bad request")}), 400

    @app.errorhandler(404)
    def _not_found(err):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def _server_error(err):
        return jsonify({"error": "internal error"}), 500

    return app


if __name__ == "__main__":
    create_app("books.json", {"admin": "password"}).run(debug=True)

