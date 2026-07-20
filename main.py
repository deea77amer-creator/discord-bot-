import os
import json
import asyncio
import discord
from discord.ext import commands
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "stats.json"
CONFIG_FILE = "config.json"

def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_data(data, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@bot.event
async def on_ready():
    print(f"البوت جاهز وشغال باسم: {bot.user}")

# 1. نظام تسجيل الدخول (الترحيب بالأعضاء الجدد)
@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    
    stats = load_data(DATA_FILE)
    if guild_id not in stats:
        stats[guild_id] = {}
    if user_id not in stats[guild_id]:
        stats[guild_id][user_id] = {"joins": 0, "leaves": 0, "points": 0}
    stats[guild_id][user_id]["joins"] += 1
    save_data(stats, DATA_FILE)

    config = load_data(CONFIG_FILE)
    if guild_id in config and "allowed_channel" in config[guild_id]:
        channel_id = config[guild_id]["allowed_channel"]
        channel = member.guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title="✨ | وعاد النور إلى السيرفر!",
                description=f"أهلاً ومرحباً بك يا {member.mention} في عائلتنا!\n• أنت العضو رقم **{member.guild.member_count}**",
                color=discord.Color.gold()
            )
            await channel.send(content=f"حياك الله {member.mention} 🚀", embed=embed)

# 2. نظام تسجيل الخروج (عند مغادرة أحد السيرفر)
@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    
    stats = load_data(DATA_FILE)
    if guild_id not in stats:
        stats[guild_id] = {}
    if user_id not in stats[guild_id]:
        stats[guild_id][user_id] = {"joins": 0, "leaves": 0, "points": 0}
    stats[guild_id][user_id]["leaves"] += 1
    save_data(stats, DATA_FILE)

    config = load_data(CONFIG_FILE)
    # تقدر تخلي الخروج يروح لنفس قناة الترحيب أو قناة مخصصة لو حبيت
    if guild_id in config and "allowed_channel" in config[guild_id]:
        channel_id = config[guild_id]["allowed_channel"]
        channel = member.guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title="👋 | طير من الطيور غادرنا!",
                description=f"العضو **{member.name}** طلع من السيرفر. نتمنى له التوفيق!",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)

# 3. أوامر الإدارة لتحديد القنوات
@bot.command(name="تحديد_الترحيب")
@commands.has_permissions(administrator=True)
async def set_welcome(ctx):
    config = load_data(CONFIG_FILE)
    guild_id = str(ctx.guild.id)
    if guild_id not in config:
        config[guild_id] = {}
    config[guild_id]["allowed_channel"] = ctx.channel.id
    save_data(config, CONFIG_FILE)
    await ctx.send("✅ تم تعيين هذه القناة للترحيب وتسجيل الخروج بنجاح!")

@bot.command(name="تحديد_الألعاب")
@commands.has_permissions(administrator=True)
async def set_games(ctx):
    config = load_data(CONFIG_FILE)
    guild_id = str(ctx.guild.id)
    if guild_id not in config:
        config[guild_id] = {}
    config[guild_id]["games_channel"] = ctx.channel.id
    save_data(config, CONFIG_FILE)
    await ctx.send("✅ تم تعيين هذه القناة للألعاب بنجاح!")

# 4. نظام الألعاب والأوامر النصية
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip()
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    if text == "نقاطي":
        stats = load_data(DATA_FILE)
        points = stats.get(guild_id, {}).get(user_id, {}).get("points", 0)
        await message.channel.send(f"💰 رصيدك الحالي يا {message.author.mention}: **{points}** نقطة.")

    elif text in ["تحدي", "حساب"]:
        config = load_data(CONFIG_FILE)
        games_channel_id = config.get(guild_id, {}).get("games_channel")
        
        # لو فيه قناة ألعاب محددة، يمنع لعبها بربروم تاني
        if games_channel_id and message.channel.id != games_channel_id:
            await message.delete()
            warn = await message.channel.send(f"❌ عذراً {message.author.mention}, الألعاب مخصصة فقط في قناة الألعاب!")
            await asyncio.sleep(4)
            await warn.delete()
            return

        if text == "تحدي":
            import random
            words = ["ديسكورد", "برمجة", "بايثون", "سيرفر", "تحدي", "سرعة"]
            target_word = random.choice(words)
            await message.channel.send(f"🎮 **لعبة السرعة!** أسرع شخص يكتب الكلمة التالية يربح 50 نقطة:\n`{target_word}`")

            def check(m):
                return m.content == target_word and m.channel == message.channel and not m.author.bot

            try:
                msg = await bot.wait_for('message', timeout=15.0, check=check)
            except asyncio.TimeoutError:
                await message.channel.send("⏰ انتهى الوقت!")
            else:
                g_id = str(msg.guild.id)
                u_id = str(msg.author.id)
                stats = load_data(DATA_FILE)
                if g_id not in stats: stats[g_id] = {}
                if u_id not in stats[g_id]: stats[g_id][u_id] = {"joins": 0, "leaves": 0, "points": 0}
                if "points" not in stats[g_id][u_id]: stats[g_id][u_id]["points"] = 0
                stats[g_id][u_id]["points"] += 50
                save_data(stats, DATA_FILE)
                await message.channel.send(f"🏆 مبروك يا {msg.author.mention}! ربحت **50 نقطة**!")

        elif text == "حساب":
            import random
            num1 = random.randint(1, 10)
            num2 = random.randint(1, 10)
            answer = num1 + num2
            await message.channel.send(f"🧮 أسرع شخص يحل العملية:\n`{num1} + {num2} = ?` (معك 15 ثانية وربحك 30 نقطة)")

            def check(m):
                return m.content.isdigit() and int(m.content) == answer and m.channel == message.channel and not m.author.bot

            try:
                msg = await bot.wait_for('message', timeout=15.0, check=check)
            except asyncio.TimeoutError:
                await message.channel.send(f"⏰ انتهى الوقت! الإجابة كانت: **{answer}**")
            else:
                g_id = str(msg.guild.id)
                u_id = str(msg.author.id)
                stats = load_data(DATA_FILE)
                if g_id not in stats: stats[g_id] = {}
                if u_id not in stats[g_id]: stats[g_id][u_id] = {"joins": 0, "leaves": 0, "points": 0}
                if "points" not in stats[g_id][u_id]: stats[g_id][u_id]["points"] = 0
                stats[g_id][u_id]["points"] += 30
                save_data(stats, DATA_FILE)
                await message.channel.send(f"🏆 بطل الرياضيات يا {msg.author.mention}! ربحت **30 نقطة**!")

    await bot.process_commands(message)

token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("خطأ: التوكن غير موجود!")
