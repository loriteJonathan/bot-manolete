import os
import requests
import telebot

# Token real de Telegram integrado directamente
TELEGRAM_TOKEN = "7756860361:AAHd1b5qK6-w_z1b..."

GROQ_API_KEY = "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"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    print(">>> ¡Comando /start recibido en consola!")
    bot.reply_to(message, "🤖 ¡Hola! Soy MANOLETE, funcionando a la perfección.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    print(f">>> Mensaje recibido de {message.from_user.first_name}: {message.text}")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "Eres MANOLETE, un asistente de IA avanzado, directo y muy útil."},
            {"role": "user", "content": message.text}
        ],
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        data = response.json()
        
        if response.status_code == 200:
            response_text = data["choices"][0]["message"]["content"]
            bot.reply_to(message, response_text)
            print(">>> Respuesta enviada con éxito a Telegram")
        else:
            error_desc = data.get('error', {}).get('message', str(data))
            bot.reply_to(message, f"⚠️ Error Groq ({response.status_code}): {error_desc}")
            print(f">>> Error de Groq: {error_desc}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Excepción interna: {str(e)}")
        print(f">>> Excepción: {str(e)}")

if __name__ == "__main__":
    print("🤖 Bot MANOLETE iniciado y escuchando mensajes...")
    bot.infinity_polling(skip_pending=True)
