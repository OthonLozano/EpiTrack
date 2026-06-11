# routes/pacientes.py
# Módulo 2 — Consulta de Pacientes
# Responsable: Brayan
# Tarea 1: Vista perfil con comorbilidades anidadas
# Tarea 2: Buscador con $or + regex (paciente_id, nombre, municipio)
# Tarea 3: Consulta $exists — pacientes con diabetes
# Tarea 4: Historial de casos dengue por paciente

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from .decoradores import requiere_rol
from bson import ObjectId

pacientes_bp = Blueprint("pacientes", __name__)


# ── Tarea 2: Buscador con $or + regex ─────────────────────────────────────────
@pacientes_bp.route("/pacientes")
@login_required
@requiere_rol(["medico", "epidemiologo", "administrador"])
def lista():
    from app import col_pacientes, col_casos
    query_texto = request.args.get("q", "").strip()
    pacientes   = []

    if query_texto:
        # Una sola query, tres campos — operador $or con regex
        regex = {"$regex": query_texto, "$options": "i"}
        filtro = {
            "$or": [
                {"paciente_id": regex},
                {"nombre":      regex},
                {"municipio":   regex},
            ]
        }
        pacientes = list(col_pacientes.find(filtro).limit(50))

    # Tarea 3: pacientes con diabetes registrada usando $exists + valor true
    diabeticos = col_pacientes.count_documents(
        {"comorbilidades.diabetes": {"$exists": True, "$eq": True}}
    )

    return render_template(
        "pacientes/lista.html",
        pacientes=pacientes,
        query=query_texto,
        total_diabeticos=diabeticos,
    )


# ── Tarea 1: Vista perfil completo con comorbilidades anidadas ────────────────
@pacientes_bp.route("/pacientes/<paciente_id>")
@login_required
@requiere_rol(["medico", "epidemiologo", "administrador"])
def perfil(paciente_id):
    from app import col_pacientes, col_casos
    # Buscar por _id de Mongo o por paciente_id legible
    paciente = None
    try:
        paciente = col_pacientes.find_one({"_id": ObjectId(paciente_id)})
    except Exception:
        pass

    if not paciente:
        paciente = col_pacientes.find_one({"paciente_id": paciente_id})

    if not paciente:
        return render_template("pacientes/no_encontrado.html"), 404

    # Tarea 4: Historial de casos dengue — find() filtrando por paciente_id
    historial = list(
        col_casos.find(
            {"paciente_id": paciente["paciente_id"]}
        ).sort("fecha_diagnostico", -1)
    )

    return render_template(
        "pacientes/perfil.html",
        paciente=paciente,
        historial=historial,
    )


# ── Tarea 3: Ruta dedicada — listado de pacientes con diabetes ($exists) ──────
@pacientes_bp.route("/pacientes/diabetes")
@login_required
@requiere_rol(["epidemiologo", "administrador"])
def con_diabetes():
    from app import col_pacientes, col_casos
    pacientes = list(
        col_pacientes.find(
            {"comorbilidades.diabetes": {"$exists": True, "$eq": True}}
        ).limit(100)
    )
    return render_template(
        "pacientes/diabetes.html",
        pacientes=pacientes,
        total=len(pacientes),
    )