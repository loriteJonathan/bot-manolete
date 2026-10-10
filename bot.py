import os
import requests
import telebot

# 1. Cargar el token de Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip().replace("\n", "").replace("\r", "")

# 2. Clave de Groq fija y directa
GROQ_API_KEY = "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"

if not TELEGRAM_TOKEN:
    raise ValueError("Falta TELEGRAM_TOKEN en las variables de entorno.")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

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

# 4. Manejador de mensajes con conexión HTTP directa a Groq
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Eres MANOLETE, un asistente de IA avanzado, directo y muy útil."},
                {"role": "user", "content": message.text}
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        
        if response.status_code == 200:
            response_text = data["choices"][0]["message"]["content"]
            bot.reply_to(message, response_text)
        else:
            error_msg = data.get('error', {}).get('message', str(data))
            bot.reply_to(message, f"⚠️ Error API Groq ({response.status_code}): {error_msg}")
            
    except Exception as e:
        bot.reply_to(message, f"⚠️ Excepción conectando con IA: {str(e)}")

if __name__ == "__main__":
    print("🤖 Bot MANOLETE iniciado correctamente y escuchando...")
    bot.infinity_polling()
