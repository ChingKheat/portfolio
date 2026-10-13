import os
import sys
import json
import asyncio

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Prevent multiple bot instances from running simultaneously
if sys.platform == "win32":
    import ctypes
    ERROR_ALREADY_EXISTS = 183
    _bot_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "GrowtopiaDataminerBotSingletonMutex")
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        print("[WARNING] Another instance of Growtopia Dataminer bot is already running. Exiting.")
        sys.exit(0)

# Handle windowless / pythonw execution
if sys.stdout is None:
    sys.stdout = open(os.path.join(SCRIPT_DIR, "bot.log"), "a", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.path.join(SCRIPT_DIR, "bot.log"), "a", encoding="utf-8")

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import discord
from discord.ext import commands, tasks
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "bot_config.json")

# Import our dataminer logic
sys.path.append(SCRIPT_DIR)
from growtopia_miner import (
    parse_itemsdat,
    convert_rttex,
    get_item_icon,
    BODY_PART_MAP,
    generate_items_diff,
    save_snapshot,
    load_snapshot,
    ITEMS_DAT_PATH,
    GAME_DIR,
    DEFAULT_GT_PATH
)

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

BOT_TOKEN = config.get("token")
PREFIX = config.get("prefix", "!")
WATCHER_ENABLED = True
ALERT_CHANNEL_ID = config.get("alert_channel_id")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Cache loaded items in memory
ITEMS_CACHE = []
ITEMS_VERSION = 27
LAST_MTIME = 0
LAST_COUNT = 0

def refresh_items():
    global ITEMS_CACHE, ITEMS_VERSION, LAST_MTIME, LAST_COUNT
    if os.path.exists(ITEMS_DAT_PATH):
        try:
            LAST_MTIME = os.path.getmtime(ITEMS_DAT_PATH)
            ITEMS_VERSION, ITEMS_CACHE = parse_itemsdat()
            LAST_COUNT = len(ITEMS_CACHE)
            print(f"Loaded {LAST_COUNT} items (v{ITEMS_VERSION})")
            return True
        except Exception as e:
            print(f"Error loading items.dat: {e}")
            return False
    return False

GROWTOPIA_EXE = os.path.join(DEFAULT_GT_PATH, "Growtopia.exe")

async def perform_silent_sync(max_seconds=5):
    """
    Silently launches Growtopia minimized in the background for 4-5 seconds
    (or closes immediately as soon as items.dat updates).
    """
    if not os.path.exists(GROWTOPIA_EXE):
        return False, "Growtopia.exe not found in local directory."

    import psutil
    # Check if user is already playing to avoid interrupting
    for p in psutil.process_iter(['name']):
        try:
            if "Growtopia.exe" in p.name():
                return False, "Growtopia is currently open. Skipping silent sync to avoid interrupting your game."
        except Exception:
            pass

    import subprocess
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 6  # SW_MINIMIZE

    old_mtime = os.path.getmtime(ITEMS_DAT_PATH) if os.path.exists(ITEMS_DAT_PATH) else 0

    try:
        proc = subprocess.Popen([GROWTOPIA_EXE], startupinfo=startupinfo)
        # Check every 0.5s up to max_seconds (default 5s max)
        steps = int(max_seconds * 2)
        for _ in range(steps):
            await asyncio.sleep(0.5)
            # If items.dat updated, finish immediately!
            if os.path.exists(ITEMS_DAT_PATH) and os.path.getmtime(ITEMS_DAT_PATH) != old_mtime:
                break

        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
        return True, "Sync completed successfully."
    except Exception as e:
        return False, f"Error during silent sync: {e}"

