import os
import sys
import time
import struct
import zlib
import json
import requests
from PIL import Image, ImageDraw, ImageFont

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
        extra_str = ""

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
            if version >= 27:
                extra_str = read_str(item_id, encoded=False)

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
            "punch_options": punch_options,
            "extra_str": extra_str
        })

        # Future-proof boundary sync: If Ubisoft adds new bytes in future versions (v28, v29+),
        # ensure pos cleanly aligns to the next sequential item ID without drifting or crashing.
        if idx + 1 < item_count:
            next_target = struct.pack("<i", idx + 1)
            if pos + 4 <= len(data) and data[pos:pos+4] != next_target:
                found = data.find(next_target, pos, pos + 64)
                if found != -1:
                    pos = found

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

BODY_PART_MAP = {
    0: "None / Block",
    1: "Shirt / Chest",
    2: "Pants",
    3: "Shoes / Feet",
    4: "Face / Mask",
    5: "Hand / Weapon",
    6: "Back / Wings",
    7: "Hair / Hat",
    8: "Chest Accessory",
    9: "Ances / Charm"
}

def get_item_icon(texture_file, tex_x, tex_y, item_id, output_dir=SCRIPT_DIR):
    """
    Crops and upscales a crystal-clear 128x128 single item icon from the game's sprite sheet.
    """
    if not texture_file:
        return None

    icons_dir = os.path.join(output_dir, "icons")
    os.makedirs(icons_dir, exist_ok=True)
    out_path = os.path.join(icons_dir, f"item_{item_id}.png")

    if os.path.exists(out_path):
        return out_path

    sheet_rttex = os.path.join(GAME_DIR, texture_file)
    if not os.path.exists(sheet_rttex):
        return None

    sheet_png = os.path.join(output_dir, texture_file.replace(".rttex", ".png"))
    if not os.path.exists(sheet_png):
        try:
            convert_rttex(sheet_rttex, sheet_png)
        except Exception:
            return None

    if not os.path.exists(sheet_png):
        return None

    try:
        img = Image.open(sheet_png)
        w, h = img.size
        tile_size = 32

        left = tex_x * tile_size
        top = tex_y * tile_size
        right = left + tile_size
        bottom = top + tile_size

        if right <= w and bottom <= h:
            cropped = img.crop((left, top, right, bottom))
            scaled = cropped.resize((128, 128), Image.Resampling.NEAREST)
            scaled.save(out_path)
            return out_path
    except Exception as e:
        print(f"Error cropping icon for item #{item_id}: {e}")

    return None

