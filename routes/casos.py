import re
from datetime import datetime

from bson import ObjectId
from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from pymongo import MongoClient
import certifi
from config import MONGO_URI, NOMBRE_BD, TLS_CA

_cliente = MongoClient(MONGO_URI, tlsCAFile=TLS_CA)
bd = _cliente[NOMBRE_BD]
from routes.decoradores import requiere_rol

casos_bp = Blueprint("casos", __name__)

REGEX_NOMBRE   = re.compile(r'^[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ\s]+$')
REGEX_TELEFONO = re.compile(r'^\d{10}$')


def _validar_campos(form) -> list:
    errores = []

    paciente_precargado = bool(form.get("paciente_id", "").strip())

    requeridos = {
        "subtipo"           : "Subtipo de dengue",
        "serotipo"          : "Serotipo",
        "region"            : "Región",
        "municipio"         : "Municipio",
        "fecha_diagnostico" : "Fecha de diagnóstico",
        "estado"            : "Estado del caso",
    }
    if not paciente_precargado:
        requeridos["paciente_nombre"]   = "Nombre del paciente"
        requeridos["paciente_telefono"] = "Teléfono"

    for campo, etiqueta in requeridos.items():
        if not form.get(campo, "").strip():
            errores.append(f"El campo '{etiqueta}' es obligatorio.")

    nombre = form.get("paciente_nombre", "").strip()
    if nombre and not paciente_precargado and not REGEX_NOMBRE.match(nombre):
        errores.append("El nombre solo puede contener letras y espacios, sin números ni caracteres especiales.")

    telefono = form.get("paciente_telefono", "").strip()
    if telefono and not paciente_precargado and not REGEX_TELEFONO.match(telefono):
        errores.append("El teléfono debe tener exactamente 10 dígitos numéricos, sin guiones ni espacios.")

    fecha_str = form.get("fecha_diagnostico", "").strip()
    if fecha_str:
        try:
            fecha_dx = datetime.strptime(fecha_str, "%Y-%m-%d")
            if fecha_dx > datetime.now():
                errores.append(
                    f"La fecha de diagnóstico ({fecha_str}) no puede ser una fecha futura. "
                    "Por favor ingresa una fecha igual o anterior a hoy."
                )
        except ValueError:
            errores.append("La fecha de diagnóstico tiene un formato inválido. Use el formato AAAA-MM-DD.")

    return errores


@casos_bp.route("/casos/registrar", methods=["GET", "POST"])
@login_required
@requiere_rol(["medico", "administrador"])
def registrar():
    from app import col_pacientes

    regiones = list(bd["regiones_sanitarias"].find({}, {"nombre": 1, "municipios": 1}))

    if request.method == "GET":
        paciente_id_param   = request.args.get("paciente_id", "").strip()
        paciente_precargado = None

        if paciente_id_param:
            paciente_precargado = col_pacientes.find_one(
                {"paciente_id": paciente_id_param},
                {"paciente_id": 1, "nombre": 1, "telefono": 1,
                 "region": 1, "municipio": 1, "edad": 1, "sexo": 1}
            )
            if not paciente_precargado:
                flash(
                    f"No se encontró el paciente con ID '{paciente_id_param}'. "
                    "Verifique los datos.",
                    "danger",
                )

        return render_template(
            "casos/registrar.html",
            regiones=regiones,
            form={},
            paciente=paciente_precargado,
        )

    form    = request.form
    errores = _validar_campos(form)

    if errores:
        for e in errores:
            flash(e, "danger")
        pid = form.get("paciente_id", "").strip()
        pac = col_pacientes.find_one({"paciente_id": pid}) if pid else None
        return render_template("casos/registrar.html",
                               regiones=regiones, form=form, paciente=pac)

    fecha_dx = datetime.strptime(form["fecha_diagnostico"], "%Y-%m-%d")
    subtipo  = form["subtipo"]

    doc = {
        "paciente_id"              : form.get("paciente_id", "").strip()
                                     or f"TMP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "paciente_nombre"          : form.get("paciente_nombre", "").strip(),
        "paciente_telefono"        : form.get("paciente_telefono", "").strip(),
        "subtipo"                  : subtipo,
        "serotipo"                 : form["serotipo"],
        "region"                   : form["region"],
        "municipio"                : form["municipio"],
        "almacen"                  : form["region"],
        "fecha_diagnostico"        : fecha_dx,
        "estado"                   : form["estado"],
        "hospitalizacion_requerida": form.get("hospitalizado") == "on",
        "dias_evolucion"           : int(form.get("dias_evolucion") or 1),
        "sintomas": {
            "fiebre"            : form.get("fiebre")            == "on",
            "cefalea"           : form.get("cefalea")           == "on",
            "dolor_retroocular" : form.get("dolor_retroocular") == "on",
            "mialgias"          : form.get("mialgias")          == "on",
            "erupcion"          : form.get("erupcion")          == "on",
            "nauseas"           : form.get("nauseas")           == "on",
        },
        "condiciones_ambientales": {
            "temperatura_c" : float(form.get("temperatura_c") or 28),
            "humedad_pct"   : int(form.get("humedad_pct")    or 70),
            "mes"           : fecha_dx.month,
        },
        "registrado_por" : current_user.username,
        "fecha_registro" : datetime.now(),
    }

    if subtipo == "Hemorrágico":
        doc["plaquetas_bajas"]      = True
        doc["conteo_plaquetas"]     = int(form.get("conteo_plaquetas") or 50000)
        doc["requirio_transfusion"] = form.get("transfusion") == "on"
        doc["dias_hospitalizacion"] = int(form.get("dias_hosp") or 0)
    elif subtipo == "Con signos de alarma":
        doc["dolor_abdominal_intenso"] = form.get("dolor_abdominal") == "on"
        doc["vomito_persistente"]      = form.get("vomito")          == "on"
        doc["seguimiento_estricto"]    = True
    else:
        doc["manejo_ambulatorio"] = True

    bd["casos_dengue"].insert_one(doc)
    flash("Caso registrado exitosamente.", "success")
    return redirect(url_for("casos.listar"))


