from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
import hashlib

# Configuración inicial
load_dotenv()
app = Flask(__name__)

# Credenciales WhatsApp
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
API_VERSION = "v19.0"

# Estados del flujo
ESTADOS = {
    "INICIO": 0,
    "CATALOGO": 1,
    "PROCESAR_PEDIDO": 2,
    "CONFIRMAR": 3,
    "DATOS_CLIENTE": 4,
    "FINALIZADO": 5,
    "PROMOCIONES": 6,
    "ASESOR": 7,
    "SEGUIMIENTO": 8
}

# Comandos globales
COMANDOS_GLOBALES = {
    "menu": "Volver al menú principal",
    "cancelar": "Cancelar pedido actual",
    "ayuda": "Mostrar opciones disponibles"
}

# Base de datos temporal
sesiones = {}

# Precios de productos
PRECIOS = {
    "A12": {"nombre": "Esmalte Rojo Pasión", "precio": 15},
    "B05": {"nombre": "Esmalte Azul Noche", "precio": 18},
    "C18": {"nombre": "Esmalte Verde Esmeralda", "precio": 20},
    "D22": {"nombre": "Esmalte Rosa Chic", "precio": 16},
    "E07": {"nombre": "Esmalte Negro Elegante", "precio": 17},
    "F15": {"nombre": "Esmalte Dorado Brillante", "precio": 19}
}

# Promociones
PROMOCIONES = [
    "🎉 2x1 en todos los esmaltes los martes",
    "💅 Combo 3 esmaltes por $45 (Ahorra $10)",
    "🛍️ Envío gratis en compras mayores a $50"
]

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

            # Verificar comandos globales primero
            if texto in COMANDOS_GLOBALES:
                manejar_comando_global(numero, texto)
                return jsonify({"status": "success"}), 200

            # Manejo del estado actual
            estado_actual = sesiones.get(numero, {}).get("estado", ESTADOS["INICIO"])
            
            if estado_actual == ESTADOS["INICIO"]:
                manejar_inicio(numero, texto)
            elif estado_actual == ESTADOS["CATALOGO"]:
                manejar_catalogo(numero, texto)
            elif estado_actual == ESTADOS["PROCESAR_PEDIDO"]:
                manejar_procesar_pedido(numero, texto)
            elif estado_actual == ESTADOS["CONFIRMAR"]:
                manejar_confirmar(numero, texto)
            elif estado_actual == ESTADOS["DATOS_CLIENTE"]:
                manejar_datos_cliente(numero, texto)
            elif estado_actual == ESTADOS["PROMOCIONES"]:
                manejar_promociones(numero, texto)
            elif estado_actual == ESTADOS["ASESOR"]:
                manejar_asesor(numero, texto)
            elif estado_actual == ESTADOS["SEGUIMIENTO"]:
                manejar_seguimiento(numero, texto)
                
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"status": "error"}), 500

# --- Manejo de comandos globales ---
def manejar_comando_global(numero, comando):
    if comando == "menu":
        sesiones[numero] = {"estado": ESTADOS["INICIO"]}
        manejar_inicio(numero, "menu")
    elif comando == "cancelar":
        if numero in sesiones:
            del sesiones[numero]
        enviar_respuesta(numero, "❌ Pedido cancelado. ¿Deseas comenzar de nuevo? (Sí/No)")
    elif comando == "ayuda":
        mensaje = "🆘 *Opciones disponibles en cualquier momento:*\n\n"
        for cmd, desc in COMANDOS_GLOBALES.items():
            mensaje += f"• *{cmd}*: {desc}\n"
        mensaje += "\nTambién puedes usar números para seleccionar opciones."
        enviar_respuesta(numero, mensaje)

# --- Flujo principal ---
def manejar_inicio(numero, texto):
    if texto == "1":
        sesiones[numero] = {"estado": ESTADOS["CATALOGO"]}
        manejar_catalogo(numero, texto)
    elif texto == "2":
        sesiones[numero] = {"estado": ESTADOS["PROMOCIONES"]}
        manejar_promociones(numero, texto)
    elif texto == "3":
        sesiones[numero] = {"estado": ESTADOS["ASESOR"]}
        manejar_asesor(numero, texto)
    elif texto == "4":
        sesiones[numero] = {"estado": ESTADOS["SEGUIMIENTO"]}
        manejar_seguimiento(numero, texto)
    else:
        mensaje = (
            "💅 *Bienvenida a Nails Color* 💅\n\n"
            "Elige una opción:\n\n"
            "1️⃣ Ver catálogo y hacer pedido\n"
            "2️⃣ Consultar promociones\n"
            "3️⃣ Hablar con asesor\n"
            "4️⃣ Seguir mi pedido\n\n"
            "ℹ️ Escribe *ayuda* en cualquier momento para ver opciones."
        )
        sesiones[numero] = {"estado": ESTADOS["INICIO"]}
        enviar_respuesta(numero, mensaje)

