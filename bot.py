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

# 4. Manejador de mensajes con múltiples modelos de respaldo (Fuerza Bruta)
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Lista de modelos a probar en orden por si alguno falla
    models_to_try = [
        "llama-3.3-70b-versatile",
        "llama3-70b-8192",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768"
    ]
    
    success = False
    response_text = ""
    
    for model_name in models_to_try:
        try:
            payload = {
                "model": model_name,
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
                success = True
                break # Si funciona con uno, salimos del bucle
        except Exception:
            continue
            
    if success:
        bot.reply_to(message, response_text)
    else:
        bot.reply_to(message, "⚠️ Error conectando con todos los modelos de Groq. Revisa la clave.")

if __name__ == "__main__":
    print("🤖 Bot MANOLETE iniciado correctamente y escuchando...")
    bot.infinity_polling()
