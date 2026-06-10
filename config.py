# config.py
# Configuración central de la aplicación EpiTrack

import certifi

MONGO_URI = "mongodb+srv://BDA_UV:othon_lozano8@cluster0.0nht3o4.mongodb.net/?appName=Cluster0"
NOMBRE_BD = "EpiTrack"
TLS_CA    = certifi.where()

SECRET_KEY = "epitrack_clave_secreta_2026"