def manejar_catalogo(numero, texto):
    # Mostrar catálogo directamente
    mensaje = (
        "🎨 *Catálogo de Esmaltes* 🎨\n\n"
        "🔍 Visualiza nuestros productos aquí:\n"
        "https://drive.google.com/catalogo.pdf\n\n"
        "📝 *Para pedir usa el formato:*\n"
        "*[Código] [Cantidad]*\n"
        "Ejemplo:\n"
        "A12 2\n"
        "B05 1\n\n"
        "Cuando termines escribe *'Listo'*\n"
        "ℹ️ Comandos: *menu*, *cancelar*, *ayuda*"
    )
    
    # Mostrar lista de productos disponibles
    mensaje += "\n\n📦 *Productos disponibles:*\n"
    for codigo, producto in PRECIOS.items():
        mensaje += f"• {codigo}: {producto['nombre']} - ${producto['precio']}\n"
    
    sesiones[numero] = {
        "estado": ESTADOS["PROCESAR_PEDIDO"],
        "pedido": {}
    }
    enviar_respuesta(numero, mensaje)

def manejar_procesar_pedido(numero, texto):
    if texto.lower() == "listo":
        if not sesiones[numero]["pedido"]:
            enviar_respuesta(numero, "🛒 Tu pedido está vacío. Agrega productos o escribe *cancelar*")
            return
        
        total = sum(item["cantidad"] * item["precio"] for item in sesiones[numero]["pedido"].values())
        sesiones[numero]["total"] = total
        
        mensaje = "🛒 *Resumen de Pedido*\n\n"
        for codigo, item in sesiones[numero]["pedido"].items():
            mensaje += f"• {codigo}: {item['cantidad']} x ${item['precio']} = ${item['cantidad'] * item['precio']}\n"
        
        mensaje += f"\n💲 *Total: ${total}*\n\n"
        mensaje += "1️⃣ Confirmar pedido\n"
        mensaje += "2️⃣ Modificar pedido\n"
        mensaje += "3️⃣ Cancelar\n"
        mensaje += "4️⃣ Volver al menú"
        
        sesiones[numero]["estado"] = ESTADOS["CONFIRMAR"]
        enviar_respuesta(numero, mensaje)
    else:
        try:
            # Procesar línea de pedido
            codigo, cantidad = texto.split()
            codigo = codigo.upper()
            cantidad = int(cantidad)
            
            if cantidad <= 0:
                raise ValueError
            
            if codigo not in PRECIOS:
                enviar_respuesta(numero, f"⚠️ Código {codigo} no válido. Verifica el catálogo.")
                return
            
            sesiones[numero]["pedido"][codigo] = {
                "nombre": PRECIOS[codigo]["nombre"],
                "cantidad": cantidad,
                "precio": PRECIOS[codigo]["precio"]
            }
            
            enviar_respuesta(numero, f"✅ Añadido: {PRECIOS[codigo]['nombre']} x {cantidad}\nContinúa o escribe *Listo*")
            
        except ValueError:
            enviar_respuesta(numero, "⚠️ Formato incorrecto. Usa: *[Código] [Cantidad]* o escribe *ayuda*")

def manejar_confirmar(numero, texto):
    if texto == "1":  # Confirmar
        sesiones[numero]["estado"] = ESTADOS["DATOS_CLIENTE"]
        enviar_respuesta(numero, (
            "📝 *Datos para el envío*\n\n"
            "Por favor envía:\n"
            "1. Nombre completo\n"
            "2. Dirección exacta\n"
            "3. Teléfono\n"
            "4. Método de pago\n\n"
            "Ejemplo:\n"
            "María López\n"
            "Av. Principal 123\n"
            "999888777\n"
            "Transferencia\n\n"
            "ℹ️ Escribe *cancelar* si deseas anular."
        ))
    elif texto == "2":  # Modificar
        sesiones[numero]["estado"] = ESTADOS["PROCESAR_PEDIDO"]
        enviar_respuesta(numero, "📝 Envía los productos nuevamente con el formato [Código] [Cantidad]")
    elif texto == "3":  # Cancelar
        manejar_comando_global(numero, "cancelar")
    elif texto == "4":  # Menú
        manejar_comando_global(numero, "menu")
    else:
        enviar_respuesta(numero, "⚠️ Opción no válida. Elige 1, 2, 3 o 4")

