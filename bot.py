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
GEMINI_API_KEY = "AQ.Ab8RN6KGJRXUr2EXlDgsdwB_AXmGl_hEVpP4QSe6NvJZ-R8dPg".strip()

PREFERRED_GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
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


def get_system_prompt() -> str:
    ahora = obtener_fecha_hora_actual()
    return (
        "Eres MANOLETE, un asistente de IA directo, claro y muy útil. "
        f"La fecha y hora exacta actuales en España son: {ahora}. "
        "Usa SIEMPRE esta fecha y hora como única verdad actual. "
        "Nunca menciones fechas pasadas de entrenamiento ni des dos fechas distintas."
    )


def build_spotify_search_link(query: str) -> str:
    encoded_query = quote(query.strip(), safe="")
    return f"https://open.spotify.com/search/{encoded_query}"


def extract_spotify_query(user_text: str):
    text = user_text.strip()
    lower = text.lower()

    if lower.startswith("/spotify"):
        partes = text.split(maxsplit=1)
        return partes[1].strip() if len(partes) > 1 else ""

    patrones = [
        r"^(?:manolete[\s,:-]*)?(?:por favor[\s,:-]*)?(?:b[uú]scame|busca|ponme|pon|encuentra|quiero escuchar)\s+(?:en\s+spotify\s+)?(?:la\s+canci[oó]n|el\s+tema|la\s+sesi[oó]n|m[uú]sica\s+de|un\s+tema\s+de|una\s+canci[oó]n\s+de)?\s*(.+)$",
        r"^(?:manolete[\s,:-]*)?(?:en\s+)?spotify[\s,:-]+(.+)$",
        r"^(.+?)\s+en\s+spotify[\?\!\.]*$",
    ]

    for patron in patrones:
        match = re.match(patron, text, flags=re.IGNORECASE)
        if match:
            consulta = match.group(1).strip(" ?!.,\"'")
            consulta = re.sub(r"\s+en\s+spotify$", "", consulta, flags=re.IGNORECASE).strip(" ?!.,\"'")
            if consulta:
                return consulta

    return None


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
            for pref in PREFERRED_GROQ_MODELS:
                if pref in ids and pref not in available:
                    available.append(pref)
            for mid in ids:
                if (
                    mid not in available
                    and "prompt-guard" not in mid
                    and "whisper" not in mid
                    and "guard" not in mid
                ):
                    available.append(mid)
            if not available:
                available = ids[:3]
            print(f">>> Modelos listos en Groq: {available}")
        else:
            print(f">>> No se pudo listar modelos de Groq (HTTP {r.status_code})")
    except Exception as e:
        print(f">>> Error listando modelos de Groq: {e}")

    return available if available else PREFERRED_GROQ_MODELS


def send_telegram_message(chat_id, text, message_thread_id=None, use_markdown=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text[:4000]}
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id
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
    system_prompt = get_system_prompt()
    last_error = "Sin respuesta de Groq"

    for model_name in models_list:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 512,
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            data = response.json()
            if response.status_code == 200:
                return True, data["choices"][0]["message"]["content"]
            last_error = data.get("error", {}).get("message", f"HTTP {response.status_code}")
            print(f">>> Groq ({model_name}) falló: {last_error}")
        except Exception as e:
            last_error = str(e)
            print(f">>> Excepción en Groq ({model_name}): {last_error}")

    return False, last_error


def ask_gemini(prompt):
    if not GEMINI_API_KEY:
        return False, "Sin clave de Gemini"

    system_prompt = get_system_prompt()
    last_error = "Sin respuesta de Gemini"

    for model_name in GEMINI_MODELS:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={GEMINI_API_KEY}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 512,
            },
        }
        try:
            response = requests.post(url, json=payload, timeout=20)
            data = response.json()
            if response.status_code == 200:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts if "text" in p).strip()
                    if text:
                        return True, text
            last_error = data.get("error", {}).get("message", f"HTTP {response.status_code}")
            print(f">>> Gemini ({model_name}) falló: {last_error}")
        except Exception as e:
            last_error = str(e)
            print(f">>> Excepción en Gemini ({model_name}): {last_error}")

    return False, last_error


def generate_ai_reply(prompt, models_list):
    ok_groq, groq_res = ask_groq(prompt, models_list)
    if ok_groq and groq_res:
        return groq_res

    print(">>> Pasando a respaldo con Gemini...")
    ok_gemini, gemini_res = ask_gemini(prompt)
    if ok_gemini and gemini_res:
        return gemini_res

    return f"⚠️ Error conectando con Groq ({groq_res}) y Gemini ({gemini_res})"


def main():
    print("🤖 Bot MANOLETE iniciado | Esperando 10s para liberar sesiones previas...")
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
                            thread_id = msg.get("message_thread_id")
                            user_text = msg["text"].strip()
                            user_name = msg.get("from", {}).get("first_name", "Usuario")
                            print(f">>> [Tema {thread_id}] {user_name}: {user_text}")

                            if user_text.startswith("/start"):
                                reply = (
                                    "🤖 ¡Hola! Ya estoy conectado y listo.\n\n"
                                    "Puedes pedirme canciones de dos formas:\n"
                                    "• /spotify <canción o artista>\n"
                                    "• O diciéndome: \"búscame en Spotify Entre dos aguas\"\n"
                                    "• /id_tema — ver el ID del tema actual"
                                )
                                send_telegram_message(
                                    chat_id,
                                    reply,
                                    message_thread_id=thread_id,
                                    use_markdown=False,
                                )
                            elif user_text.startswith("/id_tema"):
                                reply = f"🧵 ID de este tema: {thread_id}"
                                send_telegram_message(
                                    chat_id,
                                    reply,
                                    message_thread_id=thread_id,
                                    use_markdown=False,
                                )
                            else:
                                spotify_query = extract_spotify_query(user_text)
                                if spotify_query is not None:
                                    if not spotify_query:
                                        reply = "🎵 Dime qué canción o artista quieres buscar. Ejemplo: /spotify La Flaca"
                                    else:
                                        enlace = build_spotify_search_link(spotify_query)
                                        reply = f"🎵 Buscar \"{spotify_query}\" en Spotify:\n{enlace}"
                                    send_telegram_message(
                                        chat_id,
                                        reply,
                                        message_thread_id=thread_id,
                                        use_markdown=False,
                                    )
                                else:
                                    reply = generate_ai_reply(user_text, models_list)
                                    send_telegram_message(
                                        chat_id,
                                        reply,
                                        message_thread_id=thread_id,
                                        use_markdown=False,
                                    )
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
