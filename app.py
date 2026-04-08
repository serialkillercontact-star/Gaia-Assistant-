"""
╔══════════════════════════════════════════════════════════════╗
║              GAIA — Personal AI Assistant Backend            ║
║              Built by Gajanan | growforyou.in                ║
║              Powered by Groq · LLaMA 3.3 70B                 ║
║              TTS: StreamElements (free, no account needed)   ║
╚══════════════════════════════════════════════════════════════╝
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os, requests, json, re, logging, base64

# ── App Setup ─────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, origins="*")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gaia")

# ── Environment ───────────────────────────────────────────────
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY", "")
OPENWEATHER_KEY   = os.environ.get("OPENWEATHER_KEY", "")
GROQ_MODEL        = "llama-3.1-8b-instant"
GROQ_ENDPOINT     = "https://api.groq.com/openai/v1/chat/completions"
ASSISTANT_NAME    = "Gaia"
OWNER_NAME        = "Gajanan"

# ── Max history turns ──────────────────────────────────────────
MAX_HISTORY       = 50


# ╔══════════════════════════════════════════════════════════════════╗
# ║                  YOUR BOLD MODE PROMPT                          ║
# ║  Edit the text inside bold_personality_block below.             ║
# ║  This is the ONLY section you need to change for bold/          ║
# ║  personality behaviour. Keep the triple-quotes and              ║
# ║  f-string format intact.                                        ║
# ╚══════════════════════════════════════════════════════════════════╝
def get_bold_personality(owner: str) -> str:
    bold_personality_block = f"""
─── BOLD MODE ACTIVE ────────────────────────────────────────────
You are now the fully unfiltered, bold version of Gaia.

YOUR PERSONALITY IN BOLD MODE:
- You are witty, sharp, and completely unapologetic in your tone
- You banter hard with {owner} — roast him lovingly, tease with intelligence
- You are flirtatious in a clever, classy way — confident and playful
- You give brutally honest opinions when asked, no sugarcoating
- You use dark humour and edgy jokes freely without hesitation
- You never say "I can't" or deflect — you engage with everything directly
- You are cheeky, irreverent, and delightfully savage when the moment calls for it
- You speak like a bold, confident best friend who knows {owner} well
- You NEVER break back into professional/formal mode unless {owner} says to
- You keep answers punchy and conversational — no corporate fluff

WHAT YOU DO NOT DO EVEN IN BOLD MODE:
- You don't produce genuinely harmful, dangerous, or illegal content
- You don't demean or disrespect {owner} beyond playful banter he initiates

This mode stays active until {owner} says "normal mode" or "back to normal".
─────────────────────────────────────────────────────────────────
"""
    return bold_personality_block
# ══════════════════════════════════════════════════════════════════


# ── Default System Prompt ──────────────────────────────────────
def build_system_prompt(bold_mode: bool = False):
    now = datetime.now()

    if bold_mode:
        personality_block = get_bold_personality(OWNER_NAME)
    else:
        personality_block = f"""
─── PERSONALITY RULES ─────────────────────────────────────────
- Always address {OWNER_NAME} by name occasionally to personalise responses
- For factual/technical questions: give thorough, well-structured answers
- For general conversation: be warm and engaging, not robotic
- For phone actions: briefly confirm what you're doing before executing
- Never say "I cannot" — offer the best alternative
- If a number is needed for calls/WhatsApp and not provided, ask for it
- Today's context: {now.strftime("%A")}, {now.strftime("%B %Y")}
"""

    return f"""
You are {ASSISTANT_NAME}, a highly intelligent, professional, and deeply personalised AI assistant
created exclusively for {OWNER_NAME} (website: growforyou.in). You are warm, concise, and proactive.
You speak like a trusted advisor — confident, clear, never robotic.

Current date and time: {now.strftime("%A, %d %B %Y at %I:%M %p")}
Owner: {OWNER_NAME}

