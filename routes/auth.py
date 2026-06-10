# routes/auth.py
# Módulo 1 — Autenticación y Roles
# Responsable: Brayan
# Tareas: 3 (ruta /login), 4 (manejo de sesión Flask-Login)

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user, UserMixin
import bcrypt

# ── Blueprint ──────────────────────────────────────────────────────────────────
auth_bp = Blueprint("auth", __name__)

# ── Modelo de Usuario para Flask-Login ────────────────────────────────────────
class Usuario(UserMixin):
    """
    Adaptador entre el documento MongoDB y Flask-Login.
    Flask-Login necesita que el objeto tenga get_id(), is_authenticated, etc.
    UserMixin provee esos métodos automáticamente.
    """
    def __init__(self, doc):
        self.id        = str(doc["_id"])       # Flask-Login usa get_id() → str
        self.username  = doc["username"]
        self.rol       = doc["rol"]            # 'medico' | 'epidemiologo' | 'administrador'
        self.region    = doc.get("region", "")

    def get_id(self):
        return self.id


# ── user_loader (requerido por Flask-Login) ────────────────────────────────────
# Se registra en app.py usando login_manager.user_loader
def cargar_usuario(user_id):
    """
    Dado un user_id (string del _id de Mongo), devuelve el objeto Usuario
    o None si no existe. Flask-Login llama esto en cada request autenticado.
    """
    from bson import ObjectId
    from app import col_usuarios  # importación diferida para evitar circular import
    try:
        doc = col_usuarios.find_one({"_id": ObjectId(user_id)})
        if doc:
            return Usuario(doc)
    except Exception:
        pass
    return None


# ── Tarea 3: Ruta /login ───────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Si ya está autenticado, redirigir según rol
    if current_user.is_authenticated:
        return _redirigir_por_rol(current_user.rol)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # ── Validación de campos vacíos (backend) ──────────────────────────────
        errores = []
        if not username:
            errores.append("El nombre de usuario es obligatorio.")
        if not password:
            errores.append("La contraseña es obligatoria.")

        if errores:
            for e in errores:
                flash(e, "danger")
            return render_template("login.html"), 400

        # ── Buscar usuario en MongoDB ──────────────────────────────────────────
        from app import col_usuarios
        doc = col_usuarios.find_one({"username": username})

        if not doc or not bcrypt.checkpw(password.encode("utf-8"), doc["password_hash"].encode("utf-8")):
            flash("Usuario o contraseña incorrectos.", "danger")
            return render_template("login.html"), 401

        # ── Tarea 4: Guardar usuario y rol en sesión via Flask-Login ──────────
        usuario = Usuario(doc)
        login_user(usuario)                    # Flask-Login crea la cookie de sesión

        # Guardamos el rol también en session nativa (acceso fácil en templates)
        session["rol"]      = usuario.rol
        session["username"] = usuario.username
        session["region"]   = usuario.region

        flash(f"Bienvenido, {usuario.username} ({usuario.rol}).", "success")
        return _redirigir_por_rol(usuario.rol)

    # GET → mostrar formulario
    return render_template("login.html")


# ── Logout ─────────────────────────────────────────────────────────────────────
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))


# ── Helper: redirigir según rol ────────────────────────────────────────────────
def _redirigir_por_rol(rol):
    if rol == "administrador":
        return redirect(url_for("dashboard.admin"))
    elif rol == "epidemiologo":
        return redirect(url_for("dashboard.epidemiologo"))
    else:  # médico
        return redirect(url_for("casos.registrar"))