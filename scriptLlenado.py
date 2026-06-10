"""
EpiTrack — Script de Generación de Datos (Solo Dengue)
=======================================================
Universidad Veracruzana | Ingeniería Informática
Materia: Bases de Datos Distribuidas y de Nube
Equipo: Carlos · Brayan · Othon | Primavera 2026

Colecciones generadas:
    1. regiones_sanitarias   (10  documentos)
    2. unidades_salud        (~80 documentos)
    3. pacientes             (~2,000 documentos)
    4. casos_dengue          (~7,000 documentos)
    5. usuarios              (5   documentos)

Requisitos:
    pip3 install pymongo faker bcrypt certifi

Uso:
    1. Reemplaza MONGO_URI con tu Connection String de Atlas.
    2. python3 generar_datos.py
"""

import random
import bcrypt
from datetime import datetime, timedelta

import certifi
from pymongo import MongoClient, ASCENDING
from bson import ObjectId
from faker import Faker

# ── Configuración ──────────────────────────────────────────────────────────────
MONGO_URI  = "mongodb+srv://BDA_UV:othon_lozano8@cluster0.0nht3o4.mongodb.net/?appName=Cluster0"
NOMBRE_BD  = "EpiTrack"

random.seed(42)
fake = Faker("es_MX")
Faker.seed(42)

# ── Datos maestros — 10 regiones sanitarias de Veracruz ───────────────────────
REGIONES = [
    { "nombre": "Xalapa",             "sede": "Xalapa-Enríquez",       "municipios": ["Xalapa", "Coatepec", "Banderilla", "Emiliano Zapata", "Tlalnelhuayocan"],   "poblacion": 712000, "densidad_km2": 312.4, "zona": "Centro" },
    { "nombre": "Veracruz",           "sede": "Veracruz",              "municipios": ["Veracruz", "Boca del Río", "Medellín", "Alvarado", "Jamapa"],               "poblacion": 895000, "densidad_km2": 421.7, "zona": "Centro-Costa" },
    { "nombre": "Coatzacoalcos",      "sede": "Coatzacoalcos",         "municipios": ["Coatzacoalcos", "Nanchital", "Moloacán", "Las Choapas"],                    "poblacion": 520000, "densidad_km2": 198.3, "zona": "Sur" },
    { "nombre": "Poza Rica",          "sede": "Poza Rica de Hidalgo",  "municipios": ["Poza Rica", "Tihuatlán", "Papantla", "Cazones", "Espinal"],                 "poblacion": 480000, "densidad_km2": 187.6, "zona": "Norte" },
    { "nombre": "Orizaba",            "sede": "Orizaba",               "municipios": ["Orizaba", "Río Blanco", "Nogales", "Ixtaczoquitlán"],                       "poblacion": 410000, "densidad_km2": 445.2, "zona": "Centro-Montaña" },
    { "nombre": "Córdoba",            "sede": "Córdoba",               "municipios": ["Córdoba", "Fortín", "Amatlán de los Reyes", "Atoyac"],                      "poblacion": 375000, "densidad_km2": 267.9, "zona": "Centro" },
    { "nombre": "Tuxpan",             "sede": "Tuxpan",                "municipios": ["Tuxpan", "Tamiahua", "Álamo Temapache", "Tantoyuca"],                       "poblacion": 310000, "densidad_km2": 143.5, "zona": "Norte-Costa" },
    { "nombre": "Minatitlán",         "sede": "Minatitlán",            "municipios": ["Minatitlán", "Cosoleacaque", "Jáltipan", "Oteapan"],                        "poblacion": 290000, "densidad_km2": 231.1, "zona": "Sur" },
    { "nombre": "San Andrés Tuxtla",  "sede": "San Andrés Tuxtla",     "municipios": ["San Andrés Tuxtla", "Santiago Tuxtla", "Catemaco"],                         "poblacion": 260000, "densidad_km2": 112.8, "zona": "Sur-Centro" },
    { "nombre": "Acayucan",           "sede": "Acayucan",              "municipios": ["Acayucan", "Oluta", "Sayula de Alemán", "Texistepec"],                       "poblacion": 195000, "densidad_km2": 98.4,  "zona": "Sur" },
]

