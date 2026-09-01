import os, json, time, random, pickle, hashlib, traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
# Service hata diya
from google import genai
import telebot

# ====== FOLDERS BANANE HAIN - /tmp USE KARENGE ======
os.makedirs("/tmp/cookies", exist_ok=True)

# ====== SETTINGS ======
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
COOKIES_FOLDER = "/tmp/cookies"
HISTORY_FILE = "/tmp/video_history.json"
WEB_LINK = os.getenv("ZENQIRO_URL")
VIDEO_READY_FILE = "/tmp/video_ready.json"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

def safe_send(msg):
    try: bot.send_message(TELEGRAM_CHAT_ID, msg)
    except Exception as e: print("Telegram send failed:", e)

def handle_error(e):
    error_msg = f"❌ BOT CRASH: \n{str(e)[:500]}\n\n{traceback.format_exc()[:800]}"
    safe_send(error_msg)
    print(error_msg)

# ====== 1. ACCOUNTS.JSON ======
def load_accounts():
    accounts_json = os.getenv("ACCOUNTS_JSON")
    if not accounts_json:
        safe_send("❌ ACCOUNTS_JSON variable nahi mila Railway me")
        return {}
    return json.loads(accounts_json)

# ====== 2. HISTORY ======
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f: return json.load(f)
    return {"topics": [], "scripts_hash": []}

def save_history(history):
    with open(HISTORY_FILE, "w") as f: json.dump(history, f)

# ====== 3. CHROME SETUP - SELENIUM MANAGER WALA ======
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument(f"--user-data-dir={COOKIES_FOLDER}")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.binary_location = "/usr/bin/chromium"
    
    safe_send("✅ Starting Chrome driver... Selenium khud download karega")
    return webdriver.Chrome(options=options) # <-- SERVICE HATA DIYA

# ====== 4. GEMINI SCRIPT ======
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

# ====== 6. COOKIES ======
def save_cookies(driver, path):
    with open(path, 'wb') as f: pickle.dump(driver.get_cookies(), f)

def load_cookies(driver, path):
    try:
        with open(path, 'rb') as f:
            for cookie in pickle.load(f): driver.add_cookie(cookie)
        return True
    except: return False

# ====== 7. GOOGLE FLOW ======
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
            safe_send(f"⚠️ LOGIN REQUIRED: {email}. 5 min do login karne ke liye")
            time.sleep(300)
            save_cookies(driver, cookies_path)

        safe_send(f"Script paste kar di: {script[:50]}...")
        time.sleep(90)
        clips_generated.append(f"/tmp/clip_{i+1}.mp4")

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

    final_video = edit_video(clips_generated, "/tmp/output_video.mp4")
    try:
        with open(final_video, 'rb') as v:
            bot.send_video(TELEGRAM_CHAT_ID, v, caption=f"Video ready. {len(clips_generated)} clips. 5PM ka wait kar rahe.")
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

# ====== 9. MORNING JOB ======
def morning_job():
    safe_send("🚀 5:00 AM Video banana shuru")
    driver = None
    try:
        accounts = load_accounts()
        driver = get_driver()
        seo_data, aspect, is_wed = generate_content()
        safe_send(f"📝 Script bana: {seo_data[:100]}")

        flow_accounts = []
        for i, email in enumerate(accounts["GOOGLE_FLOW_EMAILS"]):
            flow_accounts.append({"email": email, "cookies_path": f"/tmp/cookies_{i+1}.json"})

        video_path = generate_video_with_flow(driver, flow_accounts, seo_data, aspect, is_wed)
        if video_path:
            with open(VIDEO_READY_FILE, 'w') as f:
                json.dump({"video_path": video_path, "seo_data": seo_data}, f)
            safe_send("💾 Video save ho gayi. 5PM ka wait...")
    except Exception as e:
        handle_error(e)
    finally:
        if driver: driver.quit()

# ====== 10. EVENING JOB ======
def evening_job():
    if not os.path.exists(VIDEO_READY_FILE):
        safe_send("⚠️ 5PM: Koi video ready nahi hai upload ke liye")
        return

    safe_send("🚀 5:00 PM Upload shuru")
    driver = None
    try:
        with open(VIDEO_READY_FILE, 'r') as f: data = json.load(f)

        accounts = load_accounts()
        driver = get_driver()
        for p, email in accounts["PLATFORMS"].items():
            upload_to_platform(driver, p, email, data["video_path"], data["seo_data"], "/tmp/thumbnail.jpg", accounts)
            time.sleep(random.randint(60, 120))
        safe_send("🎉 5:00 PM Sab jagah upload complete!")
        os.remove(VIDEO_READY_FILE)
    except Exception as e:
        handle_error(e)
    finally:
        if driver: driver.quit()

# ====== 11. START ======
if __name__ == "__main__":
    now = datetime.now().hour
    safe_send("Bot ON.")

    if now < 17:
        morning_job()
    else:
        safe_send("5PM guzar chuka hai. Foran upload kar raha hun")
        evening_job()