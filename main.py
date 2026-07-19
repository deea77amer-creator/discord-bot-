import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from flask import Flask
from threading import Thread

# --- إعداد خادم ويب وهمي لتبقي الاستضافة شغالة (Render) ---
app = Flask('')

@app.route('/')
def home():
    return "البوت يعمل بنجاح في الخلفية!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- إعداد البوت والبيانات ---
intents = discord.Intents.default()
intents.members = True          # تفعيل تتبع الأعضاء
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ملفات حفظ البيانات محلية
DATA_FILE = "user_stats.json"
CONFIG_FILE = "server_config.json"

def load_data(file):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data, file):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- الأحداث (Events) ---

@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول بنجاح باسم: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"تم مزامنة {len(synced)} أمر (Slash Commands)")
    except Exception as e:
        print(f"خطأ في المزامنة: {e}")

# 1️⃣ تتبع دخول الأعضاء + الترحيب
@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)

    # تحديث إحصائيات الدخول
    stats = load_data(DATA_FILE)
    if guild_id not in stats:
        stats[guild_id] = {}
    if user_id not in stats[guild_id]:
        stats[guild_id][user_id] = {"joins": 0, "leaves": 0}
    
    stats[guild_id][user_id]["joins"] += 1
    save_data(stats, DATA_FILE)

    # الترحيب بالعضو إذا تم تحديد قناة
    config = load_data(CONFIG_FILE)
    if guild_id in config and "welcome_channel" in config[guild_id]:
        channel_id = config[guild_id]["welcome_channel"]
        channel = member.guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title="أهلاً وسهلاً بك! 👋",
                description=f"مرحباً بك {member.mention} في سيرفر **{member.guild.name}**!\nأنورت السيرفر 🎉",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

# 2️⃣ تتبع خروج الأعضاء
@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)

    stats = load_data(DATA_FILE)
    if guild_id not in stats:
        stats[guild_id] = {}
    if user_id not in stats[guild_id]:
        stats[guild_id][user_id] = {"joins": 0, "leaves": 0}
    
    stats[guild_id][user_id]["leaves"] += 1
    save_data(stats, DATA_FILE)

# --- الأوامر (Slash Commands) ---

# 📌 1. أمر تحديد قناة الترحيب
@bot.tree.command(name="set_welcome", description="تحديد القناة الخاصة بالترحيب للأعضاء الجدد")
@app_commands.checks.has_permissions(administrator=True)
async def set_welcome(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild_id)
    config = load_data(CONFIG_FILE)
    
    if guild_id not in config:
        config[guild_id] = {}
    
    config[guild_id]["welcome_channel"] = channel.id
    save_data(config, CONFIG_FILE)

    await interaction.response.send_message(f"✅ تم تحديد قناة الترحيب بنجاح لتكون: {channel.mention}", ephemeral=True)

# 📌 2. أمر الاستعلام عن إحصائيات الدخول والخروج (/سجل)
@bot.tree.command(name="سجل", description="عرض سجل وعدد مرات دخول وخروج عضو من السيرفر")
async def check_stats(interaction: discord.Interaction, user: discord.Member = None):
    target_user = user or interaction.user
    guild_id = str(interaction.guild_id)
    user_id = str(target_user.id)

    stats = load_data(DATA_FILE)
    
    user_stats = stats.get(guild_id, {}).get(user_id, {"joins": 0, "leaves": 0})
    joins = user_stats["joins"]
    leaves = user_stats["leaves"]

    embed = discord.Embed(
        title=f"📊 سجل دخول وخروج: {target_user.display_name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)
    embed.add_field(name="📥 مرات الدخول", value=f"**{joins}** مرة", inline=True)
    embed.add_field(name="📤 مرات الخروج", value=f"**{leaves}** مرة", inline=True)

    await interaction.response.send_message(embed=embed)

# --- تشغيل خادم الويب والبوت ---
keep_alive()

token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("خطأ: لم يتم العثور على التوكين DISCORD_TOKEN في متغيرات البيئة!")
