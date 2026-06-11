# routes/dashboard.py
# Módulo 4 — Transacciones Atómicas
# Módulo 5 — Dashboard (rutas /admin y /epidemiologo)
# Responsable: Othon

from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from routes.decoradores import requiere_rol
from datetime import datetime

dashboard_bp = Blueprint("dashboard", __name__)


# ══════════════════════════════════════════════════════════════════════════
# MÓDULO 4 — FUNCIÓN DE TRANSACCIÓN ATÓMICA
# Se llama desde routes/casos.py cuando el subtipo es "Hemorrágico"
# ══════════════════════════════════════════════════════════════════════════

def registrar_caso_hemorragico_con_alerta(doc_caso):
    """
    Ejecuta una transacción atómica multi-documento en MongoDB Atlas.

    Operaciones dentro de la transacción:
      1. insert_one → colección casos_dengue
      2. insert_one → colección alertas

    Si cualquiera de las dos falla → rollback automático (abort_transaction).
    Nada queda guardado en Atlas si hay error.

    Retorna:
      dict  → documento de alerta generado (si tuvo éxito)
      None  → si ocurrió un error y se realizó rollback
    """
    from app import cliente, bd

    doc_alerta = {
        "paciente_id"  : doc_caso.get("paciente_id"),
        "paciente_nombre": doc_caso.get("paciente_nombre", "No especificado"),
        "region"       : doc_caso.get("region"),
        "municipio"    : doc_caso.get("municipio"),
        "serotipo"     : doc_caso.get("serotipo"),
        "plaquetas"    : doc_caso.get("plaquetas"),
        "nivel_alerta" : "ALTO",
        "mensaje"      : (
            f"Caso Hemorrágico detectado en {doc_caso.get('region')} — "
            f"Municipio: {doc_caso.get('municipio')}. "
            f"Serotipo: {doc_caso.get('serotipo')}. "
            f"Plaquetas: {doc_caso.get('plaquetas', 'No registradas')}."
        ),
        "fecha_alerta" : datetime.now(),
        "atendida"     : False,
        "registrado_por": doc_caso.get("registrado_por", "sistema"),
    }

    try:
        with cliente.start_session() as session:
            with session.start_transaction():
                bd["casos_dengue"].insert_one(doc_caso, session=session)
                bd["alertas"].insert_one(doc_alerta, session=session)
                # Si cualquier línea lanza excepción → abort_transaction automático
        return doc_alerta  # Transacción exitosa

    except Exception as e:
        print(f"[TRANSACCIÓN — ROLLBACK] Error en transacción atómica: {e}")
        return None  # Rollback ejecutado — nada fue guardado


# ══════════════════════════════════════════════════════════════════════════
# RUTA: /alertas
# Lista las alertas activas (nivel ALTO) para epidemiólogo y administrador
# ══════════════════════════════════════════════════════════════════════════

@dashboard_bp.route("/alertas")
@login_required
@requiere_rol(["epidemiologo", "administrador"])
def listar_alertas():
    from app import bd
    alertas = list(
        bd["alertas"]
        .find({"atendida": False})
        .sort("fecha_alerta", -1)
        .limit(50)
    )
    return render_template("dashboard/alertas.html", alertas=alertas)


# ══════════════════════════════════════════════════════════════════════════
# RUTA: /admin
# Panel del administrador — accesible solo para rol administrador
# ══════════════════════════════════════════════════════════════════════════

@dashboard_bp.route("/admin")
@login_required
@requiere_rol(["administrador"])
def admin():
    from app import bd

    # ── Aggregation Pipeline 1: casos por región ──────────────────────────
    pipeline_region = [
        {"$group": {"_id": "$region", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}}
    ]
    casos_por_region = list(bd["casos_dengue"].aggregate(pipeline_region))

    # ── Aggregation Pipeline 2: casos por subtipo ─────────────────────────
    pipeline_subtipo = [
        {"$group": {"_id": "$subtipo", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}}
    ]
    casos_por_subtipo = list(bd["casos_dengue"].aggregate(pipeline_subtipo))

    # ── Aggregation Pipeline 3: casos por estado ──────────────────────────
    pipeline_estado = [
        {"$group": {"_id": "$estado", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}}
    ]
    casos_por_estado = list(bd["casos_dengue"].aggregate(pipeline_estado))

    # ── Alertas activas (sin atender) ─────────────────────────────────────
    alertas_activas = list(
        bd["alertas"]
        .find({"atendida": False})
        .sort("fecha_alerta", -1)
        .limit(10)
    )

    # ── Total de documentos por colección ─────────────────────────────────
    totales = {
        "casos"    : bd["casos_dengue"].count_documents({}),
        "pacientes": bd["pacientes"].count_documents({}),
        "alertas"  : bd["alertas"].count_documents({"atendida": False}),
        "usuarios" : bd["usuarios"].count_documents({}),
    }

    return render_template(
        "dashboard/admin.html",
        casos_por_region  = casos_por_region,
        casos_por_subtipo = casos_por_subtipo,
        casos_por_estado  = casos_por_estado,
        alertas_activas   = alertas_activas,
        totales           = totales,
        usuario           = current_user,
    )


# ══════════════════════════════════════════════════════════════════════════
# RUTA: /epidemiologo
# Dashboard epidemiológico — accesible para epidemiólogo y administrador
# ══════════════════════════════════════════════════════════════════════════

@dashboard_bp.route("/epidemiologo")
@login_required
@requiere_rol(["epidemiologo", "administrador"])
def epidemiologo():
    from app import bd

    # ── Aggregation Pipeline 1: casos por región ──────────────────────────
    pipeline_region = [
        {"$group": {"_id": "$region", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}}
    ]
    casos_por_region = list(bd["casos_dengue"].aggregate(pipeline_region))

    # ── Aggregation Pipeline 2: casos por subtipo ─────────────────────────
    pipeline_subtipo = [
        {"$group": {"_id": "$subtipo", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}}
    ]
    casos_por_subtipo = list(bd["casos_dengue"].aggregate(pipeline_subtipo))

    # ── Aggregation Pipeline 3: casos hemorrágicos con plaquetas bajas ────
    # Demuestra query sobre campo de subdocumento y condición numérica
    pipeline_criticos = [
        {"$match": {
            "subtipo"  : "Hemorrágico",
            "plaquetas": {"$lt": 100000}
        }},
        {"$group": {"_id": "$region", "casos_criticos": {"$sum": 1}}},
        {"$sort": {"casos_criticos": -1}}
    ]
    casos_criticos = list(bd["casos_dengue"].aggregate(pipeline_criticos))

    # ── Alertas activas ────────────────────────────────────────────────────
    alertas_activas = list(
        bd["alertas"]
        .find({"atendida": False})
        .sort("fecha_alerta", -1)
        .limit(10)
    )

    return render_template(
        "dashboard/epidemiologo.html",
        casos_por_region  = casos_por_region,
        casos_por_subtipo = casos_por_subtipo,
        casos_criticos    = casos_criticos,
        alertas_activas   = alertas_activas,
        usuario           = current_user,
    )