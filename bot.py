import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import requests
import urllib.parse
import io

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
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system", 
                "content": "Eres MANOLETE, un asistente de IA experto en tecnología y programación. Responde siempre en español de forma clara."
            },
            {
                "role": "user", 
                "content": texto_usuario
            }
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        if response.status_code == 200:
            res_json = response.json()
            respuesta_texto = res_json['choices'][0]['message']['content']
            await update.message.reply_text(respuesta_texto)
        else:
            logger.error(f"Groq error details: {response.text}")
            await update.message.reply_text(f"⚠️ Error de API Groq ({response.status_code})")
    except Exception as e:
        logger.error(f"Excepción Groq: {e}")
        await update.message.reply_text(f"⚠️ Excepción conectando con IA: {str(e)}")

def main():
    # Asegurarnos de borrar cualquier webhook previo para que el Polling funcione libremente
    requests.get(f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/deleteWebhook?drop_pending_updates=true")
    
    # Construir la aplicación de Telegram
    application = Application.builder().token(TOKEN_TELEGRAM).build()

    # Registrar manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("imagen", crear_imagen))
    application.add_handler(CommandHandler("musica", comando_musica))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_ia))

    logger.info("Iniciando Manolete en modo Long Polling...")
    # Arrancar el bot con polling continuo
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
