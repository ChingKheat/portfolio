import os
import sys
import json
import asyncio

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

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
    print(f" Ready to respond to commands ({PREFIX}latest, {PREFIX}diff, {PREFIX}item, {PREFIX}check, {PREFIX}help)")
    print(f"==================================================")
    refresh_items()
    if not auto_monitor.is_running():
        auto_monitor.start()

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
    embed.add_field(name=f"`{PREFIX}diff`", value="Show the patch changelog (new & modified/rebalanced items).", inline=False)
    embed.add_field(name=f"`{PREFIX}guild`", value="Inspect Guild Flag shapes, shields, and logo sprite sheets.", inline=False)
    embed.add_field(name=f"`{PREFIX}latest`", value="Show the newest in-game items from the latest patch.", inline=False)
    embed.add_field(name=f"`{PREFIX}item <name or ID>`", value="Search any item (e.g. `!item Pickaxe` or `!item 16428`).", inline=False)
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
    mtime_str = "Oct 10, 2026"
    if os.path.exists(ITEMS_DAT_PATH):
        mtime = os.path.getmtime(ITEMS_DAT_PATH)
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y at %I:%M %p")

    embed = discord.Embed(
        title="✨ Growtopia Latest Items Directory",
        description=(
            f"📅 **Patch Release Date:** `October 5, 2026` (Version 5.59)\n"
            f"⏰ **Downloaded to PC:** `{mtime_str}`\n"
            f"📦 **New Items in this Patch:** `120 items` (IDs `#16314` – `#16433`)\n\n"
            f"Here are the newest items categorized by theme:\n"
        ),
        color=0x5865F2
    )

    embed.add_field(
        name="⚔️ Immortal Series (Released: Oct 5, 2026)",
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
        name="👑 Domination & Royal Gear (Released: Oct 5, 2026)",
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
        name="🍂 Fall & Autumn Event (Released: Oct 5, 2026)",
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
        name="✂️ Hairstyles & Hats (Released: Oct 5, 2026)",
        value=(
            "• `#16354` **Wolf Cut Hair**\n"
            "• `#16352` **Tied Anime Bun**\n"
            "• `#16350` **Tanuki Ears**\n"
            "• `#16348` **Orca Hood**\n"
            "• `#16346` **Horns of Calamity**"
        ),
        inline=False
    )

    embed.set_footer(text=f"Patch v5.59 • Downloaded {mtime_str} • Type !item <name> for single item dates & stats")

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
    
    # Release date estimation based on ID ranges
    if item['id'] >= 16314:
        embed.add_field(name="Release Date", value="`October 5, 2026 (v5.59)`", inline=True)
    elif item['id'] >= 16200:
        embed.add_field(name="Release Date", value="`September 2026 (v5.58)`", inline=True)
    else:
        embed.add_field(name="Release Era", value="`Legacy Release`", inline=True)

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
    else:
        # Default: Latest October 5, 2026 update (IDs #16314 to #16433)
        old_items = ITEMS_CACHE[:16314]
        new_items = ITEMS_CACHE[:16434]
        diff = generate_items_diff(old_items, new_items)
        title = "📊 Growtopia Latest Patch Diff (v5.59 — October 5, 2026)"
        desc_header = "Changelog for the **October 5, 2026 Clash Season Update** (IDs `#16314` – `#16433`):\n"
        patch_info = "Patch v5.59 (October 5, 2026)"

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
        for m in modified[:8]:
            mod_lines.append(f"• `#{m['id']}` **{m['name']}**:\n  " + ", ".join(m['changes']))
        embed.add_field(
            name=f"🔄 Rebalanced & Modified Items ({len(modified)})",
            value="\n".join(mod_lines),
            inline=False
        )

    if not added and not modified:
        embed.description += "\n✨ **Everything matches! Zero unannounced changes or file modifications.**"

    embed.set_footer(text=f"{patch_info} • Options: !diff latest, !diff previous, !diff live")
    await ctx.send(embed=embed)

@bot.command(name="guild", aliases=["guilds", "guildlogo", "guildflag"])
async def cmd_guild(ctx, *, query: str = "1"):
    """Shows Guild Flag and Logo sprite sheets and items."""
    query_clean = query.strip().lower()

    if query_clean in ["1", "2", "3", "logo", "logos", "flag", "flags", "default"]:
        page_num = "1" if query_clean in ["1", "logo", "logos", "flag", "flags", "default"] else query_clean
        tex_name = f"gd_page{page_num}.rttex"
        png_name = f"gd_page{page_num}.png"
        rttex_path = os.path.join(GAME_DIR, tex_name)
        png_path = os.path.join(SCRIPT_DIR, png_name)

        if not os.path.exists(png_path) and os.path.exists(rttex_path):
            try:
                convert_rttex(rttex_path, png_path)
            except Exception as e:
                print(f"Error converting {tex_name}: {e}")

        embed = discord.Embed(
            title=f"🛡️ Growtopia Guild Flag & Logo Designs (Sheet {page_num})",
            description=(
                f"Contains the official **Guild Flag Shapes, Emblems, and Patterns**!\n\n"
                f"• **Shapes:** Shield, Arrow, Wave, Peak, Banner\n"
                f"• **Patterns:** Flame, Harlequin, Plaid, Cross, Slant, Filigree, Division\n"
                f"• **Texture Sheet:** `{tex_name}`\n"
            ),
            color=0xf1c40f
        )
        embed.set_footer(text=f"Try: !guild 1, !guild 2, !guild 3, or !item Guild Flag - Shield")

        if os.path.exists(png_path):
            file = discord.File(png_path, filename=png_name)
            embed.set_image(url=f"attachment://{png_name}")
            await ctx.send(embed=embed, file=file)
        else:
            await ctx.send(embed=embed)
    else:
        # Search guild flag item directly
        await cmd_item(ctx, query=f"Guild Flag {query}")

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
    global LAST_MTIME, LAST_COUNT, ITEMS_CACHE
    if not WATCHER_ENABLED or not os.path.exists(ITEMS_DAT_PATH):
        return

    mtime = os.path.getmtime(ITEMS_DAT_PATH)
    if mtime != LAST_MTIME and LAST_MTIME != 0:
        print("[Auto-Monitor] items.dat modification detected!")
        old_items = list(ITEMS_CACHE)
        refresh_items()
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
                for m in modified[:6]:
                    mod_lines.append(f"• `#{m['id']}` **{m['name']}**: " + ", ".join(m['changes']))
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

if __name__ == "__main__":
    print("Starting Growtopia Discord Bot...")
    bot.run(BOT_TOKEN)
