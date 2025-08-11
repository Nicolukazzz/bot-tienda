from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import requests

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Configuración de WhatsApp Business API
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
API_VERSION = "v22.0" 

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    # Verificación inicial del webhook
    verify_token = os.getenv("VERIFY_TOKEN")
    hub_mode = request.args.get("hub.mode")
    hub_token = request.args.get("hub.verify_token")
    hub_challenge = request.args.get("hub.challenge")
    
    if hub_mode == "subscribe" and hub_token == verify_token:
        return hub_challenge, 200
    return "Verificación fallida", 403

@app.route("/webhook", methods=["POST"])
def recibir_mensajes():
    data = request.get_json()
    
    try:
        # Procesar mensaje entrante
        if data.get("object") == "whatsapp_business_account":
            entry = data["entry"][0]
            changes = entry["changes"][0]
            message = changes["value"]["messages"][0]
            
            numero_cliente = message["from"]
            texto = message["text"]["body"].lower()
            
            # Lógica de respuestas
            if "hola" in texto:
                enviar_respuesta(numero_cliente, "¡Hola! Escribe 1 para mayorista, 2 para minorista.")
            elif texto == "1":
                enviar_respuesta(numero_cliente, "Contacto mayorista: 3000000000")
            elif texto == "2":
                enviar_respuesta(numero_cliente, "Catálogo: [enlace a Google Drive]")
            else:
                enviar_respuesta(numero_cliente, "Opción no reconocida. Escribe 1 o 2.")
                
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"status": "error"}), 500

def enviar_respuesta(numero_destino, mensaje):
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": mensaje}
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)