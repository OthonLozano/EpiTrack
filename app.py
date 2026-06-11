from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager
from pymongo import MongoClient
import certifi
from config import MONGO_URI, NOMBRE_BD, TLS_CA, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

cliente = MongoClient(MONGO_URI, tlsCAFile=TLS_CA)
bd = cliente[NOMBRE_BD]

col_casos     = bd["casos_dengue"]
col_pacientes = bd["pacientes"]
col_unidades  = bd["unidades_salud"]
col_regiones  = bd["regiones_sanitarias"]
col_usuarios  = bd["usuarios"]
col_alertas   = bd["alertas"]   # ← AGREGAR para Módulo 4

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Debes iniciar sesión para acceder a esta sección."

# ── Brayan: registrar user_loader ──────────────────────────────────────────
from routes.auth import cargar_usuario
login_manager.user_loader(cargar_usuario)

from routes.auth      import auth_bp
from routes.casos     import casos_bp
from routes.pacientes import pacientes_bp
from routes.dashboard import dashboard_bp

app.register_blueprint(auth_bp)
app.register_blueprint(casos_bp)
app.register_blueprint(pacientes_bp)
app.register_blueprint(dashboard_bp)

# ── Brayan: manejador error 403 ────────────────────────────────────────────
@app.errorhandler(403)
def error_403(e):
    return render_template("403.html"), 403

@app.before_request
def verificar_conexion():
    pass

@app.route("/")
def index():
    return redirect(url_for("auth.login"))

if __name__ == "__main__":
    print("EpiTrack iniciado — http://localhost:5000")
    app.run(debug=True, port=5000)