def categorize_items(item_list):
    """Dynamically categorizes items by their in-game type and wearable slot."""
    categories = {
        "⚔️ Weapons & Hand Items": [],
        "🪽 Wings, Capes & Back": [],
        "🐎 Mounts & Shoes": [],
        "👑 Hats, Hair & Faces": [],
        "👕 Shirts, Pants & Suits": [],
        "🔮 Auras, Pets & Artifacts": [],
        "🧱 Placeables & Weather": [],
        "🌱 Paired Seeds": [],
        "📦 Other Items": []
    }

    for it in item_list:
        name = it.get("name", "")
        if name.endswith("Seed"):
            categories["🌱 Paired Seeds"].append(it)
            continue

        body_part = it.get("body_part", 0)
        item_type = it.get("item_type", 0)

        if body_part == 5:
            categories["⚔️ Weapons & Hand Items"].append(it)
        elif body_part == 6:
            categories["🪽 Wings, Capes & Back"].append(it)
        elif body_part == 3:
            categories["🐎 Mounts & Shoes"].append(it)
        elif body_part in (4, 7):
            categories["👑 Hats, Hair & Faces"].append(it)
        elif body_part in (1, 2):
            categories["👕 Shirts, Pants & Suits"].append(it)
        elif body_part in (8, 9) or "aura" in name.lower() or "leash" in name.lower() or "pet" in name.lower():
            categories["🔮 Auras, Pets & Artifacts"].append(it)
        elif item_type in (2, 3, 41) or body_part == 0:
            categories["🧱 Placeables & Weather"].append(it)
        else:
            categories["📦 Other Items"].append(it)

    return {k: v for k, v in categories.items() if v}

def format_item_line(it):
    rarity = f"Rarity `{it.get('rarity', 0)}`" if it.get('rarity') else "Untradeable"
    slot = BODY_PART_MAP.get(it.get("body_part", 0), "")
    slot_str = f" *({slot})*" if slot and slot != "None / Block" else ""
    line = f"• `#{it['id']}` **{it['name']}**{slot_str} — {rarity}"
    if it.get("info"):
        desc = it['info'].strip()
        if len(desc) > 95:
            desc = desc[:92] + "..."
        line += f"\n  ╰ *\"{desc}\"*"
    return line

def add_chunked_field(embed, field_name, lines, max_per_field=1000):
    chunk = []
    chunk_len = 0
    part = 1
    for line in lines:
        if chunk_len + len(line) + 1 > max_per_field:
            embed.add_field(
                name=f"{field_name} (Part {part})" if part > 1 else field_name,
                value="\n".join(chunk),
                inline=False
            )
            chunk = [line]
            chunk_len = len(line)
            part += 1
        else:
            chunk.append(line)
            chunk_len += len(line) + 1
    if chunk:
        embed.add_field(
            name=f"{field_name} (Part {part})" if part > 1 else field_name,
            value="\n".join(chunk),
            inline=False
        )

