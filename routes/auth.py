# routes/auth.py
# Módulo de autenticación — Login y Logout
# Responsable: Brayan

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Por ahora retorna un placeholder hasta que Brayan desarrolle el módulo completo
    return "<h2>EpiTrack — Login en construcción</h2><p>Conexión a Flask funcionando correctamente.</p>"


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))