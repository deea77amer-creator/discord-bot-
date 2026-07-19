import discord
from discord.ext import commands
import os
import json
from flask import Flask
from threading import Thread

# --- إعداد خادم الويب (Render) ---
app = Flask('')
@app.route('/')
def home(): return "البوت يعمل بنجاح!"

def run_web(): app.run(host='0.0.0.0', port=10000)
def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- إعداد البوت ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "user_stats.json"
CONFIG_FILE = "server_config.json"

def load_data(file):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_data(data, file):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- الأحداث (Events) ---

@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول بنجاح باسم: {bot.user}")

@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    stats = load_data(DATA_FILE)
    if guild_id not in stats: stats[guild_id] = {}
    if user_id not in stats[guild_id]: stats[guild_id][user_id] = {"joins": 0, "leaves": 0}
    stats[guild_id][user_id]["joins"] += 1
    save_data(stats, DATA_FILE)

    config = load_data(CONFIG_FILE)
    if guild_id in config and "welcome_channel" in config[guild_id]:
        channel = member.guild.get_channel(config[guild_id]["welcome_channel"])
        if channel:
            embed = discord.Embed(
                title="أهلاً وسهلاً بك! 👋", 
                description=f"مرحباً بك {member.mention} في سيرفر **{member.guild.name}**!\nأنورت السيرفر 🎉", 
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    stats = load_data(DATA_FILE)
    if guild_id not in stats: stats[guild_id] = {}
    if user_id not in stats[guild_id]: stats[guild_id][user_id] = {"joins": 0, "leaves": 0}
    stats[guild_id][user_id]["leaves"] += 1
    save_data(stats, DATA_FILE)

# 📌 التقاط الرسائل العادية بدون رموز (! أو /)
@bot.event
async def on_message(message):
    # تجنب رد البوت على نفسه
    if message.author.bot:
        return

    text = message.content.strip().lower()

    # إذا كانت الكلمة هي "سجل" أو "السجل"
    if text in ["سجل", "السجل"]:
        guild_id = str(message.guild.id)
        config = load_data(CONFIG_FILE)
        allowed_channel = config.get(guild_id, {}).get("سجل_channel")

        # التحقق مما إذا كان تم تحديد قناة ومطابقتها
        if allowed_channel and message.channel.id != allowed_channel:
            channel_obj = message.guild.get_channel(allowed_channel)
            await message.channel.send(f"❌ كلمة السجل تعمل فقط في قناة {channel_obj.mention if channel_obj else 'القناة المخصصة'}.")
            return

        # عرض السجل
        target = message.author
        stats = load_data(DATA_FILE)
        user_stats = stats.get(guild_id, {}).get(str(target.id), {"joins": 0, "leaves": 0})
        
        embed = discord.Embed(title=f"📊 سجل: {target.display_name}", color=discord.Color.blue())
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="📥 مرات الدخول", value=f"**{user_stats['joins']}** مرة", inline=True)
        embed.add_field(name="📤 مرات الخروج", value=f"**{user_stats['leaves']}** مرة", inline=True)
        
        await message.channel.send(embed=embed)

    # معالجة الأوامر الإدارية إن وجدت
    await bot.process_commands(message)

# --- الأوامر الإدارية للتحديد فقط ---

@bot.command(name="ترحيب")
@commands.has_permissions(administrator=True)
async def set_welcome_channel(ctx):
    guild_id = str(ctx.guild.id)
    config = load_data(CONFIG_FILE)
    if guild_id not in config: config[guild_id] = {}
    config[guild_id]["welcome_channel"] = ctx.channel.id
    save_data(config, CONFIG_FILE)
    await ctx.send(f"✅ تم تحديد هذه القناة ({ctx.channel.mention}) للترحيب!")

@bot.command(name="حدد_سجل")
@commands.has_permissions(administrator=True)
async def set_stats_channel(ctx):
    config = load_data(CONFIG_FILE)
    guild_id = str(ctx.guild.id)
    if guild_id not in config: config[guild_id] = {}
    config[guild_id]["سجل_channel"] = ctx.channel.id
    save_data(config, CONFIG_FILE)
    await ctx.send(f"✅ تم تخصيص قناة السجل: {ctx.channel.mention}")

# --- تشغيل ---
keep_alive()
token = os.environ.get("DISCORD_TOKEN")
if token: bot.run(token)
