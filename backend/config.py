"""Clase que contiene la configuracion de la aplicacion Flask, cargada desde variables de entorno"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

#Carga el archivo .env del backend aunque ejecutes comandos desde otra carpeta
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

#Guarda en un solo sitio la configuracion que usa Flask
class Config:
   

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_NAME = os.getenv("DB_NAME", "greenlab_checklist")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "root1234")
