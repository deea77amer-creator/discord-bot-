import os
import json
import asyncio
import discord
from discord.ext import commands
from datetime import datetime

# إعدادات البوت الأساسية
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
    print(f"تم تسجيل الدخول بنجاح باسم: {bot.user}")

# 1. نظام الترحيب المحترف بالأعضاء الجدد
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
                description=f"أهلاً ومرحباً بك يا {member.mention} في سيرفرنا!\n\n"
                            f"• نورتنا وشرفتنا بانضمامك إلينا ❤️\n"
                            f"• أنت العضو رقم **{member.guild.member_count}** في عائلتنا.\n"
                            f"• نتمنى لك أوقاتاً ممتعة ومفيدة معنا!",
                color=discord.Color.gold()
            )
            
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            
            if member.guild.banner:
                embed.set_image(url=member.guild.banner.url)
                
            embed.set_footer(text=f"ID: {member.id} | نظام الترحيب التلقائي", icon_url=member.guild.icon.url if member.guild.icon else None)
            embed.timestamp = datetime.now()

            await channel.send(content=f"حياك الله {member.mention} 🚀🎉", embed=embed)

# 2. أوامر الإدارة لتحديد قنوات الترحيب والألعاب
@bot.command(name="تحديد_الترحيب")
@commands.has_permissions(administrator=True)
async def set_welcome_channel(ctx):
    config = load_data(CONFIG_FILE)
    guild_id = str(ctx.guild.id)
    if guild_id not in config:
        config[guild_id] = {}
    config[guild_id]["allowed_channel"] = ctx.channel.id
    save_data(config, CONFIG_FILE)
    await ctx.send(f"✅ تم تحديد هذه القناة **للترحيب** بنجاح يا {ctx.author.mention}!")

@bot.command(name="تحديد_الألعاب")
@commands.has_permissions(administrator=True)
async def set_games_channel(ctx):
    config = load_data(CONFIG_FILE)
    guild_id = str(ctx.guild.id)
    if guild_id not in config:
        config[guild_id] = {}
    config[guild_id]["games_channel"] = ctx.channel.id
    save_data(config, CONFIG_FILE)
    await ctx.send(f"✅ تم تحديد هذه القناة **للألعاب** بنجاح يا {ctx.author.mention}!")

# 3. نظام الأوامر والألعاب بدون بريفكس (مع تقييد الألعاب بقناة الألعاب المحددة)
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip()
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    # التحقق مما إذا كانت القناة مخصصة للألعاب (إذا تم تحديدها مسبقاً)
    config = load_data(CONFIG_FILE)
    games_channel_id = config.get(guild_id, {}).get("games_channel")

    # أمر فحص النقاط (متاح في أي قناة أو تبي تخصصه براحتك)
    if text == "نقاطي":
        stats = load_data(DATA_FILE)
        points = stats.get(guild_id, {}).get(user_id, {}).get("points", 0)
        await message.channel.send(f"💰 رصيدك الحالي يا {message.author.mention} هو: **{points}** نقطة!")

    # ألعاب التحدي والحساب (تشتغل حصرياً في قناة الألعاب المحددة، وإذا ما حدد قناة تشتغل بكل الرومات كحماية)
    elif text in ["تحدي", "حساب"]:
        if games_channel_id and message.channel.id != games_channel_id:
            await message.delete() # حذف رسالة الخطأ عشان ما تخرب الشات
            warning = await message.channel.send(f"❌ عذراً {message.author.mention}, ألعاب البوت مخصصة فقط في قناة الألعاب المحددة!")
            await asyncio.sleep(5)
            await warning.delete()
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
                await message.channel.send("⏰ انتهى الوقت! محد كتب الكلمة في الوقت المناسب.")
            else:
                g_id = str(msg.guild.id)
                u_id = str(msg.author.id)
                
                stats = load_data(DATA_FILE)
                if g_id not in stats:
                    stats[g_id] = {}
                if u_id not in stats[g_id]:
                    stats[g_id][u_id] = {"joins": 0, "leaves": 0, "points": 0}
                if "points" not in stats[g_id][u_id]:
                    stats[g_id][u_id]["points"] = 0
                    
                stats[g_id][u_id]["points"] += 50
                save_data(stats, DATA_FILE)
                
                await message.channel.send(f"🏆 مبروك يا {msg.author.mention}! فزت بالتحدي وربحت **50 نقطة**!")

        elif text == "حساب":
            import random
            num1 = random.randint(1, 20)
            num2 = random.randint(1, 20)
            operator = random.choice(["+", "-"])
            answer = num1 + num2 if operator == "+" else num1 - num2
                
            await message.channel.send(f"🧮 **لعبة الحساب السريع!** أسرع شخص يكتب الناتج الصحيح:\nكم الناتج؟ `{num1} {operator} {num2} = ?` (معك 15 ثانية وربحك 30 نقطة)")

            def check(m):
                return m.content.isdigit() and int(m.content) == answer and m.channel == message.channel and not m.author.bot

            try:
                msg = await bot.wait_for('message', timeout=15.0, check=check)
            except asyncio.TimeoutError:
                await message.channel.send(f"⏰ انتهى الوقت! الإجابة الصحيحة كانت: **{answer}**")
            else:
                g_id = str(msg.guild.id)
                u_id = str(msg.author.id)
                
                stats = load_data(DATA_FILE)
                if g_id not in stats:
                    stats[g_id] = {}
                if u_id not in stats[g_id]:
                    stats[g_id][u_id] = {"joins": 0, "leaves": 0, "points": 0}
                if "points" not in stats[g_id][u_id]:
                    stats[g_id][u_id]["points"] = 0
                    
                stats[g_id][u_id]["points"] += 30
                save_data(stats, DATA_FILE)
                
                await message.channel.send(f"🏆 بطل الرياضيات يا {msg.author.mention}! وربح **30 نقطة**!")

    await bot.process_commands(message)

# تشغيل البوت
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("خطأ: لم يتم العثور على DISCORD_TOKEN في متغيرات البيئة!")
