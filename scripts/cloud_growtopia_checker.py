import os
import sys
import re
import json
import time
import io
import zipfile
import requests
from bs4 import BeautifulSoup

# Ensure root workspace is in sys.path so we can import growtopia_miner
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(REPO_DIR)

import growtopia_miner as gm

DISCORD_WEBHOOK_URL = os.environ.get(
    "DISCORD_WEBHOOK_URL",
    "https://discordapp.com/api/webhooks/1558414040466984963/fqks_HwbDPMBCbsO6Mu4fEDTIC568rv-6XmW9ZmFoKVFDchcwpzu0eXWaOSYfDPGT9-m"
)

STATE_FILE = os.path.join(SCRIPT_DIR, "gt_cloud_state.json")
CLOUD_SNAPSHOT_FILE = os.path.join(SCRIPT_DIR, "cloud_snapshot.json")

def parse_version_tuple(v_str):
    try:
        return tuple(int(x) for x in re.findall(r"\d+", str(v_str)))
    except Exception:
        return (0,)

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
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None, ""
        date_match = re.search(r"Updated on\s*</div><div[^>]*>([^<]+)</div>", r.text)
        updated_date = date_match.group(1).strip() if date_match else None
        whats_new = ""
        wn_match = re.search(r"What\'s new.*?<div itemprop=\"description\">([^<]+)</div>", r.text, re.DOTALL)
        if not wn_match:
            wn_match = re.search(r"What\'s new</div></div><div[^>]*>([^<]+)</div>", r.text)
        if wn_match:
            whats_new = wn_match.group(1).strip()
        return updated_date, whats_new
    except Exception as e:
        print(f"Error fetching Google Play: {e}")
        return None, ""

def fetch_apkpure_details():
    url = "https://apkpure.com/growtopia-app/com.rtsoft.growtopia"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None, None, ""
        soup = BeautifulSoup(r.text, "html.parser")

        version = None
        date = None
        whats_new = ""

        ver_match = re.search(r"Growtopia\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)", r.text)
        if ver_match:
            version = ver_match.group(1)

        for title in soup.find_all(class_="title"):
            if "what's new" in title.text.lower():
                parent = title.parent
                lines = [l.strip() for l in parent.get_text("\n").split("\n") if l.strip()]
                wn_lines = []
                for line in lines:
                    if "what's new in the latest version" in line.lower():
                        m = re.search(r"version\s+([0-9]+\.[0-9]+)", line, re.I)
                        if m:
                            version = m.group(1)
                    elif "last updated on" in line.lower() or "updated on" in line.lower():
                        m = re.search(r"(?:last\s+)?updated\s+on\s+([A-Za-z]+\s+\d+,\s+\d{4})", line, re.I)
                        if m:
                            date = m.group(1)
                    elif line.lower() not in ["show more", "show less"]:
                        wn_lines.append(line)
                whats_new = "\n".join(wn_lines)
                break

        return version, date, whats_new
    except Exception as e:
        print(f"Error fetching APKPure details: {e}")
        return None, None, ""

def download_and_extract_cloud_items(target_path="cloud_items.dat"):
    """
    Downloads latest Growtopia package and extracts assets/items.dat in memory or to disk.
    Uses session with referer headers to avoid HTTP 403.
    """
    download_page = "https://apkpure.com/growtopia-app/com.rtsoft.growtopia/download"
    download_url = "https://d.apkpure.com/b/XAPK/com.rtsoft.growtopia?version=latest"
    temp_pkg = "temp_growtopia.xapk"

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    })

    print(f"Connecting to package provider...")
    try:
        s.get(download_page, timeout=15)
        s.headers.update({"Referer": download_page})

        print(f"Downloading Growtopia package from {download_url}...")
        with s.get(download_url, stream=True, timeout=90) as r:
            if r.status_code != 200:
                print(f"Package download returned HTTP {r.status_code}")
                return False

            with open(temp_pkg, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        print(f"Package downloaded ({os.path.getsize(temp_pkg)} bytes). Extracting items.dat...")

        # Extract items.dat from XAPK / APK
        extracted = False
        with zipfile.ZipFile(temp_pkg, "r") as zf:
            for name in zf.namelist():
                if name.endswith("items.dat"):
                    with open(target_path, "wb") as out:
                        out.write(zf.read(name))
                    extracted = True
                    break

            if not extracted:
                for name in zf.namelist():
                    if name.endswith(".apk"):
                        apk_bytes = zf.read(name)
                        with zipfile.ZipFile(io.BytesIO(apk_bytes), "r") as apk_zf:
                            for apk_name in apk_zf.namelist():
                                if apk_name.endswith("items.dat"):
                                    with open(target_path, "wb") as out:
                                        out.write(apk_zf.read(apk_name))
                                    extracted = True
                                    break
                    if extracted:
                        break

        if os.path.exists(temp_pkg):
            os.remove(temp_pkg)

        if extracted and os.path.exists(target_path):
            print(f"Successfully extracted {target_path} ({os.path.getsize(target_path)} bytes)")
            return True
        else:
            print("Notice: items.dat not found inside APK package (served via server cache handshake).")
            return False
    except Exception as e:
        print(f"Package download/extraction skipped: {e}")
        if os.path.exists(temp_pkg):
            os.remove(temp_pkg)
        return False

def send_discord_alert(title, description, fields=None, color=0x00FF88):
    payload = {
        "username": "Growtopia Cloud Sentinel",
        "avatar_url": "https://static.wikia.nocookie.net/growtopia/images/8/87/Growtopia_icon.png",
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": "Growtopia 24/7 Autonomous Cloud Sentinel • Powered by GitHub Actions"}
        }]
    }
    if fields:
        payload["embeds"][0]["fields"] = fields

    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        print("Discord alert status:", res.status_code)
        return res.status_code
    except Exception as e:
        print(f"Error sending Discord alert: {e}")
        return None

