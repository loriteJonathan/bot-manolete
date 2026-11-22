from datetime import datetime
import time
import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

TELEGRAM_TOKEN = "2096960353:AAFVozuRfP-FBRaqovGF8DiFF6Dm3tMXYnY".strip()
GROQ_API_KEY = "Gsk_HBMHLL8u45buOrMqKQsvWGdyb3FYV2yKg9AAL2hhWunWvbZYYneJ".strip()

PREFERRED_MODELS = [
    "qwen/qwen3.8-27b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

DIAS_SEMANA = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]

MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def obtener_fecha_hora_actual() -> str:
    try:
        if ZoneInfo is not None:
            ahora = datetime.now(ZoneInfo("Europe/Madrid"))
        else:
            ahora = datetime.now()
    except Exception:
        ahora = datetime.now()

    dia_semana = DIAS_SEMANA[ahora.weekday()]
    nombre_mes = MESES[ahora.month - 1]
    return (
        f"{dia_semana}, {ahora.day} de {nombre_mes} de {ahora.year} "
        f"a las {ahora.strftime('%H:%M')}"
    )


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
                if pref in ids and pref not in available:
                    available.append(pref)
            for mid in ids:
                if mid not in available and "prompt-guard" not in mid and "whisper" not in mid and "guard" not in mid:
                    available.append(mid)
            if not available:
                available = ids[:3]
            print(f">>> Modelos listos en Groq: {available}")
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

    ahora = obtener_fecha_hora_actual()
    last_error = "Sin respuesta de Groq"

    for model_name in models_list:
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Eres MANOLETE, un asistente de IA directo, claro y muy útil. "
                        f"La fecha y hora exacta actuales en España son: {ahora}. "
                        "Usa SIEMPRE esta fecha y hora como única verdad actual. "
                        "Nunca menciones fechas pasadas de entrenamiento ni des dos fechas distintas."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 512,
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
    print("🤖 Bot v5 iniciado | Esperando 10s para liberar sesiones previas...")
    time.sleep(10)
    clear_webhook()
    models_list = get_available_groq_models()
    offset = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 10}
            response = requests.get(url, params=params, timeout=20)

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
                print(">>> Conflicto HTTP 409 en Telegram. Reintentando en 15s...")
                time.sleep(15)
            else:
                print(f">>> Telegram respondió HTTP {response.status_code}")
                time.sleep(4)
        except Exception as e:
            print(f">>> Error en el bucle: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
