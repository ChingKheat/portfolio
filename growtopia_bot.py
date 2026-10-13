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
try:
    if sys.stdout is None or not hasattr(sys.stdout, 'write'):
        sys.stdout = open(os.path.join(SCRIPT_DIR, "bot.log"), "a", encoding="utf-8", buffering=1)
    if sys.stderr is None or not hasattr(sys.stderr, 'write'):
        sys.stderr = open(os.path.join(SCRIPT_DIR, "bot.log"), "a", encoding="utf-8", buffering=1)
except Exception:
    pass

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
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
    generate_showcase_grid,
    generate_item_card,
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
ALERT_ROLE_ID = config.get("alert_role_id")

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
    return f"• `#{it['id']}` **{it['name']}**{slot_str} — {rarity}"

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

class LeakCategorySelect(discord.ui.Select):
    def __init__(self, items, original_embed, categories):
        self.items = items
        self.original_embed = original_embed
        self.categories = categories

        options = [
            discord.SelectOption(
                label="📊 All Slots Overview",
                value="overview",
                description="View complete categorized summary of items",
                emoji="📊",
                default=True
            )
        ]

        emoji_map = {
            "⚔️ Weapons & Hand Items": "⚔️",
            "🪽 Wings, Capes & Back": "🪽",
            "🐎 Mounts & Shoes": "🐎",
            "👑 Hats, Hair & Faces": "👑",
            "👕 Shirts, Pants & Suits": "👕",
            "🔮 Auras, Pets & Artifacts": "🔮",
            "🧱 Placeables & Weather": "🧱",
            "🌱 Paired Seeds": "🌱",
            "📦 Other Items": "📦"
        }

        for cat_name, cat_items in self.categories.items():
            if not cat_items or cat_name == "🌱 Paired Seeds":
                continue
            emoji = emoji_map.get(cat_name, "📦")
            clean_label = cat_name
            for em in emoji_map.values():
                clean_label = clean_label.replace(em, "").strip()
            options.append(
                discord.SelectOption(
                    label=f"{clean_label[:20]} ({len(cat_items)})",
                    value=cat_name,
                    description=f"Inspect all {len(cat_items)} {clean_label.lower()} in detail",
                    emoji=emoji
                )
            )

        super().__init__(
            placeholder="🔍 Select an equipment slot to inspect in detail...",
            min_values=1,
            max_values=1,
            options=options[:25]
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]

        for opt in self.options:
            opt.default = (opt.value == selected)

        if selected == "overview":
            await interaction.response.edit_message(embed=self.original_embed, view=self.view)
            return

        cat_items = self.categories.get(selected, [])
        cat_embed = discord.Embed(
            title=f"📦 {selected} Directory",
            description=f"Showing all **{len(cat_items)} items** in this category:\n",
            color=0x5865F2
        )

        for it in cat_items:
            rarity = f"Rarity `{it.get('rarity', 0)}`" if it.get("rarity") else "Untradeable"
            slot = BODY_PART_MAP.get(it.get("body_part", 0), "None / Block")
            desc = f"• **Slot:** `{slot}` | **{rarity}**\n• **Texture:** `{it.get('texture')}` (Grid: X={it.get('tex_x', 0)}, Y={it.get('tex_y', 0)})\n"
            if it.get("info"):
                desc += f"• *\"{it['info'].strip()}\"*\n"
            cat_embed.add_field(
                name=f"#{it['id']} — {it['name']}",
                value=desc,
                inline=False
            )

        cat_embed.set_footer(text=f"Total: {len(cat_items)} items • Select above to switch categories")
        await interaction.response.edit_message(embed=cat_embed, view=self.view)

