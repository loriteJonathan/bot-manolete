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

PREFERRED_GROQ_MODELS = ["qwen/qwen3.8-27b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def get_system_prompt() -> str:
    try:
        ahora = datetime.now(ZoneInfo("Europe/Madrid")) if ZoneInfo else datetime.now()
    except Exception:
        ahora = datetime.now()
    fecha_txt = f"{DIAS[ahora.weekday()]}, {ahora.day} de {MESES[ahora.month - 1]} de {ahora.year} a las {ahora.strftime('%H:%M')}"
    return (
        "Eres MANOLETE, un asistente de IA directo, claro y muy útil. "
        f"La fecha y hora exacta actuales en España son: {fecha_txt}. "
        "Usa SIEMPRE esta fecha y hora como única verdad actual."
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
            consulta = re.sub(r"\s+en\s+(?:youtube|yt)$", "", match.group(1), flags=re.IGNORECASE).strip(" ?!.,\"'")
            if consulta:
                return consulta
    return None


def get_available_groq_models():
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    available = []
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            ids = [m.get("id") for m in r.json().get("data", []) if m.get("id")]
            for pref in PREFERRED_GROQ_MODELS:
                if pref in ids and pref not in available:
                    available.append(pref)
            for mid in ids:
                if mid not in available and "guard" not in mid and "whisper" not in mid:
                    available.append(mid)
    except Exception as e:
        print(f">>> Error listando modelos Groq: {e}")
    return available if available else PREFERRED_GROQ_MODELS


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
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    sys_prompt = get_system_prompt()
    last_err = "Sin respuesta de Groq"
    for model in models_list:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
            "temperature": 
