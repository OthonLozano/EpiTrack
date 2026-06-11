# routes/decoradores.py
# Módulo 1 — Decorador de Autorización por Roles
# Responsable: Brayan — Tarea 5
#
# USO:
#   from routes.decoradores import requiere_rol
#
#   @app.route("/admin")
#   @login_required
#   @requiere_rol(["administrador"])
#   def panel_admin():
#       ...
#
#   @app.route("/dashboard")
#   @login_required
#   @requiere_rol(["epidemiologo", "administrador"])
#   def dashboard():
#       ...

from functools import wraps
from flask import abort
from flask_login import current_user


def requiere_rol(roles: list):
    """
    Decorador de fábrica que verifica si el usuario autenticado
    tiene uno de los roles permitidos.

    Si el rol NO coincide → abort(403)  (Tarea 5: retornar 403 si rol no coincide)
    Si el rol SÍ coincide → ejecuta la vista normalmente.

    Parámetros:
        roles (list): Lista de roles permitidos, ej. ["administrador"] o
                      ["medico", "administrador"]

    Ejemplo crítico (Tarea 6):
        La Dra. (médico) intenta acceder a /admin → decorador detecta que
        'medico' no está en ["administrador"] → abort(403) → bloqueado.
    """
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Obtener el rol del usuario autenticado
            rol_usuario = getattr(current_user, "rol", None)

            if rol_usuario not in roles:
                # Rol no autorizado → HTTP 403 Forbidden
                abort(403)

            return f(*args, **kwargs)
        return wrapper
    return decorador