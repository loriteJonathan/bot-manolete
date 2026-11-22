import time
import requests

TELEGRAM_TOKEN = "2096960353:AAFVozuRfP-FBRaqovGF8DiFF6Dm3tMXYnY".strip()
GROQ_API_KEY = "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".strip()
GROQ_MODEL = "llama-3.3-70b-versatile"


def send_telegram_message(chat_id, text, message_thread_id=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text[:4000]}
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")


def ask_groq(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Eres MANOLETE, un asistente de IA directo, claro y muy útil."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 512,
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        data = r.json()
        if r.status_code == 200:
            return data["choices"][0]["message"]["content"]
        err = data.get("error", {}).get("message", f"HTTP {r.status_code}")
        return f"⚠️ Error de Groq: {err}"
    except Exception as e:
        return f"⚠️ Error conectando con Groq: {e}"


def main():
    print("🤖 Bot MANOLETE iniciado | Esperando 10s...")
    time.sleep(10)
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook", timeout=15)
    except Exception:
        pass
    offset = 0

    while True:
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 10},
                timeout=20,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("ok"):
                    for res in data.get("result", []):
                        offset = res["update_id"] + 1
                        msg = res.get("message") or res.get("edited_message")
                        if msg and "text" in msg:
                            chat_id = msg["chat"]["id"]
                            thread_id = msg.get("message_thread_id")
                            text = msg["text"].strip()
                            if text.startswith("/start"):
                                reply = "🤖 ¡Hola! Soy MANOLETE, ¿en qué te ayudo?"
                            else:
                                reply = ask_groq(text)
                            send_telegram_message(chat_id, reply, message_thread_id=thread_id)
            elif r.status_code == 409:
                time.sleep(15)
            else:
                time.sleep(4)
        except Exception as e:
            print(f">>> Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
