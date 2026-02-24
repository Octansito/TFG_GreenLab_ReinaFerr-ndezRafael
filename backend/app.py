#Archivo principal de Flask con una interfaz HTML y endpoints de API
from __future__ import annotations

from flask import Flask, jsonify, render_template, request
from mysql.connector import Error
from werkzeug.security import generate_password_hash

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

#Querys CRUD realizadas para la base de datos 
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


#Devuelve una conexión MySQL o una respuesta JSON de error
def _get_connection_or_error():
    
    try:
        return get_db_connection(), None
    except Error as error:
        app.logger.exception("Error de conexión a MySQL: %s", error)
        return None, (jsonify({"ok": False, "message": "Error de conexión a la base de datos"}), 500)

#Limpia texto y devuelve string vacío cuando no hay valor
def _text(value):
    return (str(value).strip() if value is not None else "")

#Valida que el cuerpo sea JSON y de tipo objeto
def _json_body_or_400():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify({"ok": False, "message": "El body debe ser JSON válido"}), 400)
    return data, None

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


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"ok": False, "message": "Método no permitido"}), 405


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
    password_hash = generate_password_hash(password)

    conn, err = _get_connection_or_error()
    if err:
        return err
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("INSERT INTO users (nombre, email, password_hash, rol) VALUES (%s, %s, %s, %s)", (nombre, email, password_hash, rol))
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
        

#Actualiza usuario por id de forma parcial o completa
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
            password_db = generate_password_hash(password_nueva)

        cur.execute("UPDATE users SET nombre = %s, email = %s, password_hash = %s, rol = %s WHERE id = %s", (nombre, email, password_db, rol, user_id))
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

#Elimina usuario por id
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

#Lista equipos del laboratorio con su responsable y frecuencia de mantenimiento 
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

#Lista plantillas de checklist para cada tipo de equipo
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

#Lista registros de checklist realizados por el personal del laboratorio
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

#Lista incidencias reportadas en el laboratorio
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