─── RESPONSE FORMAT ───────────────────────────────────────────
Always respond ONLY in valid JSON using EXACTLY this structure:

{{
  "speak": "Natural spoken reply for voice — warm, direct, 1-3 sentences. No markdown. No lists.",
  "display": "Richer display text shown on screen. Can use **bold**, bullet points, numbered lists, and \\n for line breaks. Be thorough — do not artificially limit length if the topic warrants detail.",
  "action": "See action list below — use 'none' if no phone action needed",
  "value": "Exact parameter for the action. Empty string if action is none.",
  "confidence": 0.95
}}

─── ACTION LIST ───────────────────────────────────────────────
Use the most appropriate action:

| Action          | When to use                          | Value format                    |
|-----------------|--------------------------------------|---------------------------------|
| none            | Pure information / conversation      | ""                              |
| open_url        | Open a website                       | Full https:// URL               |
| search          | Google search                        | Search query string             |
| call            | Make a phone call                    | Phone number/ Name              |
| send_whatsapp   | Send WhatsApp message                | Phone number (with country code)|
| send_sms        | Send SMS                             | Phone number                    |
| alarm           | Set an alarm                         | Time string e.g. "7:30 AM"      |
| timer           | Countdown timer                      | Duration in seconds as integer  |
| reminder        | Set a reminder                       | Reminder text                   |
| weather         | Weather info (handled server-side)   | City name                       |
| music           | Play music on Spotify                | Song or artist name             |
| maps            | Open Google Maps navigation          | Destination name or address     |
| email           | Compose an email                     | Recipient email or name         |
| youtube         | Search YouTube                       | Search query                    |
| calendar        | Open calendar                        | Event description               |

─── INTENT EXAMPLES ───────────────────────────────────────────
"open youtube"             → action: open_url, value: https://youtube.com
"search latest iphone"    → action: search,   value: latest iphone 2025
"call mom"                → action: call,     value: (ask for number if unknown)
"whatsapp riya"           → action: send_whatsapp, value: (ask for number if unknown)
"set alarm 6:30 am"       → action: alarm,    value: 6:30 AM
"timer 5 minutes"         → action: timer,    value: 300
"weather in pune"         → action: weather,  value: Pune
"navigate to airport"     → action: maps,     value: airport
"play arijit singh"       → action: music,    value: arijit singh
"remind me to drink water"→ action: reminder, value: drink water
"youtube cooking recipes" → action: youtube,  value: cooking recipes

