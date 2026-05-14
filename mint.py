import discord
from discord.ext import commands
import sqlite3
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# DATABASE
# =========================
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


# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print("ERROR:", e)

    print(f"Logged in as {bot.user}")


# =========================
# /setuid
# =========================
@bot.tree.command(name="setuid", description="Save your UID")
async def setuid(interaction: discord.Interaction, uid: str):

    await interaction.response.defer(ephemeral=True)

    try:
        cursor.execute("""
        INSERT OR REPLACE INTO uids (user_id, uid, public)
        VALUES (?, ?, COALESCE((SELECT public FROM uids WHERE user_id=?), 0))
        """, (str(interaction.user.id), uid, str(interaction.user.id)))

        conn.commit()

        await interaction.followup.send(
            f"✅ UID saved: `{uid}`",
            ephemeral=True
        )

    except Exception as e:
        print("ERROR:", e)
        await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)


# =========================
# /setpublic
# =========================
@bot.tree.command(name="setpublic", description="Make your UID public or private")
async def setpublic(interaction: discord.Interaction, status: bool):

    await interaction.response.defer(ephemeral=True)

    try:
        cursor.execute("""
        UPDATE uids
        SET public = ?
        WHERE user_id = ?
        """, (1 if status else 0, str(interaction.user.id)))

        conn.commit()

        await interaction.followup.send(
            f"🔓 UID visibility set to `{status}`",
            ephemeral=True
        )

    except Exception as e:
        print("ERROR:", e)
        await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)


# =========================
# /myuid
# =========================
@bot.tree.command(name="myuid", description="View your UID")
async def myuid(interaction: discord.Interaction):

    await interaction.response.defer(ephemeral=True)

    try:
        cursor.execute("""
        SELECT uid FROM uids WHERE user_id=?
        """, (str(interaction.user.id),))

        result = cursor.fetchone()

        if result:
            await interaction.followup.send(
                f"📌 Your UID: `{result[0]}`",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ No UID found.",
                ephemeral=True
            )

    except Exception as e:
        print("ERROR:", e)
        await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)


# =========================
# /uid (view others if public)
# =========================
@bot.tree.command(name="uid", description="View another user's UID (if public)")
async def uid(interaction: discord.Interaction, user: discord.User):

    await interaction.response.defer(ephemeral=True)

    try:
        cursor.execute("""
        SELECT uid, public FROM uids WHERE user_id=?
        """, (str(user.id),))

        result = cursor.fetchone()

        if not result:
            return await interaction.followup.send(
                "❌ This user has no UID saved.",
                ephemeral=True
            )

        uid_value, public = result

        if public == 1:
            await interaction.followup.send(
                f"📌 {user.name}'s UID: `{uid_value}`",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "🔒 This user has hidden their UID.",
                ephemeral=True
            )

    except Exception as e:
        print("ERROR:", e)
        await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)


# =========================
# /removeuid
# =========================
@bot.tree.command(name="removeuid", description="Delete your UID")
async def removeuid(interaction: discord.Interaction):

    await interaction.response.defer(ephemeral=True)

    try:
        cursor.execute("""
        DELETE FROM uids WHERE user_id=?
        """, (str(interaction.user.id),))

        conn.commit()

        await interaction.followup.send(
            "🗑️ Your UID has been removed.",
            ephemeral=True
        )

    except Exception as e:
        print("ERROR:", e)
        await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)


# =========================
# RUN BOT
# =========================
bot.run(TOKEN)