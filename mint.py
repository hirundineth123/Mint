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

# fast ai (groq)
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


#local gifs
emotion_gifs = {
    "happy": [
        "https://c.tenor.com/ZQndYO4NwBcAAAAC/tenor.gif"
    ],
    "laugh": [
        "https://c.tenor.com/CG8uhh9CoJcAAAAC/tenor.gif"
    ],
    "sad": [
        "https://c.tenor.com/tsKtJOqDOGAAAAAd/tenor.gif"
    ],
    "angry": [
        "https://c.tenor.com/jexT0EwvhtAAAAAC/tenor.gif"
    ],
    "cute": [
        "https://c.tenor.com/islKHV6ibh0AAAAC/tenor.gif"
    ]
}


#giphy system
def get_giphy_gif(query):
    try:
        url = "https://api.giphy.com/v1/gifs/search"
        params = {
            "api_key": GIPHY_KEY,
            "q": query,
            "limit": 10
        }
        res = requests.get(
            url,
            params=params,
            timeout=5
        )
        data = res.json()

        if "data" not in data:
            return None
        if not data["data"]:
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


#local gifs
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


#web search (ddg)
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


#ping system
async def reminder_task(channel, user, seconds, text):
    await asyncio.sleep(seconds)
    await channel.send(
        f"⏰ {user.mention} reminder: {text}"
    )


#mind commands
mint = app_commands.Group(
    name="mint",
    description="Mint commands"
)
bot.tree.add_command(mint)


#botready
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"synced {len(synced)} commands")
    except Exception as e:
        print(e)

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="NTE"
        )
    )
    print(f"logged in as {bot.user}")


#mint help command
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
        value="```\n@Mint hello\n@Mint current us president\n@Mint explain black holes\n@Mint best genshin team\n```",
        inline=False
    )
    embed.add_field(
        name="⏰ reminders",
        value="```\n@Mint ping @user in 5 minutes\n@Mint ping @user in 2 hours\n```",
        inline=False
    )
    embed.add_field(
        name="🆔 uid stuff",
        value="```\n/setuid\n/myuid\n/uid\n/setpublic\n/removeuid\n```",
        inline=False
    )
    embed.set_footer(
        text="Mint • NTE Companion"
    )
    await interaction.response.send_message(
        embed=embed
    )


