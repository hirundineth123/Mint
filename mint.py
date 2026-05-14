import discord
from discord.ext import commands
import sqlite3
import re
import os

# 🔐 SAFE TOKEN (set this in hosting panel, NOT in code)
TOKEN = os.getenv("TOKEN")

# Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Database setup
conn = sqlite3.connect("uids.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS uids (
    user_id TEXT PRIMARY KEY,
    uid TEXT
)
""")
conn.commit()

# Bot ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# Listen to messages
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Only in this channel
    if message.channel.name == "uid-share":

        # Find UID (6–15 digits)
        match = re.search(r"\b\d{6,15}\b", message.content)

        if match:
            uid = match.group()

            cursor.execute("""
            INSERT OR REPLACE INTO uids (user_id, uid)
            VALUES (?, ?)
            """, (str(message.author.id), uid))

            conn.commit()

            await message.channel.send(
                f"✅ UID saved for {message.author.mention}: `{uid}`",
                delete_after=5
            )

    await bot.process_commands(message)

# Show UID
@bot.command()
async def myuid(ctx):

    cursor.execute(
        "SELECT uid FROM uids WHERE user_id=?",
        (str(ctx.author.id),)
    )

    result = cursor.fetchone()

    if result:
        await ctx.send(f"📌 Your UID: `{result[0]}`")
    else:
        await ctx.send("❌ No UID found. Go to #uid-share and send it.")

# Remove UID
@bot.command()
async def removeuid(ctx):

    cursor.execute(
        "DELETE FROM uids WHERE user_id=?",
        (str(ctx.author.id),)
    )

    conn.commit()

    await ctx.send("🗑️ Your UID has been removed.")

bot.run(TOKEN)