def build_leak_embed(diff, total_count, version, mtime_str, title="🚨 GROWTOPIA DATABASE UPDATE DETECTED!"):
    """Builds a psychological, high-contrast, full-width Details Page embed for updates."""
    added = diff.get("added", [])
    modified = diff.get("modified", [])

    embed = discord.Embed(
        title=title,
        description=(
            f"> 📦 **Database Version:** `items.dat v{version}` • **Total:** `{total_count:,}` items\n"
            f"> 📅 **Detected At:** `{mtime_str}`\n"
            f"> 🆕 **New Items Discovered:** `{len(added)}`\n"
            f"> 🔄 **Rebalanced / Unveiled Items:** `{len(modified)}`\n\n"
            "```yaml\n"
            "📊 Summary: Live game files were updated with newly datamined content!\n"
            "```"
        ),
        color=0xFF0044
    )

    if added:
        cats = categorize_items(added)
        for cat_name, cat_items in cats.items():
            if cat_name == "🌱 Paired Seeds":
                seed_strs = [f"`{s['id']}` {s['name']}" for s in cat_items[:12]]
                val = " • ".join(seed_strs)
                if len(cat_items) > 12:
                    val += f" • *...plus {len(cat_items) - 12} more seeds*"
                embed.add_field(name=f"{cat_name} ({len(cat_items)})", value=val, inline=False)
            else:
                lines = [format_item_line(it) for it in cat_items[:12]]
                if len(cat_items) > 12:
                    lines.append(f"• *...plus `{len(cat_items) - 12}` more items in this slot!*")
                add_chunked_field(embed, f"{cat_name} ({len(cat_items)})", lines)

    if modified:
        main_mods = [m for m in modified if not m['name'].endswith('Seed')]
        if main_mods:
            mod_lines = []
            for m in main_mods[:25]:
                mod_lines.append(f"• `#{m['id']}` **{m['name']}**:\n  ╰ " + ", ".join(m['changes']))
            if len(main_mods) > 25:
                mod_lines.append(f"• *...plus `{len(main_mods) - 25}` more modified items!*")
            add_chunked_field(embed, f"🔄 Unveiled / Rebalanced Items ({len(main_mods)})", mod_lines)
        seed_mods = [m for m in modified if m['name'].endswith('Seed')]
        if seed_mods:
            embed.add_field(
                name=f"🌱 Seed Changes ({len(seed_mods)})",
                value=f"• `{len(seed_mods)}` event seeds activated/updated alongside their main items.",
                inline=False
            )

    embed.set_footer(text=f"Growtopia Instant Watcher • Total: {total_count:,} items • Type !item <name or ID>")
    return embed

async def check_and_broadcast_updates(ctx_to_reply=None):
    """
    Universal update checker:
    Compares live items against items_snapshot.json.
    If ANY changes exist, broadcasts to ALERT_CHANNEL_ID and updates snapshot.
    """
    global LAST_MTIME, ITEMS_CACHE, ITEMS_VERSION, LAST_COUNT

    if not os.path.exists(ITEMS_DAT_PATH):
        return None

    snapshot = load_snapshot()
    if not refresh_items():
        return None

    import datetime
    mtime = os.path.getmtime(ITEMS_DAT_PATH)
    mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y at %I:%M:%S %p")

    if not snapshot:
        save_snapshot(ITEMS_CACHE)
        print("[Auto-Monitor] Initial baseline snapshot saved.")
        return None

    diff = generate_items_diff(snapshot, ITEMS_CACHE)
    added = diff.get("added", [])
    modified = diff.get("modified", [])

    if added or modified:
        print(f"🚨 [BROADCAST] Detected {len(added)} added and {len(modified)} modified items!")
        embed = build_leak_embed(diff, len(ITEMS_CACHE), ITEMS_VERSION, mtime_str)

        # Broadcast to alert channel (#data)
        if ALERT_CHANNEL_ID:
            ch = bot.get_channel(ALERT_CHANNEL_ID)
            if not ch:
                try:
                    ch = await bot.fetch_channel(ALERT_CHANNEL_ID)
                except Exception as e:
                    print(f"Error fetching alert channel: {e}")
            if ch:
                try:
                    await ch.send(embed=embed)
                except Exception as e:
                    print(f"Error sending update embed: {e}")

        # Also reply to command sender if called via !sync or !check
        if ctx_to_reply and ctx_to_reply.channel.id != ALERT_CHANNEL_ID:
            try:
                await ctx_to_reply.send(embed=embed)
            except Exception:
                pass

        # Update snapshot to the new baseline so it doesn't alert repeatedly
        save_snapshot(ITEMS_CACHE)
        return diff

    return None

@tasks.loop(hours=2)
async def auto_hotfix_sync_loop():
    """Periodically checks for silent server maintenance hotfixes in the background every 2 hours."""
    if not WATCHER_ENABLED:
        return
    print("[Auto-Hotfix] Starting scheduled 2-hour background game sync...")
    success, msg = await perform_silent_sync(max_seconds=5)
    print(f"[Auto-Hotfix] Result: {msg}")
    if success:
        await check_and_broadcast_updates()

