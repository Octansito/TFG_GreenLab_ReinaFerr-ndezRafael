#Archivo principal de Flask con una interfaz HTML y endpoints de API
from __future__ import annotations

import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

#Este bloque permite ejecutar el proyecto tanto como paquete como script suelto
try:
    from .config import Config
    from .db import check_db_connection, get_db_connection
except ImportError:
    from config import Config
    from db import check_db_connection, get_db_connection

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
PAGES_DIR = FRONTEND_DIR / "pages"
STYLES_DIR = FRONTEND_DIR / "styles"
SERVICES_DIR = FRONTEND_DIR / "services"
ASSETS_DIR = FRONTEND_DIR / "assets"

app = Flask(__name__)
app.config.from_object(Config)
ROLES_VALIDOS = {"jefe_laboratorio", "personal_laboratorio"}
SPECIAL_CHAR_RE = re.compile(r"[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ]")

USUARIO_SELECT = "SELECT id, nombre, email, rol FROM users"
EQUIPO_SELECT = """
SELECT e.id, e.nombre, e.tipo, e.ubicacion, e.temp_objetivo, e.responsable_id,
u.nombre AS responsable_nombre, e.frecuencia_mantenimiento, e.ultima_revision
FROM equipment e LEFT JOIN users u ON u.id = e.responsable_id
"""
PLANTILLA_SELECT = """
SELECT t.id, t.equipment_type, t.nombre, COUNT(i.id) AS total_items
FROM checklist_templates t LEFT JOIN checklist_template_items i ON i.template_id = t.id
GROUP BY t.id, t.equipment_type, t.nombre
"""
REGISTRO_SELECT = """
SELECT ce.id, ce.equipment_id, e.nombre AS equipment_nombre, ce.user_id,
u.nombre AS user_nombre, ce.fecha, ce.comentario FROM checklist_entries ce JOIN equipment e ON e.id = ce.equipment_id
JOIN users u ON u.id = ce.user_id
"""
INCIDENCIA_SELECT = """
SELECT i.id, i.equipment_id, e.nombre AS equipment_nombre, i.user_id, u.nombre AS user_nombre,
i.titulo, i.descripcion, i.prioridad, i.estado, i.creado_a, i.cerrado_a
FROM issues i JOIN equipment e ON e.id = i.equipment_id JOIN users u ON u.id = i.user_id
"""


def _add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return response


@app.after_request
def add_cors_headers(response):
    return _add_cors_headers(response)


def _get_connection_or_error():
    try:
        return get_db_connection(), None
    except Error as error:
        app.logger.exception("Error de conexión a MySQL: %s", error)
        return None, (jsonify({"ok": False, "message": "Error de conexión a la base de datos"}), 500)


def _text(value):
    return str(value).strip() if value is not None else ""


def _json_body_or_400():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify({"ok": False, "message": "El body debe ser JSON válido"}), 400)
    return data, None


def _password_error(password: str) -> str | None:
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres"
    if not re.search(r"[A-ZÁÉÍÓÚÜÑ]", password):
        return "La contraseña debe incluir al menos una mayúscula"
    if not re.search(r"[a-záéíóúüñ]", password):
        return "La contraseña debe incluir al menos una minúscula"
    if not re.search(r"\d", password):
        return "La contraseña debe incluir al menos un número"
    if not SPECIAL_CHAR_RE.search(password):
        return "La contraseña debe incluir al menos un carácter especial"
    return None


def _user_by_id(cursor, user_id: int):
    cursor.execute(f"{USUARIO_SELECT} WHERE id = %s", (user_id,))
    return cursor.fetchone()


def _user_auth_by_email(cursor, email: str):
    cursor.execute("SELECT id, nombre, email, password_hash, rol FROM users WHERE email = %s", (email,))
    return cursor.fetchone()


def _serve_frontend(directory: Path, filename: str):
    return send_from_directory(directory, filename)


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"ok": False, "message": "Solicitud incorrecta"}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({"ok": False, "message": "Recurso no encontrado"}), 404


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"ok": False, "message": "Error interno del servidor"}), 500


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"ok": False, "message": "Método no permitido"}), 405


