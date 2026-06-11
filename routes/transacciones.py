# routes/transacciones.py
# Módulo 4 — Transacciones Atómicas
# Responsable: Othon
#
# JUSTIFICACIÓN:
# Se utiliza una transacción multi-documento porque al registrar un caso
# Hemorrágico, el caso clínico y su alerta deben persistir juntos o
# no persistir ninguno. Si solo se guardara el caso sin la alerta, se
# perdería trazabilidad del evento crítico. MongoDB Atlas soporta
# transacciones ACID sobre Replica Set desde la versión 4.0.

from datetime import datetime
from bson import ObjectId


def registrar_caso_con_alerta(cliente, nombre_bd, doc_caso):
    """
    Ejecuta una transacción atómica que:
      1. Inserta el documento en la colección casos_dengue
      2. Inserta simultáneamente una alerta en la colección alertas

    Si cualquiera de los dos falla → abort_transaction()
    → ninguno se guarda en la base de datos.

    Parámetros:
        cliente    : MongoClient — instancia de conexión a Atlas
        nombre_bd  : str         — nombre de la base de datos ('EpiTrack')
        doc_caso   : dict        — documento del caso ya construido

    Retorna:
        dict con claves:
            'exito'      : bool
            'caso_id'    : ObjectId (si exito=True)
            'alerta_id'  : ObjectId (si exito=True)
            'alerta_doc' : dict     (si exito=True)
            'error'      : str      (si exito=False)
    """
    bd = cliente[nombre_bd]

    # Construir el documento de alerta ANTES de abrir la transacción
    alerta_id = ObjectId()
    doc_alerta = {
        "_id"             : alerta_id,
        "caso_id"         : doc_caso["_id"],
        "paciente_id"     : doc_caso.get("paciente_id", ""),
        "paciente_nombre" : doc_caso.get("paciente_nombre", ""),
        "region"          : doc_caso["region"],
        "municipio"       : doc_caso.get("municipio", ""),
        "subtipo"         : doc_caso["subtipo"],
        "nivel_severidad" : "CRÍTICO",
        "motivo"          : "Caso de dengue hemorrágico registrado — requiere seguimiento inmediato",
        "fecha_alerta"    : datetime.now(),
        "estado_alerta"   : "activa",
        "registrado_por"  : doc_caso.get("registrado_por", "sistema"),
    }

    # ── Iniciar sesión y transacción ──────────────────────────────────────────
    with cliente.start_session() as session:
        try:
            session.start_transaction()

            # Operación 1 — insertar el caso clínico
            bd["casos_dengue"].insert_one(doc_caso, session=session)

            # Operación 2 — insertar la alerta (simultánea, misma transacción)
            bd["alertas"].insert_one(doc_alerta, session=session)

            # Si ambas operaciones fueron exitosas → confirmar
            session.commit_transaction()

            return {
                "exito"      : True,
                "caso_id"    : doc_caso["_id"],
                "alerta_id"  : alerta_id,
                "alerta_doc" : doc_alerta,
            }

        except Exception as e:
            # Si cualquier operación falló → revertir todo
            session.abort_transaction()
            return {
                "exito" : False,
                "error" : str(e),
            }