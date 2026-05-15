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

conn.commit()


# memory system
memory = {}

# anti spam cooldown
cooldowns = {}


# random gifs mint can use
emotion_gifs = {

    "happy": [
        "https://media.tenor.com/Wz5lbhWkO4AAAAAM/anime-happy.gif"
    ],

    "laugh": [
        "https://media.tenor.com/0AVbKGY_MxMAAAAM/anime-laugh.gif"
    ],

    "sad": [
        "https://media.tenor.com/jD4-9W7SOyQAAAAM/anime-sad.gif"
    ],

    "angry": [
        "https://media.tenor.com/NV0kGJ0dKtAAAAAM/anime-angry.gif"
    ],

    "cute": [
        "https://media.tenor.com/jhJ7bEjJm7AAAAAM/anime-smile.gif"
    ]
}


# choose a gif based on the vibe
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


# web search so mint isnt outdated
def search_web(query):

    try:

        with DDGS() as ddgs:

            results = list(
                ddgs.text(query, max_results=3)
            )

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

    await channel.send(
        f"⏰ {user.mention} reminder: {text}"
    )


# mint slash commands
mint = app_commands.Group(
    name="mint",
    description="Mint commands"
)

bot.tree.add_command(mint)


# when bot starts
@bot.event
async def on_ready():

    try:

        synced = await bot.tree.sync()
        print(f"synced {len(synced)} commands")

    except Exception as e:
        print(e)

    # rich presence
    await bot.change_presence(

        status=discord.Status.online,

        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="NTE"
        )
    )

    print(f"logged in as {bot.user}")


# mint help command
@mint.command(
    name="help",
    description="shows mint commands"
)
async def mint_help(interaction: discord.Interaction):

    embed = discord.Embed(
        title="✨ Mint AI System",
        description="cute little ai companion for your server",
        color=0x00ff88
    )

    embed.add_field(
        name="💬 ai chat",
        value=(
            "```"
            "@Mint hello\n"
            "@Mint current us president\n"
            "@Mint explain black holes\n"
            "@Mint best genshin team"
            "```"
        ),
        inline=False
    )

    embed.add_field(
        name="⏰ reminders",
        value=(
            "```"
            "@Mint ping @user in 5 minutes\n"
            "@Mint ping @user in 2 hours"
            "```"
        ),
        inline=False
    )

    embed.add_field(
        name="🆔 uid stuff",
        value=(
            "```"
            "/setuid\n"
            "/myuid\n"
            "/uid\n"
            "/setpublic\n"
            "/removeuid"
            "```"
        ),
        inline=False
    )

    embed.set_footer(
        text="Mint • NTE Companion"
    )

    await interaction.response.send_message(embed=embed)


# save uid
@bot.tree.command(
    name="setuid",
    description="save your uid"
)
async def setuid(interaction: discord.Interaction, uid: str):

    cursor.execute("""
    INSERT OR REPLACE INTO uids
    VALUES (
        ?, ?,
        COALESCE(
            (SELECT public FROM uids WHERE user_id=?),
            0
        )
    )
    """, (
        str(interaction.user.id),
        uid,
        str(interaction.user.id)
    ))

    conn.commit()

    await interaction.response.send_message(
        f"✅ saved uid: `{uid}`",
        ephemeral=True
    )


# see your own uid
@bot.tree.command(
    name="myuid",
    description="view your uid"
)
async def myuid(interaction: discord.Interaction):

    cursor.execute(
        "SELECT uid FROM uids WHERE user_id=?",
        (str(interaction.user.id),)
    )

    result = cursor.fetchone()

    if result:

        await interaction.response.send_message(
            f"📌 your uid: `{result[0]}`",
            ephemeral=True
        )

    else:

        await interaction.response.send_message(
            "❌ no uid saved",
            ephemeral=True
        )


# public/private uid
@bot.tree.command(
    name="setpublic",
    description="change uid privacy"
)
async def setpublic(interaction: discord.Interaction, status: bool):

    cursor.execute("""
    UPDATE uids
    SET public=?
    WHERE user_id=?
    """, (
        1 if status else 0,
        str(interaction.user.id)
    ))

    conn.commit()

    await interaction.response.send_message(
        "✅ updated privacy",
        ephemeral=True
    )


