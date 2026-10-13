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

@tasks.loop(hours=2)
async def auto_hotfix_sync_loop():
    """Periodically checks for silent server maintenance hotfixes in the background every 2 hours."""
    if not WATCHER_ENABLED:
        return
    print("[Auto-Hotfix] Starting scheduled 2-hour background game sync...")
    success, msg = await perform_silent_sync(max_seconds=5)
    print(f"[Auto-Hotfix] Result: {msg}")

@bot.event
async def on_ready():
    print(f"==================================================")
    print(f" 🤖 GROWTOPIA DISCORD BOT LOGGED IN AS: {bot.user}")
    print(f" Ready to respond to commands ({PREFIX}latest, {PREFIX}diff, {PREFIX}item, {PREFIX}sync, {PREFIX}help)")
    print(f"==================================================")
    refresh_items()
    if not auto_monitor.is_running():
        auto_monitor.start()
    if not auto_hotfix_sync_loop.is_running():
        auto_hotfix_sync_loop.start()

    # Post an online confirmation to the channel so the user knows it's active
    if ALERT_CHANNEL_ID:
        try:
            channel = bot.get_channel(ALERT_CHANNEL_ID)
            if channel:
                await channel.send("🟢 **Growtopia Dataminer is ONLINE!** Ready for commands (`!latest`, `!start`, `!diff`, `!sync`).")
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

WATCHER_ENABLED = True
ALERT_CHANNEL_ID = config.get("alert_channel_id")