@bot.event
async def on_ready():
    print(f"==================================================")
    print(f" 🤖 GROWTOPIA DISCORD BOT LOGGED IN AS: {bot.user}")
    print(f" Ready to respond to commands ({PREFIX}latest, {PREFIX}diff, {PREFIX}item, {PREFIX}sync, {PREFIX}help)")
    print(f"==================================================")
    refresh_items()

    # CHECK FOR UPDATES IMMEDIATELY ON BOOT:
    # Catches any update that happened while the bot was offline or restarting
    await check_and_broadcast_updates()

    if not auto_monitor.is_running():
        auto_monitor.start()
    if not auto_hotfix_sync_loop.is_running():
        auto_hotfix_sync_loop.start()

    # Post an online confirmation to the channel so the user knows it's active
    if ALERT_CHANNEL_ID:
        try:
            channel = bot.get_channel(ALERT_CHANNEL_ID)
            if channel:
                await channel.send("🟢 **Growtopia Dataminer is ONLINE & MONITORING 24/7!** Ready for commands (`!latest`, `!diff`, `!sync`, `!item`).")
        except Exception as e:
            print(f"Error announcing online: {e}")

@bot.event
async def on_command_error(ctx, error):
    print(f"[Command Error in {ctx.command}]: {error}")
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"⚠️ **Error executing command:** `{error}`")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # Handle multi-line messages gracefully (e.g. user sends !sync and !start together)
    lines = [line.strip() for line in message.content.split("\n") if line.strip().startswith(PREFIX)]
    if len(lines) > 1:
        for line in lines:
            message.content = line
            await bot.process_commands(message)
    else:
        await bot.process_commands(message)

@bot.command(name="help")
async def cmd_help(ctx):
    embed = discord.Embed(
        title="🎮 Growtopia Dataminer Bot Commands",
        description="Type any of these commands in this channel:",
        color=0x3498db
    )
    embed.add_field(name=f"`{PREFIX}latest`", value="Show the newest in-game additions & leaked items from the latest patch.", inline=False)
    embed.add_field(name=f"`{PREFIX}diff`", value="Show the patch changelog & diff against baseline snapshot (or `!diff 25`).", inline=False)
    embed.add_field(name=f"`{PREFIX}check`", value="Scan local and Ubisoft game files for new updates right now.", inline=False)
    embed.add_field(name=f"`{PREFIX}sync`", value="Silently check Ubisoft servers for new patches & hotfixes.", inline=False)
    embed.add_field(name=f"`{PREFIX}item <name or ID>`", value="Search any item (e.g. `!item Pickaxe` or `!item 16400`) for stats & 128x128 sprite.", inline=False)
    embed.add_field(name=f"`{PREFIX}start`", value="Lock automatic update alerts to this channel and start 24/7 monitoring.", inline=False)
    embed.add_field(name=f"`{PREFIX}status`", value="Check if the real-time background watcher is active.", inline=False)
    embed.add_field(name=f"`{PREFIX}stop`", value="Pause automatic leak alerts.", inline=False)
    embed.set_footer(text=f"Prefix: {PREFIX} • Total Items Tracked: {len(ITEMS_CACHE):,}")
    await ctx.send(embed=embed)

@bot.command(name="start")
async def cmd_start(ctx):
    global WATCHER_ENABLED, ALERT_CHANNEL_ID
    WATCHER_ENABLED = True
    ALERT_CHANNEL_ID = ctx.channel.id

    config["alert_channel_id"] = ALERT_CHANNEL_ID
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass

    embed = discord.Embed(
        title="🚀 Growtopia Auto-Watcher STARTED!",
        description=(
            f"**Channel Locked:** Live alerts will be sent here in <#{ctx.channel.id}>!\n"
            f"**Status:** 🟢 **Active 24/7 Monitoring**\n"
            f"**Items Tracked:** `{len(ITEMS_CACHE):,}` items (v{ITEMS_VERSION})\n\n"
            f"The bot is actively listening for updates every 5 seconds. "
            f"The second a patch downloads, it will post the leak right here!"
        ),
        color=0x2ecc71
    )
    await ctx.send(embed=embed)
    await cmd_latest(ctx)

