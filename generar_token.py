from google_auth_oauthlib.flow import InstalledAppFlow
import os

# Define los permisos
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def generar():
    # Asegúrate de que el archivo credentials.json esté en la misma carpeta
    if not os.path.exists('credentials.json'):
        print("ERROR: No encuentro el archivo credentials.json en esta carpeta")
        return

    # Forzamos a que nos de el enlace manual en la consola
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    
    # Guarda el token
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    print("\n✅ ¡ÉXITO! Se ha creado el archivo token.json en tu carpeta.")

if __name__ == '__main__':
    generar()