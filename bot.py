from datetime import datetime
import time
import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

TELEGRAM_TOKEN = "2096960353:AAFVozuRfP-FBRaqovGF8DiFF6Dm3tMXYnY".strip()
GROQ_API_KEY = "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".strip()

PREFERRED_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "qwen/qwen3-32b",
    "gemma2-9b-it",
]

DIAS_SEMANA = [
    "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"
]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]


def obtener_fecha_hora_actual() -> str:
    try:
        ahora = datetime.now(ZoneInfo("Europe/Madrid")) if ZoneInfo else datetime.now()
    except Exception:
        ahora = datetime.now()
    return (
        f"{DIAS_SEMANA[ahora.weekday()]}, {ahora.day} de {MESES[ahora.month - 1]} "
        f"de {ahora.year} a las {ahora.strftime('%H:%M')}"
    )


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
                if pref in ids and pref not in available:
                    available.append(pref)
            for mid in ids:
                if (
                    mid not in available
                    and "guard" not in mid
                    and "whisper" not in mid
                    and "tts" not in mid
                ):
                    available.append(mid)
            if available:
                print(f">>> Modelos activos en Groq: {available[:4]}")
                return available
        else:
            print(f">>> Aviso al listar modelos de Groq: HTTP {r.status_code}")
    except Exception as e:
        print(f">>> Error listando modelos de Groq: {e}")

    return PREFERRED_MODELS


def send_telegram_message(chat_id, text, message_thread_id=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text[:4000]}
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")


def ask_groq(prompt, models_list):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    ahora = obtener_fecha_hora_actual()
    last_error = "Sin respuesta de Groq"

    for model_name in models_list:
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Eres MANOLETE, un asistente de IA rápido, claro, cercano y resolutivo, "
                        "al estilo de un asistente general completo. Contesta a cualquier pregunta "
                        "de forma útil y directa. "
                        f"La fecha y hora exacta actuales en España son: {ahora}. "
                        "Usa SIEMPRE esta fecha y hora como única verdad actual."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 800,
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=20)
            data = r.json()
            if r.status_code == 200:
                return data["choices"][0]["message"]["content"]
            last_error = data.get("error", {}).get("message", f"HTTP {r.status_code}")
            print(f">>> Modelo {model_name} no disponible: {last_error}")
        except Exception as e:
            last_error = str(e)
            print(f">>> Error con modelo {model_name}: {last_error}")

    return f"⚠️ Error de Groq: {last_error}"


def main():
    print("🤖 Bot MANOLETE iniciado | Esperando 10s...")
    time.sleep(10)
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook", timeout=15)
    except Exception:
        pass
    models_list = get_available_groq_models()
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
                                reply = "🤖 ¡Hola! Soy MANOLETE, tu asistente. Pregúntame lo que quieras."
                            else:
                                reply = ask_groq(text, models_list)
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