@bot.command(name="stop")
async def cmd_stop(ctx):
    global WATCHER_ENABLED
    WATCHER_ENABLED = False
    embed = discord.Embed(
        title="⏸️ Growtopia Auto-Watcher Paused",
        description="Automatic leak alerts have been paused. Type `!start` anytime to turn them back on!",
        color=0xe74c3c
    )
    await ctx.send(embed=embed)

@bot.command(name="status")
async def cmd_status(ctx):
    status_text = "🟢 **ACTIVE & MONITORING**" if WATCHER_ENABLED else "🔴 **PAUSED**"
    ch_text = f"<#{ALERT_CHANNEL_ID}>" if ALERT_CHANNEL_ID else "Default channel"
    embed = discord.Embed(
        title="📊 Growtopia Watcher Status",
        description=(
            f"• **Status:** {status_text}\n"
            f"• **Alert Channel:** {ch_text}\n"
            f"• **Total Items Tracked:** `{len(ITEMS_CACHE):,}` (v{ITEMS_VERSION})\n"
            f"• **Check Frequency:** Every 5 seconds"
        ),
        color=0x3498db
    )
    await ctx.send(embed=embed)

@bot.command(name="latest")
async def cmd_latest(ctx):
    """
    Dynamically displays the latest in-game additions from items.dat,
    categorized by gameplay slot (Weapons, Mounts, Wings, Hats, Costumes, etc.).
    Completely dynamic for all future updates.
    """
    if not ITEMS_CACHE:
        refresh_items()

    import datetime
    mtime_str = "Recently"
    if os.path.exists(ITEMS_DAT_PATH):
        mtime = os.path.getmtime(ITEMS_DAT_PATH)
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y at %I:%M %p")

    # Dynamically select the newest non-seed items from the database
    non_seeds = [it for it in ITEMS_CACHE if not it['name'].endswith('Seed') and 'null_item' not in it['name']]
    newest_items = non_seeds[-35:] if len(non_seeds) >= 35 else non_seeds
    start_id = newest_items[0]['id'] if newest_items else 0
    end_id = newest_items[-1]['id'] if newest_items else 0

    embed = discord.Embed(
        title="✨ Growtopia Latest In-Game Items Directory",
        description=(
            f"> 📦 **Database Version:** `items.dat v{ITEMS_VERSION}` • **Total Items:** `{len(ITEMS_CACHE):,}`\n"
            f"> 📅 **Last Synced:** `{mtime_str}`\n"
            f"> 🔍 **Latest Datamined Range:** IDs `#{start_id}` through `#{end_id}`\n\n"
            "```yaml\n"
            "📊 Latest In-Game Additions (Categorized by Gameplay Slot)\n"
            "```"
        ),
        color=0x5865F2
    )

    cats = categorize_items(newest_items)
    for cat_name, cat_items in cats.items():
        if cat_name != "🌱 Paired Seeds":
            lines = [format_item_line(it) for it in cat_items]
            add_chunked_field(embed, f"{cat_name} ({len(cat_items)})", lines)

    embed.set_footer(text=f"Total: {len(ITEMS_CACHE):,} items | items.dat v{ITEMS_VERSION} | Type !item <name or ID>")

    cosmetics_png = os.path.join(SCRIPT_DIR, "player_cosmetics4.png")
    if os.path.exists(cosmetics_png):
        file = discord.File(cosmetics_png, filename="player_cosmetics4.png")
        embed.set_thumbnail(url="attachment://player_cosmetics4.png")
        await ctx.send(embed=embed, file=file)
    else:
        await ctx.send(embed=embed)

