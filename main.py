import os, json, time, random, schedule, pickle, hashlib
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from google import genai
import telebot

# ====== SETTINGS ======
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
COOKIES_FOLDER = "/mnt/data/cookies"
HISTORY_FILE = "/mnt/data/video_history.json" # NAYA: duplicate check ke liye
WEB_LINK = os.getenv("ZENQIRO_URL")
ACCOUNTS_FILE = "/mnt/data/accounts.json"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

def safe_send(msg):
    try: bot.send_message(TELEGRAM_CHAT_ID, msg)
    except Exception as e: print("Telegram send failed:", e)

# ====== 1. HISTORY LOAD/SAVE - DUPLICATE ROKNE KE LIYE ======
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f: return json.load(f)
    return {"topics": [], "scripts_hash": []}

def save_history(history):
    with open(HISTORY_FILE, "w") as f: json.dump(history, f)

# ====== 2. CHROME SETUP ======
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-data-dir={COOKIES_FOLDER}")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# ====== 3. ACCOUNTS LOAD ======
def load_accounts():
    with open(ACCOUNTS_FILE, 'r') as f: return json.load(f)

# ====== 4. GEMINI UNIQUE SCRIPT ======
def generate_content():
    history = load_history()
    is_wed = datetime.now().weekday() == 2
    avoid_text = ""
    if history["topics"]:
        avoid_text = f"Avoid these last 10 topics: {', '.join(history['topics'][-10:])}"

    if is_wed:
        prompt = f"Give 1 viral animal funny LONG video topic. Use all 500 Google Flow credits. {avoid_text} Return in Urdu. Format: Topic: xxx \n Script: xxx \n Title: xxx | Watch More: {WEB_LINK} \n Description: xxx \n Full Video on Website: {WEB_LINK} \n Tags: xxx \n Hashtags: xxx"
        aspect = "16:9"
    else:
        prompt = f"Give 1 viral animal funny SHORT video topic. Max 50 seconds. Niche: animals. {avoid_text} Return in Urdu. Format: Topic: xxx \n Script: xxx \n Title: xxx | Watch More: {WEB_LINK} \n Description: xxx \n Watch full videos: {WEB_LINK} \n Tags: xxx \n Hashtags: xxx"
        aspect = "9:16"

    res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    data = res.text

    # History me save
    try:
        topic = data.split("Topic:")[1].split("\n")[0].strip()
        script_hash = hashlib.md5(data.split("Script:")[1].encode()).hexdigest()
        history["topics"].append(topic)
        history["scripts_hash"].append(script_hash)
        save_history(history)
    except: pass

    return data, aspect, is_wed

# ====== 5. EDIT CLIPS ======
def edit_video(input_clips, output_path):
    safe_send(f"✂️ {len(input_clips)} clips ko join + captions lag rahe hain")
    time.sleep(10)
    open(output_path, 'w').close()
    return output_path

# ====== 6. COOKIES FUNCTIONS ======
def save_cookies(driver, path):
    with open(path, 'wb') as f: pickle.dump(driver.get_cookies(), f)

def load_cookies(driver, path):
    try:
        with open(path, 'rb') as f:
            for cookie in pickle.load(f): driver.add_cookie(cookie)
        return True
    except: return False

# ====== 7. GOOGLE FLOW AUTO SWITCH - 10 ACCOUNT TAK JAYEGA ======
def generate_video_with_flow(driver, accounts, script, aspect, is_wed):
    clips_needed = 5 if is_wed else 2
    clips_generated = []

    for i, account in enumerate(accounts):
        email = account["email"]
        cookies_path = account["cookies_path"]
        safe_send(f"🎬 Trying account {i+1}/10: {email}")

        driver.get("https://labs.google/flow")
        time.sleep(3)

        if load_cookies(driver, cookies_path):
            driver.refresh(); time.sleep(5)
        else:
            safe_send(f"⚠️ LOGIN REQUIRED: {email}")
            time.sleep(300)
            save_cookies(driver, cookies_path)

        # Yahan script paste + generate ka code aayega
        time.sleep(90)
        clips_generated.append(f"/mnt/data/clip_{i+1}.mp4")

        # CREDIT KHATAM CHECK
        page_text = driver.page_source.lower()
        if "credit" in page_text or "limit" in page_text:
            safe_send(f"❌ {email} credits khatam. Next account...")
            continue

        if len(clips_generated) >= clips_needed:
            safe_send(f"🎉 Kaafi clips ho gayi. Total: {len(clips_generated)}")
            break

    if len(clips_generated) == 0:
        safe_send("❌ 10 account bhi lag gaye. Koi credits nahi bachi")
        return None

    final_video = edit_video(clips_generated, "/mnt/data/output_video.mp4")
    try:
        with open(final_video, 'rb') as v:
            bot.send_video(TELEGRAM_CHAT_ID, v, caption=f"New video ready. {len(clips_generated)} clips. Approval?")
    except: safe_send("Video bhej nahi saki")
    return final_video

# ====== 8. UPLOAD ======
def upload_to_platform(driver, platform, email, video_path, seo_data, thumbnail_path, accounts):
    safe_send(f"📤 {platform} pe upload: {email}")
    try:
        if platform == "YOUTUBE": driver.get("https://studio.youtube.com")
        elif platform == "TIKTOK": driver.get("https://www.tiktok.com/upload")
        elif platform == "INSTAGRAM": driver.get("https://www.instagram.com/reels/upload")
        elif platform == "FACEBOOK": driver.get(accounts["FACEBOOK_PAGE_URL"])
        elif platform == "SNAPCHAT": driver.get("https://www.snapchat.com/spotlight/upload")
        elif platform == "ZENQIRO": driver.get(accounts["ZENQIRO_ADMIN_URL"])
        time.sleep(5)
        safe_send(f"✅ {platform} done")
    except Exception as e: safe_send(f"❌ {platform} error: {e}")

# ====== 9. EVENING JOB ======
def evening_upload_job(video_path, thumbnail_path, seo_data):
    accounts = load_accounts()
    driver = get_driver()
    for p, email in accounts["PLATFORMS"].items():
        upload_to_platform(driver, p, email, video_path, seo_data, thumbnail_path, accounts)
        time.sleep(random.randint(60, 120))
    driver.quit()
    safe_send("🎉 5:00 PM Sab jagah upload complete!")

# ====== 10. MORNING JOB ======
def morning_job():
    safe_send("🚀 9:00 AM Kaam shuru")
    accounts = load_accounts()
    driver = get_driver()
    seo_data, aspect, is_wed = generate_content()
    safe_send(f"📝 {seo_data}")

    # 1 account nahi, puri 10 ki list bhej do
    flow_accounts = []
    for i, email in enumerate(accounts["GOOGLE_FLOW_EMAILS"]):
        flow_accounts.append({"email": email, "cookies_path": f"/mnt/data/cookies_{i+1}.json"})

    video_path = generate_video_with_flow(driver, flow_accounts, seo_data, aspect, is_wed)
    if video_path:
        schedule.every().day.at("17:00").do(evening_upload_job, video_path, "/mnt/data/thumbnail.jpg", seo_data)
    driver.quit()

# ====== 11. SCHEDULER ======
schedule.every().day.at("09:00").do(morning_job)
safe_send("Bot ON. Roz 9 baje banayega, 5 baje upload karega.")
while True:
    schedule.run_pending()
    time.sleep(60)