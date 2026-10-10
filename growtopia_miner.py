import os
import sys
import time
import struct
import zlib
import json
import requests
from PIL import Image

DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1558414040466984963/fqks_HwbDPMBCbsO6Mu4fEDTIC568rv-6XmW9ZmFoKVFDchcwpzu0eXWaOSYfDPGT9-m"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "dataminer_state.json")

DEFAULT_GT_PATH = os.path.expandvars(r"%LOCALAPPDATA%\Growtopia")
ITEMS_DAT_PATH = os.path.join(DEFAULT_GT_PATH, "cache", "items.dat")
GAME_DIR = os.path.join(DEFAULT_GT_PATH, "game")

SECRET_KEY = "PBG892FXX982ABC*"

def parse_itemsdat(filepath=ITEMS_DAT_PATH):
    if not os.path.exists(filepath):
        alt_path = os.path.join(DEFAULT_GT_PATH, "items.dat")
        if os.path.exists(alt_path):
            filepath = alt_path
        else:
            raise FileNotFoundError(f"Could not find items.dat at {filepath}")

    with open(filepath, "rb") as f:
        data = f.read()

    pos = 0
    version, item_count = struct.unpack_from("<HI", data, pos)
    pos += 6

    items = []

    def read_str(item_id, encoded=False):
        nonlocal pos
        length = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        raw = data[pos:pos+length]
        pos += length
        if not encoded:
            return raw.decode("latin1", errors="ignore")
        else:
            chars = []
            for i, b in enumerate(raw):
                k = ord(SECRET_KEY[(item_id + i) % len(SECRET_KEY)])
                chars.append(chr(b ^ k))
            return "".join(chars)

    for idx in range(item_count):
        item_id = struct.unpack_from("<i", data, pos)[0]
        pos += 4
        flags, it_type, material = struct.unpack_from("<HBB", data, pos)
        pos += 4

        name = read_str(item_id, encoded=True)
        texture = read_str(item_id, encoded=False)

        tex_hash, visual_fx, cook_time = struct.unpack_from("<iBi", data, pos)
        pos += 9

        tex_x, tex_y, storage_type, is_stripe, collision, break_hits = struct.unpack_from("<BBBBBB", data, pos)
        pos += 6

        reset_state, body_part, rarity, max_amount = struct.unpack_from("<iBhB", data, pos)
        pos += 8

        extra_file = read_str(item_id)
        extra_file_hash, audio_vol = struct.unpack_from("<ii", data, pos)
        pos += 8

        pet_name = read_str(item_id)
        pet_prefix = read_str(item_id)
        pet_suffix = read_str(item_id)
        pet_ability = read_str(item_id)

        seed_base, seed_over, tree_base, tree_leaves = struct.unpack_from("<BBBB", data, pos)
        pos += 4
        seed_color, seed_over_color, ingredient, grow_time, fx_flags = struct.unpack_from("<iiiii", data, pos)
        pos += 20

        extra_options = read_str(item_id)
        texture2 = read_str(item_id)
        extra_options2 = read_str(item_id)

        unk1, unk2, flags2 = struct.unpack_from("<iii", data, pos)
        pos += 12

        pos += 60  # extraBytes

        tile_range, vault_cap = struct.unpack_from("<ii", data, pos)
        pos += 8

        info = ""
        hit_sfx = ""
        punch_options = ""

        if version >= 11:
            punch_options = read_str(item_id)
            if version >= 12:
                pos += 4 + 9
            if version >= 13:
                pos += 4
            if version >= 14:
                pos += 4
            if version >= 15:
                pos += 1 + 24
                chair_tex = read_str(item_id)
            if version >= 16:
                item_renderer = read_str(item_id)
            if version >= 17:
                pos += 4
            if version >= 18:
                pos += 4
            if version >= 19:
                pos += 9
            if version >= 21:
                pos += 2
            if version >= 22:
                info = read_str(item_id)
            if version >= 23:
                pos += 4
            if version >= 24:
                pos += 1
            if version >= 25:
                hit_sfx = read_str(item_id, encoded=False)
                pos += 4
            if version >= 26:
                pos += 1

        items.append({
            "id": item_id,
            "name": name,
            "texture": texture,
            "rarity": rarity,
            "grow_time": grow_time,
            "break_hits": break_hits,
            "item_type": it_type,
            "body_part": body_part,
            "collision": collision,
            "tex_x": tex_x,
            "tex_y": tex_y,
            "info": info,
            "punch_options": punch_options
        })

    return version, items

