import os
import base64
import re
import io
import urllib.request
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, redirect

# Importaciones oficiales de Google API
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)

# ID único de tu Google Sheets
SHEET_ID = "1zpNvnE-8snXa_8HmiHmd_uqmduL5S6V9"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# =====================================================================
# LÓGICA DE CONTROL DE CLIENTES (Google Sheets)
# =====================================================================
def verificar_cliente(celular_usuario):
    try:
        req = urllib.request.Request(CSV_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()
            
        df = pd.read_csv(io.BytesIO(data), header=None)
        celular_usuario = str(celular_usuario).strip().replace(r'\.0$', '')
        
        print(f"\n--- [BOT LOG] Buscando el celular: {celular_usuario} ---")
        
        fila_cliente = None
        for idx, fila in df.iterrows():
            texto_fila = " ".join(fila.astype(str).tolist())
            if celular_usuario in texto_fila:
                fila_cliente = fila
                print("✅ ¡Cliente localizado en la base de datos!")
                break
                
        if fila_cliente is None:
            return {"status": "denegado", "msg": "Número de WhatsApp no registrado o incorrecto."}
            
        # Extracción de la primera fecha de izquierda a derecha
        fecha_corte = None
        patron_fecha = re.compile(r'\d{1,2}[-/]\d{1,2}[-/](\d{4}|\d{2})')
        
        for celda in fila_cliente.astype(str):
            celda_limpia = celda.strip()
            match = patron_fecha.search(celda_limpia)
            if match:
                fecha_str = match.group().replace('/', '-')
                try:
                    fecha_corte = datetime.strptime(fecha_str, "%d-%m-%Y").date()
                    break
                except ValueError:
                    try:
                        fecha_corte = datetime.strptime(fecha_str, "%d-%m-%y").date()
                        break
                    except ValueError:
                        continue
                        
        if not fecha_corte:
            return {"status": "error", "msg": "No se pudo determinar tu fecha de vencimiento."}
            
        hoy = datetime.now().date()
        # Calculamos la diferencia de días exactos que le quedan
        dias_restantes = (fecha_corte - hoy).days
        print(f"📅 Corte: {fecha_corte} | Hoy: {hoy} | Días restantes: {dias_restantes}")
        
        if dias_restantes < 0:
            return {"status": "vencido", "msg": f"Tu suscripción venció el {fecha_corte.strftime('%d-%m-%Y')}."}
        elif dias_restantes == 0:
            return {"status": "aviso_hoy", "msg": "¡Tu servicio vence el día de hoy! Recuerda realizar tu pago para evitar cortes."}
        elif 1 <= dias_restantes <= 5:
            return {"status": "aviso_proximo", "msg": f"Recuerda realizar tu pago a tiempo. Tu servicio vencerá en {dias_restantes} días ({fecha_corte.strftime('%d-%m-%Y')})."}
        else:
            return {"status": "ok"}
            
    except Exception as e:
        print(f"❌ Error crítico en verificación: {e}")
        return {"status": "error", "msg": "No se pudo procesar la base de datos."}


# =====================================================================
# LÓGICA DE API DE GMAIL (Espejo de correo Netflix)
# =====================================================================
def get_gmail_service():
    creds = None
    token_path = '/etc/secrets/token.json' if os.path.exists('/etc/secrets/token.json') else 'token.json'
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/gmail.readonly'])
    return build('gmail', 'v1', credentials=creds)

def obtener_html_netflix(correo_consulta):
    try:
        service = get_gmail_service()
        # Buscamos el correo más reciente filtrando por remitente y palabras clave
        query = f'from:netflix subject:(Hogar OR Actualizar) {correo_consulta}'
        results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return None
            
        msg = service.users().messages().get(userId='me', id=messages[0]['id'], format='full').execute()
        payload = msg['payload']
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        else:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            
        return body
    except Exception as e:
        print(f"Error en Gmail: {e}")
        return None


# =====================================================================
# PANTALLAS WEB FLASK
# =====================================================================

# 1. Página de login con diseño dividido moderno
@app.route('/', methods=['GET'])
def login_page():
    foto_url = "/static/img/fondo.jpeg"
    return f"""
    <html>
        <head>
            <title>Soporte Netflix - Acceso</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    background-color: #141414; 
                    margin: 0; 
                    display: flex;
                    height: 100vh;
                    width: 100vw;
                    overflow: hidden;
                }}
                .col-izquierda {{
                    width: 50vw;
                    height: 100vh;
                    background-image: url('{foto_url}');
                    background-size: cover;
                    background-position: center;
                    background-repeat: no-repeat;
                    border-right: 1px solid rgba(255, 255, 255, 0.05);
                }}
                .col-derecha {{
                    width: 50vw;
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    background-color: #141414;
                }}
                .card {{ 
                    background-color: #000000; 
                    padding: 50px 40px; 
                    border-radius: 8px; 
                    text-align: center; 
                    border: 1px solid #222222; 
                    max-width: 400px; 
                    width: 100%; 
                    box-sizing: border-box;
                    box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.5);
                }}
                h2 {{ 
                    color: #E50914; 
                    margin-bottom: 12px; 
                    font-size: 26px; 
                    font-weight: bold; 
                    letter-spacing: -0.5px;
                }}
                p {{ 
                    color: #8c8c8c; 
                    font-size: 14px; 
                    margin-bottom: 35px; 
                    line-height: 1.4; 
                }}
                input[type="text"] {{ 
                    width: 100%; 
                    padding: 14px; 
                    margin-bottom: 20px; 
                    border: 1px solid #333333; 
                    background-color: #333333; 
                    color: white; 
                    border-radius: 4px; 
                    font-size: 15px; 
                    box-sizing: border-box; 
                }}
                input[type="text"]:focus {{ 
                    border-color: #E50914; 
                    outline: none; 
                }}
                button {{ 
                    width: 100%; 
                    padding: 14px; 
                    background-color: #E50914; 
                    color: white; 
                    border: none; 
                    border-radius: 4px; 
                    font-size: 16px; 
                    font-weight: bold; 
                    cursor: pointer; 
                    transition: background 0.2s ease;
                }}
                button:hover {{ 
                    background-color: #b81d24; 
                }}
                @media (max-width: 768px) {{
                    .col-izquierda {{ display: none; }}
                    .col-derecha {{ width: 100vw; }}
                    .card {{ border: none; background-color: transparent; }}
                }}
            </style>
        </head>
        <body>
            <div class="col-izquierda"></div>
            <div class="col-derecha">
                <div class="card">
                    <h2>Ingresar al Sistema</h2>
                    <p>Escribe tu número de WhatsApp para solicitar tu código de Hogar Netflix.</p>
                    <form action="/verificar" method="POST">
                        <input type="text" name="celular" placeholder="Ej: 904735959" required>
                        <button type="submit">Validar Acceso</button>
                    </form>
                </div>
            </div>
        </body>
    </html>
    """

# 2. Ruta de validación de credenciales y alertas de pago
@app.route('/verificar', methods=['POST'])
def verificar():
    celular = request.form.get('celular')
    resultado = verificar_cliente(celular)
    
    if resultado["status"] == "ok":
        return redirect('/ver-codigo')
        
    # Pantalla amarilla de advertencia preventiva (Vence hoy o pronto)
    if resultado["status"] in ["aviso_hoy", "aviso_proximo"]:
        return f"""
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta http-equiv="refresh" content="5;url=/ver-codigo">
                <style>
                    body {{ font-family: Arial, sans-serif; background-color: #141414; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                    .card {{ background-color: #000; padding: 40px; border-radius: 10px; text-align: center; border: 1px solid #ffcc00; max-width: 400px; box-shadow: 0px 4px 15px rgba(255, 204, 0, 0.2); }}
                    h2 {{ color: #ffcc00; margin-bottom: 15px; font-size: 24px; }}
                    p {{ font-size: 16px; color: #ddd; line-height: 1.5; }}
                    .btn {{ display: inline-block; margin-top: 20px; color: black; background: #ffcc00; padding: 12px 25px; border-radius: 5px; text-decoration: none; font-weight: bold; }}
                    .btn:hover {{ background: #e6b800; }}
                    .loader {{ color: #aaa; font-size: 12px; margin-top: 15px; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>⚠️ Recordatorio Importante</h2>
                    <p>{resultado["msg"]}</p>
                    <a href="/ver-codigo" class="btn">Entendido, Continuar</a>
                    <div class="loader">Redirigiendo automáticamente en 5 segundos...</div>
                </div>
            </body>
        </html>
        """
    
    # Pantalla roja de bloqueo (Vencido o no registrado)
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #141414; color: white; text-align: center; padding-top: 100px;">
            <div style="display: inline-block; background: #000; padding: 40px; border-radius: 10px; border: 1px solid #E50914; max-width: 400px; box-shadow: 0px 4px 15px rgba(0,0,0,0.5);">
                <h2 style="color: #E50914;">Acceso Interrumpido</h2>
                <p style="font-size: 16px; color: #ddd;">{resultado["msg"]}</p>
                <p style="color: #aaa; font-size: 14px;">Por favor, comunícate con soporte para renovar tu servicio.</p>
                <br>
                <a href="/" style="color: white; background: #333; padding: 10px 20px; border-radius: 5px; text-decoration: none; font-weight: bold;">Volver</a>
            </div>
        </body>
    </html>
    """

# 3. Interfaz de buscador de correos (Abre index.html)
@app.route('/ver-codigo')
def index():
    return render_template('index.html')

# 4. Procesador de consulta de Gmail espejo
@app.route('/consultar', methods=['POST'])
def consultar():
    correo = request.form.get('correo', '').strip().lower()
    html_correo = obtener_html_netflix(correo)
    
    if not html_correo:
        return render_template('resultado.html', error="No se encontró ningún correo reciente de Actualización de Hogar Netflix.")
        
    return render_template('resultado.html', contenido_html=html_correo, email=correo)

# =====================================================================
# ARRANQUE DE LA APLICACIÓN
# =====================================================================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)