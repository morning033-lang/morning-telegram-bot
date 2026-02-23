import requests
import datetime
import os
from flask import Flask
import threading
import time

TG_TOKEN = os.environ.get("TG_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

app = Flask(__name__)

def send_message(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=data)

def get_weather():
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Taipei&appid={WEATHER_API_KEY}&units=metric&lang=zh_tw"
    r = requests.get(url).json()
    temp = r["main"]["temp"]
    desc = r["weather"][0]["description"]
    return f"🌤 天氣：{desc}，氣溫 {temp}°C"

def morning_report():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    weather = get_weather()
    message = f"📅 {today} 早安！\n\n{weather}\n\n🚗 上班順利！"
    send_message(message)

def scheduler():
    while True:
        now = datetime.datetime.now().strftime("%H:%M")
        if now == "06:30":
            morning_report()
            time.sleep(60)
        time.sleep(10)

threading.Thread(target=scheduler).start()

@app.route("/")
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)