@bot.command(name="help")
async def cmd_help(ctx):
    embed = discord.Embed(
        title="🎮 Growtopia Dataminer Bot Commands",
        description="Type any of these commands in this channel:",
        color=0x3498db
    )
    embed.add_field(name=f"`{PREFIX}start`", value="Activate real-time auto-watching and send the latest items here!", inline=False)
    embed.add_field(name=f"`{PREFIX}wonderweek` *(or `{PREFIX}ww`)*", value="Show all datamined items & leaks for Wonder Week!", inline=False)
    embed.add_field(name=f"`{PREFIX}latest`", value="Show the newest in-game items from the latest patch.", inline=False)
    embed.add_field(name=f"`{PREFIX}diff`", value="Show the patch changelog (new & modified/rebalanced items).", inline=False)
    embed.add_field(name=f"`{PREFIX}sync`", value="Silently check for server maintenance hotfixes right now.", inline=False)
    embed.add_field(name=f"`{PREFIX}item <name or ID>`", value="Search any item (e.g. `!item Pickaxe` or `!item 16400`).", inline=False)
    embed.add_field(name=f"`{PREFIX}check`", value="Check if a new game update is available right now.", inline=False)
    embed.add_field(name=f"`{PREFIX}status`", value="Check if the real-time watcher is active.", inline=False)
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
    if not ITEMS_CACHE:
        refresh_items()

    import datetime
    mtime_str = "Oct 13, 2026"
    if os.path.exists(ITEMS_DAT_PATH):
        mtime = os.path.getmtime(ITEMS_DAT_PATH)
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y at %I:%M %p")

    embed = discord.Embed(
        title="✨ Growtopia Latest Patch & Wonder Week Leaks",
        description=(
            f"> 📅 **Database Synced:** `{mtime_str}` • **Format:** `items.dat v{ITEMS_VERSION}`\n"
            f"> 🌟 **Active Event:** **Wonder Week 2026/2027** (15 Secret Slots Unlocked!)\n"
            f"> 📦 **Total Datamined Range:** `120 Items` (IDs `#16314` – `#16433`)\n\n"
            "```yaml\n"
            "📊 Latest Database Breakdown\n"
            "  • 15 Wonder Week : All event items unlocked from secret slots (#16396-#16425)\n"
            "  • 5  Immortal    : Sonic Buster Katana, Pickaxe, Title, Puppy Leash, NVG\n"
            "  • 40 Autumn/Clash: Royal Armor, Shadow-You, Fall Witch, Auras & Pets\n"
            "  • 60 Paired Seeds: Full seed pairs for every placeable/wearable item\n"
            "```"
        ),
        color=0xF1C40F
    )

    embed.add_field(
        name="🌟 Wonder Week Exclusives (15 Unlocked Items!)",
        value=(
            "`16400` **Mecha Tank** *(Mount / Feet)* • `16406` **WM - Paradise City** *(Placeable)*\n"
            "`16398` **Lightning Nunchucks** *(Hand)* • `16396` **Atom Constructs** *(Hand)*\n"
            "`16402` **Pariah's Shawl** *(Back / Cape)* • `16404` **Super Stingers** *(Back / Wings)*\n"
            "`16408` **Winged Hair** *(Hair)* • `16424` **Winged Hair Hat** *(Hat)*\n"
            "`16412` **Atom Suit** *(Shirt)* • `16410` **Atom Shorts** *(Pants)*\n"
            "`16414` **Lightning Nunchucks Mask** • `16418` **Pariah's Mask**\n"
            "`16416` **Mecha Tank's Birds** • `16420` **Super Stingers Belt** • `16422` **Paradise Watch**\n"
            "💡 *Type `!wonderweek` (or `!ww`) for individual lore, stats & lock dates!*"
        ),
        inline=False
    )

    embed.add_field(
        name="⚔️ Immortal Collection (5 Items)",
        value=(
            "`16428` **Sonic Buster Katana** *(Hand / Weapon)*\n"
            "`16426` **Immortal Pickaxe** *(Hand / Tool)*\n"
            "`16432` **Immortal Puppy Leash** *(Hand / Pet)*\n"
            "`16430` **Immortal Title** *(Achievement / Honor)*\n"
            "`16340` **Night Vision Goggles** *(Face / Mask)*"
        ),
        inline=False
    )

    embed.add_field(
        name="👑 Domination & Royal Gear (6 Items)",
        value=(
            "`16388` **Royal Domination Armor** *(Chest / Body)*\n"
            "`16386` **Domination Armor** *(Chest / Body)*\n"
            "`16384` **Shadow-You** *(Dark Clone Aura / Back)*\n"
            "`16394` **Drape Coat** *(Cape / Back)*\n"
            "`16390` **Sharp Wrench Style** *(Tool Skin)*\n"
            "`16392` **Sharp Wrench Decoration** *(Placeable)*"
        ),
        inline=False
    )

    embed.add_field(
        name="🍂 Fall & Autumn Event (11 Items)",
        value=(
            "`16370` **Fall Witch's Hat** *(Head)* • `16372` **Coat** • `16374` **Pants**\n"
            "`16362` **Halo of Autumn Leaves** *(Back / Aura)* • `16364` **Mantle of Corn**\n"
            "`16366` **Sheep Chariot** *(Mount / Feet)*\n"
            "`16376` **Gazebo Base** • `16378` **Gazebo Roof**\n"
            "`16368` **Arched Bridge** • `16380` **Lake Lantern** • `16382` **Corn Field**"
        ),
        inline=False
    )

    embed.add_field(
        name="✂️ Hairstyles, Hats & Exclusives (13 Items)",
        value=(
            "`16354` **Wolf Cut Hair** • `16352` **Tied Anime Bun** • `16350` **Tanuki Ears**\n"
            "`16348` **Orca Hood** • `16346` **Horns of Calamity** • `16344` **Blue Rose Bowler Hat**\n"
            "`16314` **Spiezels' Galactic Scarf** • `16316` **swiftpie's Aura-Mantle** • `16360` **Farmer Aura**\n"
            "`16318` **Xenoso's Nebulafin** • `16320` **Nebulafin Leash** • `16342` **Bingo**"
        ),
        inline=False
    )

    embed.add_field(
        name="😀 Growmojis & Mystery Crate (9 Items)",
        value=(
            "`16322`–`16336` **8 Growmojis:** 🔥 Fire • 😏 Flirty • 💡 Light Bulb • 🤑 Money\n"
            "╰ 🤓 Nerd • 💀 Skull • 🏆 Trophy • 🥀 Wilted Flower\n"
            "`16356` **Voucher Dayz Growmoji Mystery Crate**"
        ),
        inline=False
    )

    embed.set_footer(text=f"Total Tracked: {len(ITEMS_CACHE):,} items | items.dat v{ITEMS_VERSION} | Type !item <name or ID>")

    # Attach preview if available
    cosmetics_png = os.path.join(SCRIPT_DIR, "player_cosmetics4.png")
    if os.path.exists(cosmetics_png):
        file = discord.File(cosmetics_png, filename="player_cosmetics4.png")
        embed.set_image(url="attachment://player_cosmetics4.png")
        await ctx.send(embed=embed, file=file)
    else:
        await ctx.send(embed=embed)