class LeakDetailsView(discord.ui.View):
    def __init__(self, items, original_embed, timeout=600):
        super().__init__(timeout=timeout)
        self.items = items
        self.original_embed = original_embed
        cats = categorize_items(items)
        self.add_item(LeakCategorySelect(items, original_embed, cats))

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

        # Generate sleek showcase grid graphic
        items_for_showcase = added if added else [it for it in ITEMS_CACHE if any(m['id'] == it['id'] for m in modified)]
        showcase_path = generate_showcase_grid(items_for_showcase)
        file_to_send = None
        if showcase_path and os.path.exists(showcase_path):
            embed.set_image(url="attachment://leak_showcase.png")
            file_to_send = discord.File(showcase_path, filename="leak_showcase.png")

        view = LatestView(items_for_showcase, mtime_str, initial_mode="event") if items_for_showcase else None
        ping_content = f"<@&{ALERT_ROLE_ID}> 🚨 **NEW GROWTOPIA LEAKS / UPDATE DETECTED!**" if ALERT_ROLE_ID else None

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
                    await ch.send(content=ping_content, embed=embed, file=file_to_send, view=view)
                except Exception as e:
                    print(f"Error sending update embed: {e}")

        # Also reply to command sender if called via !sync or !check
        if ctx_to_reply and ctx_to_reply.channel.id != ALERT_CHANNEL_ID:
            try:
                file_reply = discord.File(showcase_path, filename="leak_showcase.png") if showcase_path and os.path.exists(showcase_path) else None
                await ctx_to_reply.send(embed=embed, file=file_reply, view=view)
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
    embed.add_field(
        name=f"`{PREFIX}latest` *(Interactive Hub)*",
        value=(
            "Show the newest in-game additions with **interactive buttons**:\n"
            f"• `{PREFIX}latest` (or `{PREFIX}latest event`) ➔ Grouped by **Event & Theme**\n"
            f"• `{PREFIX}latest id` ➔ Strict numerical **Item ID order** (#16364 ➔ #16432)\n"
            f"• `{PREFIX}latest date` ➔ Grouped by **Release Date & Patch Waves**\n"
            f"• `{PREFIX}latest slot` ➔ Grouped by **Equipment Slot** (Weapons, Wings, etc.)\n"
            f"• `{PREFIX}latest 50` ➔ Customize how many items to inspect"
        ),
        inline=False
    )
    embed.add_field(
        name=f"`{PREFIX}wonderweek` / `{PREFIX}fall` / `{PREFIX}immortal`",
        value="Quick shortcuts to display only items from that specific event set.",
        inline=False
    )
    embed.add_field(name=f"`{PREFIX}card <name or ID>`", value="Generate a sleek dark-themed infographic card image for any item.", inline=False)
    embed.add_field(name=f"`{PREFIX}diff`", value="Show the patch changelog & diff against baseline snapshot (or `!diff 25`).", inline=False)
    embed.add_field(name=f"`{PREFIX}item <name or ID>`", value="Search any item (e.g. `!item Pickaxe` or `!item 16400`) for stats & 128x128 sprite.", inline=False)
    embed.add_field(name=f"`{PREFIX}textures`", value="List recent sprite sheets (type `!texture <name>` to view full sheet).", inline=False)
    embed.add_field(name=f"`{PREFIX}role <@role>`", value="Set a role to ping on new leak alerts (or `!role none` to disable).", inline=False)
    embed.add_field(name=f"`{PREFIX}check`", value="Scan local and Ubisoft game files for new updates right now.", inline=False)
    embed.add_field(name=f"`{PREFIX}sync`", value="Silently check Ubisoft servers for new patches & hotfixes.", inline=False)
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

EVENT_DEFINITIONS = [
    ("🌟 Wonder Week 2026", ["atom", "lightning nunchuck", "mecha tank", "pariah", "super stinger", "paradise", "winged hair", "drape coat", "wonder week", "wonderweek", "ww"]),
    ("👑 Immortal Club & VIP", ["immortal", "vip club", "royal pass", "subscriber"]),
    ("⚔️ Guild Clash & Domination", ["shadow-you", "domination", "sharp wrench", "guild clash", "clash"]),
    ("🍂 Fall Festival / Harvest", ["fall", "autumn", "harvest", "corn", "gazebo", "lake lantern", "sheep chariot", "arched bridge", "witch"]),
    ("🎟️ Voucher Dayz & Store", ["growmoji", "voucher", "wardrobe preset", "tanuki", "orca hood", "anime bun", "wolf cut"]),
    ("🎃 Halloween / Night of the Comet", ["halloween", "ghoul", "ghost", "franken", "spooky", "dracula", "vampire", "pumpkin"]),
    ("❄️ Winterfest", ["winter", "fest", "snow", "ice", "santa", "reindeer", "frost"]),
    ("💘 Valentine's Day", ["valentine", "heart", "cupid", "golden heart"]),
    ("🍀 St. Patrick's Week", ["clover", "leprechaun", "pot o' gold", "celtic"]),
    ("🐰 Easter Week", ["easter", "bunny", "egg", "chick"]),
    ("☀️ SummerFest", ["summer", "phoenix", "firework", "beach"]),
    ("🎪 Carnival", ["carnival", "ringmaster", "circus"]),
    ("🌮 Cinco de Mayo", ["cinco", "pinata", "sombrero", "mariachi", "fiesta"]),
    ("🌋 Apocalypse Event", ["apocalypse", "anarchy", "radioactive"]),
]