TIPOS_UNIDAD  = ["Centro de Salud", "Clínica IMSS", "Hospital General", "Clínica ISSSTE", "Unidad Médica Rural"]
ESTADOS_CASO  = ["activo", "resuelto", "hospitalizado", "fallecido", "en_seguimiento"]
PESOS_ESTADO  = [0.30, 0.45, 0.16, 0.02, 0.07]
SUBTIPOS      = ["Clásico", "Hemorrágico", "Con signos de alarma"]
SEROTIPOS     = ["DENV-1", "DENV-2", "DENV-3", "DENV-4"]

# ── Helpers ────────────────────────────────────────────────────────────────────
def fecha_aleatoria(inicio, fin):
    delta = fin - inicio
    return inicio + timedelta(seconds=random.randint(0, int(delta.total_seconds())))

def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# ══════════════════════════════════════════════════════════════════════════════
# GENERADORES
# ══════════════════════════════════════════════════════════════════════════════

def generar_regiones():
    docs = []
    for r in REGIONES:
        docs.append({
            "_id"                  : ObjectId(),
            "nombre"               : r["nombre"],
            "sede"                 : r["sede"],
            "municipios"           : r["municipios"],
            "poblacion"            : r["poblacion"],
            "densidad_km2"         : r["densidad_km2"],
            "zona"                 : r["zona"],
            "num_unidades_salud"   : random.randint(6, 18),
            "coordinador"          : fake.name(),
            "telefono_emergencias" : f"228-{random.randint(100,999)}-{random.randint(1000,9999)}",
        })
    return docs


def generar_unidades(regiones_docs):
    docs = []
    for region in regiones_docs:
        for _ in range(random.randint(6, 10)):
            municipio = random.choice(region["municipios"])
            tipo      = random.choice(TIPOS_UNIDAD)
            docs.append({
                "_id"             : ObjectId(),
                "nombre"          : f"{tipo} {municipio}",
                "tipo"            : tipo,
                "region"          : region["nombre"],
                "municipio"       : municipio,
                "direccion"       : fake.street_address(),
                "capacidad_camas" : random.randint(10, 120),
                "personal_medico" : {
                    "medicos_generales" : random.randint(2, 15),
                    "especialistas"     : random.randint(0, 8),
                    "enfermeras"        : random.randint(4, 25),
                },
                "tiene_urgencias" : tipo in ["Hospital General", "Clínica IMSS", "Clínica ISSSTE"],
                "telefono"        : f"228-{random.randint(100,999)}-{random.randint(1000,9999)}",
                "activa"          : True,
            })
    return docs


def generar_pacientes(regiones_docs, n=2000):
    docs = []
    for i in range(n):
        region    = random.choice(regiones_docs)
        municipio = random.choice(region["municipios"])
        edad      = random.randint(1, 90)
        fe        = min(edad / 60, 1.0)     # factor edad para comorbilidades
        docs.append({
            "_id"         : ObjectId(),
            "paciente_id" : f"{region['nombre'][:3].upper()}-{random.randint(2023,2026)}-{str(i+1).zfill(5)}",
            "nombre"      : fake.name(),
            "edad"        : edad,
            "sexo"        : random.choice(["M", "F"]),
            "municipio"   : municipio,
            "region"      : region["nombre"],
            "telefono"    : f"{random.randint(2,9)}{random.randint(10,99)}{random.randint(1000000,9999999)}",
            "correo"      : fake.email(),
            "fecha_registro": fecha_aleatoria(datetime(2023,1,1), datetime(2026,4,1)),
            # Documento anidado — comorbilidades
            "comorbilidades": {
                "diabetes"       : random.random() < 0.15 * fe,
                "hipertension"   : random.random() < 0.20 * fe,
                "obesidad"       : random.random() < 0.18,
                "cardiopatia"    : random.random() < 0.08 * fe,
                "asma"           : random.random() < 0.10,
                "inmunosupresion": random.random() < 0.04,
            },
            "tiene_seguro_medico": random.random() < 0.62,
            "tipo_seguro"        : random.choice(["IMSS", "ISSSTE", "Seguro Popular", "Privado", None]),
        })
    return docs


