from flask import Flask, request
import requests
import os

app = Flask(__name__)

# Variables de entorno (Render las manejará)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "miverificacion123")

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Verificación del Webhook
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode and token:
            if token == VERIFY_TOKEN:
                return challenge, 200
            else:
                return "Token de verificación inválido", 403

    elif request.method == "POST":
        data = request.get_json()
        print("📩 Mensaje entrante:", data)

        try:
            mensajes = data["entry"][0]["changes"][0]["value"]["messages"]
            if mensajes:
                mensaje = mensajes[0]
                texto = mensaje.get("text", {}).get("body", "").lower()
                numero = mensaje["from"]

                # Menú básico
                if "hola" in texto:
                    enviar_mensaje(numero, "¡Hola! 👋 Escribe 1 para mayorista, 2 para minorista.")
                elif texto == "1":
                    enviar_mensaje(numero, "Contacto mayorista 📞 3000000000")
                elif texto == "2":
                    enviar_mensaje(numero, "Aquí tienes el catálogo 📦: [enlace]")
                else:
                    enviar_mensaje(numero, "No entendí 😅. Escribe 1 o 2.")
        except Exception as e:
            print("⚠️ Error procesando mensaje:", e)

        return "EVENT_RECEIVED", 200


def enviar_mensaje(numero, texto):
    """Envia un mensaje de texto usando la API de WhatsApp Cloud"""
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }
    r = requests.post(url, headers=headers, json=body)
    if r.status_code != 200:
        print(f"❌ Error enviando mensaje: {r.status_code} {r.text}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
