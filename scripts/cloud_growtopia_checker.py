import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL",
    "https://discordapp.com/api/webhooks/1558414040466984963/fqks_HwbDPMBCbsO6Mu4fEDTIC568rv-6XmW9ZmFoKVFDchcwpzu0eXWaOSYfDPGT9-m"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "gt_cloud_state.json")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"version": "5.59", "updated_date": "Oct 5, 2026", "whats_new": ""}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def fetch_google_play():
    url = "https://play.google.com/store/apps/details?id=com.rtsoft.growtopia&hl=en"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        return None, None, None

    # Extract update date
    date_match = re.search(r"Updated on\s*</div><div[^>]*>([^<]+)</div>", r.text)
    updated_date = date_match.group(1).strip() if date_match else None

    # Extract What's New changelog
    whats_new = ""
    wn_match = re.search(r"What\'s new.*?<div itemprop=\"description\">([^<]+)</div>", r.text, re.DOTALL)
    if not wn_match:
        wn_match = re.search(r"What\'s new</div></div><div[^>]*>([^<]+)</div>", r.text)
    if wn_match:
        whats_new = wn_match.group(1).strip()

    return updated_date, whats_new

def fetch_apkpure_version():
    url = "https://apkpure.com/growtopia/com.rtsoft.growtopia"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        return None

    # Find version numbers like 5.59, 5.60
    versions = re.findall(r"Growtopia\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)", r.text)
    if versions:
        # Sort to find the highest version
        sorted_vers = sorted(set(versions), key=lambda v: [int(x) for x in v.split(".") if x.isdigit()], reverse=True)
        return sorted_vers[0]
    return None

def send_discord_alert(title, description, fields=None, color=0x00FF88):
    payload = {
        "username": "Growtopia Cloud Monitor",
        "avatar_url": "https://static.wikia.nocookie.net/growtopia/images/8/87/Growtopia_icon.png",
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": "Growtopia 24/7 Cloud Sentinel • Powered by GitHub Actions"}
        }]
    }
    if fields:
        payload["embeds"][0]["fields"] = fields

    res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    print("Discord alert status:", res.status_code)
    return res.status_code

def main():
    print("Growtopia Cloud 24/7 Sentinel Checking...")
    state = load_state()
    prev_version = state.get("version", "5.59")
    prev_date = state.get("updated_date", "Oct 5, 2026")

    print(f"Current State: Version={prev_version}, UpdatedDate={prev_date}")

    apk_ver = fetch_apkpure_version()
    gp_date, gp_whats_new = fetch_google_play()

    current_ver = apk_ver or prev_version
    current_date = gp_date or prev_date

    print(f"Fetched: Version={current_ver}, UpdatedDate={current_date}")

    # Check if a new version or date was detected
    is_new_version = current_ver != prev_version
    is_new_date = current_date != prev_date

    if is_new_version or is_new_date:
        print("🚨 NEW UPDATE DETECTED IN THE CLOUD!")
        fields = [
            {"name": "🆕 New Version", "value": f"`{current_ver}` (was `{prev_version}`)", "inline": True},
            {"name": "📅 Release Date", "value": f"`{current_date}`", "inline": True}
        ]

        if gp_whats_new:
            fields.append({"name": "📝 What's New", "value": gp_whats_new[:1000], "inline": False})

        send_discord_alert(
            title="🚨 CLOUD ALERT: New Growtopia Update Released!",
            description=(
                "**A brand new Growtopia update has just been pushed to mobile app stores!**\n\n"
                "The 24/7 Cloud Sentinel detected this update automatically while running on GitHub Actions."
            ),
            fields=fields,
            color=0xff0044
        )

        state["version"] = current_ver
        state["updated_date"] = current_date
        state["last_detected"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        save_state(state)
        print("State updated and saved.")
    else:
        print("No new updates detected. Everything is current.")

if __name__ == "__main__":
    main()