@bot.command(name="wonderweek", aliases=["ww"])
async def cmd_wonderweek(ctx):
    """Filter helper for Wonder Week items."""
    if not ITEMS_CACHE:
        refresh_items()
    ww_items = [it for it in ITEMS_CACHE if 16396 <= it['id'] <= 16425 and not it['name'].endswith('Seed')]
    embed = discord.Embed(
        title="🌟 Wonder Week Event Items Directory",
        description=f"Showing all **{len(ww_items)} event items** from IDs `#16396` – `#16425`:\n",
        color=0xF1C40F
    )
    cats = categorize_items(ww_items)
    for cat_name, cat_items in cats.items():
        lines = [format_item_line(it) for it in cat_items]
        add_chunked_field(embed, f"{cat_name} ({len(cat_items)})", lines)
    embed.set_footer(text=f"Type !item <name or ID> for 128x128 sprite preview • Total Database: {len(ITEMS_CACHE):,}")
    await ctx.send(embed=embed)

@bot.command(name="item", aliases=["search", "find"])
async def cmd_item(ctx, *, query: str = None):
    if not query:
        await ctx.send(f"❌ Please provide an item name or ID. Example: `{PREFIX}item Pickaxe`")
        return

    if not ITEMS_CACHE:
        refresh_items()

    query_clean = query.strip().lower()
    matches = []

    # Check if query is item ID
    if query_clean.isdigit():
        target_id = int(query_clean)
        for it in ITEMS_CACHE:
            if it["id"] == target_id:
                matches.append(it)
                break
    else:
        # Search by name
        for it in ITEMS_CACHE:
            if query_clean in it["name"].lower():
                matches.append(it)
                if len(matches) >= 5:
                    break

    if not matches:
        await ctx.send(f"❌ No items found matching `{query}`.")
        return

    item = matches[0]
    embed = discord.Embed(
        title=f"📦 #{item['id']} — {item['name']}",
        color=0x2ecc71
    )
    embed.add_field(name="Rarity", value=f"`{item['rarity']}`", inline=True)

    # Wearable slot / Body part
    slot = BODY_PART_MAP.get(item.get("body_part", 0), "None / Block")
    if slot != "None / Block":
        embed.add_field(name="Wearable Slot", value=f"`{slot}`", inline=True)
    elif item.get("break_hits", 0) > 0:
        embed.add_field(name="Hardness", value=f"`{item['break_hits']} hits`", inline=True)

    # Release date / era estimation
    if item['id'] >= len(ITEMS_CACHE) - 50:
        embed.add_field(name="Release Era", value="`Latest Patch / New Leaks`", inline=True)
    elif item['id'] >= 16314:
        embed.add_field(name="Release Era", value="`Recent Patch (v5.59+)`", inline=True)
    elif item['id'] >= 16200:
        embed.add_field(name="Release Era", value="`Patch v5.58`", inline=True)
    else:
        embed.add_field(name="Release Era", value="`Legacy Release`", inline=True)

    if item.get("grow_time"):
        embed.add_field(name="Grow Time", value=f"{item['grow_time']}s", inline=True)
    embed.add_field(name="Texture Sheet", value=f"`{item['texture']}`", inline=True)

    if item.get("info"):
        embed.add_field(name="Description", value=item["info"], inline=False)

    if len(matches) > 1:
        other_names = ", ".join([f"`{m['name']}`" for m in matches[1:]])
        embed.add_field(name="Other Matches", value=other_names, inline=False)

    # Generate crystal-clear 128x128 single item icon thumbnail
    icon_path = get_item_icon(
        item.get("texture"),
        item.get("tex_x", 0),
        item.get("tex_y", 0),
        item["id"]
    )

    attached_file = None
    if icon_path and os.path.exists(icon_path):
        attached_file = discord.File(icon_path, filename=os.path.basename(icon_path))
        embed.set_thumbnail(url=f"attachment://{os.path.basename(icon_path)}")

    embed.set_footer(text=f"Grid: X={item.get('tex_x', 0)}, Y={item.get('tex_y', 0)} • Type !texture {item['texture']} for full sprite sheet")

    if attached_file:
        await ctx.send(embed=embed, file=attached_file)
    else:
        await ctx.send(embed=embed)