def generar_casos(pacientes_docs, unidades_docs, regiones_docs, n=7000):
    """
    Genera documentos de dengue con esquemas HETEROGÉNEOS por subtipo.
    Clásico, Hemorrágico y Con signos de alarma tienen campos distintos
    para demostrar la flexibilidad de esquema de MongoDB.
    """
    docs      = []
    reg_map   = {r["nombre"]: r for r in regiones_docs}

    for _ in range(n):
        paciente       = random.choice(pacientes_docs)
        region_nombre  = paciente["region"]
        region         = reg_map[region_nombre]
        unidades_reg   = [u for u in unidades_docs if u["region"] == region_nombre]
        unidad         = random.choice(unidades_reg) if unidades_reg else random.choice(unidades_docs)

        subtipo        = random.choices(SUBTIPOS, weights=[0.55, 0.25, 0.20])[0]
        fecha_dx       = fecha_aleatoria(datetime(2023,1,1), datetime(2026,4,30))
        estado         = random.choices(ESTADOS_CASO, weights=PESOS_ESTADO)[0]
        hospitalizado  = estado == "hospitalizado" or (subtipo != "Clásico" and random.random() < 0.30)

        temp_base = 28 if region["zona"] in ["Centro-Costa", "Sur", "Norte-Costa"] else 22
        doc = {
            "_id"                   : ObjectId(),
            "paciente_id"           : paciente["paciente_id"],
            "subtipo"               : subtipo,
            "serotipo"              : random.choice(SEROTIPOS),
            "unidad_salud_id"       : unidad["_id"],
            "unidad_salud_nombre"   : unidad["nombre"],
            "region"                : region_nombre,
            "municipio"             : random.choice(region["municipios"]),
            "fecha_diagnostico"     : fecha_dx,
            "estado"                : estado,
            "almacen"               : region_nombre,
            "hospitalizacion_requerida": hospitalizado,
            "dias_evolucion"        : random.randint(1, 21),
            # Documento anidado — síntomas base (todos los subtipos)
            "sintomas": {
                "fiebre"            : True,
                "cefalea"           : random.random() < 0.85,
                "dolor_retroocular" : random.random() < 0.75,
                "mialgias"          : random.random() < 0.80,
                "erupcion"          : random.random() < 0.50,
                "nauseas"           : random.random() < 0.60,
            },
            # Documento anidado — condiciones ambientales
            "condiciones_ambientales": {
                "temperatura_c" : round(random.gauss(temp_base, 3), 1),
                "humedad_pct"   : random.randint(55, 92),
                "mes"           : fecha_dx.month,
            },
        }

        # ── Campos ESPECÍFICOS por subtipo (heterogeneidad de esquema) ─────────
        if subtipo == "Hemorrágico":
            doc["sangrado_mucosas"]       = random.random() < 0.65
            doc["plaquetas_bajas"]        = True
            doc["conteo_plaquetas"]       = random.randint(10000, 90000)
            doc["hemoconcentracion"]      = random.random() < 0.70
            doc["requirio_transfusion"]   = random.random() < 0.25
            doc["dias_hospitalizacion"]   = random.randint(3, 14) if hospitalizado else 0

        elif subtipo == "Con signos de alarma":
            doc["dolor_abdominal_intenso"] = random.random() < 0.80
            doc["vomito_persistente"]      = random.random() < 0.75
            doc["acumulacion_liquidos"]    = random.random() < 0.55
            doc["sangrado_leve"]           = random.random() < 0.40
            doc["letargo"]                 = random.random() < 0.50
            doc["seguimiento_estricto"]    = True

        else:  # Clásico
            doc["dolor_articular"]    = random.random() < 0.70
            doc["prueba_torniquete"]  = random.choice(["Positivo", "Negativo", "No realizado"])
            doc["manejo_ambulatorio"] = True

        docs.append(doc)
    return docs


