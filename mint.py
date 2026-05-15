# bot stuff
import discord
from discord.ext import commands
from discord import app_commands

# importing libs
import sqlite3
import json
import asyncio
import random
import time
import re
import requests

# ai and search part
from duckduckgo_search import DDGS
from openai import OpenAI
from groq import Groq


# config file
with open("config.json", "r") as f:
    config = json.load(f)

TOKEN = config["token"]
OPENROUTER_KEY = config["openrouter_key"]
GROQ_KEY = config["groq_key"]
GIPHY_KEY = config["giphy_key"]


# smart ai (openrouter)
smart_ai = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY
)

#fast ai (groq)
fast_ai = Groq(
    api_key=GROQ_KEY
)


# discord setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# database setup
conn = sqlite3.connect("uids.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS uids (
    user_id TEXT PRIMARY KEY,
    uid TEXT,
    public INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    guild_id TEXT PRIMARY KEY,
    log_channel_id TEXT
)
""")

conn.commit()


# memory system
memory = {}

# anti spam cooldown
cooldowns = {}


# random gifs mint can use (fallback system)
emotion_gifs = {
    "happy": ["https://media.tenor.com/Wz5lbhWkO4AAAAAM/anime-happy.gif"],
    "laugh": ["https://media.tenor.com/0AVbKGY_MxMAAAAM/anime-laugh.gif"],
    "sad": ["https://media.tenor.com/jD4-9W7SOyQAAAAM/anime-sad.gif"],
    "angry": ["https://media.tenor.com/NV0kGJ0dKtAAAAAM/anime-angry.gif"],
    "cute": ["https://media.tenor.com/jhJ7bEjJm7AAAAAM/anime-smile.gif"]
}


# =========================
# 🎞 GIPHY SYSTEM (NEW)
# =========================
def get_giphy_gif(query):
    try:
        url = "https://api.giphy.com/v1/gifs/search"

        params = {
            "api_key": GIPHY_KEY,
            "q": query,
            "limit": 10
        }

        res = requests.get(url, params=params, timeout=5)
        data = res.json()

        if "data" not in data or not data["data"]:
            return None

        gif = random.choice(data["data"])
        return gif["images"]["original"]["url"]

    except:
        return None


mood_queries = {
    "happy": "anime happy cute",
    "laugh": "anime laugh funny",
    "sad": "anime sad crying",
    "angry": "anime angry",
    "cute": "anime blushing cute",
    "excited": "anime excited sparkle"
}


# choose fallback gif
def choose_gif(text):
    t = text.lower()

    if any(w in t for w in ["lol", "haha", "funny"]):
        return random.choice(emotion_gifs["laugh"])

    if any(w in t for w in ["sad", "sorry", "cry"]):
        return random.choice(emotion_gifs["sad"])

    if any(w in t for w in ["angry", "mad"]):
        return random.choice(emotion_gifs["angry"])

    if any(w in t for w in ["cute", "love"]):
        return random.choice(emotion_gifs["cute"])

    if any(w in t for w in ["good", "nice", "great", "awesome"]):
        return random.choice(emotion_gifs["happy"])

    return None


# web search
def search_web(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))

            if not results:
                return ""

            return "\n".join(
                f"- {r['title']}: {r['body']}"
                for r in results
            )

    except:
        return ""


# reminder task
async def reminder_task(channel, user, seconds, text):
    await asyncio.sleep(seconds)
    await channel.send(f"⏰ {user.mention} reminder: {text}")


# slash commands group
mint = app_commands.Group(name="mint", description="Mint commands")
bot.tree.add_command(mint)


@bot.event
async def on_ready():
    await bot.tree.sync()
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="NTE"
        )
    )
    print(f"logged in as {bot.user}")


# system prompt
def build_prompt(web_info, convo):
    return f"""
You are Mint.

PERSONALITY:
- cute
- cheerful
- playful
- slightly clumsy
- friendly
- natural sounding

RULES:
- never sound robotic
- keep replies readable
- be useful
- use web info if available
- never say you're an ai
- you may add mood tags like <<mood:happy>>, <<mood:sad>>, <<mood:laugh>>, <<mood:angry>>, <<mood:cute>>

WEB INFO:
{web_info}

CHAT:
{convo}
"""


# =========================
# MAIN AI + MOD SYSTEM
# =========================
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # =========================
    # 🚨 AUTO-MOD (UPDATED)
    # =========================
    illegal_content = ["scam", "discord.gg/", "hack", "nude", "free nitro"]

    if any(word in message.content.lower() for word in illegal_content):

        content_snapshot = message.content

        try:
            await message.delete()
        except:
            pass

        # find moderation-logs channel
        log_channel = discord.utils.get(message.guild.text_channels, name="moderation-logs")

        if log_channel:
            embed = discord.Embed(
                title="🚨 AutoMod Action",
                color=0xff0000,
                timestamp=message.created_at
            )
            embed.add_field(name="User", value=f"{message.author} ({message.author.id})", inline=False)
            embed.add_field(name="Channel", value=message.channel.mention, inline=False)
            embed.add_field(name="Content", value=f"```{content_snapshot}```", inline=False)

            await log_channel.send(embed=embed)

        return

    # only reply if tagged
    if bot.user not in message.mentions:
        return

    user_id = str(message.author.id)

    now = time.time()

    if user_id in cooldowns:
        if now - cooldowns[user_id] < 3:
            return

    cooldowns[user_id] = now

    async with message.channel.typing():

        text = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

        if not text:
            return await message.reply("hmm? you called me? ✨", mention_author=False)

        # web search
        needs_web = any(x in text.lower() for x in ["latest", "current", "today", "news", "who is", "now"])
        web_info = search_web(text) if needs_web else ""

        # memory
        channel_id = str(message.channel.id)

        if channel_id not in memory:
            memory[channel_id] = []

        memory[channel_id].append(f"{message.author.name}: {text}")
        memory[channel_id] = memory[channel_id][-10:]

        convo = "\n".join(memory[channel_id])

        smart_keywords = ["explain", "why", "how", "code", "compare", "latest", "who is", "help"]
        use_smart_ai = any(k in text.lower() for k in smart_keywords)

        system_prompt = build_prompt(web_info, convo)

        try:

            if use_smart_ai:
                response = smart_ai.chat.completions.create(
                    model="openai/gpt-oss-20b:free",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text}
                    ]
                )
            else:
                response = fast_ai.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text}
                    ]
                )

            reply = response.choices[0].message.content

            # mood detection
            mood = None
            match = re.search(r"<<mood:(.*?)>>", reply)

            if match:
                mood = match.group(1)
                reply = re.sub(r"<<mood:.*?>>", "", reply).strip()

            memory[channel_id].append(f"Mint: {reply}")

            await message.reply(reply[:2000], mention_author=False)

            # =========================
            # 🎞 GIF SYSTEM (NEW FINAL)
            # =========================
            gif = None

            # try AI mood first
            if mood:
                gif = get_giphy_gif(mood_queries.get(mood, mood))

            # fallback random mood
            if not gif:
                gif = get_giphy_gif(random.choice(list(mood_queries.values())))

            # fallback local gifs if GIPHY fails
            if not gif:
                gif = choose_gif(reply)

            if gif and random.randint(1, 3) == 1:
                await message.channel.send(gif)

        except Exception as e:
            await message.reply(f"❌ ai error:\n```{e}```", mention_author=False)

    await bot.process_commands(message)


# start bot
bot.run(TOKEN)