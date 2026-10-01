import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

import logging
import requests
import urllib.parse
import io
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- TUS CLAVES DESDE RENDER ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRAM")
API_KEY_AEMET = os.environ.get("API_KEY_AEMET", "") 
# -------------------------------

# --- CONFIGURACIÓN DE SEGURIDAD (GRUPOS PERMITIDOS) ---
# Pon aquí los IDs numéricos de tus grupos (suelen empezar por '-100').
GRUPOS_PERMITIDOS = [-1001234567890] 
# -----------------------------------------------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def obtener_modelo_disponible():
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json().get("data", [])
            for m in data:
                mid = m.get("id", "").lower()
                if "whisper" in mid or "orpheus" in mid or "guard" in mid:
                    continue
                return m.get("id")
    except Exception as e:
        print(f"Error buscando modelo: {e}")
    
    return "qwen/qwen3.8-27b"

MODELO_ACTIVO = obtener_modelo_disponible()

def es_chat_permitido(update: Update) -> bool:
    if not update.effective_chat:
        return False
    return update.effective_chat.id in GRUPOS_PERMITIDOS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_chat_permitido(update):
        return
    await update.message.reply_text(
        f"🤖 **MANOLETE (Asistente IA Avanzado & Programador)**\n\n"
        f"💬 **Pregúntame lo que quieras o pídeme código:** Te responderé al detalle.\n"
        f"🎵 `/musica [tema]` - Busca enlaces en YouTube\n"
        f"🎨 `/imagen [descripción]` - Genera imágenes\n"
        f"🌧 `/lluvia [municipio]` - Datos de AEMET"
    )

async def buscar_en_youtube(query):
    url_busqueda = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    return f"Resultados para: {query}", url_busqueda

async def comando_musica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_chat_permitido(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Escribe qué quieres buscar. Ejemplo: `/musica paco de lucia`")
        return
    query = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    titulo, enlace = await buscar_en_youtube(query)
    await update.message.reply_text(f"🎵 **{titulo}**\n\n🔗 Enlaces disponibles:\n{enlace}")

async def crear_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_chat_permitido(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Escribe qué quieres dibujar. Ejemplo: `/imagen un paisaje`")
        return

    prompt_usuario = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    
    prompt_codificado = urllib.parse.quote(prompt_usuario)
    url_imagen = f"https://image.pollinations.ai/prompt/{prompt_codificado}"

    try:
        img_response = requests.get(url_imagen, timeout=30)
        if img_response.status_code == 200:
            photo_bytes = io.BytesIO(img_response.content)
            photo_bytes.name = 'manolete_imagen.jpg'
            
            await update.message.reply_photo(
                photo=photo_bytes, 
                caption=f"🎨 *{prompt_usuario}*",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("⚠ No se pudo generar la imagen.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error al procesar la imagen: {str(e)}")

async def obtener_precipitaciones_aemet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_chat_permitido(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Uso correcto: `/lluvia [nombre del municipio]`")
        return
    
    nombre_municipio = " ".join(context.args).strip()
    url_base_aemet = "https://opendata.aemet.es/opendata/api"
    headers_aemet = {"api_key": API_KEY_AEMET}

    try:
        url_busqueda = f"{url_base_aemet}/maestro/municipios"
        response_busqueda = requests.get(url_busqueda, headers=headers_aemet, timeout=15)
        
        if response_busqueda.status_code == 200:
            datos_busqueda = response_busqueda.json()
            if 'datos' in datos_busqueda:
                response_datos_municipios = requests.get(datos_busqueda['datos'], headers=headers_aemet, timeout=30)
                if response_datos_municipios.status_code == 200:
                    lista_municipios = response_datos_municipios.json()
                    municipio_id = None
                    for muni in lista_municipios:
                        if muni.get('nombre', '').lower() == nombre_municipio.lower():
                            municipio_id = muni.get('id')[2:]
                            break
                            
                    if municipio_id:
                        url_precipitaciones = f"{url_base_aemet}/observacion/convencional/datos/estacion/{municipio_id}"
                        response_precipitaciones = requests.get(url_precipitaciones, headers=headers_aemet, timeout=30)
                        if response_precipitaciones.status_code == 200:
                            datos_precipitaciones = response_precipitaciones.json()
                            if 'datos' in datos_precipitaciones:
                                lista_observaciones = datos_precipitaciones['datos']
                                if lista_observaciones:
                                    ultima_obs = lista_observaciones[-1]
                                    precipitacion_mm = ultima_obs.get('prec', 'Sin datos')
                                    nombre_estacion = ultima_obs.get('ubi', nombre_municipio)
                                    await update.message.reply_text(f"🌧️ **Precipitación en {nombre_estacion} (AEMET):** {precipitacion_mm} mm")
                                else:
                                    await update.message.reply_text(f"⚠️ Sin observaciones recientes para {nombre_municipio}.")
                            else:
                                await update.message.reply_text(f"⚠️ Sin datos de precipitación.")
                        else:
                            await update.message.reply_text("⚠️ Error al consultar AEMET.")
                    else:
                        await update.message.reply_text(f"⚠️ Municipio '{nombre_municipio}' no encontrado.")
                else:
                    await update.message.reply_text("⚠️ Error al descargar municipios.")
            else:
                await update.message.reply_text("⚠️ Error en la respuesta de AEMET.")
        else:
            await update.message.reply_text("⚠️ Error de conexión con AEMET.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Excepción: {str(e)}")

async def responder_ia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_chat_permitido(update):
        return

    texto_usuario = update.message.text
    texto_lower = texto_usuario.lower()
    
    if any(palabra in texto_lower for keyword in ["canción", "enlace", "youtube", "musica", "música", "video", "vídeo"] for palabra in [keyword]):
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        query_limpia = texto_usuario.replace("búscame", "").replace("un enlace", "").replace("de YouTube", "").replace("en YouTube", "").replace("canción", "").strip()
        
        titulo, enlace = await buscar_en_youtube(query_limpia if len(query_limpia) > 3 else texto_usuario)
        await update.message.reply_text(f"🎵 **{titulo}**\n\n🔗 Enlaces disponibles:\n{enlace}")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    ahora = datetime.now()
    fecha_hora_actual = ahora.strftime("%A, %d de %B de %Y a las %H:%M:%S")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODELO_ACTIVO,
        "messages": [
            {
                "role": "system", 
                "content": (
                    f"Eres MANOLETE, un asistente de inteligencia artificial avanzado, experto en programación, desarrollo de software, análisis técnico y resolución de problemas complejos. "
                    f"Responde siempre en español de forma natural, precisa y detallada. "
                    f"Si te piden código de programación, escribe scripts limpios, funcionales y bien comentados utilizando bloques de código en Markdown. "
                    f"INFORMACIÓN TEMPORAL EN TIEMPO REAL: En este preciso instante es {fecha_hora_actual}."
                )
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
            error_detallado = response.text[:300]
            await update.message.reply_text(f"⚠️ Error {response.status_code}:\n{error_detallado}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Excepción de red: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN_TELEGRAM).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("imagen", crear_imagen))
    app.add_handler(CommandHandler("musica", comando_musica))
    app.add_handler(CommandHandler("lluvia", obtener_precipitaciones_aemet))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_ia))

    print(f"MANOLETE experto activo usando: {MODELO_ACTIVO}")
    app.run_polling()
