#Archivo principal de Flask con una interfaz HTML y endpoints de API
from __future__ import annotations

from flask import Flask, jsonify, render_template, request
from mysql.connector import Error

#Este bloque permite ejecutar el proyecto tanto como paquete como script suelto
try:
    from .config import Config
    from .db import check_db_connection, get_db_connection
except ImportError:
    from config import Config
    from db import check_db_connection, get_db_connection

app = Flask(__name__)
app.config.from_object(Config)
#Roles válidos para los usuarios
ROLES_VALIDOS = {"jefe_laboratorio", "personal_laboratorio"}
#Querys realizadas para la base de datos
USUARIO_SELECT = "SELECT id, nombre, email, rol FROM users"

#Devuelve una conexión MySQL o una respuesta JSON de error
def _get_connection_or_error():
    
    try:
        return get_db_connection(), None
    except Error as error:
        return None, (jsonify({"ok": False, "message": f"Error de conexión a la base de datos: {error}"}), 500)

#Limpia texto y devuelve string vacío cuando no hay valor
def _text(value):
    return (str(value).strip() if value is not None else "")

#Devuelve un usuario por id
def _user_by_id(cursor, user_id: int):
    cursor.execute(f"{USUARIO_SELECT} WHERE id = %s", (user_id,))
    return cursor.fetchone()

#Las siguientes funciones manejan errores y devuelven respuestas JSON para la base de datos 
@app.errorhandler(400)
def bad_request(error):
    return jsonify({"ok": False, "message": "Solicitud incorrecta"}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({"ok": False, "message": "Recurso no encontrado"}), 404


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"ok": False, "message": "Error interno del servidor"}), 500


#Muestra la página principal con el estado actual de la base de datos
@app.route("/", methods=["GET"])
def home():
    db_ok, db_message = check_db_connection()
    return render_template("index.html", db_ok=db_ok, db_message=db_message)


#Devuelve un JSON simple con el estado del backend y de MySQL
@app.route("/health", methods=["GET"])
def health():
    db_ok, db_message = check_db_connection()
    status = 200 if db_ok else 500
    return jsonify({"ok": db_ok, "service": "flask", "database": "connected" if db_ok else "disconnected", "message": db_message}), status

#Lista usuarios de la tabla users
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

#Crea usuario en la tabla users
@app.route("/api/usuarios", methods=["POST"])
def crear_usuario():
    data = request.get_json(silent=True) or {}
    nombre = _text(data.get("nombre"))
    email = _text(data.get("email"))
    password = _text(data.get("password"))
    rol = _text(data.get("rol")) or "personal_laboratorio"
    if not nombre or not email or not password:
        return jsonify({"ok": False, "message": "Faltan campos obligatorios: nombre, email, password"}), 400
    if rol not in ROLES_VALIDOS:
        return jsonify({"ok": False, "message": "Rol inválido"}), 400

    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("INSERT INTO users (nombre, email, password, rol) VALUES (%s, %s, %s, %s)", (nombre, email, password, rol))
        conn.commit()
        user = _user_by_id(cur, cur.lastrowid)
        return jsonify({"ok": True, "data": user}), 201
    except Error as error:
        if getattr(error, "errno", None) == 1062:
            return jsonify({"ok": False, "message": "El email ya existe"}), 409
        return jsonify({"ok": False, "message": f"Error al crear usuario: {error}"}), 500
    finally:
        cur.close()
        conn.close()

#Obtiene usuario por id
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