def classify_event(it):
    name = it.get('name', '').lower()
    desc = it.get('info', '').lower()
    text = f"{name} {desc}"
    for ev_name, kws in EVENT_DEFINITIONS:
        if any(kw in text for kw in kws):
            return ev_name
    return "📦 Other Additions"

def build_latest_event_embed(items, mtime_str):
    start_id = items[0]['id'] if items else 0
    end_id = items[-1]['id'] if items else 0

    events = {}
    for it in items:
        ev = classify_event(it)
        events.setdefault(ev, []).append(it)

    summary_lines = [f"• {ev}: {len(ev_items)} items" for ev, ev_items in events.items()]
    summary_str = "\n".join(summary_lines)

    embed = discord.Embed(
        title="✨ Growtopia Latest In-Game Items Directory",
        description=(
            f"> 📦 **Database Version:** `items.dat v{ITEMS_VERSION}` • **Total Items:** `{len(ITEMS_CACHE):,}`\n"
            f"> 📅 **Last Synced:** `{mtime_str}`\n"
            f"> 🔍 **Datamined Range:** IDs `#{start_id}` through `#{end_id}` ({len(items)} items)\n\n"
            "```yaml\n"
            f"🎪 Filter Mode: Grouped by Event & Theme ({len(events)} Events Detected)\n"
            f"{summary_str}\n"
            "```\n"
            "💡 *Click buttons below to switch view by **Item ID**, **Date / Patch**, or **Slot**!*"
        ),
        color=0xF1C40F
    )

    for ev_name, ev_items in events.items():
        range_str = f"IDs `#{ev_items[0]['id']} – #{ev_items[-1]['id']}`"
        lines = [format_item_line(it) for it in ev_items]
        add_chunked_field(embed, f"{ev_name} ({len(ev_items)} items • {range_str})", lines)

    embed.set_footer(text=f"Total: {len(ITEMS_CACHE):,} items | items.dat v{ITEMS_VERSION} | Type !item <name or ID>")

    cosmetics_png = os.path.join(SCRIPT_DIR, "player_cosmetics4.png")
    if os.path.exists(cosmetics_png):
        embed.set_thumbnail(url="attachment://player_cosmetics4.png")

    return embed

def build_latest_id_embed(items, mtime_str):
    start_id = items[0]['id'] if items else 0
    end_id = items[-1]['id'] if items else 0

    embed = discord.Embed(
        title="✨ Growtopia Latest In-Game Items Directory",
        description=(
            f"> 📦 **Database Version:** `items.dat v{ITEMS_VERSION}` • **Total Items:** `{len(ITEMS_CACHE):,}`\n"
            f"> 📅 **Last Synced:** `{mtime_str}`\n"
            f"> 🔍 **Strict ID Range:** IDs `#{start_id}` through `#{end_id}` ({len(items)} items)\n\n"
            "```yaml\n"
            "🔢 Filter Mode: Sequential Numerical Item ID Order\n"
            "```\n"
            "💡 *Chronological in-game datamine registry ordered directly by internal Item ID:*"
        ),
        color=0x3498DB
    )

    # Chunk into clean, readable batches of 10 items
    chunk_size = 10
    id_chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    for chunk in id_chunks:
        header = f"📋 IDs `#{chunk[0]['id']}` through `#{chunk[-1]['id']}` ({len(chunk)} items)"
        lines = [format_item_line(it) for it in chunk]
        add_chunked_field(embed, header, lines)

    embed.set_footer(text=f"Total: {len(ITEMS_CACHE):,} items | items.dat v{ITEMS_VERSION} | Type !item <name or ID>")

    cosmetics_png = os.path.join(SCRIPT_DIR, "player_cosmetics4.png")
    if os.path.exists(cosmetics_png):
        embed.set_thumbnail(url="attachment://player_cosmetics4.png")

    return embed

