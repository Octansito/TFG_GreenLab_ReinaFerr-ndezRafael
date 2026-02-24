#El archivo db.py contiene funciones para gestionar la conexión a MySQL y verificar su estado
from __future__ import annotations

from contextlib import closing

import mysql.connector
from mysql.connector import Error

#Este bloque permite importar config de forma estable en distintos modos de ejecución
try:
    from .config import Config
except ImportError:
    from config import Config


#Abre y devuelve una conexión nueva a MySQL con la configuración actual
def get_db_connection() -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
    )


#Comprueba si MySQL responde y devuelve estado más mensaje
def check_db_connection() -> tuple[bool, str]:
    try:
        with closing(get_db_connection()) as connection:
            if connection.is_connected():
                return True, "Conexion con MySQL correcta"
            return False, "MySQL no responde"
    except Error as error:
        return False, f"Error MySQL: {error}"