@bot.command(name="diff", aliases=["changelog", "changes"])
async def cmd_diff(ctx, *, patch_name: str = "latest"):
    """
    Shows patch diffs and changelogs.
    Options:
    - !diff (or !diff latest) -> Compares live database against snapshot baseline
    - !diff <number> (e.g. !diff 25) -> Shows changelog for the newest N items
    """
    if not ITEMS_CACHE:
        refresh_items()

    import datetime
    mtime_str = "Recently"
    if os.path.exists(ITEMS_DAT_PATH):
        mtime = os.path.getmtime(ITEMS_DAT_PATH)
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y at %I:%M %p")

    q = patch_name.strip().lower()

    # If query is a number, e.g. !diff 25
    if q.isdigit():
        count = max(1, min(int(q), 100))
        non_seeds = [it for it in ITEMS_CACHE if not it['name'].endswith('Seed') and 'null_item' not in it['name']]
        slice_items = non_seeds[-count:] if len(non_seeds) >= count else non_seeds
        fake_diff = {"added": slice_items, "modified": [], "removed": []}
        embed = build_leak_embed(
            fake_diff, len(ITEMS_CACHE), ITEMS_VERSION, mtime_str,
            title=f"📊 Growtopia Changelog (Last {len(slice_items)} Items)"
        )
        embed.description = (
            f"> 📦 **Database Version:** `items.dat v{ITEMS_VERSION}` • **Total:** `{len(ITEMS_CACHE):,}` items\n"
            f"> 📅 **Synced At:** `{mtime_str}`\n"
            f"> 🔍 **Inspecting:** Last `{len(slice_items)}` non-seed item additions\n\n"
            "```yaml\n"
            f"📊 Displaying the newest {len(slice_items)} items added to Growtopia:\n"
            "```"
        )
        await ctx.send(embed=embed)
        return

    # Check live database against baseline snapshot
    snapshot = load_snapshot()
    if not snapshot:
        save_snapshot(ITEMS_CACHE)
        snapshot = ITEMS_CACHE

    diff = generate_items_diff(snapshot, ITEMS_CACHE)
    added = diff.get("added", [])
    modified = diff.get("modified", [])

    if added or modified:
        embed = build_leak_embed(
            diff, len(ITEMS_CACHE), ITEMS_VERSION, mtime_str,
            title=f"📊 Growtopia Patch Diff & Changelog (v{ITEMS_VERSION})"
        )
        await ctx.send(embed=embed)
    else:
        # Zero unannounced changes: show confirmation and guide user
        embed = discord.Embed(
            title=f"📊 Growtopia Patch Diff (v{ITEMS_VERSION})",
            description=(
                f"> 📦 **Database Version:** `items.dat v{ITEMS_VERSION}` • **Total Items:** `{len(ITEMS_CACHE):,}`\n"
                f"> 📅 **Last Synced:** `{mtime_str}`\n\n"
                f"✅ **Database is 100% current with the latest snapshot.** Zero unannounced changes detected.\n\n"
                f"💡 *Tip: Type `{PREFIX}latest` to view the newest in-game items, or `{PREFIX}diff <number>` (e.g. `{PREFIX}diff 25`) to inspect the newest additions.*"
            ),
            color=0x3498db
        )
        embed.set_footer(text=f"Total Database: {len(ITEMS_CACHE):,} items • Real-Time Watcher Active")
        await ctx.send(embed=embed)