def build_latest_date_embed(items, mtime_str):
    start_id = items[0]['id'] if items else 0
    end_id = items[-1]['id'] if items else 0
    max_id = items[-1]['id'] if items else 0

    embed = discord.Embed(
        title="✨ Growtopia Latest In-Game Items Directory",
        description=(
            f"> 📦 **Database Version:** `items.dat v{ITEMS_VERSION}` • **Total Items:** `{len(ITEMS_CACHE):,}`\n"
            f"> 📅 **Last Game File Sync:** `{mtime_str}`\n"
            f"> 🔍 **Datamined Range:** IDs `#{start_id}` through `#{end_id}` ({len(items)} items)\n\n"
            "```yaml\n"
            "📅 Filter Mode: Grouped by Release Date & Patch Waves\n"
            "```\n"
            "💡 *Timeline breakdown of when items arrived in the game database:*"
        ),
        color=0x9B59B6
    )

    wave_defs = [
        {
            "title": "🚀 Wave 1: Latest Hotfix & Live Leaks (v5.59 Patch)",
            "date_info": f"Live File Synced: {mtime_str}",
            "note": "Wonder Week & Immortal Club sets",
            "items": [it for it in items if it['id'] >= max_id - 38],
        },
        {
            "title": "📦 Wave 2: October Update Wave (v5.59 Base)",
            "date_info": "Early October 2026 • Main Patch",
            "note": "Fall Festival & Guild Clash sets",
            "items": [it for it in items if max_id - 75 <= it['id'] < max_id - 38],
        },
        {
            "title": "⏳ Wave 3: Earlier Patch Additions (v5.58)",
            "date_info": "September 2026 • Prior Expansion",
            "note": "Growmojis & Voucher Dayz",
            "items": [it for it in items if it['id'] < max_id - 75],
        }
    ]

    for w in wave_defs:
        if w["items"]:
            w_range = f"IDs `#{w['items'][0]['id']} – #{w['items'][-1]['id']}`"
            header = f"{w['title']}\n📅 `{w['date_info']}` • {w_range} ({len(w['items'])} items)"
            lines = [format_item_line(it) for it in w["items"]]
            add_chunked_field(embed, header, lines)

    embed.set_footer(text=f"Total: {len(ITEMS_CACHE):,} items | items.dat v{ITEMS_VERSION} | Type !item <name or ID>")

    cosmetics_png = os.path.join(SCRIPT_DIR, "player_cosmetics4.png")
    if os.path.exists(cosmetics_png):
        embed.set_thumbnail(url="attachment://player_cosmetics4.png")

    return embed

def build_latest_slot_embed(items, mtime_str):
    start_id = items[0]['id'] if items else 0
    end_id = items[-1]['id'] if items else 0

    embed = discord.Embed(
        title="✨ Growtopia Latest In-Game Items Directory",
        description=(
            f"> 📦 **Database Version:** `items.dat v{ITEMS_VERSION}` • **Total Items:** `{len(ITEMS_CACHE):,}`\n"
            f"> 📅 **Last Synced:** `{mtime_str}`\n"
            f"> 🔍 **Latest Datamined Range:** IDs `#{start_id}` through `#{end_id}`\n\n"
            "```yaml\n"
            "👔 Filter Mode: Categorized by Gameplay Equipment Slot\n"
            "```\n"
            "💡 *Weapons, wings, mounts, hats, costumes, and placeables:*"
        ),
        color=0x5865F2
    )

    cats = categorize_items(items)
    for cat_name, cat_items in cats.items():
        if cat_name != "🌱 Paired Seeds":
            lines = [format_item_line(it) for it in cat_items]
            add_chunked_field(embed, f"{cat_name} ({len(cat_items)})", lines)

    embed.set_footer(text=f"Total: {len(ITEMS_CACHE):,} items | items.dat v{ITEMS_VERSION} | Type !item <name or ID>")

    cosmetics_png = os.path.join(SCRIPT_DIR, "player_cosmetics4.png")
    if os.path.exists(cosmetics_png):
        embed.set_thumbnail(url="attachment://player_cosmetics4.png")

    return embed

