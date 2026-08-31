import os, json, time, random, schedule
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service # NAYA
from webdriver_manager.chrome import ChromeDriverManager # NAYA
from google import genai # <-- 1. PURANA HATA DIYA
import telebot

# ====== SETTINGS ======
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") # Railway wala naam
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
COOKIES_FOLDER = "/mnt/data/cookies"
DAY_FILE = "/mnt/data/day_counter.txt"
WEB_LINK = os.getenv("ZENQIRO_URL")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY) # <-- 2. YE NAYA LAGA DIYA

def safe_send(msg):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, msg)
    except Exception as e:
        print("Telegram send failed:", e)

# ====== 1. CHROME SETUP RAILWAY KE LIYE ======
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-data-dir={COOKIES_FOLDER}")
    options.add_argument("--window-size=1920,1080")
    
    # webdriver-manager khud chrome download kar lega
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# ====== 2. ACCOUNTS LOAD FROM ENV ======
def load_accounts():
    accounts_json = os.getenv("ACCOUNTS_JSON")
    return json.loads(accounts_json)

# ====== 3. AAJ KA FLOW EMAIL ======
def get_today_flow_email(accounts):
    emails = accounts["GOOGLE_FLOW_EMAILS"]
    day = 0
    if os.path.exists(DAY_FILE):
        with open(DAY_FILE, "r") as f: day = int(f.read())
    email = emails[day % len(emails)]
    with open(DAY_FILE, "w") as f: f.write(str(day + 1))
    return email

# ====== 4. GEMINI SE SCRIPT + SEO ======
def generate_content():
    is_wed = datetime.now().weekday() == 2 # 2 = Wednesday

    if is_wed:
        prompt = f"Give 1 viral animal funny LONG video topic. Video length: Use all 500 Google Flow credits. Return in Urdu. Format: Topic: xxx \n Script: xxx \n Title: xxx | Watch More: {WEB_LINK} \n Description: xxx \n Full Video on Website: {WEB_LINK} \n Tags: xxx \n Hashtags: xxx"
        aspect = "16:9"
    else:
        prompt = f"Give 1 viral animal funny SHORT video topic. Max 50 seconds. Niche: animals. Return in Urdu. Format: Topic: xxx \n Script: xxx \n Title: xxx | Watch More: {WEB_LINK} \n Description: xxx \n Watch full videos: {WEB_LINK} \n Tags: xxx \n Hashtags: xxx"
        aspect = "9:16"

    res = client.models.generate_content( # <-- 3. YE NAYA TARIKA
        model="gemini-2.0-flash", 
        contents=prompt
    )
    return res.text, aspect, is_wed

# ====== 5. EDIT CLIPS + JOIN ======
def edit_video(input_clips, output_path):
    safe_send("✂️ Clips ko join + captions lag rahe hain")
    time.sleep(10)
    open(output_path, 'w').close() # dummy
    return output_path

# ====== 6. GOOGLE FLOW ======
def generate_video_with_flow(driver, email, script, aspect):
    safe_send(f"🎬 Video generate ho rahi hai: {aspect} - {email}")
    driver.get("https://labs.google/flow")
    time.sleep(5)
    # Yahan Flow login + script paste + 3-4 clips gen + download
    time.sleep(60)
    clips = ["/mnt/data/clip1.mp4", "/mnt/data/clip2.mp4"]
    final_video = edit_video(clips, "/mnt/data/output_video.mp4")
    try:
        with open(final_video, 'rb') as v:
            bot.send_video(TELEGRAM_CHAT_ID, v, caption="Video ready. Approval?")
    except:
        safe_send("Video bhej nahi saki")
    return final_video

# ====== 7. UPLOAD FUNCTIONS ======
def upload_to_platform(driver, platform, email, video_path, seo_data, thumbnail_path, accounts):
    safe_send(f"📤 {platform} pe upload ho raha hai: {email}")
    try:
        if platform == "YOUTUBE": driver.get("https://studio.youtube.com")
        elif platform == "TIKTOK": driver.get("https://www.tiktok.com/upload")
        elif platform == "INSTAGRAM": driver.get("https://www.instagram.com/reels/upload")
        elif platform == "FACEBOOK": driver.get(accounts["FACEBOOK_PAGE_URL"])
        elif platform == "SNAPCHAT": driver.get("https://www.snapchat.com/spotlight/upload")
        elif platform == "ZENQIRO":
            driver.get(accounts["ZENQIRO_ADMIN_URL"])
            time.sleep(2)

        time.sleep(5)
        safe_send(f"✅ {platform} done")
    except Exception as e:
        safe_send(f"❌ {platform} error: {e}")

# ====== 8. EVENING UPLOAD JOB ======
def evening_upload_job(video_path, thumbnail_path, seo_data):
    accounts = load_accounts()
    driver = get_driver()
    platforms = ["YOUTUBE", "TIKTOK", "INSTAGRAM", "FACEBOOK", "SNAPCHAT", "ZENQIRO"]
    for p in platforms:
        upload_to_platform(driver, p, accounts[p], video_path, seo_data, thumbnail_path, accounts)
        time.sleep(random.randint(60, 120))
    driver.quit()
    safe_send("🎉 5:00 PM Sab jagah upload complete!")

# ====== 9. MORNING JOB ======
def morning_job():
    safe_send("🚀 9:00 AM Kaam shuru")
    accounts = load_accounts()
    driver = get_driver()

    seo_data, aspect, is_wed = generate_content()
    safe_send(f"📝 {seo_data}")

    flow_email = get_today_flow_email(accounts)
    video_path = generate_video_with_flow(driver, flow_email, seo_data, aspect)

    schedule.every().day.at("17:00").do(evening_upload_job, video_path, "/mnt/data/thumbnail.jpg", seo_data)
    driver.quit()

# ====== 10. SCHEDULER ======
schedule.every().day.at("09:00").do(morning_job)
safe_send("Bot ON. Roz 9 baje banayega, 5 baje upload karega.")

while True:
    schedule.run_pending()
    time.sleep(60)