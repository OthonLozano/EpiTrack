# routes/dashboard.py
from flask import Blueprint, render_template
from flask_login import login_required
from routes.decoradores import requiere_rol

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/admin")
@login_required
@requiere_rol(["administrador"])
def admin():
    return '''<h1>Panel Administrador</h1>
    <a href="/pacientes">🔍 Consulta de Pacientes</a>'''

@dashboard_bp.route("/epidemiologo")
@login_required
@requiere_rol(["epidemiologo", "administrador"])
def epidemiologo():
    return '''<h1>Dashboard Epidemiólogo</h1>
    <a href="/pacientes">🔍 Consulta de Pacientes</a>'''