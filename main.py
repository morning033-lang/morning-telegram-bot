import os
import time
import threading
import datetime
import requests
from flask import Flask, request

app = Flask(__name__)

TG_TOKEN = os.environ.get("TG_TOKEN")  # Railway Variables: TG_TOKEN
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")  # Railway Variables: WEATHER_API_KEY
MORNING_CHAT_ID = os.environ.get("MORNING_CHAT_ID")  # 可選：要推早安到哪個 chat_id

# 你的 Railway 公網網址（像 https://xxxx.up.railway.app）
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL")  # Railway Variables: PUBLIC_BASE_URL

DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Taipei")  # 預設城市（OpenWeather 用英文較穩）


def tg_send_message(chat_id: int, text: str):
    if not TG_TOKEN:
        print("❌ TG_TOKEN not set")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            print("❌ sendMessage failed:", r.status_code, r.text)
    except Exception as e:
        print("❌ sendMessage exception:", e)


def get_weather(city: str) -> str:
    if not WEATHER_API_KEY:
        return "❌ WEATHER_API_KEY 沒設定（Railway Variables）"

    # OpenWeather 建議用英文城市名；中文可能也可，但不保證
    q = city.strip() if city else DEFAULT_CITY

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": q,
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "zh_tw",
    }

    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return f"❌ 查天氣失敗：{r.status_code} {r.text}"

        data = r.json()
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        feels = data["main"].get("feels_like")
        hum = data["main"].get("humidity")

        parts = [f"🌤 {q} 天氣：{desc}", f"🌡 氣溫：{temp}°C"]
        if feels is not None:
            parts.append(f"🤗 體感：{feels}°C")
        if hum is not None:
            parts.append(f"💧 濕度：{hum}%")

        return "\n".join(parts)

    except Exception as e:
        return f"❌ 查天氣例外：{e}"


def handle_command(chat_id: int, text: str):
    # 支援：
    # /weather
    # /weather 台北
    # /start
    t = (text or "").strip()

    if t.startswith("/start"):
        tg_send_message(chat_id, "✅ Bot 已啟動\n指令：/weather 或 /weather 台北")
        return

    if t.startswith("/weather"):
        # 取參數
        parts = t.split(maxsplit=1)
        city = parts[1] if len(parts) > 1 else DEFAULT_CITY
        msg = get_weather(city)
        tg_send_message(chat_id, msg)
        return

    # 其他訊息：可忽略或提示
    # tg_send_message(chat_id, "我只看得懂：/weather 或 /weather 台北")


@app.get("/")
def home():
    return "OK"


# ✅ Telegram webhook 入口（路徑帶 token，避免亂打）
@app.post(f"/webhook/{os.environ.get('TG_TOKEN','')}")
def webhook():
    update = request.get_json(silent=True) or {}

    # Telegram update 可能是 message / edited_message / channel_post...
    message = update.get("message") or update.get("edited_message") or update.get("channel_post")
    if not message:
        return "no message", 200

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = message.get("text", "")

    if chat_id and text:
        handle_command(chat_id, text)

    return "ok", 200


def morning_report():
    if not MORNING_CHAT_ID:
        return
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    weather = get_weather(DEFAULT_CITY)
    msg = f"📅 {today} 早安！\n\n{weather}\n\n🚗 上班順利！"
    try:
        tg_send_message(int(MORNING_CHAT_ID), msg)
    except Exception as e:
        print("❌ morning_report error:", e)


def scheduler_loop():
    last_sent_date = None
    while True:
        now = datetime.datetime.now()
        hm = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        if hm == "06:30" and last_sent_date != today:
            morning_report()
            last_sent_date = today
            time.sleep(60)

        time.sleep(5)


def set_webhook():
    """部署後自動 setWebhook（需要 PUBLIC_BASE_URL）"""
    if not TG_TOKEN:
        print("❌ TG_TOKEN not set, skip setWebhook")
        return
    if not PUBLIC_BASE_URL:
        print("⚠️ PUBLIC_BASE_URL not set, skip setWebhook")
        return

    webhook_url = f"{PUBLIC_BASE_URL.rstrip('/')}/webhook/{TG_TOKEN}"
    url = f"https://api.telegram.org/bot{TG_TOKEN}/setWebhook"
    try:
        r = requests.get(url, params={"url": webhook_url}, timeout=15)
        print("setWebhook:", r.status_code, r.text)
    except Exception as e:
        print("❌ setWebhook exception:", e)


if __name__ == "__main__":
    # 啟動排程
    threading.Thread(target=scheduler_loop, daemon=True).start()

    # 自動設定 webhook
    set_webhook()

    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