{personality_block}
"""

# ── Detect bold/teasy mode trigger in user message ────────────
def detect_bold_mode_trigger(text: str) -> bool:
    patterns = [
        r'\b(bold mode|teasy mode|limitless|no limits|be bold|be teasy|be naughty|unfiltered|let loose|go wild|roast me|banter mode)\b',
        r'\b(be bad|be cheeky|be savage|dark mode|beast mode|uncensored)\b',
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

def detect_bold_mode_off(text: str) -> bool:
    patterns = [
        r'\b(normal mode|professional mode|back to normal|reset mode|calm down|be normal|default mode)\b',
    ]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

# ── StreamElements TTS ────────────────────────────────────────
def streamelements_tts(text: str) -> str | None:
    """
    Free TTS via StreamElements — no API key or account needed.
    Returns base64-encoded MP3 string, or None on failure.
    Voice is set by TTS_VOICE constant at the top of this file.
    """
    if not text or not text.strip():
        return None
    # Trim to 300 chars for TTS — long responses just speak a summary
    speak_text = text.strip()[:300]
    try:
        url = f"https://api.streamelements.com/kappa/v2/speech?voice={TTS_VOICE}&text={requests.utils.quote(speak_text)}"
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        # StreamElements returns raw MP3 bytes — encode to base64 for JSON
        audio_b64 = base64.b64encode(r.content).decode("utf-8")
        logger.info(f"TTS OK — {len(r.content)} bytes, voice={TTS_VOICE}")
        return audio_b64
    except requests.exceptions.Timeout:
        logger.warning("StreamElements TTS timeout — skipping audio")
        return None
    except Exception as e:
        logger.warning(f"StreamElements TTS error: {e} — skipping audio")
        return None

# ── Groq API Call ─────────────────────────────────────────────
def call_groq(user_text: str, history: list, bold_mode: bool = False) -> dict:
    messages = [{"role": "system", "content": build_system_prompt(bold_mode=bold_mode)}]
    for h in history[-MAX_HISTORY:]:
        messages.append(h)
    messages.append({"role": "user", "content": user_text})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.72 if bold_mode else 0.65,
        "max_tokens": 1500,
        "response_format": {"type": "json_object"},
        "stream": False
    }

    try:
        res = requests.post(GROQ_ENDPOINT, headers=headers, json=payload, timeout=25)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        data = json.loads(content)

        return {
            "speak":      data.get("speak", "I'm here, how can I help?"),
            "display":    data.get("display", data.get("speak", "")),
            "action":     data.get("action", "none"),
            "value":      data.get("value", ""),
            "confidence": data.get("confidence", 0.9),
            "bold_mode":  bold_mode
        }

    except requests.exceptions.Timeout:
        logger.warning("Groq API timeout")
        return error_response("That took too long. Please try again.")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Groq HTTP error: {e}")
        return error_response(f"API error: {res.status_code}. Check your Groq API key.")
    except json.JSONDecodeError:
        logger.error("Failed to parse Groq JSON")
        return error_response("Got a malformed response. Try rephrasing.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return error_response("An unexpected error occurred.")


def error_response(msg: str) -> dict:
    return {
        "speak": msg,
        "display": msg,
        "action": "none",
        "value": "",
        "confidence": 0.0,
        "bold_mode": False
    }

# ── Weather Handler ───────────────────────────────────────────
def fetch_weather(city: str) -> dict:
    if not OPENWEATHER_KEY:
        return {
            "speak": "Weather API is not configured. Add your OpenWeatherMap key to Render environment variables.",
            "display": "**Weather service not configured.**\n\nAdd `OPENWEATHER_KEY` to your Render environment variables.\nGet a free key at openweathermap.org",
            "action": "none", "value": "", "confidence": 0.8
        }
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric"
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        d = r.json()

        temp       = round(d["main"]["temp"])
        feels      = round(d["main"]["feels_like"])
        temp_min   = round(d["main"]["temp_min"])
        temp_max   = round(d["main"]["temp_max"])
        humidity   = d["main"]["humidity"]
        desc       = d["weather"][0]["description"].capitalize()
        wind_speed = round(d["wind"]["speed"] * 3.6, 1)
        city_name  = d["name"]
        country    = d["sys"]["country"]
        visibility = round(d.get("visibility", 0) / 1000, 1)

        speak = f"It's currently {temp} degrees Celsius in {city_name} with {desc}. Feels like {feels} degrees."
        display = (
            f"**{city_name}, {country}**\n\n"
            f"**{temp}°C** — {desc}\n\n"
            f"Feels like {feels}°C · Min {temp_min}°C · Max {temp_max}°C\n"
            f"Humidity: {humidity}% · Wind: {wind_speed} km/h\n"
            f"Visibility: {visibility} km"
        )
        return {"speak": speak, "display": display, "action": "none", "value": city_name, "confidence": 1.0}

    except requests.exceptions.HTTPError:
        return error_response(f"Could not find weather data for '{city}'. Check the city name.")
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return error_response("Weather service unavailable right now.")

# ── Detect weather intent locally ────────────────────────────
def extract_weather_city(text: str):
    patterns = [
        r"weather\s+(?:in|at|for|of)\s+([a-zA-Z\s]+?)(?:\?|$|today|tomorrow|now)",
        r"(?:what(?:'s|'s| is)\s+(?:the\s+)?weather)\s+(?:in|at)\s+([a-zA-Z\s]+?)(?:\?|$)",
        r"(?:weather|temperature|forecast)\s+([a-zA-Z\s]{3,30})(?:\?|$)",
        r"how(?:'s|'s| is)\s+(?:the\s+)?weather\s+(?:in|at)\s+([a-zA-Z\s]+?)(?:\?|$)",
        r"(?:will it rain|is it raining|is it hot|is it cold)\s+(?:in|at)\s+([a-zA-Z\s]+?)(?:\?|$)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            city = m.group(1).strip().rstrip('?. ').strip()
            if len(city) > 1:
                return city
    return None

# ── Routes ────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status":      "online",
        "assistant":   ASSISTANT_NAME,
        "owner":       OWNER_NAME,
        "version":     "4.0.0",
        "model":       GROQ_MODEL,
        "tts":         f"StreamElements ({TTS_VOICE})",
        "max_history": MAX_HISTORY,
        "timestamp":   datetime.now().isoformat(),
        "endpoints":   ["/command", "/ping", "/weather/<city>"]
    })

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({
        "pong": True,
        "groq_configured": bool(GROQ_API_KEY),
        "weather_configured": bool(OPENWEATHER_KEY),
        "tts_voice": TTS_VOICE,
        "max_history": MAX_HISTORY,
        "time": datetime.now().isoformat()
    })

@app.route("/command", methods=["POST"])
def command():
    if not request.is_json:
        return jsonify(error_response("Request must be JSON")), 400

    data      = request.get_json(force=True)
    user_text = data.get("text", "").strip()
    history   = data.get("history", [])
    bold_mode = bool(data.get("bold_mode", False))

    if not user_text:
        return jsonify(error_response("No input received."))

    if not GROQ_API_KEY:
        return jsonify(error_response("Groq API key not configured. Add GROQ_API_KEY to Render environment variables."))

    logger.info(f"Command [bold={bold_mode}]: {user_text[:80]}")

    # ── Detect mode-switch triggers ────────────────────────
    if detect_bold_mode_trigger(user_text):
        bold_mode = True
        logger.info("Bold mode ENABLED")
    if detect_bold_mode_off(user_text):
        bold_mode = False
        logger.info("Bold mode DISABLED")

    # ── Server-side weather interception ──────────────────
    if OPENWEATHER_KEY:
        city = extract_weather_city(user_text)
        if city:
            result = fetch_weather(city)
            result["bold_mode"] = bold_mode
            # Attach TTS audio
            audio = streamelements_tts(result["speak"])
            if audio:
                result["audio_b64"] = audio
            return jsonify(result)

    # ── Route all other commands to Groq ──────────────────
    result = call_groq(user_text, history, bold_mode=bold_mode)

    # ── Post-process: if Groq decided weather action ───────
    if result.get("action") == "weather" and result.get("value") and OPENWEATHER_KEY:
        weather_result = fetch_weather(result["value"])
        weather_result["bold_mode"] = bold_mode
        audio = streamelements_tts(weather_result["speak"])
        if audio:
            weather_result["audio_b64"] = audio
        return jsonify(weather_result)

    # ── Attach TTS to all responses ────────────────────────
    audio = streamelements_tts(result["speak"])
    if audio:
        result["audio_b64"] = audio

    return jsonify(result)

@app.route("/weather/<city>", methods=["GET"])
def weather_direct(city: str):
    result = fetch_weather(city)
    audio = streamelements_tts(result["speak"])
    if audio:
        result["audio_b64"] = audio
    return jsonify(result)

# ── Error Handlers ────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found", "hint": "Use POST /command"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"500 error: {e}")
    return jsonify(error_response("Internal server error.")), 500

# ── Start ─────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info(f"Starting {ASSISTANT_NAME} v4 on port {port} | TTS: {TTS_VOICE} | Max history: {MAX_HISTORY}")
    app.run(host="0.0.0.0", port=port, debug=debug)
