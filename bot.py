import os
import telebot
from groq import Groq

# 1. Cargar el token de Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip().replace("\n", "").replace("\r", "")

# 2. Clave de Groq oficial y directa
GROQ_API_KEY = "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"

if not TELEGRAM_TOKEN:
    raise ValueError("Falta TELEGRAM_TOKEN en las variables de entorno.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

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

# 4. Manejador de mensajes con la librería oficial de Groq
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    models_to_try = [
        "llama-3.3-70b-versatile",
        "llama3-70b-8192",
        "llama-3.1-8b-instant"
    ]
    
    response_text = None
    
    for model_name in models_to_try:
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "Eres MANOLETE, un asistente de IA avanzado, directo y muy útil."},
                    {"role": "user", "content": message.text}
                ],
                temperature=0.7,
                max_tokens=1024
            )
            response_text = completion.choices[0].message.content
            break
        except Exception:
            continue
            
    if response_text:
        bot.reply_to(message, response_text)
    else:
        bot.reply_to(message, "⚠️ Error conectando con Groq. Asegúrate de que 'groq' está en requirements.txt")

if __name__ == "__main__":
    print("🤖 Bot MANOLETE iniciado correctamente y escuchando...")
    bot.infinity_polling()