@casos_bp.route("/casos")
@login_required
@requiere_rol(["medico", "epidemiologo", "administrador"])
def listar():
    filtro_region  = request.args.get("region",      "")
    filtro_subtipo = request.args.get("subtipo",     "")
    filtro_estado  = request.args.get("estado",      "")
    fecha_desde    = request.args.get("fecha_desde", "")
    fecha_hasta    = request.args.get("fecha_hasta", "")

    query = {}

    if current_user.rol == "medico" and getattr(current_user, "region", None):
        query["region"] = current_user.region
    elif filtro_region:
        query["region"] = filtro_region

    if filtro_subtipo:
        query["subtipo"] = filtro_subtipo
    if filtro_estado:
        query["estado"]  = filtro_estado

    if fecha_desde or fecha_hasta:
        query["fecha_diagnostico"] = {}
        if fecha_desde:
            query["fecha_diagnostico"]["$gte"] = datetime.strptime(fecha_desde, "%Y-%m-%d")
        if fecha_hasta:
            query["fecha_diagnostico"]["$lte"] = datetime.strptime(fecha_hasta, "%Y-%m-%d")

    pipeline = [
        {"$match": query},
        {"$sort": {"fecha_diagnostico": -1}},
        {"$limit": 200},
        {"$project": {
            "subtipo": 1, "serotipo": 1, "region": 1, "municipio": 1,
            "estado": 1, "fecha_diagnostico": 1, "paciente_id": 1,
            "paciente_nombre": 1, "hospitalizacion_requerida": 1
        }}
    ]
    casos    = list(bd["casos_dengue"].aggregate(pipeline))
    regiones = list(bd["regiones_sanitarias"].find({}, {"nombre": 1}))

    return render_template("casos/listar.html",
                           casos=casos,
                           regiones=regiones,
                           filtros={
                               "region"     : filtro_region,
                               "subtipo"    : filtro_subtipo,
                               "estado"     : filtro_estado,
                               "fecha_desde": fecha_desde,
                               "fecha_hasta": fecha_hasta,
                           })


@casos_bp.route("/casos/editar/<caso_id>", methods=["GET", "POST"])
@login_required
@requiere_rol(["medico", "administrador"])
def editar(caso_id):
    try:
        oid = ObjectId(caso_id)
    except Exception:
        abort(404)

    caso = bd["casos_dengue"].find_one({"_id": oid})
    if not caso:
        abort(404)

    regiones = list(bd["regiones_sanitarias"].find({}, {"nombre": 1, "municipios": 1}))

    if request.method == "POST":
        form    = request.form
        errores = _validar_campos(form)

        if errores:
            for e in errores:
                flash(e, "danger")
            form_data = dict(caso)
            if caso.get("fecha_diagnostico"):
                form_data["fecha_diagnostico"] = caso["fecha_diagnostico"].strftime("%Y-%m-%d")

            return render_template("casos/editar.html",
                                   caso=caso, regiones=regiones, form=form_data)

        fecha_dx = datetime.strptime(form["fecha_diagnostico"], "%Y-%m-%d")
        bd["casos_dengue"].update_one(
            {"_id": oid},
            {"$set": {
                "subtipo"                  : form["subtipo"],
                "serotipo"                 : form["serotipo"],
                "region"                   : form["region"],
                "municipio"                : form["municipio"],
                "almacen"                  : form["region"],
                "estado"                   : form["estado"],
                "fecha_diagnostico"        : fecha_dx,
                "hospitalizacion_requerida": form.get("hospitalizado") == "on",
                "dias_evolucion"           : int(form.get("dias_evolucion") or 1),
                "condiciones_ambientales.mes": fecha_dx.month,
                "actualizado_por"          : current_user.username,
                "fecha_actualizacion"      : datetime.now(),
            }}
        )
        flash("Caso actualizado correctamente.", "success")
        return redirect(url_for("casos.listar"))

    return render_template("casos/editar.html",
                           caso=caso, regiones=regiones, form=caso)


@casos_bp.route("/casos/eliminar/<caso_id>", methods=["POST"])
@login_required
@requiere_rol(["administrador"])
def eliminar(caso_id):
    if request.form.get("confirmar") != "1":
        flash("Debes confirmar la eliminación antes de proceder.", "warning")
        return redirect(url_for("casos.listar"))

    try:
        oid = ObjectId(caso_id)
    except Exception:
        abort(404)

    resultado = bd["casos_dengue"].delete_one({"_id": oid})
    if resultado.deleted_count == 0:
        flash("No se encontró el caso especificado.", "danger")
    else:
        flash("Caso eliminado correctamente.", "success")

    return redirect(url_for("casos.listar"))


@casos_bp.route("/casos/actualizar-almacen", methods=["POST"])
@login_required
@requiere_rol(["administrador"])
def actualizar_almacen():
    region = request.form.get("region", "").strip()
    if not region:
        flash("Selecciona una región para actualizar.", "warning")
        return redirect(url_for("casos.listar"))

    resultado = bd["casos_dengue"].update_many(
        {"region": region},
        {"$set": {
            "almacen"             : region,
            "almacen_actualizado" : datetime.now(),
        }}
    )

    flash(
        f"updateMany ejecutado correctamente: {resultado.modified_count} casos "
        f"de la región '{region}' actualizados en el campo 'almacen'.",
        "success"
    )
    return redirect(url_for("casos.listar"))