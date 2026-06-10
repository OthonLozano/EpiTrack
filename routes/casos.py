# routes/casos.py
from flask import Blueprint
from flask_login import login_required
from routes.decoradores import requiere_rol

casos_bp = Blueprint("casos", __name__)

@casos_bp.route("/casos/registrar")
@login_required
@requiere_rol(["medico", "administrador"])
def registrar():
    return "<h1>Registrar Caso ✅</h1><p>Módulo en construcción.</p>"