@app.route("/", methods=["GET"])
@app.route("/login", methods=["GET"])
@app.route("/login.html", methods=["GET"])
def home():
    return _serve_frontend(PAGES_DIR, "login.html")


@app.route("/register", methods=["GET"])
@app.route("/register.html", methods=["GET"])
def register_page():
    return _serve_frontend(PAGES_DIR, "register.html")





@app.route("/styles/<path:filename>", methods=["GET"])
def frontend_styles(filename: str):
    return _serve_frontend(STYLES_DIR, filename)


@app.route("/services/<path:filename>", methods=["GET"])
def frontend_services(filename: str):
    return _serve_frontend(SERVICES_DIR, filename)


@app.route("/assets/<path:filename>", methods=["GET"])
def frontend_assets(filename: str):
    return _serve_frontend(ASSETS_DIR, filename)


@app.route("/health", methods=["GET"])
def health():
    db_ok, db_message = check_db_connection()
    status = 200 if db_ok else 500
    return jsonify({"ok": db_ok, "service": "flask", "database": "connected" if db_ok else "disconnected", "message": db_message}), status


@app.route("/api/login", methods=["POST"])
def login():
    data, err_json = _json_body_or_400()
    if err_json:
        return err_json
    email = _text(data.get("email"))
    password = _text(data.get("password"))
    if not email or not password:
        return jsonify({"ok": False, "message": "Faltan campos obligatorios: email, password"}), 400

    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        user = _user_auth_by_email(cur, email)
        if user is None or not check_password_hash(user["password_hash"], password):
            return jsonify({"ok": False, "message": "Credenciales inválidas"}), 401
        return jsonify(
            {
                "ok": True,
                "data": {
                    "id": user["id"],
                    "nombre": user["nombre"],
                    "email": user["email"],
                    "rol": user["rol"],
                },
            }
        ), 200
    except Error as error:
        app.logger.exception("Error SQL al iniciar sesión: %s", error)
        return jsonify({"ok": False, "message": "Error interno al iniciar sesión"}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/usuarios", methods=["GET"])
def listar_usuarios():
    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(f"{USUARIO_SELECT} ORDER BY id DESC")
        return jsonify({"ok": True, "data": cur.fetchall()}), 200
    except Error as error:
        return jsonify({"ok": False, "message": f"Error al listar usuarios: {error}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/usuarios", methods=["POST"])
def crear_usuario():
    data, err = _json_body_or_400()
    if err:
        return err
    nombre = _text(data.get("nombre"))
    email = _text(data.get("email"))
    password = _text(data.get("password"))
    rol = _text(data.get("rol")) or "personal_laboratorio"
    if not nombre or not email or not password:
        return jsonify({"ok": False, "message": "Faltan campos obligatorios: nombre, email, password"}), 400
    if rol not in ROLES_VALIDOS:
        return jsonify({"ok": False, "message": "Rol inválido"}), 400
    password_message = _password_error(password)
    if password_message:
        return jsonify({"ok": False, "message": password_message}), 400
    password_hash = generate_password_hash(password)

    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "INSERT INTO users (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s)",
            (nombre, email, password_hash, rol),
        )
        conn.commit()
        user = _user_by_id(cur, cur.lastrowid)
        return jsonify({"ok": True, "data": user}), 201
    except Error as error:
        if getattr(error, "errno", None) == 1062:
            return jsonify({"ok": False, "message": "El email ya existe"}), 409
        app.logger.exception("Error SQL al crear usuario: %s", error)
        return jsonify({"ok": False, "message": "Error interno al crear usuario"}), 500
    finally:
        cur.close()
        conn.close()
@app.route("/api/usuarios/<int:user_id>", methods=["GET"])
def obtener_usuario(user_id: int):
    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        user = _user_by_id(cur, user_id)
        if user is None:
            return jsonify({"ok": False, "message": "Usuario no encontrado"}), 404
        return jsonify({"ok": True, "data": user}), 200
    except Error as error:
        return jsonify({"ok": False, "message": f"Error al obtener usuario: {error}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/usuarios/<int:user_id>", methods=["PUT", "PATCH"])
def actualizar_usuario(user_id: int):
    data, err_json = _json_body_or_400()
    if err_json:
        return err_json
    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, nombre, email, password_hash, rol FROM users WHERE id = %s", (user_id,))
        actual = cur.fetchone()
        if actual is None:
            return jsonify({"ok": False, "message": "Usuario no encontrado"}), 404

        nombre = _text(data.get("nombre", actual["nombre"]))
        email = _text(data.get("email", actual["email"]))
        rol = _text(data.get("rol", actual["rol"]))
        if not nombre or not email:
            return jsonify({"ok": False, "message": "Faltan campos obligatorios: nombre, email, password"}), 400
        if rol not in ROLES_VALIDOS:
            return jsonify({"ok": False, "message": "Rol inválido"}), 400
        password_db = actual["password_hash"]
        if "password" in data:
            password_nueva = _text(data.get("password"))
            if not password_nueva:
                return jsonify({"ok": False, "message": "Faltan campos obligatorios: nombre, email, password"}), 400
            password_message = _password_error(password_nueva)
            if password_message:
                return jsonify({"ok": False, "message": password_message}), 400
            password_db = generate_password_hash(password_nueva)

        cur.execute(
            "UPDATE users SET nombre = %s, email = %s, password_hash = %s, rol = %s WHERE id = %s",
            (nombre, email, password_db, rol, user_id),
        )
        conn.commit()
        return jsonify({"ok": True, "data": _user_by_id(cur, user_id)}), 200
    except Error as error:
        if getattr(error, "errno", None) == 1062:
            return jsonify({"ok": False, "message": "El email ya existe"}), 409
        app.logger.exception("Error SQL al actualizar usuario %s: %s", user_id, error)
        return jsonify({"ok": False, "message": "Error interno al actualizar usuario"}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/usuarios/<int:user_id>", methods=["DELETE"])
def eliminar_usuario(user_id: int):
    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        if _user_by_id(cur, user_id) is None:
            return jsonify({"ok": False, "message": "Usuario no encontrado"}), 404
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return "", 204
    except Error as error:
        if getattr(error, "errno", None) == 1451:
            return jsonify({"ok": False, "message": "No se puede eliminar: tiene registros asociados"}), 409
        return jsonify({"ok": False, "message": f"Error al eliminar usuario: {error}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/equipos", methods=["GET"])
def listar_equipos():
    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(f"{EQUIPO_SELECT} ORDER BY e.id DESC")
        return jsonify({"ok": True, "data": cur.fetchall()}), 200
    except Error as error:
        return jsonify({"ok": False, "message": f"Error al listar equipos: {error}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/checklist/plantillas", methods=["GET"])
def listar_plantillas():
    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(f"{PLANTILLA_SELECT} ORDER BY t.id DESC")
        return jsonify({"ok": True, "data": cur.fetchall()}), 200
    except Error as error:
        return jsonify({"ok": False, "message": f"Error al listar plantillas: {error}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/checklist/registros", methods=["GET"])
def listar_registros():
    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(f"{REGISTRO_SELECT} ORDER BY ce.fecha DESC, ce.id DESC")
        return jsonify({"ok": True, "data": cur.fetchall()}), 200
    except Error as error:
        return jsonify({"ok": False, "message": f"Error al listar registros checklist: {error}"}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/incidencias", methods=["GET"])
def listar_incidencias():
    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(f"{INCIDENCIA_SELECT} ORDER BY i.creado_a DESC, i.id DESC")
        return jsonify({"ok": True, "data": cur.fetchall()}), 200
    except Error as error:
        return jsonify({"ok": False, "message": f"Error al listar incidencias: {error}"}), 500
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)





