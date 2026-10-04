import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import requests
import urllib.parse
import io
from datetime import datetime

# --- CONFIGURACIÓN DE LOGS ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CREDENCIALES ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TOKEN_TELEGRAM = "2096960353:AAEwe0Hp9gE0PpX3EaHUvFDdzVRDNuTYjSw"

# --- SEGURIDAD (GRUPOS PERMITIDOS) ---
GRUPOS_PERMITIDOS = [-1001770410209]

def es_chat_permitido(update: Update) -> bool:
    if not update.effective_chat:
        return False
    if update.effective_chat.type == 'private':
        return True
    return update.effective_chat.id in GRUPOS_PERMITIDOS

# --- APLICACIÓN FLASK Y TELEGRAM ---
app_flask = Flask(__name__)
telegram_app = None

async def setup_telegram():
    global telegram_app
    if not telegram_app:
        telegram_app = Application.builder().token(TOKEN_TELEGRAM).updater(None).build()
        
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(CommandHandler("imagen", crear_imagen))
        telegram_app.add_handler(CommandHandler("musica", comando_musica))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_ia))
        
        await telegram_app.initialize()

@app_flask.route('/')
def home():
    return "Bot Manolete is running via Webhook!"

@app_flask.route(f'/{TOKEN_TELEGRAM}', methods=['POST'])
def webhook():
    try:
        json_update = request.get_json(force=True)
        update = Update.de_json(json_update, telegram_app.bot)
        
        # Ejecutar el update de forma asíncrona en el bucle de eventos
        import asyncio
        asyncio.run(telegram_app.process_update(update))
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Error procesando update: {e}")
        return "Error", 500

# --- FUNCIONES DEL BOT ---
async def start(update: Update, context):
    if not es_chat_permitido(update):
        return
    await update.message.reply_text(
        "🤖 ¡Hola! Soy **MANOLETE**, tu asistente de IA avanzado y programador.\n\n"
        "Pregúntame lo que necesites o usa:\n"
        "🎵 `/musica [tema]`\n"
        "🎨 `/imagen [descripción]`\n"
        "🌧 `/lluvia [municipio]`"
    )

async def buscar_en_youtube(query):
    url_busqueda = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    return f"Resultados para: {query}", url_busqueda

async def comando_musica(update: Update, context):
    if not es_chat_permitido(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Escribe qué quieres buscar. Ejemplo: `/musica rock`")
        return
    query = " ".join(context.args)
    titulo, enlace = await buscar_en_youtube(query)
    await update.message.reply_text(f"🎵 **{titulo}**\n\n🔗 Enlace:\n{enlace}")

async def crear_imagen(update: Update, context):
    if not es_chat_permitido(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Escribe una descripción. Ejemplo: `/imagen un gato con gafas`")
        return

    prompt_usuario = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    
    url_imagen = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt_usuario)}"

    intentos = 3
    for intento in range(intentos):
        try:
            img_response = requests.get(url_imagen, timeout=60)
            if img_response.status_code == 200:
                photo_bytes = io.BytesIO(img_response.content)
                photo_bytes.name = 'manolete.jpg'
                await update.message.reply_photo(photo=photo_bytes, caption=f"🎨 *{prompt_usuario}*", parse_mode="Markdown")
                return
        except requests.exceptions.Timeout:
            if intento == intentos - 1:
                await update.message.reply_text("⚠️ El servicio de imágenes está tardando demasiado en responder. Prueba otra vez en un minuto.")
                return
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {str(e)}")
            return

async def responder_ia(update: Update, context):
    if not es_chat_permitido(update):
        return

    texto_usuario = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    ahora = datetime.now().strftime("%A, %d de %B de %Y a las %H:%M:%S")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {
                "role": "system", 
                "content": f"Eres MANOLETE, un asistente de IA experto en programación y tecnología. Responde siempre en español. Fecha actual: {ahora}."
            },
            {"role": "user", "content": texto_usuario}
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        if response.status_code == 200:
            res_json = response.json()
            respuesta_texto = res_json['choices'][0]['message']['content']
            await update.message.reply_text(respuesta_texto)
        else:
            await update.message.reply_text(f"⚠️ Error de API Groq ({response.status_code})")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Excepción conectando con IA: {str(e)}")

# Configurar el Webhook en Telegram al arrancar la app Flask
import asyncio
with app_flask.app_context():
    asyncio.run(setup_telegram())
    # Obtener la URL pública de tu servicio en Render automáticamente o configurarla
    # Render suele inyectar la URL o puedes usar la dirección de tu web service.
    # Como Flask necesita saber a dónde apuntar, configuramos el webhook usando requests:
    # (Asegúrate de cambiar 'tu-servicio.onrender.com' por tu dominio real de Render)
    # Ejemplo: RENDER_EXTERNAL_URL es una variable que Render proporciona automáticamente.
    url_render = os.environ.get("RENDER_EXTERNAL_URL")
    if url_render:
        webhook_url = f"{url_render}/{TOKEN_TELEGRAM}"
        requests.get(f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/setWebhook?url={webhook_url}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)