def manejar_datos_cliente(numero, texto):
    try:
        lineas = [linea.strip() for linea in texto.split('\n') if linea.strip()]
        if len(lineas) >= 4:
            sesiones[numero]["cliente"] = {
                "nombre": lineas[0],
                "direccion": lineas[1],
                "telefono": lineas[2],
                "pago": lineas[3],
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Generar número de pedido único
            pedido_hash = hashlib.md5(str(sesiones[numero]).encode()).hexdigest()[:8].upper()
            
            # Generar confirmación
            pedido = sesiones[numero]
            resumen = (
                "✅ *¡Pedido Confirmado!* ✅\n\n"
                f"📋 *N° Pedido:* {pedido_hash}\n"
                f"👤 *Cliente:* {pedido['cliente']['nombre']}\n"
                f"📞 *Contacto:* {pedido['cliente']['telefono']}\n"
                f"📍 *Dirección:* {pedido['cliente']['direccion']}\n"
                f"💳 *Pago:* {pedido['cliente']['pago']}\n\n"
                "🛍️ *Detalles del pedido:*\n"
            )
            
            for codigo, item in pedido["pedido"].items():
                resumen += f"• {item['nombre']}: {item['cantidad']} x ${item['precio']} = ${item['cantidad'] * item['precio']}\n"
            
            resumen += (
                f"\n💲 *Total:* ${pedido['total']}\n\n"
                "📬 Recibirás los detalles de pago por este medio.\n"
                "¡Gracias por tu compra! 💖\n\n"
                "Escribe *menu* para volver al inicio."
            )
            
            enviar_respuesta(numero, resumen)
            
            # Guardar en base de datos (implementar)
            guardar_pedido(pedido, pedido_hash)
            
            sesiones[numero]["estado"] = ESTADOS["FINALIZADO"]
        else:
            enviar_respuesta(numero, "⚠️ Faltan datos. Por favor envía 4 líneas como en el ejemplo.")
    except Exception as e:
        print(f"Error procesando datos: {str(e)}")
        enviar_respuesta(numero, "⚠️ Error al procesar. Por favor envía los datos nuevamente.")

# --- Funciones para otras opciones del menú ---
def manejar_promociones(numero, texto):
    mensaje = "🎁 *Promociones Actuales* 🎁\n\n"
    for promo in PROMOCIONES:
        mensaje += f"• {promo}\n"
    
    mensaje += "\n1️⃣ Volver al menú\n2️⃣ Hacer pedido"
    sesiones[numero]["estado"] = ESTADOS["PROMOCIONES"]
    enviar_respuesta(numero, mensaje)

def manejar_asesor(numero, texto):
    mensaje = (
        "👩‍💼 *Asesoría Personalizada*\n\n"
        "Un asesor se pondrá en contacto contigo en breve.\n"
        "Mientras tanto, ¿deseas dejar algún mensaje específico?\n\n"
        "1️⃣ Volver al menú\n"
        "2️⃣ No, esperaré al asesor"
    )
    sesiones[numero]["estado"] = ESTADOS["ASESOR"]
    enviar_respuesta(numero, mensaje)

def manejar_seguimiento(numero, texto):
    mensaje = (
        "📦 *Seguimiento de Pedido*\n\n"
        "Por favor ingresa tu número de pedido:\n"
        "(Ejemplo: ABC123)\n\n"
        "ℹ️ Escribe *menu* para volver al inicio"
    )
    sesiones[numero]["estado"] = ESTADOS["SEGUIMIENTO"]
    enviar_respuesta(numero, mensaje)

# --- Funciones auxiliares ---
def guardar_pedido(pedido, numero_pedido):
    """Guardar en base de datos (implementar)"""
    print(f"📦 Pedido guardado - N° {numero_pedido}: {pedido}")

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
        print(f"📤 Respuesta enviada a {numero}: {response.status_code}")
    except Exception as e:
        print(f"❌ Error enviando mensaje: {str(e)}")

def enviar_imagen(numero, url):
    """Para enviar imágenes del catálogo"""
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "image",
        "image": {"link": url}
    }
    # Implementación similar a enviar_respuesta()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))