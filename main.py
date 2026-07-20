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

# 1. نظام الترحيب عند دخول السيرفر (Embed فخم)
@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    
    stats = load_data(DATA_FILE)
    if guild_id not in stats: stats[guild_id] = {}
    if user_id not in stats[guild_id]: 
        stats[guild_id][user_id] = {"joins": 0, "leaves": 0, "points": 0, "last_checkin": ""}
        
    stats[guild_id][user_id]["joins"] += 1
    save_data(stats, DATA_FILE)

    config = load_data(CONFIG_FILE)
    if guild_id in config and "welcome_channel" in config[guild_id]:
        channel_id = config[guild_id]["welcome_channel"]
        channel = member.guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title="✨ | وعاد النور إلى السيرفر!",
                description=f"أهلاً ومرحباً بك يا {member.mention} في عائلتنا!\n"
                            f"• أنت العضو رقم **{member.guild.member_count}**\n"
                            f"• عدد مرات دخولك للسيرفر: **{stats[guild_id][user_id]['joins']}** مرة",
                color=discord.Color.gold()
            )
            await channel.send(content=f"حياك الله {member.mention} 🚀", embed=embed)

# 2. نظام تسجيل المغادرة عند الخروج من السيرفر
@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    
    stats = load_data(DATA_FILE)
    if guild_id not in stats: stats[guild_id] = {}
    if user_id not in stats[guild_id]: 
        stats[guild_id][user_id] = {"joins": 0, "leaves": 0, "points": 0, "last_checkin": ""}
        
    stats[guild_id][user_id]["leaves"] += 1
    save_data(stats, DATA_FILE)

    config = load_data(CONFIG_FILE)
    if guild_id in config and "leave_channel" in config[guild_id]:
        channel_id = config[guild_id]["leave_channel"]
        channel = member.guild.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title="👋 | طير من الطيور غادرنا!",
                description=f"العضو **{member.name}** طلع من السيرفر.\n"
                            f"• إجمالي مرات خروجه: **{stats[guild_id][user_id]['leaves']}** مرة",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)

# 3. أوامر الإدارة لتحديد القنوات (تكتب برمز !)
@bot.command(name="تحديد_الترحيب")
@commands.has_permissions(administrator=True)
async def set_welcome(ctx):
    config = load_data(CONFIG_FILE)
    guild_id = str(ctx.guild.id)
    if guild_id not in config: config[guild_id] = {}
    config[guild_id]["welcome_channel"] = ctx.channel.id
    save_data(config, CONFIG_FILE)
    await ctx.send("✅ تم تعيين هذه القناة **للترحيب** بنجاح!")

@bot.command(name="تحديد_الخروج")
@commands.has_permissions(administrator=True)
async def set_leave(ctx):
    config = load_data(CONFIG_FILE)
    guild_id = str(ctx.guild.id)
    if guild_id not in config: config[guild_id] = {}
    config[guild_id]["leave_channel"] = ctx.channel.id
    save_data(config, CONFIG_FILE)
    await ctx.send("✅ تم تعيين هذه القناة **للخروج** بنجاح!")

@bot.command(name="تحديد_الألعاب")
@commands.has_permissions(administrator=True)
async def set_games(ctx):
    config = load_data(CONFIG_FILE)
    guild_id = str(ctx.guild.id)
    if guild_id not in config: config[guild_id] = {}
    config[guild_id]["games_channel"] = ctx.channel.id
    save_data(config, CONFIG_FILE)
    await ctx.send("✅ تم تعيين هذه القناة **للألعاب** بنجاح!")

@bot.command(name="تحديد_السجلات")
@commands.has_permissions(administrator=True)
async def set_records(ctx):
    config = load_data(CONFIG_FILE)
    guild_id = str(ctx.guild.id)
    if guild_id not in config: config[guild_id] = {}
    config[guild_id]["records_channel"] = ctx.channel.id
    save_data(config, CONFIG_FILE)
    await ctx.send("✅ تم تعيين هذه القناة **لسجلات الدخول اليومي** بنجاح!")

# 4. الأوامر التفاعلية الكاملة (بدون أي رموز)
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip()
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    # أ. أمر تسجيل الحضور اليومي (دخول) وأمر السجل (مقيدين بقناة السجلات المحددة)
    if text in ["دخول", "سجل"]:
        config = load_data(CONFIG_FILE)
        records_channel_id = config.get(guild_id, {}).get("records_channel")
        
        if records_channel_id and message.channel.id != records_channel_id:
            await message.delete()
            warn = await message.channel.send(f"❌ عذراً {message.author.mention}, أوامر السجلات مخصصة فقط في قناة السجلات!")
            await asyncio.sleep(4)
            await warn.delete()
            return

        if text == "دخول":
            today_date = datetime.now().strftime("%Y-%m-%d")
            stats = load_data(DATA_FILE)
            
            if guild_id not in stats: stats[guild_id] = {}
            if user_id not in stats[guild_id]: 
                stats[guild_id][user_id] = {"joins": 0, "leaves": 0, "points": 0, "last_checkin": "", "checkins_count": 0}
            
            if "checkins_count" not in stats[guild_id][user_id]:
                stats[guild_id][user_id]["checkins_count"] = 0

            # التحقق إذا سجل حضور اليوم من قبل
            if stats[guild_id][user_id].get("last_checkin") == today_date:
                await message.channel.send(f"⚠️ يا {message.author.mention}، أنت سجلت دخولك اليوم بالفعل!")
            else:
                stats[guild_id][user_id]["last_checkin"] = today_date
                stats[guild_id][user_id]["checkins_count"] += 1
                save_data(stats, DATA_FILE)
                
                count = stats[guild_id][user_id]["checkins_count"]
                await message.channel.send(f"📥 **تم تسجيل الدخول اليومي**\nأهلاً بك يا {message.author.mention}! تم تسجيل حضورك اليوم بنجاح.\nإجمالي مرات الدخول: **{count}**")

        elif text == "سجل":
            stats = load_data(DATA_FILE)
            user_data = stats.get(guild_id, {}).get(user_id, {"joins": 0, "leaves": 0, "points": 0, "checkins_count": 0})
            
            embed = discord.Embed(
                title=f"📊 سجل دخولك وخروجوك يا {message.author.display_name}",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.add_field(name="📥 مرات الدخول", value=f"**{user_data.get('checkins_count', user_data.get('joins', 0))}**", inline=False)
            embed.add_field(name="📤 مرات الخروج", value=f"**{user_data.get('leaves', 0)}**", inline=False)
            
            await message.channel.send(embed=embed)

    # ب. فحص النقاط
    elif text == "نقاطي":
        stats = load_data(DATA_FILE)
        points = stats.get(guild_id, {}).get(user_id, {}).get("points", 0)
        await message.channel.send(f"💰 رصيدك الحالي يا {message.author.mention}: **{points}** نقطة.")

    # ج. ألعاب التحدي والحساب
    elif text in ["تحدي", "حساب"]:
        config = load_data(CONFIG_FILE)
        games_channel_id = config.get(guild_id, {}).get("games_channel")
        
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