def main():
    print("Growtopia Cloud 24/7 Autonomous Sentinel Starting...")
    state = load_state()
    prev_version = state.get("version", "5.59")
    prev_date = state.get("updated_date", "Oct 5, 2026")
    prev_whats_new = state.get("whats_new", "")

    print(f"Baseline State: Version={prev_version}, UpdatedDate={prev_date}")

    apk_ver, apk_date, apk_wn = fetch_apkpure_details()
    gp_date, gp_whats_new = fetch_google_play()

    current_ver = apk_ver or prev_version
    current_date = apk_date or gp_date or prev_date
    current_wn = apk_wn or gp_whats_new or prev_whats_new

    print(f"Fetched Status: Version={current_ver}, UpdatedDate={current_date}")

    force_run = "--force" in sys.argv
    is_newer_version = parse_version_tuple(current_ver) > parse_version_tuple(prev_version)
    is_version_changed = (current_ver != prev_version)
    is_new_date = (current_date != prev_date)

    # Prevent false alarms: If version is identical, do NOT send a "new version leak" alert!
    if not is_newer_version and not is_version_changed and not force_run:
        if is_new_date:
            print(f"Store date updated ({prev_date} -> {current_date}), but version remains {current_ver}. Updating state silently.")
            state["updated_date"] = current_date
            if current_wn:
                state["whats_new"] = current_wn
            state["last_detected"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            save_state(state)
        else:
            print("No new updates detected. Everything is current.")
        return

    print(f"🚨 UPDATE DETECTED! (v{current_ver}) Starting autonomous cloud processing...")

    fields = [
        {"name": "🆕 New Version", "value": f"`v{current_ver}` (was `v{prev_version}`)", "inline": True},
        {"name": "📅 Release Date", "value": f"`{current_date}`", "inline": True}
    ]

    if current_wn:
        fields.append({"name": "📝 What's New", "value": current_wn[:1000], "inline": False})

    # Autonomous Datamining in Cloud if package contains items.dat
    cloud_dat_file = "cloud_items.dat"
    has_items_dat = download_and_extract_cloud_items(cloud_dat_file)

    if has_items_dat:
        try:
            v, new_items = gm.parse_itemsdat(cloud_dat_file)
            print(f"Parsed {len(new_items)} items from cloud items.dat (v{v})")

            # Load previous cloud snapshot
            prev_snapshot = gm.load_snapshot(CLOUD_SNAPSHOT_FILE)
            if not prev_snapshot:
                prev_snapshot = gm.load_snapshot()

            diff = gm.generate_items_diff(prev_snapshot, new_items)
            added = diff["added"]
            modified = diff["modified"]

            print(f"Cloud Diff computed: {len(added)} added, {len(modified)} modified")

            diff_summary = (
                f"• **🆕 New Items Added:** `{len(added)}`\n"
                f"• **🔄 Items Modified / Rebalanced:** `{len(modified)}`\n"
                f"• **📦 Total Database Count:** `{len(new_items):,}` (v{v})\n"
            )
            fields.append({"name": "📊 Autonomous Datamined Diff", "value": diff_summary, "inline": False})

            if added:
                top_added = [
                    f"• `#{it['id']}` **{it['name']}** (Rarity `{it['rarity']}`)"
                    for it in added[:12] if not it['name'].endswith('Seed')
                ]
                fields.append({
                    "name": f"✨ Key New Additions ({len(added)})",
                    "value": "\n".join(top_added) if top_added else f"{len(added)} new items",
                    "inline": False
                })

            if modified:
                mod_lines = []
                for m in modified[:6]:
                    mod_lines.append(f"• `#{m['id']}` **{m['name']}**: " + ", ".join(m['changes']))
                fields.append({
                    "name": f"🔄 Rebalanced / Modified Items ({len(modified)})",
                    "value": "\n".join(mod_lines),
                    "inline": False
                })

            # Save updated cloud snapshot
            with open(CLOUD_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
                json.dump(new_items, f, separators=(',', ':'))
            print("Cloud snapshot updated successfully.")

        except Exception as e:
            print(f"Error parsing cloud items.dat: {e}")
        finally:
            if os.path.exists(cloud_dat_file):
                os.remove(cloud_dat_file)

        description = (
            "**Ubisoft released a new Growtopia update!**\n"
            "The GitHub Actions Cloud Sentinel automatically downloaded the package, extracted `items.dat`, and decoded the new assets."
        )
    else:
        description = (
            "**Ubisoft released a new Growtopia update on the app store!**\n"
            f"The 24/7 Cloud Sentinel detected a version bump (`v{prev_version}` ➔ `v{current_ver}`).\n\n"
            "⚡ **Action:** Run the local dataminer (`python growtopia_miner.py`) or sync on your PC to extract the new `items.dat`."
        )

    send_discord_alert(
        title=f"🚨 NEW UPDATE: Growtopia v{current_ver} Released!",
        description=description,
        fields=fields,
        color=0xff0044
    )

    state["version"] = current_ver
    state["updated_date"] = current_date
    state["whats_new"] = current_wn
    state["last_detected"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    save_state(state)
    print("State updated and saved.")

if __name__ == "__main__":
    main()
