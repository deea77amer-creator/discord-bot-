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

# جدول المنتجات في المتجر
SHOP_ITEMS = {
    "1": {"name": "سيف الأساطير", "price": 150, "desc": "سيف حربي قوي لزيادة هيبتك"},
    "2": {"name": "درع الماس", "price": 250, "desc": "درع واقي من الضربات القوية"},
    "3": {"name": "جرعة حظ ذهبية", "desc": "تزيد حظك في الألعاب", "price": 100}
}

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

        # تهيئة قاعدة بيانات الحقيبة والممتلكات إن لم تكن موجودة
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (guild_id TEXT, user_id TEXT, item_name TEXT)''')
        conn.commit()
        conn.close()

        # 1. قائمة الأوامر العامة
        if text in ["اوامر", "!اوامر", "/اوامر"]:
            embed = discord.Embed(
                title="📜 قائمة الأوامر والألعاب",
                description="مرحباً بك! إليك دليل الاستخدام والأوامر المتاحة:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🎲 الألعاب والمتجر",
                value="• `العاب` — لعرض قائمة الـ 26 لعبة.\n"
                      "• `اسعار` — لعرض أسعار الأغراض.\n"
                      "• `شراء` — لعرض قائمة المتجر والشراء التفاعلي (مثال: شراء 1).\n"
                      "• `بيع` — لبيع أغراضك واسترداد النقاط (مثال: بيع سيف الأساطير).\n"
                      "• `ممتلكات` أو `حقيبتي` — لعرض محتويات حقيبتك.",
                inline=False
            )
            embed.set_footer(text="جميع الأوامر تعمل في القناة المخصصة!")
            await message.channel.send(embed=embed)
            return

        # 2. قائمة الـ 26 لعبة
        if text in ["العاب", "!العاب", "/العاب"]:
            if channel_id != self.target_channel_id:
                return await message.channel.send(f"❌ عذراً، ألعاب السيرفر مخصصة فقط في القناة المحددة!", delete_after=5)
            
            embed = discord.Embed(
                title="🎮 الألعاب والأنظمة التفاعلية (26 لعبة باللغة العربية)",
                description="كل لعبة تفاعلية تتطلب منك الخيار ولكل لعبة وقت انتظار دقيقتين:",
                color=discord.Color.gold()
            )
            part1 = "\n".join([f"{i+1}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[:13])])
            part2 = "\n".join([f"{i+14}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[13:])])
            
            embed.add_field(name="📋 الألعاب (1 - 13)", value=part1, inline=True)
            embed.add_field(name="📋 الألعاب (14 - 26)", value=part2, inline=True)
            embed.set_footer(text="اكتب اسم اللعبة للبدء فوراً!")
            await message.channel.send(embed=embed)
            return

        # 3. نظام الأسعار
        if text in ["اسعار", "!اسعار"]:
            embed = discord.Embed(title="🛒 قائمة أسعار المتجر", color=discord.Color.green())
            for k, v in SHOP_ITEMS.items():
                embed.add_field(name=f"{k}. {v['name']}", value=f"السعر: **{v['price']}** نقطة\nالوصف: {v['desc']}", inline=False)
            embed.set_footer(text="لشراء غرض اكتب: شراء [رقم الغرض] (مثال: شراء 1)")
            return await message.channel.send(embed=embed)

        # 4. نظام الشراء التفاعلي (مثال: شراء 1)
        if text.startswith("شراء ") or text.startswith("!شراء "):
            parts = message.content.strip().split()
            if len(parts) < 2 or not parts[1] in SHOP_ITEMS:
                return await message.channel.send("❌ يرجى اختيار رقم غرض صحيح من المتجر. اكتب `اسعار` لمعرفة الأرقام.", delete_after=5)
            
            item_key = parts[1]
            item = SHOP_ITEMS[item_key]
            current_pts = get_user_points(guild_id, user_id)
            
            if current_pts < item["price"]:
                return await message.channel.send(f"❌ لا توجد نقاط كافية لديك! رصيدك `{current_pts}` وتحتاج إلى `{item['price']}` نقطة.", delete_after=5)
            
            # خصم النقاط وإضافة الغرض للحقتيبة
            add_points(guild_id, user_id, -item["price"])
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO inventory (guild_id, user_id, item_name) VALUES (?, ?, ?)", (str(guild_id), str(user_id), item["name"]))
            conn.commit()
            conn.close()
            return await message.channel.send(f"✅ مبروك يا {message.author.mention}! اشتريت **{item['name']}** بنجاح مقابل `{item['price']}` نقطة!")

        # 5. نظام الممتلكات / الحقيبة
        if text in ["ممتلكات", "حقيبتي", "!حقيبتي"]:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT item_name FROM inventory WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
            items = cursor.fetchall()
            conn.close()
            
            pts = get_user_points(guild_id, user_id)
            embed = discord.Embed(title=f"🎒 حقيبة الممتلكات لـ {message.author.name}", color=discord.Color.purple())
            embed.add_field(name="💰 رصيد النقاط", value=f"`{pts}` نقطة", inline=False)
            
            if items:
                items_list = "\n".join([f"• {item[0]}" for item in items])
                embed.add_field(name="📦 الأغراض والممتلكات", value=items_list, inline=False)
            else:
                embed.add_field(name="📦 الأغراض والممتلكات", value="حقيبتك فارغة حالياً! استخدم `اسعار` ثم `شراء [رقم]`.", inline=False)
            return await message.channel.send(embed=embed)

        # 6. نظام البيع (استرداد النقاط)
        if text.startswith("بيع ") or text.startswith("!بيع "):
            item_to_sell = message.content.replace("بيع", "").replace("!", "").strip()
            if not item_to_sell:
                return await message.channel.send("❌ يرجى كتابة اسم الغرض الذي تريد بيعه (مثال: بيع سيف الأساطير)", delete_after=5)
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT rowid FROM inventory WHERE guild_id = ? AND user_id = ? AND item_name LIKE ?", (str(guild_id), str(user_id), f"%{item_to_sell}%"))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return await message.channel.send(f"❌ ليس لديك غرض بهذا الاسم في حقيبتك!", delete_after=5)
            
            # حذف الغرض من الحقيبة وإرجاع نصف سعره أو سعره كاملاً
            cursor.execute("DELETE FROM inventory WHERE rowid = ?", (row[0],))
            conn.commit()
            conn.close()
            
            refund = 75 # استرداد افتراضي أو حسب السعر
            new_pts = add_points(guild_id, user_id, refund)
            return await message.channel.send(f"✅ تم بيع الغرض بنجاح واسترداد **{refund} نقطة**! رصيدك الحالي: `{new_pts}`")

        # 7. أمر إعطاء النقاط (خاص بمالك السيرفر)
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

        # 8. التحقق من قناة الألعاب للبدء بالألعاب التفاعلية الحقيقية
        if channel_id != self.target_channel_id:
            return

        # --- تفاعلات الألعاب الحقيقية التي تتطلب اختيارك وتفاعلك مع وقت انتظار دقيقتين لكل لعبة ---
        
        # 1. لعبة النرد السريع (تفاعلية باختيار اتجاه النرد أو التوقع)
        if text == "نرد":
            rem = self.check_cooldown(user_id, "نرد")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** للعب (النرد السريع) مرة أخرى!", delete_after=5)

            await message.channel.send(f"🎲 يا {message.author.mention}! هل توقعك لنردك سيكون **عالي** (4 إلى 6) أم **منخفض** (1 إلى 3)؟\nاكتب اختيارك في الشات خلال 10 ثواني:")
            def check(m):
                return m.author.id == user_id and m.channel.id == channel_id and m.content.strip().lower() in ["عالي", "منخفض"]
            try:
                user_msg = await self.bot.wait_for("message", timeout=10.0, check=check)
                choice = user_msg.content.strip().lower()
                roll = random.randint(1, 6)
                is_high = roll >= 4
                user_won = (choice == "عالي" and is_high) or (choice == "منخفض" and not is_high)
                
                if user_won:
                    pts = add_points(guild_id, user_id, 40)
                    await message.channel.send(f"🎉 طلع النرد (`{roll}`). توقعك كان صحيحاً! **ربحت 40 نقطة** (رصيدك: {pts})")
                else:
                    await message.channel.send(f"❌ طلع النرد (`{roll}`). توقعك كان خاطئاً، حظاً أوفر!")
            except asyncio.TimeoutError:
                await message.channel.send(f"⌛ انتهى الوقت ولم تقم باختيار التوقع!")

        # 2. لعبة الحظ أو الروليت (تفاعلية باختيار باب الكنز)
        if text in ["حظ", "روليت"]:
            rem = self.check_cooldown(user_id, "حظ")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** لتدوير (عجلة الحظ) مرة أخرى!", delete_after=5)

            await message.channel.send(f"🎰 أمامك 3 أبواب مغلقة يا {message.author.mention}: `باب 1` أو `باب 2` أو `باب 3`.\nاكتب رقم الباب الذي تختاره في الشات خلال 10 ثواني:")
            def check(m):
                return m.author.id == user_id and m.channel.id == channel_id and m.content.strip().lower() in ["باب 1", "باب 2", "باب 3", "1", "2", "3"]
            try:
                await self.bot.wait_for("message", timeout=10.0, check=check)
                reward = random.choice([50, 100, -20, 150, 0, 80])
                pts = add_points(guild_id, user_id, reward)
                if reward > 0:
                    await message.channel.send(f"✨ فتحت الباب ووجد خلفه كنز بقيمة **+{reward} نقطة**! رصيدك: `{pts}`")
                elif reward < 0:
                    await message.channel.send(f"💥 عصف بك فخ خلف الباب وخسرت **{reward} نقطة**! رصيدك: `{pts}`")
                else:
                    await message.channel.send(f"💨 الباب كان فارغاً! لم تربح ولم تخسر.")
            except asyncio.TimeoutError:
                await message.channel.send(f"⌛ انتهى الوقت ولمختر الباب المناسب!")

        # 3. حجرة ورقة مقص
        elif text in ["مقص", "حجر ورقة مقص"]:
            rem = self.check_cooldown(user_id, "مقص")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** للعب (حجرة ورقة مقص) مرة أخرى!", delete_after=5)

            await message.channel.send(f"✂️ هيا يا {message.author.mention}! اكتب خيارك في الشات خلال 10 ثواني:\n`حجر` أو `ورقة` أو `مقص`")
            def check(m):
                return m.author.id == user_id and m.channel.id == channel_id and m.content.strip().lower() in ["حجر", "ورقة", "مقص"]
            try:
                user_msg = await self.bot.wait_for("message", timeout=10.0, check=check)
                choice = user_msg.content.strip().lower()
                bot_choice = random.choice(["حجر", "ورقة", "مقص"])
                
                if choice == bot_choice:
                    await message.channel.send(f"🤝 اختيارك ({choice}) والبوت ({bot_choice}) -> **تعادل!**")
                elif (choice == "حجر" and bot_choice == "مقص") or (choice == "ورقة" and bot_choice == "حجر") or (choice == "مقص" and bot_choice == "ورقة"):
                    pts = add_points(guild_id, user_id, 50)
                    await message.channel.send(f"🎉 اختيارك ({choice}) والبوت ({bot_choice}) -> **فزت وربحت 50 نقطة!** (رصيدك: {pts})")
                else:
                    await message.channel.send(f"❌ اختيارك ({choice}) والبوت ({bot_choice}) -> **خسرت أمام البوت!**")
            except asyncio.TimeoutError:
                await message.channel.send(f"⌛ انتهى الوقت ولم ترد بالخيار!")

        # 4. تخمين الرقم
        elif text == "تخمين":
            rem = self.check_cooldown(user_id, "تخمين")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** للعب (تخمين الرقم) مرة أخرى!", delete_after=5)

            secret = random.randint(1, 5)
            await message.channel.send(f"🎯 اخترت رقماً سرياً بين **1 و 5**. اكتب رقمك في الشات خلال 8 ثواني:")
            def check(m):
                return m.author.id == user_id and m.channel.id == channel_id and m.content.strip().isdigit()
            try:
                user_msg = await self.bot.wait_for("message", timeout=8.0, check=check)
                guess = int(user_msg.content.strip())
                if guess == secret:
                    pts = add_points(guild_id, user_id, 80)
                    await message.channel.send(f"🏆 كفووو! الرقم الصحيح كان (`{secret}`). **ربحت 80 نقطة!** (رصيدك: {pts})")
                else:
                    await message.channel.send(f"❌ خطأ! الرقم السري كان `{secret}`.")
            except asyncio.TimeoutError:
                await message.channel.send(f"⌛ انتهى الوقت! الرقم السري كان `{secret}`.")

        # 5. رياضيات سريعة (حساب)
        elif text == "حساب":
            rem = self.check_cooldown(user_id, "حساب")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** للعب (رياضيات سريعة) مرة أخرى!", delete_after=5)

            n1, n2 = random.randint(1, 20), random.randint(1, 20)
            op = random.choice(["+", "-"])
            ans = n1 + n2 if op == "+" else n1 - n2
            await message.channel.send(f"🧮 أوجد الناتج في الشات خلال 7 ثواني:\n**{n1} {op} {n2} = ؟**")
            def check(m):
                content = m.content.strip()
                if content.lstrip("-").isdigit():
                    return m.author.id == user_id and m.channel.id == channel_id
                return False
            try:
                user_msg = await self.bot.wait_for("message", timeout=7.0, check=check)
                if int(user_msg.content.strip()) == ans:
                    pts = add_points(guild_id, user_id, 50)
                    await message.channel.send(f"⚡ إجابة صحيحة يا {message.author.mention}! **ربحت 50 نقطة.** (رصيدك: {pts})")
                else:
                    await message.channel.send(f"❌ إجابة خاطئة! الناتج الصحيح هو `{ans}`.")
            except asyncio.TimeoutError:
                await message.channel.send(f"⌛ انتهى الوقت! الناتج الصحيح كان `{ans}`.")

        # باقي الألعاب الـ 21 الأخرى (تفاعلية تتطلب اختيار كلمة أو حرف أسرع)
        elif text in [g["cmd"] for g in GAMES_LIST]:
            game_name = next(g["name"] for g in GAMES_LIST if g["cmd"] == text)
            
            rem = self.check_cooldown(user_id, text)
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** للعب ({game_name}) مرة أخرى!", delete_after=5)

            target_word = random.choice(["تحدي", "سرعة", "بطل", "ذكاء", "صقر", "قوة", "فوز"])
            await message.channel.send(f"🕹️ تحدي **{game_name}** بدأ!\nاكتب الكلمة التالية بسرعة في الشات لتفوز: **`{target_word}`** (أمامك 8 ثواني)")
            
            def check(m):
                return m.author.id == user_id and m.channel.id == channel_id and m.content.strip() == target_word
            try:
                await self.bot.wait_for("message", timeout=8.0, check=check)
                reward = random.randint(30, 70)
                total = add_points(guild_id, user_id, reward)
                await message.channel.send(f"🏆 بطل يا {message.author.mention}! كتبت الكلمة في الوقت المناسب وربحت **+{reward} نقطة**! رصيدك: `{total}`")
            except asyncio.TimeoutError:
                await message.channel.send(f"⌛ انتهى الوقت ولم تكتب الكلمة المطلوبة (`{target_word}`) بشكل صحيح!")

async def setup(bot):
    await bot.add_cog(InteractiveGamesCog(bot))