SNAPSHOT_FILE = os.path.join(SCRIPT_DIR, "items_snapshot.json")

def save_snapshot(items, filepath=SNAPSHOT_FILE):
    """Saves items list as JSON baseline snapshot."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving snapshot: {e}")
        return False

def load_snapshot(filepath=SNAPSHOT_FILE):
    """Loads previous items list baseline snapshot."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading snapshot: {e}")
    return None

def generate_items_diff(old_items, new_items):
    """
    Compares two lists of item dicts and detects:
    - New items (new IDs)
    - Modified / rebalanced items (rarity, grow time, break hits, textures, name changes)
    - Removed items
    """
    if not old_items:
        return {"added": new_items, "modified": [], "removed": []}

    old_map = {it["id"]: it for it in old_items}
    new_map = {it["id"]: it for it in new_items}

    added = []
    modified = []
    removed = []

    for item_id, new_it in new_map.items():
        if item_id not in old_map:
            added.append(new_it)
        else:
            old_it = old_map[item_id]
            changes = []

            # Check rename (e.g. placeholder null_item -> actual item name)
            old_name = old_it.get("name", "")
            new_name = new_it.get("name", "")
            if old_name != new_name:
                changes.append(f"Name: `{old_name}` -> **`{new_name}`**")

            # Check rarity change / rebalance
            if old_it.get("rarity") != new_it.get("rarity"):
                changes.append(f"Rarity: `{old_it.get('rarity')}` -> `{new_it.get('rarity')}`")

            # Check grow time change
            if old_it.get("grow_time") != new_it.get("grow_time"):
                changes.append(f"Grow Time: `{old_it.get('grow_time')}s` -> `{new_it.get('grow_time')}s`")

            # Check break hits / hardness change
            if old_it.get("break_hits") != new_it.get("break_hits"):
                changes.append(f"Break Hits: `{old_it.get('break_hits')}` -> `{new_it.get('break_hits')}`")

            # Check texture change
            if old_it.get("texture") != new_it.get("texture"):
                changes.append(f"Texture: `{old_it.get('texture')}` -> `{new_it.get('texture')}`")

            if changes:
                modified.append({
                    "id": item_id,
                    "name": new_name or old_name,
                    "changes": changes
                })

    for item_id, old_it in old_map.items():
        if item_id not in new_map:
            removed.append(old_it)

    return {
        "added": added,
        "modified": modified,
        "removed": removed
    }

def convert_rttex(rttex_path, output_png_path):
    with open(rttex_path, "rb") as f:
        data = f.read()

    if data.startswith(b"RTPACK"):
        data = zlib.decompress(data[32:])

    if not data.startswith(b"RTTXTR"):
        raise ValueError(f"{rttex_path} is not a valid RTTEX file")

    h, w, fmt, orig_h, orig_w = struct.unpack_from("<IIIII", data, 8)
    pixel_data = data[124:124 + h * w * 4]

    img = Image.frombytes("RGBA", (w, h), pixel_data)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img.save(output_png_path)
    return w, h

