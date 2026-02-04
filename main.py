import os
import base64
import re
from flask import Flask, render_template, request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)

def get_gmail_service():
    creds = None
    token_path = '/etc/secrets/token.json' if os.path.exists('/etc/secrets/token.json') else 'token.json'
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/gmail.readonly'])
    return build('gmail', 'v1', credentials=creds)

def obtener_html_netflix(correo_consulta):
    try:
        service = get_gmail_service()
        # Buscamos el correo más reciente de Netflix para ese usuario
        query = f'from:netflix {correo_consulta}'
        results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
        messages = results.get('messages', [])

        if not messages:
            return None

        msg = service.users().messages().get(userId='me', id=messages[0]['id'], format='full').execute()
        
        # Extraemos el cuerpo del correo en HTML
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
        print(f"Error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/consultar', methods=['POST'])
def consultar():
    correo = request.form.get('correo', '').strip().lower()
    html_correo = obtener_html_netflix(correo)
    
    if not html_correo:
        return render_template('resultado.html', error="No se encontró ningún correo reciente de Netflix.")
    
    # Pasamos el HTML directamente a la vista
    return render_template('resultado.html', contenido_html=html_correo, email=correo)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)