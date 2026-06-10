# app.py
# Punto de entrada principal de la aplicación EpiTrack
# Universidad Veracruzana — Ingeniería Informática
# Bases de Datos Distribuidas y de Nube — Primavera 2026

from flask import Flask
from flask_login import LoginManager
from pymongo import MongoClient
import certifi

from config import MONGO_URI, NOMBRE_BD, TLS_CA, SECRET_KEY

# ── Inicializar Flask ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY

# ── Conexión a MongoDB Atlas ───────────────────────────────────────────────────
cliente  = MongoClient(MONGO_URI, tlsCAFile=TLS_CA)
bd       = cliente[NOMBRE_BD]

# ── Colecciones disponibles ────────────────────────────────────────────────────
col_casos     = bd["casos_dengue"]
col_pacientes = bd["pacientes"]
col_unidades  = bd["unidades_salud"]
col_regiones  = bd["regiones_sanitarias"]
col_usuarios  = bd["usuarios"]

# ── Flask-Login ────────────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Debes iniciar sesión para acceder a esta sección."

# ── Registrar blueprints (rutas) ───────────────────────────────────────────────
from routes.auth      import auth_bp
from routes.casos     import casos_bp
from routes.pacientes import pacientes_bp
from routes.dashboard import dashboard_bp

app.register_blueprint(auth_bp)
app.register_blueprint(casos_bp)
app.register_blueprint(pacientes_bp)
app.register_blueprint(dashboard_bp)

# ── Verificar conexión al arrancar ─────────────────────────────────────────────
@app.before_request
def verificar_conexion():
    pass

# ── Ruta raíz ──────────────────────────────────────────────────────────────────
from flask import redirect, url_for

@app.route("/")
def index():
    return redirect(url_for("auth.login"))

# ── Ejecutar ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("EpiTrack iniciado — http://localhost:5000")
    app.run(debug=True, port=5000)