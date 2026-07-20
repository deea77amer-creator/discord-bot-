import os
import json
import discord
from discord.ext import commands

# إعداد البوت والـ Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# أسماء ملفات حفظ البيانات
DATA_FILE = "user_stats.json"
CONFIG_FILE = "config.json"

def load_data(file_name):
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_data(data, file_name):
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول بنجاح باسم: {bot.user.name}")

# تحديد القناة التي يستجيب فيها البوت عبر الأمر !حدد_سجل
@bot.command(name="حدد_سجل")
@commands.has_permissions(administrator=True)
async def set_log_channel(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    guild_id = str(ctx.guild.id)
    
    config = load_data(CONFIG_FILE)
    if guild_id not in config:
        config[guild_id] = {}
    
    config[guild_id]["allowed_channel"] = channel.id
    save_data(config, CONFIG_FILE)
    
    await ctx.send(f"✅ تم تحديد القناة {channel.mention} لتلقي أسباب الترحيب وأوامر السجل.")

# تتبع دخول الاعضاء + إرسال الترحيب
@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    
    # 1. تحديث الإحصائيات
    stats = load_data(DATA_FILE)
    if guild_id not in stats:
        stats[guild_id] = {}
    if user_id not in stats[guild_id]:
        stats[guild_id][user_id] = {"joins": 0, "leaves": 0}
        
    stats[guild_id][user_id]["joins"] += 1
    save_data(stats, DATA_FILE)

    # 2. إرسال رسالة الترحيب في القناة المحددة
    config = load_data(CONFIG_FILE)
    if guild_id in config and "allowed_channel" in config[guild_id]:
        channel_id = config[guild_id]["allowed_channel"]
        channel = member.guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title=f"👋 أهلاً وسهلاً بك يا {member.display_name}!",
                description=f"أنورت السيرفر بنضمامك معنا! ❤️\nأنت العضو رقم **{member.guild.member_count}** في السيرفر.",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

# تتبع خروج الاعضاء
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

# التقاط رسائل "سجل" أو "السجل" مع دعم المنشن
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip().lower()

    if text.startswith("سجل") or text.startswith("السجل"):
        guild_id = str(message.guild.id)
        config = load_data(CONFIG_FILE)
        allowed_channel = config.get(guild_id, {}).get("allowed_channel")

        # التأكد من القناة المحددة
        if allowed_channel and message.channel.id != allowed_channel:
            return

        stats = load_data(DATA_FILE)

        # 1. إذا كان فيه منشن لشخص آخر
        if message.mentions:
            target_user = message.mentions[0]
            target_id = str(target_user.id)
            
            user_data = stats.get(guild_id, {}).get(target_id, {"joins": 0, "leaves": 0})
            joins = user_data.get("joins", 0)
            leaves = user_data.get("leaves", 0)

            embed = discord.Embed(
                title=f"📊 سجل دخول وخروج: {target_user.display_name}",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            embed.add_field(name="📥 مرات الدخول", value=f"**{joins}**", inline=True)
            embed.add_field(name="📤 مرات الخروج", value=f"**{leaves}**", inline=True)
            
            await message.channel.send(embed=embed)

        # 2. إذا كتب "سجل" فقط ليعرض سجله الخاص
        elif text in ["سجل", "السجل"]:
            user_id = str(message.author.id)
            
            user_data = stats.get(guild_id, {}).get(user_id, {"joins": 0, "leaves": 0})
            joins = user_data.get("joins", 0)
            leaves = user_data.get("leaves", 0)

            embed = discord.Embed(
                title=f"📊 سجل دخولك وخروجك يا {message.author.display_name}",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.add_field(name="📥 مرات الدخول", value=f"**{joins}**", inline=True)
            embed.add_field(name="📤 مرات الخروج", value=f"**{leaves}**", inline=True)

            await message.channel.send(embed=embed)

    await bot.process_commands(message)

# تشغيل البوت باستخدام التوكن من الـ Environment Variable
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("خطأ: لم يتم العثور على DISCORD_TOKEN في متغيرات البيئة!")
