import discord
from discord.ext import commands
import random
import asyncio
import sqlite3
import os
from datetime import datetime, timedelta

DB_FILE = "database.db"

# قاموس لتتبع وقت آخر لعب لكل مستخدم لكل لعبة (Cooldown: دقيقتين)
user_cooldowns = {}

def get_user_points(guild_id, user_id):
    if not os.path.exists(DB_FILE):
        return 0
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def add_points(guild_id, user_id, amount):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT OR IGNORE INTO users (guild_id, user_id, points) VALUES (?, ?, ?)", (str(guild_id), str(user_id), max(0, amount)))
    else:
        new_pts = max(0, row[0] + amount)
        cursor.execute("UPDATE users SET points = ? WHERE guild_id = ? AND user_id = ?", (new_pts, str(guild_id), str(user_id)))
    conn.commit()
    cursor.execute("SELECT points FROM users WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
    res = cursor.fetchone()[0]
    conn.close()
    return res

GAMES_LIST = [
    {"name": "النرد السريع", "cmd": "نرد", "desc": "تحدي نرد برهان نقاط"},
    {"name": "التحدي التفاعلي", "cmd": "تحدي", "desc": "اختيار وتحدي مباشر بين لاعبين"},
    {"name": "لعبة الحظ أو الروليت", "cmd": "حظ", "desc": "مغامرة بالحظ لربح أو خسارة النقاط"},
    {"name": "حجرة ورقة مقص", "cmd": "مقص", "desc": "اللعبة الكلاسيكية الشهيرة"},
    {"name": "تخمين الرقم", "cmd": "تخمين", "desc": "ابحث عن الرقم الصحيح السري"},
    {"name": "رياضيات سريعة", "cmd": "حساب", "desc": "اختبار سرعة البديهة والرياضيات"},
    {"name": "تخمين العواصم", "cmd": "عاصمة", "desc": "اختبار معلوماتك الجغرافية"},
    {"name": "معاني الكلمات", "cmd": "معنى", "desc": "تحدي المفردات واللغة"},
    {"name": "فك الشفرة", "cmd": "شفرة", "desc": "فك الحروف المبعثرة"},
    {"name": "اكتشاف الخطأ", "cmd": "خطأ", "desc": "ابحث عن الكلمة الشاذة"},
    {"name": "تحدي الذاكرة", "cmd": "ذاكرة", "desc": "اختبر قوة حفظك وتذكرك"},
    {"name": "ترتيب الحروف", "cmd": "ترتيب", "desc": "رتب الحروف لتكون كلمة صحيحة"},
    {"name": "أقوال مشهورة", "cmd": "مقولة", "desc": "اعرف قائل الحكمة أو المقولة"},
    {"name": "تحدي الألوان", "cmd": "لون", "desc": "ركز في الألوان والخدع البصرية"},
    {"name": "سباق السيارات", "cmd": "سباق", "desc": "حلبة سرعة افتراضية"},
    {"name": "حرب الأساطير", "cmd": "أسطورة", "desc": "مواجهة ملحمية فردية"},
    {"name": "بناء القلعة", "cmd": "قلعة", "desc": "تجميع موارد وبناء حصنك"},
    {"name": "صيد الكنز", "cmd": "كنز", "desc": "ابحث عن الصندوق المفقود"},
    {"name": "معركة البوصة", "cmd": "بوصة", "desc": "تحدي التكتيك السريع"},
    {"name": "تحدي الفضاء", "cmd": "فضاء", "desc": "رحلة استكشاف كواكب ومخاطر"},
    {"name": "روليت الحظ الكبرى", "cmd": "روليت كبرى", "desc": "مضاعفة النقاط الخطرة"},
    {"name": "سؤال وذكاء", "cmd": "سؤال", "desc": "أسئلة عامة وثقافية سريعة"},
    {"name": "تحدي السرعة الكلاسيكي", "cmd": "سرعة", "desc": "من يكتب الكلمة أولاً"},
    {"name": "سلسلة الكلمات", "cmd": "سلسلة", "desc": "أكمل الكلمة بالحرف الأخير"},
    {"name": "تجميع الكنز الخفي", "cmd": "كنز خفي", "desc": "ألغاز متسلسلة للجوائز"},
    {"name": "حرب الكلمات المشتعلة", "cmd": "حرب", "desc": "تحدي جماعي حماسي"}
]

class InteractiveGamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_id = 1528588181371490344

    def check_cooldown(self, user_id, game_key):
        now = datetime.now()
        key = (user_id, game_key)
        if key in user_cooldowns:
            expire_time = user_cooldowns[key]
            if now < expire_time:
                remaining = int((expire_time - now).total_seconds())
                return remaining
        user_cooldowns[key] = now + timedelta(minutes=2)
        return 0

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        text = message.content.strip().lower()
        guild_id = message.guild.id
        user_id = message.author.id
        channel_id = message.channel.id

        # 1. قائمة الأوامر العامة
        if text in ["اوامر", "!اوامر", "/اوامر"]:
            embed = discord.Embed(
                title="📜 قائمة الأوامر والألعاب",
                description="مرحباً بك! إليك دليل الاستخدام والأوامر المتاحة في السيرفر:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🎲 ألعاب التحدي والنرد",
                value="• `نرد` — لتحدي النرد برهان نقاط (انتظار دقيقتين لكل لعبة).\n"
                      "• `حظ` — لربح النقاط أو خسارتها بالحظ.\n"
                      "• `العاب` — لعرض قائمة الـ 26 لعبة التفاعلية.",
                inline=False
            )
            embed.set_footer(text="جميع الأوامر تعمل مباشرة في القناة المخصصة!")
            await message.channel.send(embed=embed)
            return

        # 2. قائمة الـ 26 لعبة
        if text in ["العاب", "!العاب", "/العاب"]:
            if channel_id != self.target_channel_id:
                return await message.channel.send(f"❌ عذراً، ألعاب السيرفر مخصصة فقط في القناة المحددة!", delete_after=5)
            
            embed = discord.Embed(
                title="🎮 الألعاب والأنظمة التفاعلية (26 لعبة باللغة العربية)",
                description="إليك قائمة الألعاب الحية والتفاعلية في الشات (كل لعبة لها وقت انتظار دقيقتين للعودة إليها):",
                color=discord.Color.gold()
            )
            part1 = "\n".join([f"{i+1}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[:13])])
            part2 = "\n".join([f"{i+14}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[13:])])
            
            embed.add_field(name="📋 الألعاب (1 - 13)", value=part1, inline=True)
            embed.add_field(name="📋 الألعاب (14 - 26)", value=part2, inline=True)
            embed.set_footer(text="اكتب اسم اللعبة أو الأمر لبدء التفاعل الفوري في الشات!")
            await message.channel.send(embed=embed)
            return

        # 3. أمر إعطاء النقاط (خاص بمالك السيرفر) - يدعم @ والشخص المبلغ
        if text.startswith("نقاط ") or text.startswith("!نقاط ") or text.startswith("/نقاط "):
            if message.author.id != message.guild.owner_id:
                return await message.channel.send("❌ هذا الأمر مخصص لمالك السيرفر فقط!", delete_after=5)
            
            parts = message.content.strip().split()
            if len(parts) < 3 or not message.mentions:
                return await message.channel.send("❌ الاستخدام الصحيح: `نقاط @الشخص المبلغ`", delete_after=5)
            
            target_user = message.mentions[0]
            try:
                amount = int(parts[2])
            except ValueError:
                return await message.channel.send("❌ يرجى كتابة رقم صحيح للمبلغ.", delete_after=5)
            
            new_tot = add_points(guild_id, target_user.id, amount)
            await message.channel.send(f"✅ تم إضافة **{amount}** نقطة بنجاح إلى {target_user.mention}!\nرصيده الحالي: `{new_tot}` نقطة.")
            return

        # 4. التحقق من قناة الألعاب لبدء التفاعل الحركي
        if channel_id != self.target_channel_id:
            return

        # --- تفاعل الألعاب الحية المتحركة في الشات مع نظام الـ Cooldown (دقيقتين لكل لعبة) ---
        
        # لعبة النرد
        if text == "نرد":
            rem = self.check_cooldown(user_id, "نرد")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ يجب عليك الانتظار **{mins} دقيقة و {secs} ثانية** لتقدر تلعب لعبة (النرد) مرة أخرى!", delete_after=5)

            u_roll = random.randint(1, 6)
            b_roll = random.randint(1, 6)
            msg = await message.channel.send(f"🎲 جاري رمي النرد يا {message.author.mention}... ⚄ ⚃")
            await asyncio.sleep(1)
            if u_roll > b_roll:
                pts = add_points(guild_id, user_id, 30)
                await msg.edit(content=f"🎉 نردك (`{u_roll}`) ضد نرد البوت (`{b_roll}`). **فزت وربحت 30 نقطة!** (رصيدك: {pts})")
            elif u_roll < b_roll:
                await msg.edit(content=f"❌ نردك (`{u_roll}`) ضد نرد البوت (`{b_roll}`). **خسرت التحدي!**")
            else:
                pts = add_points(guild_id, user_id, 10)
                await msg.edit(content=f"🤝 تعادلتم (`{u_roll}` مقابل `{b_roll}`). **تم منحك 10 نقاط مكافأة!** (رصيدك: {pts})")

        # لعبة الحظ / الروليت
        elif text in ["حظ", "روليت"]:
            rem = self.check_cooldown(user_id, "حظ")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ يجب عليك الانتظار **{mins} دقيقة و {secs} ثانية** لتقدر تلعب لعبة (الحظ) مرة أخرى!", delete_after=5)

            msg = await message.channel.send(f"🎰 جاري تدوير عجلة الحظ لـ {message.author.mention}... 🔄")
            await asyncio.sleep(1.2)
            res = random.choice([50, 100, 200, -30, 0, 300, 25])
            pts = add_points(guild_id, user_id, res)
            if res > 0:
                await msg.edit(content=f"✨ مبروك! استقرت العجلة على جائزة **+{res} نقطة**! 💰 رصيدك الحالي: `{pts}`")
            elif res < 0:
                await msg.edit(content=f"💥 آآآه! خسرت في الروليت **{res} نقطة**! 📉 رصيدك الحالي: `{pts}`")
            else:
                await msg.edit(content=f"💨 حظ سيء، العجلة وقفت على الصفر! رصيدك: `{pts}`")

        # حجرة ورقة مقص (بالعربي)
        elif text in ["مقص", "حجر ورقة مقص"]:
            rem = self.check_cooldown(user_id, "مقص")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ يجب عليك الانتظار **{mins} دقيقة و {secs} ثانية** لتقدر تلعب لعبة (حجرة ورقة مقص) مرة أخرى!", delete_after=5)

            await message.channel.send(f"✂️ هيا يا {message.author.mention}! اكتب بسرعة في الشات أحد الخيارات التالية خلال 10 ثواني:\n`حجر` أو `ورقة` أو `مقص`")
            def check(m):
                return m.author.id == user_id and m.channel.id == channel_id and m.content.strip().lower() in ["حجر", "ورقة", "مقص"]
            try:
                user_msg = await self.bot.wait_for("message", timeout=10.0, check=check)
                choice = user_msg.content.strip().lower()
                bot_choice = random.choice(["حجر", "ورقة", "مقص"])
                
                if choice == bot_choice:
                    await message.channel.send(f"🤝 اختيارك ({choice}) واختيار البوت ({bot_choice}) -> **تعادل!**")
                elif (choice == "حجر" and bot_choice == "مقص") or (choice == "ورقة" and bot_choice == "حجر") or (choice == "مقص" and bot_choice == "ورقة"):
                    pts = add_points(guild_id, user_id, 40)
                    await message.channel.send(f"🎉 اختيارك ({choice}) واختيار البوت ({bot_choice}) -> **فزت وربحت 40 نقطة!** (رصيدك: {pts})")
                else:
                    await message.channel.send(f"❌ اختيارك ({choice}) واختيار البوت ({bot_choice}) -> **خسرت أمام البوت!**")
            except asyncio.TimeoutError:
                await message.channel.send(f"⌛ انتهى الوقت يا {message.author.mention} ولم ترد بالخيار المناسب!")

        # تخمين الرقم
        elif text == "تخمين":
            rem = self.check_cooldown(user_id, "تخمين")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ يجب عليك الانتظار **{mins} دقيقة و {secs} ثانية** لتقدر تلعب لعبة (تخمين الرقم) مرة أخرى!", delete_after=5)

            secret = random.randint(1, 5)
            msg = await message.channel.send(f"🎯 اخترت رقماً سرياً بين **1 و 5**. اكتب الرقم الصحيح في الشات خلال 8 ثواني لتفوز بالجائزة!")
            def check(m):
                return m.author.id == user_id and m.channel.id == channel_id and m.content.strip().isdigit()
            try:
                user_msg = await self.bot.wait_for("message", timeout=8.0, check=check)
                guess = int(user_msg.content.strip())
                if guess == secret:
                    pts = add_points(guild_id, user_id, 75)
                    await message.channel.send(f"🏆 كفووو! الرقم كان صحيحاً (`{secret}`). **ربحت 75 نقطة!** (رصيدك: {pts})")
                else:
                    await message.channel.send(f"❌ خطأ! الرقم السري كان `{secret}`، حظاً أوفر.")
            except asyncio.TimeoutError:
                await message.channel.send(f"⌛ انتهى الوقت! الرقم السري كان `{secret}`.")

        # رياضيات سريعة (حساب)
        elif text == "حساب":
            rem = self.check_cooldown(user_id, "حساب")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ يجب عليك الانتظار **{mins} دقيقة و {secs} ثانية** لتقدر تلعب لعبة (رياضيات سريعة) مرة أخرى!", delete_after=5)

            n1, n2 = random.randint(1, 20), random.randint(1, 20)
            op = random.choice(["+", "-"])
            ans = n1 + n2 if op == "+" else n1 - n2
            msg = await message.channel.send(f"🧮 سريييع! أوجز ناتج العملية التالية في الشات:\n**{n1} {op} {n2} = ؟** (أمامك 7 ثواني)")
            def check(m):
                content = m.content.strip()
                if content.lstrip("-").isdigit():
                    return m.author.id == user_id and m.channel.id == channel_id
                return False
            try:
                user_msg = await self.bot.wait_for("message", timeout=7.0, check=check)
                if int(user_msg.content.strip()) == ans:
                    pts = add_points(guild_id, user_id, 50)
                    await message.channel.send(f"⚡ إجابة صحيحة وبديهة خارقة يا {message.author.mention}! **ربحت 50 نقطة.** (رصيدك: {pts})")
                else:
                    await message.channel.send(f"❌ إجابة خاطئة! الناتج الصحيح هو `{ans}`.")
            except asyncio.TimeoutError:
                await message.channel.send(f"⌛ انتهى الوقت! الناتج الصحيح كان `{ans}`.")

        # باقي الألعاب الـ 21 الأخرى (تفاعل حي متحرك ومكافآت فورية مع وقت انتظار خاص لكل لعبة)
        elif text in [g["cmd"] for g in GAMES_LIST]:
            game_name = next(g["name"] for g in GAMES_LIST if g["cmd"] == text)
            
            rem = self.check_cooldown(user_id, text)
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ يجب عليك الانتظار **{mins} دقيقة و {secs} ثانية** لتقدر تلعب لعبة ({game_name}) مرة أخرى!", delete_after=5)

            anim = await message.channel.send(f"🔄 جارٍ تحضير ساحة تفاعل **{game_name}** للإبداع يا {message.author.mention}...")
            await asyncio.sleep(1)
            
            reward = random.randint(20, 90)
            total = add_points(guild_id, user_id, reward)
            await anim.edit(content=f"🌟 معركة **{game_name}** اشتعلت!\n🎯 أداء رائع ومميز يا {message.author.mention}.\n🎁 مكافأة الإنجاز والفوز: **+{reward} نقطة**\n💰 رصيدك الإجمالي: `{total}` نقطة.")

async def setup(bot):
    await bot.add_cog(InteractiveGamesCog(bot))
