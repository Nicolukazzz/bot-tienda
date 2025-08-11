from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv

# Carga las variables de entorno
load_dotenv()

app = Flask(__name__)

# Configuración de WhatsApp Business API
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")  # Token de acceso de Meta
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")  # ID de tu número personal verificado
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")  # Token de verificación que elegiste
API_VERSION = "v22.0"  # Versión actualizada (2024)

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    """Verificación inicial del webhook requerida por Meta"""
    hub_mode = request.args.get("hub.mode")
    hub_token = request.args.get("hub.verify_token")
    hub_challenge = request.args.get("hub.challenge")
    
    if hub_mode == "subscribe" and hub_token == VERIFY_TOKEN:
        print("✅ Webhook verificado")
        return hub_challenge, 200
    print("❌ Falló la verificación del webhook")
    return "Verificación fallida", 403

@app.route("/webhook", methods=["POST"])
def recibir_mensajes():
    """Endpoint principal que procesa los mensajes entrantes"""
    try:
        data = request.get_json()
        print(f"\n📦 Datos recibidos: {data}")  # Debug
        
        # Validación básica del payload
        if data.get("object") != "whatsapp_business_account":
            return jsonify({"error": "Estructura inválida"}), 400

        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        # Extrae información del mensaje
        if "messages" in value:
            message = value["messages"][0]
            numero_cliente = message["from"]
            texto = message["text"]["body"].lower() if message["type"] == "text" else None
            
            print(f"📩 Mensaje de {numero_cliente}: {texto or '(multimedia)'}")

            # Lógica de respuestas
            if texto:
                if "hola" in texto:
                    enviar_respuesta(numero_cliente, "¡Hola! Escribe 1 para mayorista, 2 para minorista.")
                elif texto == "1":
                    enviar_respuesta(numero_cliente, "Contacto mayorista: 3000000000")
                elif texto == "2":
                    enviar_respuesta(numero_cliente, "Catálogo: https://drive.google.com/...")
                else:
                    enviar_respuesta(numero_cliente, "Opción no reconocida. Escribe 1 o 2.")
        
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"\n❌ Error procesando mensaje: {str(e)}")
        return jsonify({"status": "error"}), 500

def enviar_respuesta(numero_destino, mensaje):
    """Envía mensajes a través de la API de WhatsApp"""
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": mensaje}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"✅ Respuesta enviada a {numero_destino}")
        return response.json()
    except Exception as e:
        print(f"\n🔥 Error enviando mensaje: {str(e)}")
        print(f"Respuesta de la API: {response.text if 'response' in locals() else 'N/A'}")
        return None

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))