@bot.command(name="check")
async def cmd_check(ctx):
    """
    Manually checks local items.dat and tests against baseline snapshot.
    If an update is found, broadcasts the full details page!
    """
    if not os.path.exists(ITEMS_DAT_PATH):
        await ctx.send("❌ `items.dat` not found on local machine.")
        return

    diff = await check_and_broadcast_updates(ctx_to_reply=ctx)
    if not diff:
        import datetime
        mtime = os.path.getmtime(ITEMS_DAT_PATH)
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y at %I:%M %p")
        embed = discord.Embed(
            title="✅ Growtopia Database Is Up To Date",
            description=(
                f"• **Database Version:** `items.dat v{ITEMS_VERSION}`\n"
                f"• **Total Items Tracked:** `{len(ITEMS_CACHE):,}` items\n"
                f"• **Last File Modified:** `{mtime_str}`\n"
                f"• **Status:** No new patches or leaks detected. The 24/7 watcher is actively listening every 5 seconds."
            ),
            color=0x2ecc71
        )
        embed.set_footer(text=f"Type {PREFIX}latest to view newest items • Type {PREFIX}sync to check Ubisoft servers")
        await ctx.send(embed=embed)

@bot.command(name="sync", aliases=["fetch", "hotfix"])
async def cmd_sync(ctx):
    """
    Fast-syncs with Ubisoft servers by silently booting Growtopia in the background for 4-5s,
    checking if an update downloads, and broadcasting if changes are found.
    """
    status_msg = await ctx.send("⚡ **Fast-syncing with Ubisoft servers...** Checking in the background (4-5s)...")
    old_mtime = os.path.getmtime(ITEMS_DAT_PATH) if os.path.exists(ITEMS_DAT_PATH) else 0

    success, msg = await perform_silent_sync(max_seconds=5)
    if not success:
        await status_msg.edit(content=f"⚠️ {msg}")
        return

    diff = await check_and_broadcast_updates(ctx_to_reply=ctx)
    if diff:
        await status_msg.edit(content="🚨 **NEW UPDATE / HOTFIX DETECTED!** Broadcast sent below!")
    else:
        await status_msg.edit(content=f"✅ **Sync complete!** Your game database is 100% current with Ubisoft servers (`{len(ITEMS_CACHE):,}` items, v{ITEMS_VERSION}). Zero unannounced updates detected.")

@bot.command(name="texture")
async def cmd_texture(ctx, *, tex_name: str = None):
    if not tex_name:
        await ctx.send(f"❌ Please provide a texture filename. Example: `{PREFIX}texture tiles_page1`")
        return

    if not tex_name.endswith(".rttex"):
        tex_name += ".rttex"

    rttex_path = os.path.join(GAME_DIR, tex_name)
    if not os.path.exists(rttex_path):
        await ctx.send(f"❌ Texture `{tex_name}` not found in game directory.")
        return

    out_png = os.path.join(SCRIPT_DIR, tex_name.replace(".rttex", ".png"))
    try:
        w, h = convert_rttex(rttex_path, out_png)
        file = discord.File(out_png, filename=os.path.basename(out_png))
        embed = discord.Embed(
            title=f"🖼️ Texture: `{tex_name}`",
            description=f"Dimensions: **{w}x{h}** pixels",
            color=0x9b59b6
        )
        embed.set_image(url=f"attachment://{os.path.basename(out_png)}")
        await ctx.send(embed=embed, file=file)
    except Exception as e:
        await ctx.send(f"❌ Error converting texture: {e}")

# 24/7 background watcher loop
@tasks.loop(seconds=5)
async def auto_monitor():
    global LAST_MTIME
    if not WATCHER_ENABLED or not os.path.exists(ITEMS_DAT_PATH):
        return

    try:
        mtime = os.path.getmtime(ITEMS_DAT_PATH)
        if mtime != LAST_MTIME:
            LAST_MTIME = mtime
            print(f"[Auto-Monitor] items.dat modification detected at {mtime}!")
            await check_and_broadcast_updates()
    except Exception as e:
        print(f"[Auto-Monitor Exception]: {e}")

if __name__ == "__main__":
    print("Starting Growtopia Discord Bot...")
    bot.run(BOT_TOKEN)
