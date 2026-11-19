import time
import requests

TELEGRAM_TOKEN = "2096960353:AAFVozuRfP-FBRaqovGF8DiFF6Dm3tMXYnY".strip()
GROQ_API_KEY = "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".strip()

PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]


def clear_webhook():
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook"
        r = requests.get(url, params={"drop_pending_updates": "false"}, timeout=15)
        print(f">>> Webhook check: {r.status_code}")
    except Exception as e:
        print(f">>> No se pudo comprobar webhook: {e}")


def get_available_groq_models():
    url = "https://api.groq.com/openai/v1/models"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    available = []
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
            for pref in PREFERRED_MODELS:
                if pref in ids:
                    available.append(pref)
            for mid in ids:
                if mid not in available and ("llama" in mid or "qwen" in mid or "deepseek" in mid or "gemma" in mid):
                    available.append(mid)
            if not available:
                available = ids[:5]
            print(f">>> Modelos activos detectados en Groq: {available}")
        else:
            print(f">>> No se pudo listar modelos de Groq (HTTP {r.status_code})")
    except Exception as e:
        print(f">>> Error listando modelos de Groq: {e}")

    return available if available else PREFERRED_MODELS


def send_telegram_message(chat_id, text, use_markdown=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text[:4000]}
    if use_markdown:
        payload["parse_mode"] = "Markdown"
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200 and use_markdown:
            payload.pop("parse_mode", None)
            requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")


def ask_groq(prompt, models_list):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    last_error = "Sin respuesta de Groq"
    for model_name in models_list:
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un asistente de IA avanzado, directo y muy útil.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            data = response.json()
            if response.status_code == 200:
                return data["choices"][0]["message"]["content"]
            last_error = data.get("error", {}).get("message", f"HTTP {response.status_code}")
            print(f">>> Modelo {model_name} falló: {last_error}")
        except Exception as e:
            last_error = str(e)
            print(f">>> Excepción con {model_name}: {last_error}")

    return f"⚠️ Error conectando con Groq: {last_error}"


def main():
    print(f"🤖 Bot v3 iniciado | Token empieza por: {TELEGRAM_TOKEN[:10]}...")
    clear_webhook()
    models_list = get_available_groq_models()
    offset = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 25}
            response = requests.get(url, params=params, timeout=35)

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    for result in data.get("result", []):
                        offset = result["update_id"] + 1
                        msg = result.get("message") or result.get("edited_message")
                        if msg and "text" in msg:
                            chat_id = msg["chat"]["id"]
                            user_text = msg["text"].strip()
                            user_name = msg.get("from", {}).get("first_name", "Usuario")
                            print(f">>> {user_name}: {user_text}")

                            if user_text.startswith("/start"):
                                reply = (
                                    "🤖 ¡Hola! Ya estoy conectado y listo.\n\n"
                                    "Escríbeme lo que necesites."
                                )
                                send_telegram_message(chat_id, reply, use_markdown=True)
                            else:
                                reply = ask_groq(user_text, models_list)
                                send_telegram_message(chat_id, reply, use_markdown=False)
            elif response.status_code == 409:
                print(">>> Conflicto HTTP 409 (otra sesión activa con este token). Reintentando en 12s...")
                time.sleep(12)
            else:
                print(f">>> Telegram respondió HTTP {response.status_code}")
                time.sleep(4)
        except Exception as e:
            print(f">>> Error en el bucle: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