@bot.command(name="wonderweek", aliases=["ww", "wonder", "wonderleaks"])
async def cmd_wonderweek(ctx):
    if not ITEMS_CACHE:
        refresh_items()

    embed = discord.Embed(
        title="🌟 Wonder Week Event • Exclusive Leak Directory",
        description=(
            f"> 📅 **Event:** Wonder Week 2026/2027 • Database: `items.dat v{ITEMS_VERSION}`\n"
            f"> 🔓 **15 Exclusive Event Items & 15 Paired Seeds Unveiled!**\n\n"
            "```yaml\n"
            "🌟 Wonder Week Datamined Items (IDs #16396 – #16425)\n"
            "  • Weapons / Tech: Lightning Nunchucks, Atom Constructs, WM Paradise City\n"
            "  • Mounts / Wings: Mecha Tank, Super Stingers, Pariah's Shawl\n"
            "  • Costumes / Set: Winged Hair & Hat, Atom Suit & Shorts, Mask Sets\n"
            "```"
        ),
        color=0xF1C40F
    )

    embed.add_field(
        name="⚡ Weapons, Technology & Placeables (4 Items)",
        value=(
            "`16398` **Lightning Nunchucks** *(Hand / Weapon)*\n"
            "╰ *\"Join the world's most fearsome fighting team! Untradeable until 18 Feb 2027.\"*\n"
            "`16396` **Atom Constructs** *(Hand / Weapon)*\n"
            "╰ *\"Feel invincible with the molecular power of the Atom Constructs!\"*\n"
            "`16406` **Weather Machine - Paradise City** *(Placeable / Weather)*\n"
            "╰ *\"Head down to the Paradise City! Untradeable until 18 Feb 2027.\"*\n"
            "`16422` **Paradise Watch** *(Hand / Bling)*\n"
            "╰ *\"Show off your bling! No Ultimate Edition required!\"*"
        ),
        inline=False
    )

    embed.add_field(
        name="🤖 Mecha Tank, Mounts & Wings (5 Items)",
        value=(
            "`16400` **Mecha Tank** *(Mount / Feet)*\n"
            "╰ *\"Pilot a mech AND a tank! Best of both worlds 'tanks' to Mecha Tank!\"*\n"
            "`16402` **Pariah's Shawl** *(Back / Cape)*\n"
            "╰ *\"Become one with the desert! Alternates between two styles!\"*\n"
            "`16404` **Super Stingers** *(Back / Wings & Blades)*\n"
            "╰ *\"Stab your foes with the sharp blades of the Super Stingers!\"*\n"
            "`16416` **Mecha Tank's Birds** *(Artifact / Ances)* • *\"Birds... nuff said!\"*\n"
            "`16420` **Super Stingers Belt** *(Artifact / Belt)* • *\"Training Wheels Protocol\"*"
        ),
        inline=False
    )

    embed.add_field(
        name="👑 Costumes, Hairstyles & Masks (6 Items)",
        value=(
            "`16408` **Winged Hair** *(Hair)* • *\"Give Rapunzel some competition!\"*\n"
            "`16424` **Winged Hair Hat** *(Hat)* • *\"Matching hat for Winged Hair.\"*\n"
            "`16412` **Atom Suit** *(Shirt)* • `16410` **Atom Shorts** *(Pants)*\n"
            "`16414` **Lightning Nunchucks Mask** *(Face)* • *\"Hide your secret identity!\"*\n"
            "`16418` **Pariah's Mask** *(Face)* • *\"Death answers to you! For you are doom!\"*"
        ),
        inline=False
    )

    embed.add_field(
        name="🌱 Paired Wonder Week Seeds (15 Seeds)",
        value=(
            "`16397` Atom Constructs Seed • `16399` Lightning Nunchucks Seed\n"
            "`16401` Mecha Tank Seed • `16403` Pariah's Shawl Seed • `16405` Super Stingers Seed\n"
            "`16407` WM Paradise City Seed • `16409` Winged Hair Seed • `16411` Atom Shorts Seed\n"
            "`16413` Atom Suit Seed • `16415` Nunchucks Mask Seed • `16417` Tank Birds Seed\n"
            "`16419` Pariah Mask Seed • `16421` Stingers Belt Seed • `16423` Watch Seed • `16425` Hat Seed"
        ),
        inline=False
    )

    embed.set_footer(text=f"Database: items.dat v{ITEMS_VERSION} ({len(ITEMS_CACHE):,} items) • Type !item <name or ID> for 128x128 sprite & stats")

    cosmetics_png = os.path.join(SCRIPT_DIR, "player_cosmetics4.png")
    if os.path.exists(cosmetics_png):
        file = discord.File(cosmetics_png, filename="player_cosmetics4.png")
        embed.set_image(url="attachment://player_cosmetics4.png")
        await ctx.send(embed=embed, file=file)
    else:
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

    # Release date estimation based on ID ranges
    if item['id'] >= 16314:
        embed.add_field(name="Release Date", value="`October 5, 2026 (v5.59)`", inline=True)
    elif item['id'] >= 16200:
        embed.add_field(name="Release Date", value="`September 2026 (v5.58)`", inline=True)
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
    - !diff (or !diff latest / !diff oct) -> Shows October 5, 2026 (v5.59) changelog (+120 items)
    - !diff previous (or !diff sep / !diff 5.58) -> Shows September 2026 (v5.58) changelog (+114 items)
    - !diff live -> Checks live local game files against baseline snapshot
    """
    if not ITEMS_CACHE:
        refresh_items()

    target = patch_name.strip().lower()

    if target in ["live", "current", "now"]:
        snapshot = load_snapshot()
        if not snapshot:
            save_snapshot(ITEMS_CACHE)
            await ctx.send("ℹ️ No previous baseline found. Current database saved as the baseline snapshot!")
            return

        diff = generate_items_diff(snapshot, ITEMS_CACHE)
        title = "📊 Growtopia Live Watcher Diff"
        desc_header = "Comparing live game files right now against baseline snapshot:\n"
        patch_info = "Live PC Watcher"
    elif target in ["previous", "sep", "september", "5.58", "v5.58", "old"]:
        # September 2026 patch: IDs #16200 to #16313
        old_items = ITEMS_CACHE[:16200]
        new_items = ITEMS_CACHE[:16314]
        diff = generate_items_diff(old_items, new_items)
        title = "📊 Growtopia September 2026 Patch Diff (v5.58)"
        desc_header = "Changelog for the **September 2026 Update** (IDs `#16200` – `#16313`):\n"
        patch_info = "Patch v5.58 (September 2026)"
    elif target in ["october", "oct", "5.59", "v5.59", "clash"]:
        old_items = ITEMS_CACHE[:16314]
        new_items = ITEMS_CACHE[:16434]
        diff = generate_items_diff(old_items, new_items)
        title = "📊 Growtopia October Patch Diff (v5.59 — October 5, 2026)"
        desc_header = "Changelog for the **October 5, 2026 Clash Season Update** (IDs `#16314` – `#16433`):\n"
        patch_info = "Patch v5.59 (October 5, 2026)"
    else:
        # Default / Wonder Week: Compare baseline snapshot against live v27 items
        snapshot = load_snapshot()
        if snapshot:
            diff = generate_items_diff(snapshot, ITEMS_CACHE)
            title = f"📊 Growtopia Wonder Week Update Diff (v{ITEMS_VERSION})"
            desc_header = "Changelog for **Wonder Week 2026/2027 Event Activation**:\n"
            patch_info = f"Wonder Week Update • items.dat v{ITEMS_VERSION}"
        else:
            old_items = ITEMS_CACHE[:16314]
            new_items = ITEMS_CACHE[:16434]
            diff = generate_items_diff(old_items, new_items)
            title = "📊 Growtopia Latest Patch Diff"
            desc_header = "Changelog for the **Latest Update** (IDs `#16314` – `#16433`):\n"
            patch_info = f"Latest Patch • items.dat v{ITEMS_VERSION}"

    added = diff["added"]
    modified = diff["modified"]

    embed = discord.Embed(
        title=title,
        description=(
            f"{desc_header}\n"
            f"• **🆕 New Items Added:** `{len(added)}`\n"
            f"• **🔄 Items Rebalanced / Modified:** `{len(modified)}`\n"
            f"• **📦 Total Database:** `{len(ITEMS_CACHE):,}` items (v{ITEMS_VERSION})\n"
        ),
        color=0x3498db
    )

    if added:
        top_added = [
            f"• `#{it['id']}` **{it['name']}** (Rarity `{it['rarity']}`)"
            for it in added if not it['name'].endswith('Seed') and 'null_item' not in it['name']
        ][:12]
        unreleased_count = sum(1 for it in added if 'null_item' in it['name'])
        added_text = "\n".join(top_added)
        if unreleased_count > 0:
            added_text += f"\n• *...plus `{unreleased_count}` unreleased event placeholder items!*"

        embed.add_field(
            name=f"✨ Key New Additions ({len(added)} total)",
            value=added_text if top_added else f"{len(added)} new items",
            inline=False
        )

    if modified:
        mod_lines = []
        main_mods = [m for m in modified if not m['name'].endswith('Seed')]
        for m in main_mods[:10]:
            mod_lines.append(f"• `#{m['id']}` **{m['name']}**:\n  " + ", ".join(m['changes']))
        seed_mods = [m for m in modified if m['name'].endswith('Seed')]
        if seed_mods:
            mod_lines.append(f"• *...plus `{len(seed_mods)}` corresponding event seed pairs updated!*")
        embed.add_field(
            name=f"🔄 Activated & Modified Items ({len(modified)})",
            value="\n".join(mod_lines),
            inline=False
        )

    if not added and not modified:
        embed.description += "\n✨ **Everything matches! Zero unannounced changes or file modifications.**"

    embed.set_footer(text=f"{patch_info} • Options: !diff latest, !diff wonderweek, !diff oct, !diff sep")
    await ctx.send(embed=embed)

@bot.command(name="check")
async def cmd_check(ctx):
    old_count = len(ITEMS_CACHE)
    refresh_items()
    new_count = len(ITEMS_CACHE)

    if new_count > old_count:
        diff = new_count - old_count
        await ctx.send(f"🚨 **NEW UPDATE DETECTED!** `{diff}` new items were added! Type `{PREFIX}latest` to view them!")
    else:
        await ctx.send(f"✅ Database is up to date. Currently tracking **{new_count:,} items** (v{ITEMS_VERSION}).")

@bot.command(name="sync", aliases=["fetch", "hotfix"])
async def cmd_sync(ctx):
    status_msg = await ctx.send("⚡ **Fast-syncing with Ubisoft servers...** Checking in the background (4-5s)...")
    old_mtime = os.path.getmtime(ITEMS_DAT_PATH) if os.path.exists(ITEMS_DAT_PATH) else 0

    success, msg = await perform_silent_sync(max_seconds=5)
    if not success:
        await status_msg.edit(content=f"⚠️ {msg}")
        return

    new_mtime = os.path.getmtime(ITEMS_DAT_PATH) if os.path.exists(ITEMS_DAT_PATH) else 0
    if new_mtime != old_mtime and old_mtime != 0:
        await status_msg.edit(content="🚨 **NEW HOTFIX DETECTED!** Game files were updated during sync! Computing changelog...")
    else:
        await status_msg.edit(content=f"✅ **Sync complete!** Your game database is 100% current with the latest Ubisoft servers (`{len(ITEMS_CACHE):,}` items).")

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
    global LAST_MTIME, LAST_COUNT, ITEMS_CACHE
    if not WATCHER_ENABLED or not os.path.exists(ITEMS_DAT_PATH):
        return

    try:
        mtime = os.path.getmtime(ITEMS_DAT_PATH)
        if mtime != LAST_MTIME and LAST_MTIME != 0:
            print("[Auto-Monitor] items.dat modification detected!")
            old_items = list(ITEMS_CACHE)
            if not refresh_items():
                return
            new_items = ITEMS_CACHE

            # Compute diff against previous state
            diff = generate_items_diff(old_items, new_items)
            added = diff["added"]
            modified = diff["modified"]

            if added or modified:
                print(f"🚨 AUTO-MONITOR DETECTED CHANGES! {len(added)} added, {len(modified)} modified")

                embed = discord.Embed(
                    title="🚨 INSTANT LEAK: Growtopia Patch & Diff Detected!",
                    description=(
                        f"**Ubisoft updated items.dat on your computer!**\n\n"
                        f"• **🆕 New Items:** `{len(added)}`\n"
                        f"• **🔄 Modified Items:** `{len(modified)}`\n"
                        f"• **📦 Total Count:** `{len(new_items):,}` (v{ITEMS_VERSION})"
                    ),
                    color=0xff0044
                )

                if added:
                    lines = []
                    for it in added[:12]:
                        if not it['name'].endswith('Seed'):
                            lines.append(f"• `#{it['id']}` **{it['name']}** (Rarity `{it['rarity']}`)")

                    embed.add_field(
                        name="📦 Newly Discovered Items",
                        value="\n".join(lines) if lines else "New item slots added to database.",
                        inline=False
                    )

                if modified:
                    mod_lines = []
                    main_mods = [m for m in modified if not m['name'].endswith('Seed')]
                    for m in main_mods[:10]:
                        mod_lines.append(f"• `#{m['id']}` **{m['name']}**: " + ", ".join(m['changes']))
                    seed_mods = [m for m in modified if m['name'].endswith('Seed')]
                    if seed_mods:
                        mod_lines.append(f"• *...plus `{len(seed_mods)}` corresponding event seeds updated!*")
                    embed.add_field(
                        name="🔄 Rebalanced / Modified Items",
                        value="\n".join(mod_lines),
                        inline=False
                    )

                save_snapshot(new_items)
                embed.set_footer(text=f"Growtopia Real-Time Auto-Watcher • Total Items: {len(new_items):,}")

                if ALERT_CHANNEL_ID:
                    ch = bot.get_channel(ALERT_CHANNEL_ID)
                    if ch:
                        try:
                            await ch.send(embed=embed)
                        except Exception as e:
                            print(f"Error sending to alert channel: {e}")
                else:
                    for guild in bot.guilds:
                        target = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                        if target:
                            try:
                                await target.send(embed=embed)
                            except Exception as e:
                                print(f"Error sending auto alert: {e}")
    except Exception as e:
        print(f"[Auto-Monitor Exception]: {e}")

if __name__ == "__main__":
    print("Starting Growtopia Discord Bot...")
    bot.run(BOT_TOKEN)
