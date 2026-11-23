from datetime import datetime
import re
import time
from urllib.parse import quote
import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

TELEGRAM_TOKEN = "2096960353:AAFVozuRfP-FBRaqovGF8DiFF6Dm3tMXYnY".strip()
GROQ_API_KEY = "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".strip()
GROQ_MODEL = "llama-3.3-70b-versatile"

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


def extract_youtube_query(user_text: str):
    text = user_text.strip()
    lower = text.lower()
    if lower.startswith("/yt") or lower.startswith("/youtube"):
        partes = text.split(maxsplit=1)
        return partes[1].strip() if len(partes) > 1 else ""

    patrones = [
        r"^(?:manolete[\s,:-]*)?(?:por favor[\s,:-]*)?(?:b[uú]scame|busca|ponme|pon|encuentra|quiero escuchar|quiero ver)\s+(?:en\s+youtube\s+)?(?:el\s+v[ií]deo|la\s+canci[oó]n|el\s+tema|la\s+sesi[oó]n|m[uú]sica\s+de|un\s+tema\s+de|una\s+canci[oó]n\s+de|un\s+v[ií]deo\s+de)?\s*(.+)$",
        r"^(?:manolete[\s,:-]*)?(?:en\s+)?(?:youtube|yt)[\s,:-]+(.+)$",
        r"^(.+?)\s+en\s+(?:youtube|yt)[\?\!\.]*$",
    ]
    for patron in patrones:
        match = re.match(patron, text, flags=re.IGNORECASE)
        if match:
            consulta = re.sub(
                r"\s+en\s+(?:youtube|yt)$", "", match.group(1), flags=re.IGNORECASE
            ).strip(" ?!.,\"'")
            if consulta:
                return consulta
    return None


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
    ahora = obtener_fecha_hora_actual()
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres MANOLETE, un asistente de IA directo, claro y muy útil. "
                    f"La fecha y hora exacta actuales en España son: {ahora}. "
                    "Usa SIEMPRE esta fecha y hora como única verdad actual."
                ),
            },
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
                                reply = "🤖 ¡Hola! Usa /yt <canción> o dime: búscame en YouTube Entre dos aguas"
                            else:
                                yt_q = extract_youtube_query(text)
                                if yt_q is not None:
                                    if not yt_q:
                                        reply = "▶️ Ejemplo: /yt Entre dos aguas"
                                    else:
                                        enlace = f"https://www.youtube.com/results?search_query={quote(yt_q, safe='')}"
                                        reply = f"▶️ Buscar \"{yt_q}\" en YouTube:\n{enlace}"
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