class LatestView(discord.ui.View):
    def __init__(self, items, mtime_str, initial_mode="event", timeout=300):
        super().__init__(timeout=timeout)
        self.items = items
        self.mtime_str = mtime_str
        self.mode = initial_mode
        self._sync_buttons()

    def _sync_buttons(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == f"btn_{self.mode}":
                    child.style = discord.ButtonStyle.primary
                else:
                    child.style = discord.ButtonStyle.secondary

    @discord.ui.button(label="By Event", emoji="🎪", style=discord.ButtonStyle.primary, custom_id="btn_event")
    async def on_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "event"
        self._sync_buttons()
        embed = build_latest_event_embed(self.items, self.mtime_str)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="By Item ID", emoji="🔢", style=discord.ButtonStyle.secondary, custom_id="btn_id")
    async def on_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "id"
        self._sync_buttons()
        embed = build_latest_id_embed(self.items, self.mtime_str)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="By Date / Patch", emoji="📅", style=discord.ButtonStyle.secondary, custom_id="btn_date")
    async def on_date(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "date"
        self._sync_buttons()
        embed = build_latest_date_embed(self.items, self.mtime_str)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="By Slot", emoji="👔", style=discord.ButtonStyle.secondary, custom_id="btn_slot")
    async def on_slot(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.mode = "slot"
        self._sync_buttons()
        embed = build_latest_slot_embed(self.items, self.mtime_str)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

@bot.command(name="latest", aliases=["recent", "newest", "leaks"])
async def cmd_latest(ctx, *, filter_mode: str = None):
    """
    Dynamically displays the latest in-game additions from items.dat.
    Can be viewed by Event, Item ID, Date / Patch, or Equipment Slot.
    Interactive buttons allow instant switching in Discord.
    """
    if not ITEMS_CACHE:
        refresh_items()

    import datetime
    mtime_str = "Recently"
    if os.path.exists(ITEMS_DAT_PATH):
        mtime = os.path.getmtime(ITEMS_DAT_PATH)
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y at %I:%M %p")

    # Select the newest non-seed items
    non_seeds = [it for it in ITEMS_CACHE if not it['name'].endswith('Seed') and 'null_item' not in it['name']]

    count = 35
    target_mode = "event"
    specific_event_filter = None

    if filter_mode:
        q = filter_mode.strip().lower()
        if q.isdigit():
            count = max(5, min(100, int(q)))
        elif q in ("id", "ids", "num", "number", "numerical"):
            target_mode = "id"
        elif q in ("date", "dates", "patch", "time", "wave", "era"):
            target_mode = "date"
        elif q in ("slot", "slots", "wearable", "body", "part"):
            target_mode = "slot"
        elif q in ("event", "events", "theme"):
            target_mode = "event"
        else:
            # User passed an event keyword like "ww", "fall", "immortal"
            target_mode = "event"
            specific_event_filter = q

    newest_items = non_seeds[-count:] if len(non_seeds) >= count else non_seeds

    if specific_event_filter:
        filtered = [it for it in newest_items if specific_event_filter in it['name'].lower() or specific_event_filter in it.get('info', '').lower()]
        if not filtered:
            # Search last 100 items if not found in top 35
            filtered = [it for it in non_seeds[-100:] if specific_event_filter in it['name'].lower() or specific_event_filter in it.get('info', '').lower()]
        if filtered:
            newest_items = filtered

    if target_mode == "id":
        embed = build_latest_id_embed(newest_items, mtime_str)
    elif target_mode == "date":
        embed = build_latest_date_embed(newest_items, mtime_str)
    elif target_mode == "slot":
        embed = build_latest_slot_embed(newest_items, mtime_str)
    else:
        embed = build_latest_event_embed(newest_items, mtime_str)

    view = LatestView(newest_items, mtime_str, initial_mode=target_mode)

    showcase_path = generate_showcase_grid(newest_items)
    if showcase_path and os.path.exists(showcase_path):
        embed.set_image(url="attachment://leak_showcase.png")
        file = discord.File(showcase_path, filename="leak_showcase.png")
        await ctx.send(embed=embed, view=view, file=file)
    else:
        await ctx.send(embed=embed, view=view)

@bot.command(name="wonderweek", aliases=["ww"])
async def cmd_wonderweek(ctx):
    """Filter helper for Wonder Week items."""
    await cmd_latest(ctx, filter_mode="wonder week")

@bot.command(name="fall", aliases=["harvest", "autumn"])
async def cmd_fall(ctx):
    """Filter helper for Fall Festival / Harvest items."""
    await cmd_latest(ctx, filter_mode="fall")

@bot.command(name="immortal", aliases=["vip"])
async def cmd_immortal(ctx):
    """Filter helper for Immortal Club & VIP items."""
    await cmd_latest(ctx, filter_mode="immortal")

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

@bot.command(name="card", aliases=["showcase", "preview"])
async def cmd_card(ctx, *, query: str = None):
    """
    Generates a sleek dark-themed infographic card image for any item.
    Usage: !card Pickaxe or !card 16396
    """
    if not query:
        await ctx.send(f"❌ Please provide an item name or ID. Example: `{PREFIX}card Pickaxe`")
        return

    if not ITEMS_CACHE:
        refresh_items()

    q = query.strip().lower()
    target = None
    if q.isdigit():
        tid = int(q)
        target = next((it for it in ITEMS_CACHE if it["id"] == tid), None)
    else:
        target = next((it for it in ITEMS_CACHE if q in it["name"].lower()), None)

    if not target:
        await ctx.send(f"❌ Item `{query}` not found in database.")
        return

    card_path = generate_item_card(target)
    if card_path and os.path.exists(card_path):
        file = discord.File(card_path, filename=f"card_{target['id']}.png")
        embed = discord.Embed(
            title=f"✨ Item Showcase: #{target['id']} {target['name']}",
            color=0x5865F2
        )
        embed.set_image(url=f"attachment://card_{target['id']}.png")
        embed.set_footer(text=f"items.dat v{ITEMS_VERSION} • Type {PREFIX}item {target['id']} for text details")
        await ctx.send(embed=embed, file=file)
    else:
        await ctx.send(f"❌ Failed to render card for #{target['id']}.")

@bot.command(name="role", aliases=["setrole", "leakrole"])
async def cmd_role(ctx, *, role_input: str = None):
    """
    Configures the role to ping when new leaks or updates drop.
    Usage:
    !role @Leaks (or !role 123456789)
    !role none (to disable role pings)
    !role (to check current setting)
    """
    global ALERT_ROLE_ID
    if not role_input:
        if ALERT_ROLE_ID:
            await ctx.send(f"🔔 **Current Leak Alert Role:** <@&{ALERT_ROLE_ID}> (`{ALERT_ROLE_ID}`)\nType `{PREFIX}role none` to disable.")
        else:
            await ctx.send(f"ℹ️ **No leak alert role is currently set.** Type `{PREFIX}role @RoleName` to set one!")
        return

    inp = role_input.strip().lower()
    if inp in ["none", "off", "disable", "clear", "remove"]:
        ALERT_ROLE_ID = None
        config["alert_role_id"] = None
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass
        await ctx.send("✅ **Role alerts disabled.** The bot will not ping any role on new updates.")
        return

    target_id = None
    if ctx.message.role_mentions:
        target_id = ctx.message.role_mentions[0].id
    elif inp.isdigit():
        target_id = int(inp)
    else:
        if ctx.guild:
            for r in ctx.guild.roles:
                if inp in r.name.lower():
                    target_id = r.id
                    break

    if not target_id:
        await ctx.send(f"❌ Could not find role `{role_input}`. Please mention the role (e.g. `{PREFIX}role @Leaks`) or provide its ID.")
        return

    ALERT_ROLE_ID = target_id
    config["alert_role_id"] = ALERT_ROLE_ID
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass
    await ctx.send(f"✅ **Leak Alert Role Set!** <@&{ALERT_ROLE_ID}> will now be pinged whenever new items or updates are datamined!")

@bot.command(name="textures", aliases=["sprites"])
async def cmd_textures(ctx):
    """
    Lists the texture sheets used by the latest items and explains how to inspect them.
    """
    if not ITEMS_CACHE:
        refresh_items()

    non_seeds = [it for it in ITEMS_CACHE if not it['name'].endswith('Seed') and 'null_item' not in it['name']]
    newest = non_seeds[-35:] if len(non_seeds) >= 35 else non_seeds
    tex_set = {}
    for it in newest:
        tex = it.get("texture", "")
        if tex:
            tex_set[tex] = tex_set.get(tex, 0) + 1

    lines = [f"• `{tex}` — used by `{count}` recent items" for tex, count in sorted(tex_set.items(), key=lambda x: x[1], reverse=True)[:10]]
    embed = discord.Embed(
        title="🖼️ Recent Item Sprite Sheets",
        description=(
            "The newest datamined items use the following texture sheets in the game directory:\n\n" +
            "\n".join(lines) +
            f"\n\n💡 *Tip: Type `{PREFIX}texture <sheet_name>` (e.g. `{PREFIX}texture player_cosmetics4`) to view the complete full-resolution sprite sheet!*"
        ),
        color=0x9b59b6
    )
    await ctx.send(embed=embed)

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
    print("Starting Growtopia Discord Bot...", flush=True)
    import time
    import traceback
    while True:
        try:
            bot.run(BOT_TOKEN)
        except KeyboardInterrupt:
            print("[INFO] Bot stopped by user.", flush=True)
            break
        except Exception as e:
            print(f"[FATAL EXCEPTION in bot.run]: {e}", flush=True)
            traceback.print_exc()
            time.sleep(5)
            print("[Auto-Restart] Attempting to reconnect bot...", flush=True)
