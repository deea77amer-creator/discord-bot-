import os
import json
import asyncio
import discord
from discord.ext import commands
from datetime import datetime
from flask import Flask
from threading import Thread
import random

# --- إعداد سيرفر الـ Flask الوهمي لمنع مشكلة Port Timeout على Render ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------------------

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

def add_points(guild_id, user_id, amount):
    stats = load_data(DATA_FILE)
    g_id = str(guild_id)
    u_id = str(user_id)
    if g_id not in stats: stats[g_id] = {}
    if u_id not in stats[g_id]: 
        stats[g_id][u_id] = {"joins": 0, "leaves": 0, "points": 0}
    if "points" not in stats[g_id][u_id]: 
        stats[g_id][u_id]["points"] = 0
    
    stats[g_id][u_id]["points"] += amount
    save_data(stats, DATA_FILE)
    return stats[g_id][u_id]["points"]

@bot.event
async def on_ready():
    print(f"البوت جاهز وشغال باسم: {bot.user}")

# 1. نظام الترحيب عند دخول السيرفر
@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    
    stats = load_data(DATA_FILE)
    if guild_id not in stats: stats[guild_id] = {}
    if user_id not in stats[guild_id]: 
        stats[guild_id][user_id] = {"joins": 0, "leaves": 0, "points": 0, "last_checkin": "", "checkins_count": 0, "last_leave": "", "manual_leaves_count": 0}
        
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

# 2. نظام تسجيل المغادرة التلقائي عند الخروج الفعلي من السيرفر
@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    
    stats = load_data(DATA_FILE)
    if guild_id not in stats: stats[guild_id] = {}
    if user_id not in stats[guild_id]: 
        stats[guild_id][user_id] = {"joins": 0, "leaves": 0, "points": 0, "last_checkin": "", "checkins_count": 0, "last_leave": "", "manual_leaves_count": 0}
        
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

# 3. أوامر الإدارة لتحديد القنوات بدقة
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
    await ctx.send("✅ تم تعيين هذه القناة **لسجلات الحضور** بنجاح!")

# دالة إرسال قائمة الـ 15 لعبة
async def send_games_menu(channel):
    embed = discord.Embed(
        title="🎮 | قائمة ألعاب السيرفر الكبرى (15 لعبة)",
        description="جميع الألعاب تعمل **بدون رموز** مباشرة في الشات المخصص للألعاب:\n",
        color=discord.Color.blue()
    )
    embed.add_field(name="1. 🎡 عجلة الحظ", value="اكتب: `عجلة`", inline=True)
    embed.add_field(name="2. 🎲 تحدي النرد", value="اكتب: `نرد`", inline=True)
    embed.add_field(name="3. 📦 فتح الصناديق", value="اكتب: `صناديق`", inline=True)
    embed.add_field(name="4. ✂️ حجر ورقة مقص", value="اكتب: `مقص حجر`", inline=True)
    embed.add_field(name="5. 🎯 التخمين الرقمي", value="اكتب: `تخمين [1-10]`", inline=True)
    embed.add_field(name="6. 🔮 حظك اليوم", value="اكتب: `حظك`", inline=True)
    embed.add_field(name="7. ⚡ لعبة السرعة", value="اكتب: `تحدي`", inline=True)
    embed.add_field(name="8. 🧮 لعبة الحساب", value="اكتب: `حساب`", inline=True)
    embed.add_field(name="9. 🏴‍☠️ كنز الموت", value="اكتب: `كنز`", inline=True)
    embed.add_field(name="10. ⚽ ضربة جزاء", value="اكتب: `بلنتي`", inline=True)
    embed.add_field(name="11. 🏀 سلة", value="اكتب: `سلة`", inline=True)
    embed.add_field(name="12. 🐟 صيد السمك", value="اكتب: `صيد`", inline=True)
    embed.add_field(name="13. 🏎️ سباق السيارات", value="اكتب: `سباق`", inline=True)
    embed.add_field(name="14. ⛏️ التنقيب", value="اكتب: `تعدين`", inline=True)
    embed.add_field(name="15. 🗡️ المبارزة", value="اكتب: `مبارزة`", inline=True)
    embed.set_footer(text="استمتع باللعب واجمع أكبر عدد من النقاط!")
    await channel.send(embed=embed)

