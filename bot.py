import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
import os
import pytz
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

WIB = pytz.timezone("Asia/Jakarta")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

active_reminders = {}
reminder_channel = {}
voice_sessions = {}
MAX_ACTIVE_VOICE = 2


# ================= SET CHANNEL =================
@bot.tree.command(name="setchannel", description="Set channel khusus reminder")
async def setchannel(interaction: discord.Interaction):

    reminder_channel[interaction.guild.id] = interaction.channel.id

    await interaction.response.send_message(
        "✅ Channel reminder berhasil diset di sini!"
    )


# ================= STOP =================
def stop_reminder(user_id):
    if user_id in active_reminders:
        active_reminders[user_id]["active"] = False


# ================= PLAY ALARM =================
async def play_alarm(member, level):

    if not member.voice:
        return

    if len(voice_sessions) >= MAX_ACTIVE_VOICE:
        return

    vc = await member.voice.channel.connect()
    voice_sessions[member.id] = vc

    loop_count = 1
    if level == "sadis":
        loop_count = 3
    elif level == "kiamat":
        loop_count = 10

    for _ in range(loop_count):

        if not active_reminders.get(member.id, {}).get("active"):
            break

        source = discord.FFmpegPCMAudio(
            executable="C:/ffmpeg/bin/ffmpeg.exe",
            source="alarm.mp3"
        )

        vc.play(source)

        while vc.is_playing():
            await asyncio.sleep(1)

    await vc.disconnect()
    voice_sessions.pop(member.id, None)


# ================= REMINDER TASK =================
async def reminder_task(guild_id, user_id, task_name, target_time, level):

    now = datetime.datetime.now(WIB)
    delay = (target_time - now).total_seconds()

    if delay > 0:
        await asyncio.sleep(delay)

    if not active_reminders.get(user_id, {}).get("active"):
        return

    guild = bot.get_guild(guild_id)
    member = guild.get_member(user_id)

    channel_id = reminder_channel.get(guild_id)
    if not channel_id:
        return

    channel = bot.get_channel(channel_id)

    await channel.send(
        f"""
━━━━━━━━━━━━━━━━━━
🚨 DEADLINE TIBA 🚨
━━━━━━━━━━━━━━━━━━
👤 <@{user_id}>
📌 Tugas: **{task_name}**
━━━━━━━━━━━━━━━━━━
"""
    )

    if member and member.voice:
        await play_alarm(member, level)

    if level in ["sadis", "kiamat"]:

        repeat = 3 if level == "sadis" else 10

        for i in range(repeat):

            if not active_reminders.get(user_id, {}).get("active"):
                break

            await asyncio.sleep(60)

            await channel.send(
                f"<@{user_id}> ⏰ {i+1} menit lewat buat **{task_name}**!"
            )


# ================= REMIND COMMAND =================
@bot.tree.command(name="remind", description="Bikin reminder tugas")
@app_commands.describe(
    tugas="Nama tugas",
    tanggal="Format: YYYY-MM-DD",
    jam="Format: HH:MM (WIB)",
    level="normal / sadis / kiamat"
)
async def remind(interaction: discord.Interaction,
                 tugas: str,
                 tanggal: str,
                 jam: str,
                 level: str):

    await interaction.response.defer()

    if interaction.guild.id not in reminder_channel:
        await interaction.followup.send("❌ Owner belum set channel reminder pakai /setchannel")
        return

    try:
        naive = datetime.datetime.strptime(f"{tanggal} {jam}", "%Y-%m-%d %H:%M")
        target_time = WIB.localize(naive)
    except:
        await interaction.followup.send("❌ Format salah.")
        return

    active_reminders[interaction.user.id] = {"active": True}

    bot.loop.create_task(
        reminder_task(
            interaction.guild.id,
            interaction.user.id,
            tugas,
            target_time,
            level
        )
    )

    await interaction.followup.send(
        f"""
━━━━━━━━━━━━━━━━━━
✅ REMINDER AKTIF
━━━━━━━━━━━━━━━━━━
📌 {tugas}
🗓 {tanggal}
⏰ {jam} WIB
🔥 Mode: {level}
━━━━━━━━━━━━━━━━━━
"""
    )


# ================= DONE =================
@bot.tree.command(name="done", description="Stop reminder")
async def done(interaction: discord.Interaction):

    stop_reminder(interaction.user.id)

    await interaction.response.send_message("✅ Reminder dihentikan.")


# ================= AUTO STOP IF CHAT =================
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.author.id in active_reminders:
        stop_reminder(message.author.id)

    await bot.process_commands(message)


# ================= READY =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🔥 Bot login sebagai {bot.user}")


bot.run(TOKEN)
