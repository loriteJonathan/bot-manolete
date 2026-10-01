import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
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
TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRAM")
API_KEY_AEMET = os.environ.get("API_KEY_AEMET", "")

# --- SEGURIDAD (GRUPOS PERMITIDOS) ---
GRUPOS_PERMITIDOS = [-1770410209]

def es_chat_permitido(update: Update) -> bool:
    if not update.effective_chat:
        return False
    # Permite chats privados (tipo 'private') o el grupo autorizado
    if update.effective_chat.type == 'private':
        return True
    return update.effective_chat.id in GRUPOS_PERMITIDOS

# --- SERVIDOR WEB PARA RENDER ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Manolete is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# --- FUNCIONES DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def comando_musica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_chat_permitido(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Escribe qué quieres buscar. Ejemplo: `/musica rock`")
        return
    query = " ".join(context.args)
    titulo, enlace = await buscar_en_youtube(query)
    await update.message.reply_text(f"🎵 **{titulo}**\n\n🔗 Enlace:\n{enlace}")

async def crear_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_chat_permitido(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Escribe una descripción. Ejemplo: `/imagen un gato con gafas`")
        return

    prompt_usuario = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    
    url_imagen = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt_usuario)}"

    try:
        img_response = requests.get(url_imagen, timeout=30)
        if img_response.status_code == 200:
            photo_bytes = io.BytesIO(img_response.content)
            photo_bytes.name = 'manolete.jpg'
            await update.message.reply_photo(photo=photo_bytes, caption=f"🎨 *{prompt_usuario}*", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ No se pudo generar la imagen.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def responder_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {
                "role": "system", 
                "content": f"Eres MANOLETE, un asistente de IA experto en programación y tecnología. Responde siempre en español de forma precisa. Fecha actual: {ahora}."
            },
            {"role": "user", "content": texto_usuario}
        ],
        "max_tokens": 2048,
        "temperature": 0.7
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

def main():
    # Iniciar servidor web en segundo plano para Render
    threading.Thread(target=run_web_server, daemon=True).start()

    # Construir aplicación de Telegram
    app = ApplicationBuilder().token(TOKEN_TELEGRAM).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("imagen", crear_imagen))
    app.add_handler(CommandHandler("musica", comando_musica))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_ia))

    logger.info("Iniciando Bot Manolete...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