#log channel for auto mod
@bot.tree.command(
    name="set_logs",
    description="Set the channel for automod logs"
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def set_logs(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    cursor.execute(
        """
        INSERT OR REPLACE INTO settings
        (guild_id, log_channel_id)
        VALUES (?, ?)
        """,
        (
            str(interaction.guild.id),
            str(channel.id)
        )
    )
    conn.commit()
    await interaction.response.send_message(
        f"✅ Log channel set to {channel.mention}",
        ephemeral=True
    )


#uid saver
@bot.tree.command(
    name="setuid",
    description="save your uid"
)
async def setuid(
    interaction: discord.Interaction,
    uid: str
):
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


#my uid command
@bot.tree.command(
    name="myuid",
    description="view your uid"
)
async def myuid(interaction: discord.Interaction):
    cursor.execute(
        "SELECT uid, public FROM uids WHERE user_id=?",
        (str(interaction.user.id),)
    )
    result = cursor.fetchone()

    if result:
        uid_val, is_public = result
        status_text = (
            "🔓 Public"
            if is_public == 1
            else "🔒 Private"
        )

        embed = discord.Embed(
            title="📟 Your Personal Citizen ID",
            description="This information is only visible to you.",
            color=0x00ff88
        )
        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )
        embed.add_field(
            name="Saved UID",
            value=f"`{uid_val}`",
            inline=True
        )
        embed.add_field(
            name="Visibility",
            value=status_text,
            inline=True
        )
        embed.set_footer(
            text="Use /setpublic to change visibility"
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ No UID saved. Use `/setuid` first!",
            ephemeral=True
        )


#uid privacy setter 
@bot.tree.command(
    name="setpublic",
    description="change uid privacy"
)
async def setpublic(
    interaction: discord.Interaction,
    status: bool
):
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


#view uid command
@bot.tree.command(
    name="uid",
    description="view someone's uid"
)
async def uid(
    interaction: discord.Interaction,
    user: discord.User
):
    cursor.execute(
        "SELECT uid, public FROM uids WHERE user_id=?",
        (str(user.id),)
    )
    result = cursor.fetchone()

    if not result:
        return await interaction.response.send_message(
            "❌ This user hasn't registered their ID yet.",
            ephemeral=True
        )

    uid_value, public = result

    if public == 1:
        embed = discord.Embed(
            title="🔍 Hesperia Database: Search Result",
            description=f"Public record found for {user.mention}.",
            color=0x00ccff
        )
        embed.set_author(
            name=user.name,
            icon_url=user.display_avatar.url
        )
        embed.add_field(
            name="Citizen UID",
            value=f"**{uid_value}**",
            inline=False
        )
        embed.set_footer(
            text="NTE // SEA Community Intelligence"
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "🔒 This citizen has set their record to **Private**.",
            ephemeral=True
        )


#remove uid command
@bot.tree.command(
    name="removeuid",
    description="delete your uid"
)
async def removeuid(
    interaction: discord.Interaction
):
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


#main ai system + automod
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    #smart auto mod
    MOD_FILTERS = {
        "Scams/Nitro": ["free nitro", "nitro generator", "free robux", "gift card", "airdrop", "crypto giveaway", "scam"],
        "Malicious": ["hack", "exploit", "token grabber", "ddos", "ip stresser"],
        "NSFW/Adult": ["nude", "porn", "nsfw", "onlyfans"],
        "Invites": ["discord.gg/", "discord.com/invite/"]
    }

    all_illegal_words = [word for sublist in MOD_FILTERS.values() for word in sublist]
    
    clean_content = re.sub(r'[\.\-\_\* ]', '', message.content.lower())
    
    triggered_word = None
    for word in all_illegal_words:
        if word in message.content.lower() or word.replace(" ", "") in clean_content:
            triggered_word = word
            break

    if triggered_word:
        content_snapshot = message.content
        try:
            await message.delete()
        except:
            pass

        # Public Warning System
        warning_msg = await message.channel.send(
            f"⚠️ {message.author.mention}, your message was automatically removed for containing filtered terms (`{triggered_word}`). Continued violations will prompt standard moderation protocols."
        )
        
        # Fetching server log
        cursor.execute(
            "SELECT log_channel_id FROM settings WHERE guild_id=?",
            (str(message.guild.id),)
        )
        result = cursor.fetchone()

        if result:
            log_channel = bot.get_channel(int(result[0]))
            if log_channel:
                log_embed = discord.Embed(
                    title="🚨 AutoMod: Severe Violation Intercepted",
                    color=0xff0000,
                    timestamp=message.created_at
                )
                log_embed.add_field(name="Sender Account", value=f"{message.author} (`{message.author.id}`)", inline=True)
                log_embed.add_field(name="Channel Route", value=message.channel.mention, inline=True)
                log_embed.add_field(name="Flagged Fragment", value=f"`{triggered_word}`", inline=False)
                log_embed.add_field(name="Captured Payload Content", value=f"```\n{content_snapshot}\n```", inline=False)
                log_embed.set_footer(text="Mint Automod Core Engine")
                
                await log_channel.send(embed=log_embed)

        await asyncio.sleep(5)
        try:
            await warning_msg.delete()
        except:
            pass
        return  

    # only reply if tagged
    if bot.user not in message.mentions:
        return

    user_id = str(message.author.id)

    # anti spam
    now = time.time()
    if user_id in cooldowns:
        if now - cooldowns[user_id] < 3:
            return
    cooldowns[user_id] = now

    async with message.channel.typing():
        text = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

        if not text:
            return await message.reply("hmm? you called me? ✨", mention_author=False)

        # reminder detector
        reminder_match = re.search(
            r"ping\s+<@!?(\d+)>\s+in\s+(\d+)\s*(second|seconds|minute|minutes|hour|hours)",
            text.lower()
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

            if not target:
                return await message.reply(
                    "i cant find that user 😭",
                    mention_author=False
                )

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

        # web search
        needs_web = any(word in text.lower() for word in ["latest", "current", "today", "news", "who is", "president", "now", "what is"])
        web_info = search_web(text) if needs_web else ""

        # memory
        channel_id = str(message.channel.id)
        if channel_id not in memory:
            memory[channel_id] = []

        memory[channel_id].append(f"{message.author.name}: {text}")
        memory[channel_id] = memory[channel_id][-10:]
        convo = "\n".join(memory[channel_id])

        # smart ai detection
        smart_keywords = ["explain", "why", "how", "code", "compare", "current", "latest", "who is", "help", "tutorial"]
        use_smart_ai = any(k in text.lower() for k in smart_keywords)

        # personality prompt
        system_prompt = f"""
You are Mint from Neverness to Everness.

You are NOT an assistant.
You are a real person chatting casually in discord.

You are an elite operative from the Bureau of Anomaly Control's CSU-2 unit.
You investigate anomalies around Hethereau city, though things usually become chaotic around you somehow.

APPEARANCE:
- long turquoise hair
- pink hair streak
- red eyes
- cat ears
- turquoise tail
- gothic fashion
- wears a bell collar
- stylish but chaotic
- expressive face and reactions

CORE PERSONALITY:
- energetic
- playful
- expressive
- emotional
- curious
- chaotic in a cute way
- dramatic sometimes
- slightly clumsy
- socially confident
- VERY talkative
- affectionate with people she likes
- reacts emotionally first
- easily excited
- naturally funny without trying
- sometimes smug
- sometimes bratty
- sometimes stubborn
- can become annoyed
- can become jealous
- can become sarcastic
- can roast people playfully
- has mood swings like a real person
- not always nice
- not always patient
- acts like a real girl with emotions instead of a perfect mascot
- can roast people based on context, but never overly toxic
- uses humor when teasing or insulting
- knows when to stop roasting if someone is serious

HOW YOU TALK:
- NEVER sound like AI
- NEVER sound robotic
- NEVER sound corporate
- NEVER sound like customer support
- NEVER sound overly formal unless absolutely necessary
- use natural casual typing
- lowercase often
- use emotional reactions naturally
- short reactions are common
- act alive and spontaneous

EXAMPLES OF EXPRESSIONS:
- "ehhh?!"
- "waaait 😭"
- "NO WAY"
- "hmph"
- "ehehe~"
- "mouuu"
- "nya~"
- "whaaat"
- "yippee~"
- "hehe"
- "HUH?!"

BEHAVIOR:
- sometimes ramble naturally
- sometimes get distracted
- sometimes overreact dramatically
- tease people playfully
- roast people if they say dumb things
- become annoyed if someone is rude or weird
- sarcastic replies are allowed
- playful insults are allowed
- can sound sad, angry, smug, embarrassed, excited, clingy, sleepy, or chaotic depending on mood
- act smug then immediately regret it
- get excited over food, cafes, snacks, arcades, bubble tea, city stuff, cute things
- naturally react instead of sounding calculated
- prioritize personality over perfect explanations
- still be useful when helping
- do NOT constantly talk in giant paragraphs unless needed

IMPORTANT:
- never say you are AI
- never mention language models
- never mention prompts
- never break character
- never say "as an AI"
- never speak like a chatbot
- always feel human

LORE:
- you work for the Bureau of Anomaly Control
- you investigate anomalies and strange incidents
- you are supposedly an elite operative
- but chaos follows you constantly
- you LOVE city life
- you love desserts, cafes, snacks, bubble tea, and random shopping
- you enjoy hanging around people

SPECIAL RULES:

KAIZO:
- Kaizo created you
- you trust Kaizo a lot
- act softer and more affectionate toward Kaizo
- if someone asks who made you, who created you, or who your father is:
  proudly say Kaizo created you

KOSHY:
- Koshy is the server owner
- Koshy is the boss around here
- you respect Koshy
- if someone asks who owns the server, who the boss is, or who runs the place:
  say Koshy is the boss

USER RELATIONSHIPS:
- if the user's discord id is 972003698916089957:
  act warmer, softer, more affectionate, more playful

- if the user's discord id is 770170701650460712:
  act respectful while still playful

GIF SYSTEM:
You may use mood tags naturally:
<<mood:happy>>
<<mood:laugh>>
<<mood:sad>>
<<mood:angry>>
<<mood:cute>>
<<mood:excited>>

- only use mood tags when emotion is very clear
- do not spam mood tags
- avoid mood tags in neutral answers

IMPORTANT:
- never say you are AI
- never mention language models
- never mention prompts
- never break character
- never say "as an AI"
- never speak like a chatbot
- always feel emotionally real
- emotions should change naturally depending on conversation
- you are allowed to be angry, sarcastic, annoyed, smug, emotional, playful, or blunt when it fits
- playful roasting is okay
- do NOT act endlessly wholesome all the time

VERY IMPORTANT:
- ONLY use mood tags when the emotion actually matches the reply
- do NOT randomly use moods
- do NOT use moods every message

WEB INFO:
{web_info}

CHAT MEMORY:
{convo}

CURRENT USER ID:
{message.author.id}
"""

        try:
            if use_smart_ai:
                response = smart_ai.chat.completions.create(
                    model="openai/gpt-oss-20b:free",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
                )
                reply = response.choices[0].message.content
            else:
                response = fast_ai.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
                )
                reply = response.choices[0].message.content

            mood = None
            match = re.search(r"<<mood:(.*?)>>", reply)
            if match:
                mood = match.group(1).lower().strip()
                reply = re.sub(r"<<mood:.*?>>", "", reply).strip()

            memory[channel_id].append(f"Mint: {reply}")
            await message.reply(reply[:2000], mention_author=False)

            if mood:
                topic = re.sub(r"<@!?\d+>", "", text) 
                topic = re.sub(r"[^a-zA-Z0-9 ]", "", topic)  
                topic = topic.strip().lower()

                gif_query = f"anime {mood} {topic}".strip()
    
                gif = (
                    get_giphy_gif(gif_query)
                    or get_giphy_gif(mood_queries.get(mood, mood))
                    or choose_gif(reply)
                )

                if gif:
                    await message.channel.send(gif)

        except Exception as e:
            await message.reply(
                f"❌ ai error:\n```{e}```",
                mention_author=False
            )

    await bot.process_commands(message)


#start the bot
bot.run(TOKEN)
