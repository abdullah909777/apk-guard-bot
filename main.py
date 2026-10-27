import os
import asyncio
import requests
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events

# --- 1. Render Keep-Alive Server ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- 2. Configuration ---
API_ID = 31845739
API_HASH = "7b16e9c95048e7d5393afa39da0566b6"
VT_API_KEY = "83bdf39706c76701a32fe0851c1f7afa69917d360b6607eb9ae5e0177c573423"

client = TelegramClient('apk_guard_session', API_ID, API_HASH)

# --- 3. VirusTotal Scan Function (Large File Supported) ---
def scan_file_with_virustotal(file_path):
    headers = {"x-apikey": VT_API_KEY} # 🟢 Fixed Header
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    try:
        if file_size_mb > 32:
            upload_url_res = requests.get("https://www.virustotal.com/api/v3/files/upload_url", headers=headers)
            if upload_url_res.status_code == 200:
                upload_url = upload_url_res.json().get("data")
            else:
                return f"⚠️ API Error (Upload Link): {upload_url_res.status_code} - {upload_url_res.text}"
        else:
            upload_url = "https://www.virustotal.com/api/v3/files"

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file)}
            response = requests.post(upload_url, headers=headers, files=files)
            
        if response.status_code == 200:
            analysis_id = response.json().get("data", {}).get("id")
            return analysis_id
        else:
            return f"⚠️ API Error (Upload): {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

# --- 4. Telegram Event Listener ---
@client.on(events.NewMessage(incoming=True))
async def handle_incoming_file(event):
    if event.document:
        for attr in event.document.attributes:
            if hasattr(attr, 'file_name') and attr.file_name.endswith('.apk'):
                msg = await event.respond("📥 ফাইলটি ডাউনলোড হচ্ছে, দয়া করে অপেক্ষা করুন... (বড় ফাইলে কিছুটা সময় লাগতে পারে)")
                
                os.makedirs("./downloads/", exist_ok=True)
                file_path = await event.download_media(file="./downloads/")
                
                await msg.edit("🔍 ফাইলটি VirusTotal-এ আপলোড ও স্ক্যান করা হচ্ছে...")
                
                analysis_id = await asyncio.to_thread(scan_file_with_virustotal, file_path)
                
                if os.path.exists(file_path):
                    os.remove(file_path)

                if not analysis_id or "Error" in analysis_id or "⚠️" in analysis_id:
                    await msg.edit(f"❌ স্ক্যান ব্যর্থ হয়েছে: {analysis_id}")
                    return

                await msg.edit("⏳ VirusTotal ফাইলটি বিশ্লেষণ করছে... দয়া করে অপেক্ষা করুন।")
                
                await asyncio.sleep(15)
                
                report_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
                headers = {"x-apikey": VT_API_KEY} # 🟢 Fixed Header
                report_res = await asyncio.to_thread(requests.get, report_url, headers=headers)
                
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
                    await msg.edit(result_text)
                else:
                    await msg.edit(f"⚠️ স্ক্যান রিপোর্ট আনতে সমস্যা হয়েছে: Error {report_res.status_code}")
                break

# --- 5. Main Execution ---
if __name__ == '__main__':
    keep_alive()
    print("Bot is starting...")
    client.start()
    client.run_until_disconnected()