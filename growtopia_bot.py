import os
import sys
import json
import asyncio

# Ensure UTF-8 output on Windows terminal
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

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
ITEMS_VERSION = 26
LAST_MTIME = 0
LAST_COUNT = 0

def refresh_items():
    global ITEMS_CACHE, ITEMS_VERSION, LAST_MTIME, LAST_COUNT
    if os.path.exists(ITEMS_DAT_PATH):
        LAST_MTIME = os.path.getmtime(ITEMS_DAT_PATH)
        ITEMS_VERSION, ITEMS_CACHE = parse_itemsdat()
        LAST_COUNT = len(ITEMS_CACHE)
        print(f"Loaded {LAST_COUNT} items (v{ITEMS_VERSION})")
        return True
    return False

@bot.event
async def on_ready():
    print(f"==================================================")
    print(f" 🤖 GROWTOPIA DISCORD BOT LOGGED IN AS: {bot.user}")
    print(f" Ready to respond to commands ({PREFIX}latest, {PREFIX}search, {PREFIX}check, {PREFIX}help)")
    print(f"==================================================")
    refresh_items()
    if not auto_monitor.is_running():
        auto_monitor.start()

@bot.command(name="help")
async def cmd_help(ctx):
    embed = discord.Embed(
        title="🎮 Growtopia Dataminer Bot Commands",
        description="Type any of these commands in this channel:",
        color=0x3498db
    )
    embed.add_field(name=f"`{PREFIX}latest`", value="Show the newest in-game items from the latest patch.", inline=False)
    embed.add_field(name=f"`{PREFIX}item <name or ID>`", value="Search any item (e.g. `!item Pickaxe` or `!item 16428`).", inline=False)
    embed.add_field(name=f"`{PREFIX}check`", value="Check if a new game update is available right now.", inline=False)
    embed.add_field(name=f"`{PREFIX}texture <filename>`", value="Extract and view any game `.rttex` sprite sheet.", inline=False)
    embed.set_footer(text=f"Prefix: {PREFIX} • Total Items Tracked: {len(ITEMS_CACHE):,}")
    await ctx.send(embed=embed)

@bot.command(name="latest")
async def cmd_latest(ctx):
    if not ITEMS_CACHE:
        refresh_items()

    embed = discord.Embed(
        title="✨ Growtopia Latest Items Directory",
        description="Here are the newest items from the latest patch, organized by category:\n",
        color=0x5865F2
    )

    embed.add_field(
        name="⚔️ Immortal Series",
        value=(
            "• `#16432` **Immortal Puppy Leash**\n"
            "• `#16430` **Immortal Title**\n"
            "• `#16428` **Immortal Sonic Buster Katana**\n"
            "• `#16426` **Immortal Pickaxe**\n"
            "• `#16340` **Immortal Night Vision Goggles**"
        ),
        inline=False
    )

    embed.add_field(
        name="👑 Domination & Royal Gear",
        value=(
            "• `#16388` **Royal Domination Armor**\n"
            "• `#16386` **Domination Armor**\n"
            "• `#16384` **Shadow-You** (Dark Clone)\n"
            "• `#16394` **Drape Coat**\n"
            "• `#16390` **Sharp Wrench Style**"
        ),
        inline=False
    )

    embed.add_field(
        name="🍂 Fall & Autumn Event",
        value=(
            "• `#16370` **Fall Witch's Hat**\n"
            "• `#16372` **Fall Witch's Coat**\n"
            "• `#16374` **Fall Witch's Pants**\n"
            "• `#16362` **Halo of Autumn Leaves**\n"
            "• `#16366` **Sheep Chariot** (Mount)\n"
            "• `#16368` **Arched Bridge** • `#16380` **Lake Lantern**"
        ),
        inline=False
    )

    embed.add_field(
        name="✂️ Hairstyles & Hats",
        value=(
            "• `#16354` **Wolf Cut Hair**\n"
            "• `#16352` **Tied Anime Bun**\n"
            "• `#16350` **Tanuki Ears**\n"
            "• `#16348` **Orca Hood**\n"
            "• `#16346` **Horns of Calamity**"
        ),
        inline=False
    )

    embed.set_footer(text=f"💡 Tip: Type !item <name> (e.g. !item Pickaxe) to view detailed stats & sprites!")

    # Attach preview if available
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
    embed.add_field(name="Texture File", value=f"`{item['texture']}`", inline=True)
    if item.get("grow_time"):
        embed.add_field(name="Grow Time", value=f"{item['grow_time']}s", inline=True)
    if item.get("info"):
        embed.add_field(name="Description", value=item["info"], inline=False)

    if len(matches) > 1:
        other_names = ", ".join([f"`{m['name']}`" for m in matches[1:]])
        embed.add_field(name="Other Matches", value=other_names, inline=False)

    # Try to convert and attach texture if it exists
    tex_file = item["texture"]
    attached_file = None
    if tex_file:
        rttex_path = os.path.join(GAME_DIR, tex_file)
        if os.path.exists(rttex_path):
            out_png = os.path.join(SCRIPT_DIR, tex_file.replace(".rttex", ".png"))
            if not os.path.exists(out_png):
                convert_rttex(rttex_path, out_png)
            if os.path.exists(out_png):
                attached_file = discord.File(out_png, filename=os.path.basename(out_png))
                embed.set_image(url=f"attachment://{os.path.basename(out_png)}")

    if attached_file:
        await ctx.send(embed=embed, file=attached_file)
    else:
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
    global LAST_MTIME, LAST_COUNT
    if not os.path.exists(ITEMS_DAT_PATH):
        return

    mtime = os.path.getmtime(ITEMS_DAT_PATH)
    if mtime != LAST_MTIME and LAST_MTIME != 0:
        print("[Auto-Monitor] items.dat modification detected!")
        old_count = LAST_COUNT
        refresh_items()
        new_count = LAST_COUNT

        if new_count > old_count:
            diff = new_count - old_count
            new_items = ITEMS_CACHE[old_count:]
            print(f"🚨 AUTO-MONITOR DETECTED {diff} NEW ITEMS!")

            embed = discord.Embed(
                title="🚨 INSTANT LEAK: New Growtopia Update Detected!",
                description=f"**Ubisoft just updated the game files!** Added **+{diff}** new items:\n",
                color=0xff0044
            )

            lines = []
            for it in new_items[:15]:
                if not it['name'].endswith('Seed'):
                    lines.append(f"• `#{it['id']}` **{it['name']}** (Rarity `{it['rarity']}`)")

            embed.add_field(
                name="📦 Newly Discovered Items",
                value="\n".join(lines) if lines else "New item slots added to database.",
                inline=False
            )
            embed.set_footer(text=f"Growtopia Real-Time Auto-Watcher • Total Items: {new_count:,}")

            for guild in bot.guilds:
                target = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)
                if target:
                    try:
                        await target.send(embed=embed)
                    except Exception as e:
                        print(f"Error sending auto alert: {e}")

if __name__ == "__main__":
    print("Starting Growtopia Discord Bot...")
    bot.run(BOT_TOKEN)
