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
        
        # Volvemos a tu query original limpia que sí te funcionaba perfectamente
        query = f'from:netflix {correo_consulta}'
        
        # Traemos una lista pequeña de los últimos correos (máximo 5)
        results = service.users().messages().list(userId='me', q=query, maxResults=5).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return None
            
        # GMAIL entrega la lista siempre ordenada del MÁS RECIENTE al más antiguo.
        # Al seleccionar estrictamente 'messages[0]', aseguramos jalar el último que ha entrado.
        ultimo_mensaje_id = messages[0]['id']
        
        msg = service.users().messages().get(userId='me', id=ultimo_mensaje_id, format='full').execute()
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
# RUTAS Y NAVEGACIÓN (Flask)
# =====================================================================

# 1. Pantalla principal de acceso (PC y Celular con imagen de fondo fija)
@app.route('/', methods=['GET'])
def login_page():
    foto = "/static/img/fondo.jpeg"
    return render_template('login.html', foto_url=foto)

# 2. Procesador de validación de WhatsApp y alertas de pago
@app.route('/verificar', methods=['POST'])
def verificar():
    celular = request.form.get('celular')
    resultado = verificar_cliente(celular)
    
    if resultado["status"] == "ok":
        return redirect('/ver-codigo')
        
    if resultado["status"] in ["aviso_hoy", "aviso_proximo"]:
        return render_template('alerta.html', msg=resultado["msg"])
    
    return render_template('bloqueo.html', msg=resultado["msg"])

# 3. Interfaz del buscador de correos recientes
@app.route('/ver-codigo')
def index():
    return render_template('index.html')

# 4. Buscador y renderizador de HTML espejo de Netflix
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