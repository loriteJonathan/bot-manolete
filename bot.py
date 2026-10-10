import os
import telebot
from groq import Groq

# 1. Cargar y limpiar estrictamente las credenciales para evitar saltos de línea (\n, \r) o espacios
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip().replace("\n", "").replace("\r", "")
clean_groq_key = os.environ.get("GROQ_API_KEY", "").strip().replace("\n", "").replace("\r", "")

# Validar que las variables estén configuradas
if not TELEGRAM_TOKEN or not clean_groq_key:
    raise ValueError("Faltan TELEGRAM_TOKEN o GROQ_API_KEY en las variables de entorno de Railway.")

# 2. Inicializar los clientes de Telegram y Groq con la clave ya saneada
bot = telebot.TeleBot(TELEGRAM_TOKEN)
groq_client = Groq(api_key=clean_groq_key)

# 3. Comando /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🤖 ¡Hola! Soy **MANOLETE**, tu asistente de IA avanzado y programador.\n\n"
        "Pregúntame lo que necesites o usa:\n"
        "🎵 `/musica [tema]`\n"
        "🎨 `/imagen [descripcion]`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# 4. Manejador para los mensajes de texto (conecta con la IA de Groq)
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        # Petición a la API de Groq
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
        # En caso de error, devuelve el aviso para fácil depuración
        bot.reply_to(message, f"⚠️ Error conectando con IA: {str(e)}")

if __name__ == "__main__":
    print("🤖 Bot MANOLETE iniciado correctamente y escuchando...")
    bot.infinity_polling()