def generate_showcase_grid(item_list, output_path=None, max_items=25):
    """
    Generates a high-resolution dark-themed composite showcase grid of datamined items.
    Combines up to max_items into a single sleek graphic with item IDs, names, and rarities.
    """
    if not item_list:
        return None

    # Filter out seeds unless only seeds are provided
    display_items = [it for it in item_list if not it.get("name", "").endswith("Seed") and "null_item" not in it.get("name", "")]
    if not display_items:
        display_items = item_list
    display_items = display_items[:max_items]

    if not display_items:
        return None

    if output_path is None:
        output_path = os.path.join(SCRIPT_DIR, "leak_showcase.png")

    cols = 5
    rows = (len(display_items) + cols - 1) // cols
    cell_w, cell_h = 140, 160
    header_h = 44
    padding = 12

    total_w = padding * 2 + cols * cell_w
    total_h = header_h + rows * cell_h + padding * 2

    canvas = Image.new("RGBA", (total_w, total_h), (24, 25, 28, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    # Header banner
    draw.rectangle([0, 0, total_w, header_h], fill=(35, 39, 42, 255))
    draw.line([0, header_h, total_w, header_h], fill=(88, 101, 242, 255), width=2)
    header_text = f"GROWTOPIA DATAMINED ASSETS • {len(display_items)} ITEMS SHOWCASE"
    draw.text((padding + 6, 16), header_text, fill=(235, 237, 239, 255), font=font)

    for i, it in enumerate(display_items):
        col = i % cols
        row = i // cols
        x = padding + col * cell_w
        y = header_h + padding + row * cell_h

        # Card container
        card_rect = [x + 4, y + 4, x + cell_w - 4, y + cell_h - 4]
        draw.rounded_rectangle(card_rect, radius=8, fill=(43, 45, 49, 255), outline=(58, 62, 69, 255), width=1)

        # Draw icon
        icon_path = get_item_icon(it.get("texture"), it.get("tex_x", 0), it.get("tex_y", 0), it["id"])
        if icon_path and os.path.exists(icon_path):
            try:
                icon_img = Image.open(icon_path).convert("RGBA")
                icon_resized = icon_img.resize((84, 84), Image.Resampling.NEAREST)
                canvas.paste(icon_resized, (x + (cell_w - 84) // 2, y + 10), icon_resized)
            except Exception:
                pass

        # Draw Item ID badge
        id_str = f"#{it['id']}"
        badge_w = len(id_str) * 7 + 8
        draw.rounded_rectangle([x + 10, y + 102, x + 10 + badge_w, y + 118], radius=4, fill=(30, 31, 34, 255))
        draw.text((x + 14, y + 104), id_str, fill=(88, 101, 242, 255), font=font)

        # Draw Item Name (truncated)
        name = it.get("name", "Unknown")
        if len(name) > 17:
            name = name[:15] + ".."
        draw.text((x + 10, y + 124), name, fill=(255, 255, 255, 255), font=font)

        # Draw Rarity or slot
        rarity = it.get("rarity", 0)
        rarity_str = f"Rarity: {rarity}" if rarity else "Untradeable"
        draw.text((x + 10, y + 138), rarity_str, fill=(150, 155, 165, 255), font=font)

    try:
        canvas.save(output_path, "PNG")
        return output_path
    except Exception as e:
        print(f"Error saving showcase grid: {e}")
        return None

def generate_item_card(item, output_path=None):
    """
    Renders a sleek dark-themed infographic card for an individual item.
    Includes item icon, ID, name, rarity, slot, break hits/grow time, and description quote.
    """
    if not item:
        return None

    cards_dir = os.path.join(SCRIPT_DIR, "cards")
    os.makedirs(cards_dir, exist_ok=True)
    if output_path is None:
        output_path = os.path.join(cards_dir, f"card_{item['id']}.png")

    w, h = 480, 200
    canvas = Image.new("RGBA", (w, h), (24, 25, 28, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    # Outer border & background
    draw.rounded_rectangle([2, 2, w - 2, h - 2], radius=12, fill=(35, 37, 41, 255), outline=(58, 62, 69, 255), width=2)

    # Left icon container
    rarity = item.get("rarity", 0)
    border_color = (241, 196, 15, 255) if rarity >= 900 else (88, 101, 242, 255)
    draw.rounded_rectangle([18, 18, 162, 162], radius=10, fill=(43, 45, 49, 255), outline=border_color, width=2)

    # Get & paste icon
    icon_path = get_item_icon(item.get("texture"), item.get("tex_x", 0), item.get("tex_y", 0), item["id"])
    if icon_path and os.path.exists(icon_path):
        try:
            icon_img = Image.open(icon_path).convert("RGBA")
            icon_resized = icon_img.resize((120, 120), Image.Resampling.NEAREST)
            canvas.paste(icon_resized, (30, 30), icon_resized)
        except Exception:
            pass

    # Right details area
    id_str = f"#{item['id']}"
    badge_w = len(id_str) * 8 + 10
    draw.rounded_rectangle([180, 20, 180 + badge_w, 38], radius=4, fill=(88, 101, 242, 255))
    draw.text((185, 23), id_str, fill=(255, 255, 255, 255), font=font)

    # Item Name
    name = item.get("name", "Unknown Item")
    draw.text((180, 46), name[:28], fill=(255, 255, 255, 255), font=font)

    # Slot & Rarity
    slot = BODY_PART_MAP.get(item.get("body_part", 0), "None / Block")
    draw.text((180, 72), f"Slot: {slot}", fill=(185, 190, 200, 255), font=font)
    rarity_text = f"Rarity: {rarity}" if rarity else "Untradeable"
    draw.text((180, 90), rarity_text, fill=(241, 196, 15, 255) if rarity >= 900 else (185, 190, 200, 255), font=font)

    if item.get("break_hits", 0) > 0:
        draw.text((180, 108), f"Hardness: {item['break_hits']} hits", fill=(150, 155, 165, 255), font=font)
    elif item.get("grow_time", 0) > 0:
        draw.text((180, 108), f"Grow Time: {item['grow_time']}s", fill=(150, 155, 165, 255), font=font)
    else:
        tex = item.get("texture", "")
        draw.text((180, 108), f"Texture: {tex[:24]}", fill=(150, 155, 165, 255), font=font)

    # Description (quote)
    if item.get("info"):
        desc = item["info"].strip()
        if len(desc) > 38:
            desc = desc[:36] + "..."
        draw.text((180, 132), f'"{desc}"', fill=(130, 135, 145, 255), font=font)

    # Watermark / Footer
    draw.text((180, 166), "GROWTOPIA DATAMINER • ASSET LEAKS", fill=(100, 105, 115, 255), font=font)

    try:
        canvas.save(output_path, "PNG")
        return output_path
    except Exception as e:
        print(f"Error saving item card: {e}")
        return None

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
