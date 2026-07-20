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

# نظام الترحيب التلقائي بالأعضاء الجدد
@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    config = load_data(CONFIG_FILE)
    
    if guild_id in config and "allowed_channel" in config[guild_id]:
        channel_id = config[guild_id]["allowed_channel"]
        channel = member.guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title="✨ | نورت السيرفر!",
                description=f"أهلاً بك يا {member.mention} معنا في العائلة!",
                color=discord.Color.gold()
            )
            await channel.send(content=f"حياك الله {member.mention} 🚀", embed=embed)

# أمر لتحديد قناة الترحيب
@bot.command(name="تحديد_الترحيب")
@commands.has_permissions(administrator=True)
async def set_welcome(ctx):
    config = load_data(CONFIG_FILE)
    guild_id = str(ctx.guild.id)
    if guild_id not in config:
        config[guild_id] = {}
    config[guild_id]["allowed_channel"] = ctx.channel.id
    save_data(config, CONFIG_FILE)
    await ctx.send("✅ تم تعيين هذه القناة للترحيب بنجاح!")

# نظام الألعاب والأوامر النصية بدون بريفكس
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip()
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    # 1. فحص النقاط
    if text == "نقاطي":
        stats = load_data(DATA_FILE)
        points = stats.get(guild_id, {}).get(user_id, {}).get("points", 0)
        await message.channel.send(f"💰 رصيدك الحالي يا {message.author.mention}: **{points}** نقطة.")

    # 2. لعبة تحدي الكلمات
    elif text == "تحدي":
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
            if g_id not in stats:
                stats[g_id] = {}
            if u_id not in stats[g_id]:
                stats[g_id][u_id] = {"points": 0}
            if "points" not in stats[g_id][u_id]:
                stats[g_id][u_id]["points"] = 0
                
            stats[g_id][u_id]["points"] += 50
            save_data(stats, DATA_FILE)
            
            await message.channel.send(f"🏆 مبروك يا {msg.author.mention}! فزت بـ **50 نقطة**!")

    # 3. لعبة الحساب السريع
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
            if g_id not in stats:
                stats[g_id] = {}
            if u_id not in stats[g_id]:
                stats[g_id][u_id] = {"points": 0}
            if "points" not in stats[g_id][u_id]:
                stats[g_id][u_id]["points"] = 0
                
            stats[g_id][u_id]["points"] += 30
            save_data(stats, DATA_FILE)
            
            await message.channel.send(f"🏆 بطل الرياضيات يا {msg.author.mention}! ربحت **30 نقطة**!")

    # ضروري جداً عشان أوامر الـ Prefix (مثل !تحديد_الترحيب) تشتغل
    await bot.process_commands(message)

# تشغيل البوت
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("خطأ: التوكن غير موجود!")
