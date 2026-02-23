import requests
import datetime
import os
import threading
import time
from flask import Flask, request

TG_TOKEN = os.environ.get("TG_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

app = Flask(__name__)

# ===== Telegram Send =====
def send_message(text, chat_id=CHAT_ID):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, data=data)


# ===== Weather =====
def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Taipei&appid={WEATHER_API_KEY}&units=metric&lang=zh_tw"
    r = requests.get(url).json()

    temp = r["main"]["temp"]
    desc = r["weather"][0]["description"]

    return f"☁️ 天氣：{desc}\n🌡 氣溫：{temp}°C"


# ===== Morning Report =====
def morning_report():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    weather = get_weather()

    message = f"""📅 {today} 早安！

{weather}

🚗 上班順利！"""

    send_message(message)


# ===== Scheduler =====
def scheduler():
    last_sent_date = None

    while True:
        now = datetime.datetime.now()
        hm = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        if hm == "06:30" and last_sent_date != today:
            print("Sending morning report...")
            morning_report()
            last_sent_date = today

        time.sleep(10)


# ===== Telegram Webhook =====
@app.route("/", methods=["GET"])
def home():
    return "Bot Alive"


@app.route("/", methods=["POST"])
def webhook():
    data = request.json

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/weather":
            send_message(get_weather(), chat_id)

    return "ok"


# ===== Start Scheduler =====
threading.Thread(target=scheduler).start()


# ===== Run Flask =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