# view other peoples uid
@bot.tree.command(
    name="uid",
    description="view someone's uid"
)
async def uid(interaction: discord.Interaction, user: discord.User):

    cursor.execute("""
    SELECT uid, public
    FROM uids
    WHERE user_id=?
    """, (str(user.id),))

    result = cursor.fetchone()

    if not result:

        return await interaction.response.send_message(
            "❌ no uid found",
            ephemeral=True
        )

    uid_value, public = result

    if public == 1:

        await interaction.response.send_message(
            f"📌 {user.name}'s uid: `{uid_value}`"
        )

    else:

        await interaction.response.send_message(
            "🔒 uid is private",
            ephemeral=True
        )


# remove uid
@bot.tree.command(
    name="removeuid",
    description="delete your uid"
)
async def removeuid(interaction: discord.Interaction):

    cursor.execute("""
    DELETE FROM uids
    WHERE user_id=?
    """, (
        str(interaction.user.id),
    ))

    conn.commit()

    await interaction.response.send_message(
        "🗑️ uid removed",
        ephemeral=True
    )


# main ai system
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # only reply if tagged
    if bot.user not in message.mentions:
        return

    user_id = str(message.author.id)

    # tiny anti spam cooldown
    now = time.time()

    if user_id in cooldowns:

        if now - cooldowns[user_id] < 3:
            return

    cooldowns[user_id] = now

    async with message.channel.typing():

        text = message.content.replace(
            f"<@{bot.user.id}>",
            ""
        ).replace(
            f"<@!{bot.user.id}>",
            ""
        ).strip()

        if not text:

            return await message.reply(
                "hmm? you called me? ✨",
                mention_author=False
            )

        # reminder detector
        reminder_match = re.search(
            r"ping\s+<@!?(\d+)>\s+in\s+(\d+)\s*(second|seconds|minute|minutes|hour|hours)",
            text.lower()
        )

        if reminder_match:

            target_id = int(reminder_match.group(1))
            amount = int(reminder_match.group(2))
            unit = reminder_match.group(3)

            target = message.guild.get_member(target_id)

            seconds = amount

            if "minute" in unit:
                seconds *= 60

            elif "hour" in unit:
                seconds *= 3600

            asyncio.create_task(
                reminder_task(
                    message.channel,
                    target,
                    seconds,
                    f"requested by {message.author.name}"
                )
            )

            return await message.reply(
                f"⏰ okay! i'll ping {target.mention} in {amount} {unit}",
                mention_author=False
            )

        # search web for recent stuff
        needs_web = any(
            word in text.lower()
            for word in [
                "latest",
                "current",
                "today",
                "news",
                "who is",
                "president",
                "now"
            ]
        )

        web_info = search_web(text) if needs_web else ""

        # memory
        channel_id = str(message.channel.id)

        if channel_id not in memory:
            memory[channel_id] = []

        memory[channel_id].append(
            f"{message.author.name}: {text}"
        )

        memory[channel_id] = memory[channel_id][-10:]

        convo = "\n".join(memory[channel_id])

        # harder questions use smarter ai
        smart_keywords = [
            "explain",
            "why",
            "how",
            "code",
            "compare",
            "current",
            "latest",
            "who is",
            "help",
            "tutorial"
        ]

        use_smart_ai = any(
            k in text.lower()
            for k in smart_keywords
        )

        # mint personality
        system_prompt = f"""
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

WEB INFO:
{web_info}

CHAT:
{convo}
"""

        try:

            # smarter ai
            if use_smart_ai:

                response = smart_ai.chat.completions.create(

                    model="openai/gpt-oss-20b:free",

                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ]
                )

                reply = response.choices[0].message.content

            # faster ai
            else:

                response = fast_ai.chat.completions.create(

                    model="llama-3.1-8b-instant",

                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ]
                )

                reply = response.choices[0].message.content

            # save ai reply into memory
            memory[channel_id].append(
                f"Mint: {reply}"
            )

            # send reply
            await message.reply(
                reply[:2000],
                mention_author=False
            )

            # sometimes send gif too
            gif = choose_gif(reply)

            if gif and random.randint(1, 3) == 1:

                await message.channel.send(gif)

        except Exception as e:

            await message.reply(
                f"❌ ai error:\n```{e}```",
                mention_author=False
            )

    await bot.process_commands(message)


# start bot
bot.run(TOKEN)