# 4. الأوامر التفاعلية (بدون رموز)
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    text = message.content.strip()
    text_lower = text.lower()
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    # أ. أمر الدخول
    if text_lower == "دخول":
        config = load_data(CONFIG_FILE)
        records_channel_id = config.get(guild_id, {}).get("records_channel")
        
        if records_channel_id and message.channel.id != records_channel_id:
            await message.delete()
            warn = await message.channel.send(f"❌ عذراً {message.author.mention}, هذا الأمر مخصص فقط في قناة السجلات!")
            await asyncio.sleep(4)
            await warn.delete()
            return

        today_date = datetime.now().strftime("%Y-%m-%d")
        stats = load_data(DATA_FILE)
        
        if guild_id not in stats: stats[guild_id] = {}
        if user_id not in stats[guild_id]: 
            stats[guild_id][user_id] = {"joins": 0, "leaves": 0, "points": 0, "last_checkin": "", "checkins_count": 0, "last_leave": "", "manual_leaves_count": 0}
        
        if "checkins_count" not in stats[guild_id][user_id]:
            stats[guild_id][user_id]["checkins_count"] = 0

        if stats[guild_id][user_id].get("last_checkin") == today_date:
            await message.channel.send(f"⚠️ يا {message.author.mention}، أنت سجلت دخولك اليوم بالفعل!")
        else:
            stats[guild_id][user_id]["last_checkin"] = today_date
            stats[guild_id][user_id]["checkins_count"] += 1
            save_data(stats, DATA_FILE)
            
            count = stats[guild_id][user_id]["checkins_count"]
            await message.channel.send(f"📥 **تم تسجيل الدخول اليومي**\nأهلاً بك يا {message.author.mention}! تم تسجيل حضورك اليوم بنجاح.\nإجمالي مرات الدخول: **{count}**")

    # ب. أمر الخروج اليدوي
    elif text_lower == "خروج":
        config = load_data(CONFIG_FILE)
        records_channel_id = config.get(guild_id, {}).get("records_channel")
        
        if records_channel_id and message.channel.id != records_channel_id:
            await message.delete()
            warn = await message.channel.send(f"❌ عذراً {message.author.mention}, هذا الأمر مخصص فقط في قناة السجلات!")
            await asyncio.sleep(4)
            await warn.delete()
            return

        today_date = datetime.now().strftime("%Y-%m-%d")
        stats = load_data(DATA_FILE)
        
        if guild_id not in stats: stats[guild_id] = {}
        if user_id not in stats[guild_id]: 
            stats[guild_id][user_id] = {"joins": 0, "leaves": 0, "points": 0, "last_checkin": "", "checkins_count": 0, "last_leave": "", "manual_leaves_count": 0}
        
        if "manual_leaves_count" not in stats[guild_id][user_id]:
            stats[guild_id][user_id]["manual_leaves_count"] = 0

        if stats[guild_id][user_id].get("last_leave") == today_date:
            await message.channel.send(f"⚠️ يا {message.author.mention}، أنت سجلت خروجك اليوم بالفعل!")
        else:
            stats[guild_id][user_id]["last_leave"] = today_date
            stats[guild_id][user_id]["manual_leaves_count"] += 1
            save_data(stats, DATA_FILE)
            
            leave_count = stats[guild_id][user_id]["manual_leaves_count"]
            await message.channel.send(f"📤 **تم تسجيل الخروج اليومي**\nمع السلامة يا {message.author.mention}! تم تسجيل خروجك اليوم بنجاح.\nإجمالي مرات الخروج: **{leave_count}**")

    # ج. أمر السجل (مع دعم المنشن)
    elif text_lower.startswith("سجل"):
        config = load_data(CONFIG_FILE)
        records_channel_id = config.get(guild_id, {}).get("records_channel")
        
        if records_channel_id and message.channel.id != records_channel_id:
            await message.delete()
            warn = await message.channel.send(f"❌ عذراً {message.author.mention}, هذا الأمر مخصص فقط في قناة السجلات!")
            await asyncio.sleep(4)
            await warn.delete()
            return

        target_user = message.mentions[0] if message.mentions else message.author
        target_id = str(target_user.id)

        stats = load_data(DATA_FILE)
        user_data = stats.get(guild_id, {}).get(target_id, {"joins": 0, "leaves": 0, "points": 0, "checkins_count": 0, "manual_leaves_count": 0})
        
        checkins = user_data.get('checkins_count', 0)
        manual_leaves = user_data.get('manual_leaves_count', 0)
        
        embed = discord.Embed(
            title=f"📊 سجل دخول وخروج العضو {target_user.display_name}",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="📥 مرات الدخول", value=f"**{checkins}**", inline=False)
        embed.add_field(name="📤 مرات الخروج", value=f"**{manual_leaves}**", inline=False)
        
        await message.channel.send(embed=embed)

    # د. فحص النقاط
    elif text_lower == "نقاطي":
        stats = load_data(DATA_FILE)
        points = stats.get(guild_id, {}).get(user_id, {}).get("points", 0)
        await message.channel.send(f"💰 رصيدك الحالي يا {message.author.mention}: **{points}** نقطة.")

    # هـ. ألعاب السيرفر الـ 15 (بدون رموز)
    else:
        game_keywords = ["عجلة", "نرد", "زهر", "صناديق", "كنز", "مقص", "تخمين", "حظك", "الالعاب", "تحدي", "حساب", "بلنتي", "سلة", "صيد", "سباق", "تعدين", "مبارزة"]
        matched = False
        for kw in game_keywords:
            if text_lower == kw or text_lower.startswith(kw + " "):
                matched = True
                break
                
        if matched:
            config = load_data(CONFIG_FILE)
            games_channel_id = config.get(guild_id, {}).get("games_channel")
            
            if games_channel_id and message.channel.id != games_channel_id:
                await message.delete()
                warn = await message.channel.send(f"❌ عذراً {message.author.mention}, الألعاب مخصصة فقط في قناة الألعاب!")
                await asyncio.sleep(4)
                await warn.delete()
                return

            if text_lower == "الالعاب":
                await send_games_menu(message.channel)

            elif text_lower == "عجلة":
                prizes = [10, 25, 50, 100, 200, 0, 500, 50]
                weights = [30, 25, 20, 10, 5, 5, 2, 3]
                won = random.choices(prizes, weights=weights)[0]
                embed = discord.Embed(title="🎡 | عجلة الحظ الكبرى", description=f"يا هلا يا {message.author.mention}, قمت بتدوير العجلة...", color=discord.Color.gold())
                if won > 0:
                    total = add_points(guild_id, user_id, won)
                    embed.add_field(name="النتيجة:", value=f"🎉 مبروك! ربحت **{won} نقطة**!\n💰 رصيدك الإجمالي: **{total} نقطة**")
                else:
                    embed.add_field(name="النتيجة:", value=" خسارة! العجلة وقفت على الصفر، حظاً أوفر!")
                await message.channel.send(embed=embed)

            elif text_lower in ["نرد", "زهر"]:
                user_roll = random.randint(1, 6)
                bot_roll = random.randint(1, 6)
                embed = discord.Embed(title="🎲 | تحدي النرد", color=discord.Color.blue())
                embed.add_field(name="رقمك:", value=f"**{user_roll}**", inline=True)
                embed.add_field(name="رقم البوت:", value=f"**{bot_roll}**", inline=True)
                if user_roll > bot_roll:
                    total = add_points(guild_id, user_id, 40)
                    embed.description = f"🏆 مبروك فزت على البوت وربحت **40 نقطة**! (الرصيد: {total})"
                elif user_roll < bot_roll:
                    embed.description = "❌ فاز البوت عليك! حظاً أوفر."
                else:
                    total = add_points(guild_id, user_id, 10)
                    embed.description = f"🤝 تعادلتم! تم منحك **10 نقاط** كمكافأة."
                await message.channel.send(embed=embed)

            elif text_lower == "صناديق":
                boxes = ["💎 كنز ثمين (150 نقطة)", "🪙 قطعة ذهبية (50 نقطة)", "💨 صندوق فارغ", "💣 قنبلة (-20 نقطة)"]
                weights = [10, 30, 45, 15]
                result = random.choices(boxes, weights=weights)[0]
                points_map = {"💎 كنز ثمين (150 نقطة)": 150, "🪙 قطعة ذهبية (50 نقطة)": 50, "💨 صندوق فارغ": 0, "💣 قنبلة (-20 نقطة)": -20}
                won = points_map[result]
                total = add_points(guild_id, user_id, won)
                embed = discord.Embed(title="📦 | فتح الصناديق السرية", description=f"يا {message.author.mention}, اخترت صندوقاً وطلع لك:\n**{result}**\n\n💰 رصيدك الحالي: **{total} نقطة**", color=discord.Color.purple())
                await message.channel.send(embed=embed)

            elif text_lower.startswith("مقص"):
                parts = text.split()
                if len(parts) < 2 or parts[1] not in ["حجر", "ورقة", "مقص"]:
                    await message.channel.send("⚠️ الاستخدام الصحيح:\n`مقص حجر` أو `مقص ورقة` أو `مقص مقص`")
                    return
                choice = parts[1]
                bot_choice = random.choice(["حجر", "ورقة", "مقص"])
                embed = discord.Embed(title="✂️ | حجر، ورقة، مقص", color=discord.Color.orange())
                embed.add_field(name="اختيارك:", value=choice, inline=True)
                embed.add_field(name="اختيار البوت:", value=bot_choice, inline=True)
                if choice == bot_choice:
                    embed.description = "🤝 تعادلنا!"
                elif (choice == "حجر" and bot_choice == "مقص") or (choice == "ورقة" and bot_choice == "حجر") or (choice == "مقص" and bot_choice == "ورقة"):
                    total = add_points(guild_id, user_id, 35)
                    embed.description = f"🎉 مبروك فزت! ربحت **35 نقطة** (الرصيد: {total})"
                else:
                    embed.description = "❌ خسرت أمام البوت!"
                await message.channel.send(embed=embed)

            elif text_lower.startswith("تخمين"):
                parts = text.split()
                if len(parts) < 2 or not parts[1].isdigit():
                    await message.channel.send("⚠️ الاستخدام الصحيح:\n`تخمين 7` (اختر رقماً من 1 إلى 10)")
                    return
                number = int(parts[1])
                if not (1 <= number <= 10):
                    await message.channel.send("⚠️ أرجو اختيار رقم بين 1 و 10 فقط!")
                    return
                secret = random.randint(1, 10)
                if number == secret:
                    total = add_points(guild_id, user_id, 100)
                    await message.channel.send(f"🎯 كفووو يا {message.author.mention}! الرقم الصحيح كان **{secret}**، ربحت جائزة كبرى **100 نقطة**! (الرصيد: {total})")
                else:
                    await message.channel.send(f"❌ للأسف تخمينك خطأ. الرقم الصحيح كان **{secret}**، حظاً أوفر!")

            elif text_lower in ["حظك", "حظك_اليوم"]:
                fortunes = [
                    ("حظك ممتاز اليوم! ربحت 60 نقطة.", 60),
                    ("يومك سعيد، استمتع بـ 30 نقطة.", 30),
                    ("الأمور عادية، خذ 10 نقاط.", 10),
                    ("اليوم يحمل لك مفاجأة! ربحت 80 نقطة.", 80),
                    ("حظك سيء اليوم، ما ربحت شيء.", 0)
                ]
                text_result, prize = random.choice(fortunes)
                total = add_points(guild_id, user_id, prize)
                embed = discord.Embed(title="🔮 | طالع حظك اليوم", description=f"{message.author.mention}\n{text_result}\n\n💰 رصيدك الإجمالي: **{total} نقطة**", color=discord.Color.teal())
                await message.channel.send(embed=embed)

            elif text_lower == "تحدي":
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
                    total = add_points(msg.guild.id, msg.author.id, 50)
                    await message.channel.send(f"🏆 مبروك يا {msg.author.mention}! ربحت **50 نقطة**! (الرصيد: {total})")

            elif text_lower == "حساب":
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
                    total = add_points(msg.guild.id, msg.author.id, 30)
                    await message.channel.send(f"🏆 بطل الرياضيات يا {msg.author.mention}! ربحت **30 نقطة**! (الرصيد: {total})")

            elif text_lower == "كنز":
                won = random.choice([0, 70, 120, -30])
                total = add_points(guild_id, user_id, won)
                embed = discord.Embed(title="🏴‍☠️ | مغامرة الكنز الملعون", color=discord.Color.dark_gold())
                if won > 0:
                    embed.description = f"💰 يا له من حظ! عثرت على صندوق كنز يحتوي على **{won} نقطة**.\n• رصيدك: {total}"
                elif won < 0:
                    embed.description = f"💣 وقعت في فخ مفخخ وخسرت **{abs(won)} نقطة**.\n• رصيدك: {total}"
                else:
                    embed.description = "💨 الكنز كان فارغاً ولم تجد شيئاً!"
                await message.channel.send(embed=embed)

            elif text_lower == "بلنتي":
                results = ["goal", "saved", "out"]
                res = random.choice(results)
                embed = discord.Embed(title="⚽ | ركلة جزاء حاسمة", color=discord.Color.green())
                if res == "goal":
                    total = add_points(guild_id, user_id, 45)
                    embed.description = f"⚽ تسديدة صاروخية في الشباك! هدف! ربحت **45 نقطة** (الرصيد: {total})"
                elif res == "saved":
                    embed.description = "🧤 الحارس تصدى للكرة ببرعة! ضاعت الركلة."
                else:
                    embed.description = "✈️ الكرة مرت جوار القائم إلى خارج الملعب!"
                await message.channel.send(embed=embed)

            elif text_lower == "سلة":
                scored = random.choice([True, False])
                embed = discord.Embed(title="🏀 | رمية ثلاثية", color=discord.Color.orange())
                if scored:
                    total = add_points(guild_id, user_id, 40)
                    embed.description = f"🎯 يا سِلااام! الكرة في السلة من منتصف الملعب! ربحت **40 نقطة** (الرصيد: {total})"
                else:
                    embed.description = "❌ اصطدمت الكرة بالحلقة وخرجت!"
                await message.channel.send(embed=embed)

            elif text_lower == "صيد":
                catch = random.choice(["سمكة ذهبية", "سمكة عادية", "حذاء قديم", "صندوق زجاجي"])
                p_map = {"سمكة ذهبية": 60, "سمكة عادية": 25, "حذاء قديم": 0, "صندوق زجاجي": 90}
                won = p_map[catch]
                total = add_points(guild_id, user_id, won)
                await message.channel.send(f"🎣 سحبت سنارتك من الماء وطلع معك: **{catch}**! ربحت **{won} نقطة** (الرصيد: {total})")

            elif text_lower == "سباق":
                cars = ["🏎️ فيراري", "🚗 بورش", "🚙 لبرجيني"]
                winner = random.choice(cars)
                total = add_points(guild_id, user_id, 50)
                await message.channel.send(f"🏁 انتهى السباق بفوز السيارة: **{winner}**! تم منحك **50 نقطة** مشاركة (الرصيد: {total})")

            elif text_lower == "تعدين":
                 minerals = ["💎 الماس", "🪙 ذهب", "🪨 حجر عادي"]
                 m_pts = {"💎 الماس": 100, "🪙 ذهب": 50, "🪨 حجر عادي": 5}
                 found = random.choice(minerals)
                 won = m_pts[found]
                 total = add_points(guild_id, user_id, won)
                 await message.channel.send(f"⛏️ نقبت في الصخور واستخرجت: **{found}**! ربحت **{won} نقطة** (الرصيد: {total})")

            elif text_lower == "مبارزة":
                won = random.choice([True, False])
                embed = discord.Embed(title="🗡️ | مبارزة الفرسان", color=discord.Color.dark_red())
                if won:
                    total = add_points(guild_id, user_id, 70)
                    embed.description = f"⚔️ انتصرت على خصمك في المعركة ببراعة! ربحت **70 نقطة** (الرصيد: {total})"
                else:
                    embed.description = "🛡️ هزمك الخصم في النزال وأجبرك على الانسحاب!"
                await message.channel.send(embed=embed)

    await bot.process_commands(message)

# دالة تحميل الملفات الخارجية تلقائياً
async def load_extensions():
    for filename in os.listdir("./"):
        if filename.endswith(".py") and filename != "main.py":
            extension_name = filename[:-3]
            try:
                await bot.load_extension(extension_name)
            except Exception as e:
                pass

if __name__ == "__main__":
    keep_alive()
    
    try:
        asyncio.run(load_extensions())
    except Exception:
        pass
    
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("خطأ: التوكن غير موجود!")
