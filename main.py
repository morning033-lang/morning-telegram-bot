import os
import time
import threading
import datetime
import asyncio
import requests

from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ========= 讀取環境變數（Railway Variables）=========
TG_TOKEN = os.environ.get("TG_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

if not TG_TOKEN or not CHAT_ID or not WEATHER_API_KEY:
    print("❌ Missing env vars. Please set TG_TOKEN, CHAT_ID, WEATHER_API_KEY in Railway Variables.")

app = Flask(__name__)

# ========= Telegram 發訊息（用 requests 直接打 Bot API）=========
def send_message(text: str):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text}
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("❌ send_message error:", e)

# ========= 天氣（OpenWeatherMap）=========
def get_weather(city: str = "Taipei") -> str:
    try:
        # lang=zh_tw 顯示中文
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=zh_tw"
        )
        r = requests.get(url, timeout=10).json()

        # OpenWeather 失敗時通常會有 cod/message
        if str(r.get("cod")) != "200":
            return f"⚠️ 查詢失敗：{r.get('message', 'unknown error')}"

        temp = r["main"]["temp"]
        desc = r["weather"][0]["description"]
        return f"☁️ 天氣：{desc}\n🌡 氣溫：{temp}°C"
    except Exception as e:
        return f"⚠️ 天氣服務錯誤：{e}"

# ========= /weather 指令（telegram.ext async）=========
async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 可支援 /weather 台中 這種寫法（有參數就當城市）
    city = "Taipei"
    if context.args:
        city = " ".join(context.args).strip()

    msg = get_weather(city)
    await update.message.reply_text(msg)

# ========= 每日早安推播 =========
def morning_report():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    weather = get_weather("Taipei")
    message = f"🗓 {today} 早安！\n\n{weather}\n\n🚗 上班順利！"
    send_message(message)

def scheduler():
    last_sent_date = None
    while True:
        now = datetime.datetime.now()
        hm = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        # 每天 06:30 只送一次
        if hm == "06:30" and last_sent_date != today:
            print("✅ Trigger morning_report")
            morning_report()
            last_sent_date = today
            time.sleep(60)

        time.sleep(5)

# ========= Telegram polling（背景 thread + asyncio）=========
def run_bot_polling():
    async def start():
        app_bot = Application.builder().token(TG_TOKEN).build()
        app_bot.add_handler(CommandHandler("weather", weather_cmd))

        print("✅ Telegram bot polling started")
        await app_bot.initialize()
        await app_bot.start()
        await app_bot.updater.start_polling()

        # 一直掛著不退出
        while True:
            await asyncio.sleep(3600)

    asyncio.run(start())

# ========= Flask keep-alive route =========
@app.route("/")
def home():
    return "OK - morning-telegram-bot is running"

# ========= 程式進入點 =========
if __name__ == "__main__":
    # 背景跑：排程 + telegram polling
    threading.Thread(target=scheduler, daemon=True).start()
    threading.Thread(target=run_bot_polling, daemon=True).start()

    # Railway 會提供 PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
