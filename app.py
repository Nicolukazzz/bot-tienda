from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# Configuración inicial
load_dotenv()
app = Flask(__name__)

# Credenciales WhatsApp
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
API_VERSION = "v19.0"

# Estados del flujo conversacional
ESTADOS = {
    "INICIO": 0,
    "ENVIAR_CATALOGO": 1,
    "PROCESAR_PEDIDO": 2,
    "CONFIRMAR_PEDIDO": 3,
    "DATOS_CLIENTE": 4,
    "FINALIZADO": 5
}

# Datos temporales (en producción usa base de datos)
sesiones = {}

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    hub_mode = request.args.get("hub.mode")
    hub_token = request.args.get("hub.verify_token")
    hub_challenge = request.args.get("hub.challenge")
    
    if hub_mode == "subscribe" and hub_token == VERIFY_TOKEN:
        print("✅ Webhook verificado")
        return hub_challenge, 200
    return "Verificación fallida", 403

@app.route("/webhook", methods=["POST"])
def recibir_mensajes():
    try:
        data = request.get_json()
        
        if data.get("object") != "whatsapp_business_account":
            return jsonify({"error": "Estructura inválida"}), 400

        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" in value:
            message = value["messages"][0]
            numero = message["from"]
            texto = message["text"]["body"].lower() if message["type"] == "text" else None
            
            print(f"📩 Mensaje de {numero}: {texto}")

            # Manejo del estado de conversación
            estado_actual = sesiones.get(numero, {}).get("estado", ESTADOS["INICIO"])
            
            if estado_actual == ESTADOS["INICIO"]:
                manejar_inicio(numero, texto)
            elif estado_actual == ESTADOS["ENVIAR_CATALOGO"]:
                manejar_envio_catalogo(numero, texto)
            elif estado_actual == ESTADOS["PROCESAR_PEDIDO"]:
                manejar_procesar_pedido(numero, texto)
            elif estado_actual == ESTADOS["CONFIRMAR_PEDIDO"]:
                manejar_confirmar_pedido(numero, texto)
            elif estado_actual == ESTADOS["DATOS_CLIENTE"]:
                manejar_datos_cliente(numero, texto)
                
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"status": "error"}), 500

# --- Funciones de manejo de estados ---
def manejar_inicio(numero, texto):
    if any(palabra in texto for palabra in ["hola", "buenas", "quiero comprar"]):
        mensaje = (
            "💅 *Bienvenida a Nails Color* 💅\n\n"
            "¡Gracias por contactarnos! Aquí puedes hacer tu pedido de esmaltes profesionales.\n\n"
            "📌 *Instrucciones:*\n"
            "1. Te enviaré nuestro catálogo visual\n"
            "2. Me indicas los productos con el formato:\n"
            "   *[Código] [Cantidad]* (ej: A12 2)\n"
            "3. Confirmaremos tu pedido\n\n"
            "¿Lista para comenzar? (Sí/No)"
        )
        sesiones[numero] = {"estado": ESTADOS["ENVIAR_CATALOGO"]}
    else:
        mensaje = (
            "💬 Por favor indícanos si deseas:\n\n"
            "• Ver catálogo y hacer pedido\n"
            "• Consultar promociones\n"
            "• Hablar con asesor"
        )
    enviar_respuesta(numero, mensaje)

def manejar_envio_catalogo(numero, texto):
    if texto.lower() in ["sí", "si", "yes"]:
        # Envía el enlace al catálogo (PDF/imagen)
        mensaje = (
            "🎨 *Catálogo de Esmaltes* 🎨\n\n"
            "Puedes ver todos nuestros colores aquí:\n"
            "https://drive.google.com/... (enlace a tu PDF/imagen)\n\n"
            "📝 *Formato para pedir:*\n"
            "Envía los códigos con sus cantidades, ejemplo:\n"
            "A12 2\nB05 1\nC18 3\n\n"
            "Cuando termines escribe *'Listo'*"
        )
        sesiones[numero] = {
            "estado": ESTADOS["PROCESAR_PEDIDO"],
            "pedido": {}
        }
    else:
        mensaje = "¿En qué más podemos ayudarte?"
        sesiones[numero] = {"estado": ESTADOS["INICIO"]}
    
    enviar_respuesta(numero, mensaje)
    
    # Opcional: Enviar imagen del catálogo directamente
    # enviar_imagen(numero, "https://ejemplo.com/catalogo.jpg")