def send_discord_webhook(title, description, fields=None, image_path=None, color=0x2ecc71):
    payload = {
        "username": "Growtopia Dataminer",
        "avatar_url": "https://static.wikia.nocookie.net/growtopia/images/8/87/Growtopia_icon.png",
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": "Growtopia Dataminer • Real-Time Watcher"}
        }]
    }

    if fields:
        payload["embeds"][0]["fields"] = fields

    if image_path and os.path.exists(image_path):
        filename = os.path.basename(image_path)
        payload["embeds"][0]["image"] = {"url": f"attachment://{filename}"}
        with open(image_path, "rb") as f:
            files = {"file": (filename, f, "image/png")}
            res = requests.post(
                DISCORD_WEBHOOK_URL,
                data={"payload_json": json.dumps(payload)},
                files=files
            )
    else:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload)

    return res.status_code

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_count": 0, "last_mtime": 0}

def save_state(count, mtime):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_count": count, "last_mtime": mtime}, f)

def watch_mode():
    print("======================================================")
    print(" 👀 GROWTOPIA REAL-TIME AUTO-WATCHER STARTED")
    print(f" Target File: {ITEMS_DAT_PATH}")
    print(" Checks every 2 seconds for instant leak detection...")
    print(" Press Ctrl + C to stop.")
    print("======================================================")

    state = load_state()
    version, items = parse_itemsdat()
    current_count = len(items)
    current_mtime = os.path.getmtime(ITEMS_DAT_PATH)

    if state["last_count"] == 0:
        save_state(current_count, current_mtime)
        print(f"Baseline established: {current_count} items (items.dat v{version}). Watching for new patches...")
    else:
        print(f"Currently tracking: {current_count} items. Previous recorded: {state['last_count']}")

    while True:
        try:
            time.sleep(2)
            if not os.path.exists(ITEMS_DAT_PATH):
                continue

            mtime = os.path.getmtime(ITEMS_DAT_PATH)
            state = load_state()

            # Check if file was modified
            if mtime != state.get("last_mtime"):
                print(f"\n[ALERT] items.dat modification detected at {time.strftime('%H:%M:%S')}!")
                v, new_items = parse_itemsdat()
                new_count = len(new_items)
                old_count = state.get("last_count", 0)

                if new_count > old_count:
                    added_items = new_items[old_count:]
                    print(f"🚨 FOUND {len(added_items)} BRAND NEW ITEMS!")

                    # Format Discord alert
                    fields = []
                    for it in added_items[:15]:
                        fields.append({
                            "name": f"ID #{it['id']}: {it['name']}",
                            "value": f"**Texture:** `{it['texture']}` | **Rarity:** {it['rarity']}",
                            "inline": False
                        })

                    # Try to convert texture of the newest item
                    attached_img = None
                    newest_tex = added_items[-1]["texture"]
                    if newest_tex:
                        rttex_path = os.path.join(GAME_DIR, newest_tex)
                        if os.path.exists(rttex_path):
                            attached_img = os.path.join(SCRIPT_DIR, "instant_leak_sprite.png")
                            convert_rttex(rttex_path, attached_img)

                    send_discord_webhook(
                        title="🚨 INSTANT LEAK: New Growtopia Update Detected!",
                        description=(
                            f"**Growtopia just updated in the last second!**\n\n"
                            f"📦 **Previous items:** `{old_count:,}`\n"
                            f"🔥 **New items count:** `{new_count:,}` (+{len(added_items)} items added)\n"
                            f"🆕 **Database Version:** `v{v}`"
                        ),
                        fields=fields,
                        image_path=attached_img,
                        color=0xff0044
                    )
                    print("✅ Discord alert posted instantly!")

                save_state(new_count, mtime)

        except KeyboardInterrupt:
            print("\nAuto-Watcher stopped.")
            break
        except Exception as e:
            print(f"[Error] {e}")
            time.sleep(3)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        watch_mode()
    else:
        # Default run: Show current items and prompt for watch mode
        version, items = parse_itemsdat()
        print(f"Loaded {len(items)} items from items.dat (v{version})")
        print("\nTip: Run 'python growtopia_miner.py watch' to start real-time 24/7 monitoring!")
