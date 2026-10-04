import os
import logging
import asyncio
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

# Construir la aplicación de Telegram
telegram_app = Application.builder().token(TOKEN_TELEGRAM).build()

# Registrar manejadores
async def start(update: Update, context):
    if not es_chat_permitido(update):
        return
    await update.message.reply_text(
        "🤖 ¡Hola! Soy **MANOLETE**, tu asistente de IA avanzado y programador.\n\n"
        "Pregúntame lo que necesites o usa:\n"
        "🎵 `/musica [tema]`\n"
        "🎨 `/imagen [descripción]`"
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

    try:
        img_response = requests.get(url_imagen, timeout=60)
        if img_response.status_code == 200:
            photo_bytes = io.BytesIO(img_response.content)
            photo_bytes.name = 'manolete.jpg'
            await update.message.reply_photo(photo=photo_bytes, caption=f"🎨 *{prompt_usuario}*", parse_mode="Markdown")
            return
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error generando imagen: {str(e)}")
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

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("imagen", crear_imagen))
telegram_app.add_handler(CommandHandler("musica", comando_musica))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_ia))

# Inicializar la aplicación de Telegram para que procese los updates correctamente
async def inicializar_bot():
    await telegram_app.initialize()

# Ejecutar la inicialización en el arranque de Gunicorn/Flask
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(inicializar_bot())

# Registro automático del Webhook al arrancar
url_render = os.environ.get("RENDER_EXTERNAL_URL")
if url_render:
    webhook_url = f"{url_render}/{TOKEN_TELEGRAM}"
    requests.get(f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/setWebhook?url={webhook_url}")
    logger.info(f"Webhook configurado en: {webhook_url}")

@app_flask.route('/')
def home():
    return "Bot Manolete is running perfectly with Gunicorn!"

@app_flask.route(f'/{TOKEN_TELEGRAM}', methods=['POST'])
def webhook():
    try:
        json_update = request.get_json(force=True)
        update = Update.de_json(json_update, telegram_app.bot)
        
        # Procesar el update de forma asíncrona dentro del bucle de eventos
        async def procesar():
            await telegram_app.process_update(update)

        loop.run_until_complete(procesar())
        return "OK", 200
    except Exception as e:
        logger.error(f"Error procesando update: {e}")
        return "Error", 500

if __name__ == '__main__':
    app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