def generar_usuarios():
    """
    Genera los 5 usuarios del sistema con contraseñas hasheadas.
    Roles: administrador, epidemiologo, medico (x3 regiones distintas).
    """
    usuarios = [
        { "username": "admin",        "password": "Admin2026!",   "rol": "administrador", "nombre": "Administrador Sistema",   "region": None },
        { "username": "epidemiologo", "password": "Epid2026!",    "rol": "epidemiologo",  "nombre": "Dr. Ricardo Mendoza",     "region": None },
        { "username": "medico_ver",   "password": "Medico2026!",  "rol": "medico",        "nombre": "Dra. Laura Sánchez",      "region": "Veracruz" },
        { "username": "medico_xal",   "password": "Medico2026!",  "rol": "medico",        "nombre": "Dr. Jorge Pérez",         "region": "Xalapa" },
        { "username": "medico_oriz",  "password": "Medico2026!",  "rol": "medico",        "nombre": "Dra. Ana González",       "region": "Orizaba" },
    ]
    docs = []
    for u in usuarios:
        docs.append({
            "_id"           : ObjectId(),
            "username"      : u["username"],
            "password_hash" : hash_password(u["password"]),
            "rol"           : u["rol"],
            "nombre"        : u["nombre"],
            "region"        : u["region"],
            "activo"        : True,
            "fecha_creacion": datetime.now(),
        })
    return docs

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("  EpiTrack — Generación de Datos (Solo Dengue)")
    print("=" * 60)

    print("\n[1/8] Conectando a MongoDB Atlas...")
    cliente = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    bd      = cliente[NOMBRE_BD]

    try:
        cliente.admin.command("ping")
        print("      Conexión exitosa.")
    except Exception as e:
        print(f"      ERROR: {e}")
        return

    print("\n[2/8] Eliminando colecciones existentes...")
    for col in ["regiones_sanitarias", "unidades_salud", "pacientes", "casos_dengue", "usuarios"]:
        bd[col].drop()
    print("      Colecciones eliminadas.")

    print("\n[3/8] Generando regiones sanitarias...")
    regiones_docs = generar_regiones()
    bd["regiones_sanitarias"].insert_many(regiones_docs)
    print(f"      {len(regiones_docs)} regiones insertadas.")

    print("\n[4/8] Generando unidades de salud...")
    unidades_docs = generar_unidades(regiones_docs)
    bd["unidades_salud"].insert_many(unidades_docs)
    print(f"      {len(unidades_docs)} unidades insertadas.")

    print("\n[5/8] Generando pacientes...")
    pacientes_docs = generar_pacientes(regiones_docs, n=2000)
    for i in range(0, len(pacientes_docs), 500):
        bd["pacientes"].insert_many(pacientes_docs[i:i+500])
    print(f"      {len(pacientes_docs)} pacientes insertados.")

    print("\n[6/8] Generando casos de dengue (esto tarda unos segundos)...")
    casos_docs = generar_casos(pacientes_docs, unidades_docs, regiones_docs, n=7000)
    for i in range(0, len(casos_docs), 500):
        bd["casos_dengue"].insert_many(casos_docs[i:i+500])
    print(f"      {len(casos_docs)} casos insertados.")

    print("\n[7/8] Generando usuarios del sistema...")
    usuarios_docs = generar_usuarios()
    bd["usuarios"].insert_many(usuarios_docs)
    print(f"      {len(usuarios_docs)} usuarios insertados.")
    print("      Credenciales:")
    print("        admin        / Admin2026!")
    print("        epidemiologo / Epid2026!")
    print("        medico_ver   / Medico2026!")

    print("\n[8/8] Creando índices...")
    bd["casos_dengue"].create_index([("region",            ASCENDING)])
    bd["casos_dengue"].create_index([("subtipo",           ASCENDING)])
    bd["casos_dengue"].create_index([("estado",            ASCENDING)])
    bd["casos_dengue"].create_index([("fecha_diagnostico", ASCENDING)])
    bd["pacientes"].create_index([("paciente_id", ASCENDING)], unique=True)
    bd["pacientes"].create_index([("region",      ASCENDING)])
    bd["usuarios"].create_index([("username",     ASCENDING)], unique=True)
    print("      Índices creados.")

    print("\n" + "=" * 60)
    print("  RESUMEN FINAL")
    print("=" * 60)
    total = 0
    for col in ["regiones_sanitarias", "unidades_salud", "pacientes", "casos_dengue", "usuarios"]:
        n = bd[col].count_documents({})
        total += n
        print(f"  {col:<30} {n:>6} documentos")
    print("-" * 60)
    print(f"  {'TOTAL':<30} {total:>6} documentos")
    print("=" * 60)
    print("\nBase de datos lista.")
    cliente.close()

if __name__ == "__main__":
    main()