def manejar_procesar_pedido(numero, texto):
    if texto.lower() == "listo":
        if not sesiones[numero]["pedido"]:
            enviar_respuesta(numero, "⚠️ No has agregado productos. Por favor envía códigos con cantidades.")
            return
        
        mensaje = "🛒 *Resumen de tu pedido:*\n\n"
        total = 0
        for codigo, detalle in sesiones[numero]["pedido"].items():
            mensaje += f"• {codigo}: {detalle['cantidad']} und x ${detalle['precio']} = ${detalle['cantidad'] * detalle['precio']}\n"
            total += detalle['cantidad'] * detalle['precio']
        
        mensaje += f"\n💲 *Total a pagar: ${total}*\n\n"
        mensaje += "¿Confirmas este pedido? (Sí/No)"
        
        sesiones[numero]["estado"] = ESTADOS["CONFIRMAR_PEDIDO"]
        sesiones[numero]["total"] = total
        enviar_respuesta(numero, mensaje)
    else:
        try:
            # Procesar línea de pedido (formato: Código Cantidad)
            partes = texto.split()
            if len(partes) != 2:
                raise ValueError
            
            codigo = partes[0].upper()
            cantidad = int(partes[1])
            
            if cantidad <= 0:
                raise ValueError
            
            # Simulación: Obtener precio de base de datos (en producción)
            precio = obtener_precio_producto(codigo)  # Función simulada
            
            if precio:
                sesiones[numero]["pedido"][codigo] = {
                    "cantidad": cantidad,
                    "precio": precio
                }
                enviar_respuesta(numero, f"✅ Añadido: {codigo} x {cantidad}\nContinúa agregando o escribe *'Listo'*")
            else:
                enviar_respuesta(numero, f"⚠️ Código {codigo} no válido. Verifica el catálogo.")
                
        except ValueError:
            enviar_respuesta(numero, "⚠️ Formato incorrecto. Usa: *[Código] [Cantidad]* (ej: A12 2)")

def manejar_confirmar_pedido(numero, texto):
    if texto.lower() in ["sí", "si", "yes"]:
        sesiones[numero]["estado"] = ESTADOS["DATOS_CLIENTE"]
        enviar_respuesta(numero, (
            "📝 *Datos para el envío*\n\n"
            "Por favor envía:\n"
            "1. Nombre completo\n"
            "2. Dirección exacta\n"
            "3. Teléfono de contacto\n"
            "4. Método de pago (Efectivo/Transferencia)\n\n"
            "Ejemplo:\n"
            "María López\n"
            "Av. Principal 123, Lima\n"
            "999888777\n"
            "Transferencia"
        ))
    else:
        sesiones[numero] = {"estado": ESTADOS["INICIO"]}
        enviar_respuesta(numero, "❌ Pedido cancelado. ¿Deseas comenzar de nuevo?")

def manejar_datos_cliente(numero, texto):
    try:
        lineas = [linea.strip() for linea in texto.split('\n') if linea.strip()]
        if len(lineas) >= 4:
            pedido = sesiones[numero]
            pedido["cliente"] = {
                "nombre": lineas[0],
                "direccion": lineas[1],
                "telefono": lineas[2],
                "pago": lineas[3],
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Generar resumen final
            resumen = (
                "✅ *Pedido Confirmado* ✅\n\n"
                f"📋 *N° Pedido:* {hash(frozenset(pedido.items()))}\n"
                f"👤 *Cliente:* {pedido['cliente']['nombre']}\n"
                f"📞 *Contacto:* {pedido['cliente']['telefono']}\n"
                f"🏠 *Envío:* {pedido['cliente']['direccion']}\n"
                f"💳 *Pago:* {pedido['cliente']['pago']}\n"
                f"💲 *Total:* ${pedido['total']}\n\n"
                "📬 Te contactaremos para coordinar el pago y envío.\n"
                "¡Gracias por tu compra! 💅✨"
            )
            
            enviar_respuesta(numero, resumen)
            
            # Aquí deberías guardar el pedido en tu base de datos
            print(f"\n🔥 Nuevo pedido registrado: {pedido}")
            
            # Opcional: Enviar confirmación por correo/otro sistema
            # enviar_notificacion_pedido(pedido)
            
            # Reiniciar estado
            sesiones[numero]["estado"] = ESTADOS["FINALIZADO"]
        else:
            enviar_respuesta(numero, "⚠️ Faltan datos. Por favor envía exactamente 4 líneas como en el ejemplo.")
    except Exception as e:
        print(f"Error procesando datos: {str(e)}")
        enviar_respuesta(numero, "⚠️ Error al procesar. Por favor envía los datos nuevamente.")

# --- Funciones auxiliares ---
def obtener_precio_producto(codigo):
    """Función simulada - en producción conecta a tu base de datos"""
    # Ejemplo básico (deberías tener tu propia lógica aquí)
    precios = {
        "A12": 15, "B05": 18, "C18": 20,
        "D22": 16, "E07": 17, "F15": 19
    }
    return precios.get(codigo)

def enviar_respuesta(numero, mensaje):
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error enviando mensaje: {str(e)}")

def enviar_imagen(numero, url_imagen):
    """Función para enviar imagen del catálogo"""
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "image",
        "image": {
            "link": url_imagen,
            "caption": "🎨 Catálogo actualizado de esmaltes"
        }
    }
    # Implementación similar a enviar_respuesta()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))