import os
import re
import telebot
from groq import Groq

# 1. Limpieza total de Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_TOKEN = re.sub(r'\s+', '', TELEGRAM_TOKEN)

# 2. Clave de Groq limpia a prueba de bombas (elimina cualquier espacio o salto oculto)
raw_groq_key = "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"
clean_groq_key = re.sub(r'\s+', '', raw_groq_key)

# Validar que las variables estén configuradas
if not TELEGRAM_TOKEN or not clean_groq_key:
    raise ValueError("Faltan TELEGRAM_TOKEN o GROQ_API_KEY en el entorno.")

# 3. Inicializar los clientes
bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=clean_groq_key)

# 4. Comando /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🤖 ¡Hola! Soy **MANOLETE**, tu asistente de IA avanzado y programador.\n\n"
        "Pregúntame lo que necesites o usa:\n"
        "🎵 `/musica [tema]`\n"
        "🎨 `/imagen [descripcion]`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# 5. Manejador de mensajes de texto (conecta con Groq)
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Eres MANOLETE, un asistente de IA avanzado, directo y muy útil."},
                {"role": "user", "content": message.text}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        
        response_text = completion.choices[0].message.content
        bot.reply_to(message, response_text)
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error conectando con IA: {str(e)}")

if __name__ == "__main__":
    print("🤖 Bot MANOLETE iniciado correctamente y escuchando...")
    bot.infinity_polling()
