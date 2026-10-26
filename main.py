import os
import asyncio
import requests
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events

# --- 1. Render Keep-Alive Server (সার্ভার ২৪ ঘণ্টা চালু রাখার জন্য) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running 24/7!"

def run_web():
    # Render-এর নিজস্ব পোর্ট নেওয়ার জন্য ডায়নামিক কোড
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- 2. Configuration (আপনার আসল ক্রেডেনশিয়াল এখানে সেট করা আছে) ---
API_ID = 31845739
API_HASH = "7b16e9c95048e7d5393afa39da0566b6"
VT_API_KEY = "83bdf39706c76701a32fe0851c1f7afa69917d360b6607eb9ae5e0177c573423"

# Telethon Client ইনিশিয়ালাইজ করা
client = TelegramClient('apk_guard_session', API_ID, API_HASH)

# --- 3. VirusTotal Scan Function ---
def scan_file_with_virustotal(file_path):
    url = "https://www.virustotal.com/api/v3/files"
    headers = {"x-api-key": VT_API_KEY}
    
    try:
        # ফাইল আপলোড ও স্ক্যান করা
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file)}
            response = requests.post(url, headers=headers, files=files)
            
        if response.status_code == 200:
            analysis_id = response.json().get("data", {}).get("id")
            # রেজাল্ট পাওয়ার জন্য ১০ সেকেন্ড অপেক্ষা করা
            import time
            time.sleep(10)
            
            report_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
            report_res = requests.get(report_url, headers=headers)
            
            if report_res.status_code == 200:
                stats = report_res.json().get("data", {}).get("attributes", {}).get("stats", {})
                malicious = stats.get("malicious", 0)
                suspicious = stats.get("suspicious", 0)
                harmless = stats.get("harmless", 0)
                undetected = stats.get("undetected", 0)
                
                result_text = (
                    f"🛡️ **VirusTotal Scan Report** 🛡️\n\n"
                    f"❌ Malicious: {malicious}\n"
                    f"⚠️ Suspicious: {suspicious}\n"
                    f"✅ Harmless: {harmless}\n"
                    f"🔍 Undetected: {undetected}\n"
                )
                return result_text
        return "⚠️ VirusTotal স্ক্যান করতে সমস্যা হয়েছে বা ফাইল সাইজ খুব বেশি।"
    except Exception as e:
        return f"❌ Error: {str(e)}"

# --- 4. Telegram Event Listener (APK ফাইল রিসিভ করা) ---
@client.on(events.NewMessage(incoming=True))
async def handle_incoming_file(event):
    # যদি কোনো ফাইল বা ডকুমেন্ট আসে এবং সেটি যদি APK হয়
    if event.document:
        for attr in event.document.attributes:
            if hasattr(attr, 'file_name') and attr.file_name.endswith('.apk'):
                msg = await event.respond("📥 বড় APK ফাইলটি ডাউনলোড হচ্ছে, দয়া করে অপেক্ষা করুন...")
                
                # ফোল্ডার নিশ্চিত করা
                os.makedirs("./downloads/", exist_ok=True)
                file_path = await event.download_media(file="./downloads/")
                
                await msg.edit("🔍 ফাইলটি VirusTotal-এ স্ক্যান করা হচ্ছে...")
                
                # স্ক্যান ফাংশন কল করা
                report = scan_file_with_virustotal(file_path)
                
                # স্ক্যান শেষ হলে লোকাল ফাইল ডিলিট করে স্টোরেজ বাঁচানো
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                await msg.edit(report)
                break

# --- 5. Main Execution ---
if __name__ == '__main__':
    keep_alive()  # ফ্লাস্ক সার্ভার চালু রাখা যাতে Render সজাগ থাকে
    print("Bot is starting...")
    client.start()
    client.run_until_disconnected()