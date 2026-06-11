from datetime import datetime

from bson import ObjectId
from flask import (Blueprint, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import login_required

from .decoradores import requiere_rol

pacientes_bp = Blueprint("pacientes", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# PASO 1 — Búsqueda de paciente antes de registrar un caso
# GET  /pacientes/buscar           → muestra el formulario de búsqueda
# POST /pacientes/buscar           → ejecuta la búsqueda y muestra resultados
# ─────────────────────────────────────────────────────────────────────────────
@pacientes_bp.route("/pacientes/buscar", methods=["GET", "POST"])
@login_required
@requiere_rol(["medico", "administrador"])
def buscar_para_caso():
    from app import col_pacientes, col_regiones

    regiones   = list(col_regiones.find({}, {"nombre": 1}))
    resultados = []
    buscado    = False
    nombre_q   = ""
    region_q   = ""

    if request.method == "POST":
        nombre_q = request.form.get("nombre", "").strip()
        region_q = request.form.get("region", "").strip()
        buscado  = True

        if nombre_q:
            filtro = {
                "nombre": {"$regex": nombre_q, "$options": "i"},
            }
            if region_q:
                filtro["region"] = region_q

            resultados = list(col_pacientes.find(filtro).limit(20))

    return render_template(
        "pacientes/buscar.html",
        regiones=regiones,
        resultados=resultados,
        buscado=buscado,
        nombre_q=nombre_q,
        region_q=region_q,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2A — Registro de paciente nuevo
# GET  /pacientes/nuevo            → formulario de registro
# POST /pacientes/nuevo            → insert_one en colección pacientes,
#                                    redirige a /casos/registrar?paciente_id=…
# ─────────────────────────────────────────────────────────────────────────────
@pacientes_bp.route("/pacientes/nuevo", methods=["GET", "POST"])
@login_required
@requiere_rol(["medico", "administrador"])
def registrar_paciente():
    from app import col_pacientes, col_regiones
    import re

    regiones = list(col_regiones.find({}, {"nombre": 1, "municipios": 1}))

    REGEX_NOMBRE   = re.compile(r'^[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ\s]+$')
    REGEX_TELEFONO = re.compile(r'^\d{10}$')
    REGEX_CORREO   = re.compile(r'^[\w\.\+\-]+@[\w\-]+\.[a-z]{2,}$', re.IGNORECASE)

    # Recuperar valores pre-llenados desde la búsqueda anterior
    nombre_previo = request.args.get("nombre", "")
    region_previa = request.args.get("region", "")

    if request.method == "POST":
        form    = request.form
        errores = []

        nombre    = form.get("nombre", "").strip()
        telefono  = form.get("telefono", "").strip()
        correo    = form.get("correo", "").strip()
        edad_str  = form.get("edad", "").strip()
        sexo      = form.get("sexo", "").strip()
        municipio = form.get("municipio", "").strip()
        region    = form.get("region", "").strip()

        # ── Campos obligatorios ───────────────────────────────────────────────
        requeridos = {
            "nombre": "Nombre completo",
            "telefono": "Teléfono",
            "edad": "Edad",
            "sexo": "Sexo",
            "municipio": "Municipio",
            "region": "Región",
        }
        for campo, etiqueta in requeridos.items():
            if not form.get(campo, "").strip():
                errores.append(f"El campo '{etiqueta}' es obligatorio.")

        # ── Validaciones de formato ───────────────────────────────────────────
        if nombre and not REGEX_NOMBRE.match(nombre):
            errores.append("El nombre solo puede contener letras y espacios.")

        if telefono and not REGEX_TELEFONO.match(telefono):
            errores.append("El teléfono debe tener exactamente 10 dígitos numéricos.")

        if correo and not REGEX_CORREO.match(correo):
            errores.append("El formato del correo electrónico no es válido.")

        edad = None
        if edad_str:
            try:
                edad = int(edad_str)
                if edad < 0 or edad > 120:
                    errores.append("La edad debe estar entre 0 y 120 años.")
            except ValueError:
                errores.append("La edad debe ser un número entero.")

        # ── Verificar duplicado exacto por nombre + región ────────────────────
        if not errores:
            duplicado = col_pacientes.find_one({
                "nombre": {"$regex": f"^{re.escape(nombre)}$", "$options": "i"},
                "region": region,
            })
            if duplicado:
                errores.append(
                    f"Ya existe un paciente con ese nombre en la región {region}. "
                    f"ID: {duplicado['paciente_id']}. Verifique antes de continuar."
                )

        if errores:
            for e in errores:
                flash(e, "danger")
            return render_template(
                "pacientes/nuevo.html",
                regiones=regiones,
                form=form,
            )

        # ── Generar paciente_id legible ───────────────────────────────────────
        prefijo      = region[:3].upper()
        anio         = datetime.now().year
        total        = col_pacientes.count_documents({}) + 1
        paciente_id  = f"{prefijo}-{anio}-{str(total).zfill(5)}"

        doc = {
            "paciente_id": paciente_id,
            "nombre":      nombre,
            "edad":        edad,
            "sexo":        sexo,
            "municipio":   municipio,
            "region":      region,
            "telefono":    telefono,
            "correo":      correo if correo else None,
            "fecha_registro": datetime.now(),
            "comorbilidades": {
                "diabetes":        form.get("diabetes")        == "on",
                "hipertension":    form.get("hipertension")    == "on",
                "obesidad":        form.get("obesidad")        == "on",
                "cardiopatia":     form.get("cardiopatia")     == "on",
                "asma":            form.get("asma")            == "on",
                "inmunosupresion": form.get("inmunosupresion") == "on",
            },
            "tiene_seguro_medico": form.get("tiene_seguro") == "on",
            "tipo_seguro": form.get("tipo_seguro", "").strip() or None,
            "registrado_por": __import__("flask_login").current_user.username,
        }

        col_pacientes.insert_one(doc)
        flash(
            f"Paciente registrado correctamente con ID {paciente_id}. "
            "Complete ahora el registro del caso de dengue.",
            "success",
        )
        return redirect(
            url_for("casos.registrar", paciente_id=paciente_id)
        )

    return render_template(
        "pacientes/nuevo.html",
        regiones=regiones,
        form={"nombre": nombre_previo, "region": region_previa},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rutas existentes — sin modificaciones
# ─────────────────────────────────────────────────────────────────────────────

@pacientes_bp.route("/pacientes")
@login_required
@requiere_rol(["medico", "epidemiologo", "administrador"])
def lista():
    from app import col_pacientes

    query_texto = request.args.get("q", "").strip()
    pacientes   = []

    if query_texto:
        regex  = {"$regex": query_texto, "$options": "i"}
        filtro = {
            "$or": [
                {"paciente_id": regex},
                {"nombre":      regex},
                {"municipio":   regex},
            ]
        }
        pacientes = list(col_pacientes.find(filtro).limit(50))

    diabeticos = col_pacientes.count_documents(
        {"comorbilidades.diabetes": {"$exists": True, "$eq": True}}
    )

    return render_template(
        "pacientes/lista.html",
        pacientes=pacientes,
        query=query_texto,
        total_diabeticos=diabeticos,
    )


@pacientes_bp.route("/pacientes/<paciente_id>")
@login_required
@requiere_rol(["medico", "epidemiologo", "administrador"])
def perfil(paciente_id):
    from app import col_pacientes, col_casos

    paciente = None
    try:
        paciente = col_pacientes.find_one({"_id": ObjectId(paciente_id)})
    except Exception:
        pass

    if not paciente:
        paciente = col_pacientes.find_one({"paciente_id": paciente_id})

    if not paciente:
        return render_template("pacientes/no_encontrado.html"), 404

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


@pacientes_bp.route("/pacientes/diabetes")
@login_required
@requiere_rol(["epidemiologo", "administrador"])
def con_diabetes():
    from app import col_pacientes

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