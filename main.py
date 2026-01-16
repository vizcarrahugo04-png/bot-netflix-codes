import os
import base64
import re
from flask import Flask, render_template, request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

app = Flask(__name__)

# Si modificas estos ámbitos, elimina el archivo token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    # RUTAS PARA RENDER: Render guarda los "Secret Files" en /etc/secrets/
    token_path = '/etc/secrets/token.json' if os.path.exists('/etc/secrets/token.json') else 'token.json'
    creds_path = '/etc/secrets/credentials.json' if os.path.exists('/etc/secrets/credentials.json') else 'credentials.json'

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Guardar el token localmente (esto solo funciona en tu PC)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def buscar_codigo(correo_cliente, plataforma):
    service = get_gmail_service()
    
    # Definimos el remitente según la plataforma seleccionada
    remitentes = {
        'netflix': 'info@account.netflix.com',
        'disney': 'disneyplus@mail.disneyplus.com',
        'prime': 'amazon.com'
    }
    
    remitente = remitentes.get(plataforma, 'info@account.netflix.com')
    
    # Buscamos correos que vengan del remitente y mencionen el correo del cliente
    query = f'from:{remitente} {correo_cliente}'
    results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
    messages = results.get('messages', [])

    if not messages:
        return "No se encontró ningún código reciente."

    msg = service.users().messages().get(userId='me', id=messages[0]['id']).execute()
    payload = msg['payload']
    parts = payload.get('parts', [])
    data = ""

    if not parts:
        data = payload['body']['data']
    else:
        data = parts[0]['body']['data']

    # Decodificar el mensaje
    decoded_data = base64.urlsafe_b64decode(data).decode('utf-8')

    # Buscar un código de 4 a 8 dígitos usando expresiones regulares
    codigo = re.findall(r'\b\d{4,8}\b', decoded_data)
    
    return codigo[0] if codigo else "Código no encontrado en el texto del correo."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/consultar', methods=['POST'])
def consultar():
    correo = request.form.get('correo')
    plataforma = request.form.get('plataforma', 'netflix') # Por defecto Netflix
    codigo = buscar_codigo(correo, plataforma)
    return f"<h1>Tu código de {plataforma.upper()} es: {codigo}</h1><br><a href='/'>Volver</a>"

if __name__ == '__main__':
    # Puerto dinámico para Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)