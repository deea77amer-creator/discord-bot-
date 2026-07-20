import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
from datetime import datetime, timedelta

DB_FILE = "database.db"
COOLDOWN_TIME = timedelta(minutes=2)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            guild_id TEXT PRIMARY KEY,
            games_channel TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            guild_id TEXT,
            user_id TEXT,
            points INTEGER,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cooldowns (
            guild_id TEXT,
            user_id TEXT,
            game_name TEXT,
            last_time TEXT,
            PRIMARY KEY (guild_id, user_id, game_name)
        )
    """)
    # جدول أسعار المزاد الحالية لكل سيرفر
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_prices (
            guild_id TEXT,
            item_name TEXT,
            price INTEGER,
            PRIMARY KEY (guild_id, item_name)
        )
    """)
    # جدول ممتلكات المستخدمين من المزاد
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_inventory (
            guild_id TEXT,
            user_id TEXT,
            item_name TEXT,
            quantity INTEGER,
            PRIMARY KEY (guild_id, user_id, item_name)
        )
    """)
    conn.commit()
    conn.close()

# تهيئة الجداول تلقائياً لمنع ظهور خطأ عدم وجود الجداول
init_db()

def get_config(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT games_channel FROM config WHERE guild_id = ?", (str(guild_id),))
    row = cursor.fetchone()
    conn.close()
    return int(row[0]) if (row and row[0]) else None

def get_user_data(guild_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT OR IGNORE INTO users (guild_id, user_id, points) VALUES (?, ?, 0)", (str(guild_id), str(user_id)))
        conn.commit()
        points = 0
    else:
        points = row[0]
    conn.close()
    return points

def add_points(guild_id, user_id, amount):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    current = get_user_data(guild_id, user_id)
    new_points = current + amount
    cursor.execute("UPDATE users SET points = ? WHERE guild_id = ? AND user_id = ?", (new_points, str(guild_id), str(user_id)))
    conn.commit()
    conn.close()
    return new_points

def check_cooldown(guild_id, user_id, game_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT last_time FROM cooldowns WHERE guild_id = ? AND user_id = ? AND game_name = ?", (str(guild_id), str(user_id), game_name))
    row = cursor.fetchone()
    if row:
        last_time = datetime.fromisoformat(row[0])
        now = datetime.now()
        if now - last_time < COOLDOWN_TIME:
            remaining = COOLDOWN_TIME - (now - last_time)
            mins = int(remaining.total_seconds() // 60)
            secs = int(remaining.total_seconds() % 60)
            conn.close()
            return False, f"{mins} دقيقة و {secs} ثانية"
    conn.close()
    return True, ""

def set_cooldown(guild_id, user_id, game_name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("INSERT INTO cooldowns (guild_id, user_id, game_name, last_time) VALUES (?, ?, ?, ?) ON CONFLICT(guild_id, user_id, game_name) DO UPDATE SET last_time = ?", (str(guild_id), str(user_id), game_name, now_str, now_str))
    conn.commit()
    conn.close()

# --- إدارة أسعار وممتلكات المزاد ---
BASE_MARKET_ITEMS = {
    "سيف أسطوري": 300,
    "درع الماس": 250,
    "صندوق سري نادر": 150,
    "مفتاح ذهبي": 100,
    "جرعة حظ": 75,
    "سيارة سباق فارهة": 600
}

def update_and_get_market_prices(guild_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, price FROM market_prices WHERE guild_id = ?", (str(guild_id),))
    rows = cursor.fetchall()
    
    current_prices = {row[0]: row[1] for row in rows}
    
    # تحديث أو إنشاء الأسعار عشوائياً (ترتفع أو ترخص)
    for item, base_price in BASE_MARKET_ITEMS.items():
        if item not in current_prices:
            current_prices[item] = base_price
        else:
            # تغيّر بنسبة تتراوح بين -20% إلى +25%
            change_percent = random.uniform(-0.20, 0.25)
            new_price = int(current_prices[item] * (1 + change_percent))
            if new_price < 20: 
                new_price = 20
            current_prices[item] = new_price
            
        cursor.execute("INSERT OR REPLACE INTO market_prices (guild_id, item_name, price) VALUES (?, ?, ?)", (str(guild_id), item, current_prices[item]))
    
    conn.commit()
    conn.close()
    return current_prices

def get_user_inventory(guild_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, quantity FROM user_inventory WHERE guild_id = ? AND user_id = ? AND quantity > 0", (str(guild_id), str(user_id)))
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def add_to_inventory(guild_id, user_id, item_name, qty):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM user_inventory WHERE guild_id = ? AND user_id = ? AND item_name = ?", (str(guild_id), str(user_id), item_name))
    row = cursor.fetchone()
    current_qty = row[0] if row else 0
    new_qty = current_qty + qty
    cursor.execute("INSERT OR REPLACE INTO user_inventory (guild_id, user_id, item_name, quantity) VALUES (?, ?, ?, ?)", (str(guild_id), str(user_id), item_name, new_qty))
    conn.commit()
    conn.close()

def remove_from_inventory(guild_id, user_id, item_name, qty):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM user_inventory WHERE guild_id = ? AND user_id = ? AND item_name = ?", (str(guild_id), str(user_id), item_name))
    row = cursor.fetchone()
    if not row or row[0] < qty:
        conn.close()
        return False
    new_qty = row[0] - qty
    cursor.execute("UPDATE user_inventory SET quantity = ? WHERE guild_id = ? AND user_id = ? AND item_name = ?", (new_qty, str(guild_id), str(user_id), item_name))
    conn.commit()
    conn.close()
    return True

# --- تعريف الـ 26 لعبة تفاعلية ---

class GamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        games_channel_id = get_config(ctx.guild.id)
        if games_channel_id and ctx.channel.id != games_channel_id:
            try:
                await ctx.message.delete()
            except:
                pass
            return False
        return True

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        games_channel_id = get_config(message.guild.id)
        if games_channel_id and message.channel.id != games_channel_id:
            return

        text = message.content.strip().lower()
        guild_id = message.guild.id
        user_id = message.author.id

        # أمر تعيين قناة الألعاب لصاحب السيرفر: تعيين_قناة_الالعاب #القناة
        if text.startswith("تعيين_قناة_الالعاب") or text.startswith("/تعيين_قناة_الالعاب"):
            if message.author.id != message.guild.owner_id:
                return await message.channel.send(f"❌ يا {message.author.mention}, هذا الأمر لمالك السيرفر فقط!", delete_after=5)
            if message.channel_mentions:
                ch = message.channel_mentions[0]
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO config (guild_id, games_channel) VALUES (?, ?)", (str(guild_id), str(ch.id)))
                conn.commit()
                conn.close()
                await message.channel.send(f"✅ تم تعيين {ch.mention} كقناة رسمية للألعاب بنجاح!")
            else:
                await message.channel.send("❌ يرجى منشنة القناة المطلوبة. مثال: `تعيين_قناة_الالعاب #العاب`", delete_after=5)
            return

        # أمر تحكم صاحب السيرفر لإعطاء/خصم النقاط: نقاط @المستخدم العدد
        if text.startswith("نقاط ") or text.startswith("/نقاط "):
            if message.author.id != message.guild.owner_id:
                return await message.channel.send(f"❌ يا {message.author.mention}, هذا الأمر مخصص لصاحب السيرفر فقط!", delete_after=5)
            
            parts = message.content.strip().split()
            if len(parts) >= 3 and message.mentions:
                target_user = message.mentions[0]
                try:
                    amount = int(parts[2])
                    new_total = add_points(guild_id, target_user.id, amount)
                    await message.channel.send(f"✅ تم تعديل نقاط {target_user.mention} بمقدار `{amount}`. الرصيد الحالي: **{new_total}** نقطة.")
                except ValueError:
                    await message.channel.send("❌ يرجى كتابة رقم صحيح للنقاط. مثال: `نقاط @user 100`", delete_after=5)
            else:
                await message.channel.send("❌ الاستخدام الصحيح: `نقاط @المستخدم العدد`", delete_after=5)
            return

        # أمر أسعار المزاد (لمعرفة أسعار الأشياء وكيف ترتفع وترخص)
        if text in ["اسعار", "الأسعار", "/اسعار", "أسعار"]:
            prices = update_and_get_market_prices(guild_id)
            embed = discord.Embed(
                title="📈 سُوق المِزَاد العَالَمِي (تتغير الأسعار باستمرار) 📉",
                description="إليك أسعار الأغراض الحالية في المزاد:\n",
                color=discord.Color.gold()
            )
            for item, price in prices.items():
                embed.add_field(name=item, value=f"💰 **{price}** نقطة", inline=True)
            embed.set_footer(text="💡 استخدم أمر: شراء <اسم الغرض> لشرائه.")
            await message.channel.send(embed=embed)
            return

        # أمر شراء من المزاد: شراء <اسم الغرض>
        if text.startswith("شراء ") or text.startswith("/شراء "):
            parts = message.content.strip().split(maxsplit=1)
            if len(parts) < 2:
                return await message.channel.send("❌ الاستخدام: `شراء <اسم الغرض>`", delete_after=5)
            item_query = parts[1].strip()
            prices = update_and_get_market_prices(guild_id)
            
            matched_item = None
            for itm in prices.keys():
                if item_query in itm.lower():
                    matched_item = itm
                    break
            
            if not matched_item:
                return await message.channel.send("❌ هذا الغرض غير موجود في المزاد! اكتب `أسعار` لرؤية القائمة.", delete_after=5)
            
            cost = prices[matched_item]
            user_pts = get_user_data(guild_id, user_id)
            if user_pts < cost:
                return await message.channel.send(f"❌ رصيدك ({user_pts} نقطة) لا يكفي لشراء **{matched_item}** بسعر `{cost}` نقطة!", delete_after=5)
            
            add_points(guild_id, user_id, -cost)
            add_to_inventory(guild_id, user_id, matched_item, 1)
            await message.channel.send(f"🎉 مبروك! اشتريت **{matched_item}** بقيمة `{cost}` نقطة بنجاح.")
            return

        # أمر ممتلكات (لعرض كم شيء شريته من المزاد)
        if text in ["ممتلكات", "/ممتلكات", "حقيبتي", "أغراضي"]:
            inv = get_user_inventory(guild_id, user_id)
            embed = discord.Embed(
                title=f"🎒 مُمْتَلَكَات وحَقِيبَة {message.author.display_name}",
                color=discord.Color.purple()
            )
            if not inv:
                embed.description = "❌ حقيبتك فارغة تماماً! لم تقم بشراء أي شيء من المزاد بعد."
            else:
                desc = ""
                for itm, qty in inv.items():
                    desc += f"• **{itm}** ⟵ الكمية: `{qty}`\n"
                embed.description = desc
            embed.set_footer(text="💡 استخدم أمر: بيع <اسم الغرض> (أو بيع الكل / بيع نص) لبيع ممتلكاتك.")
            await message.channel.send(embed=embed)
            return

        # أمر بيع (بيع كامل، بيع نص، أو حسب العدد)
        # الصيغ المتوقعة: بيع <الغرض> كامل | بيع <الغرض> نص | بيع <الغرض> <العدد> | بيع كل شيء
        if text.startswith("بيع ") or text.startswith("/بيع "):
            parts = message.content.strip().split()
            if len(parts) < 2:
                return await message.channel.send("❌ الاستخدام الصحيح:\n• `بيع <الغرض> كامل`\n• `بيع <الغرض> نص`\n• `بيع <الغرض> <العدد>`", delete_after=5)
            
            inv = get_user_inventory(guild_id, user_id)
            if not inv:
                return await message.channel.send("❌ ليس لديك أي ممتلكات لتبيعها!", delete_after=5)
            
            # محاولة مطابقة اسم الغرض من الحقيبة
            matched_item = None
            query_str = " ".join(parts[1:-1]).lower()
            last_arg = parts[-1].lower()
            
            # فحص إذا كان الغرض يتكون من كلمة واحدة أو أكثر
            for itm in inv.keys():
                if message.content.strip().lower().contains(itm.lower()) or query_str in itm.lower():
                    matched_item = itm
                    break
            
            # تبسيط عملية البحث إذا فشلت المطابقة الجزئية
            if not matched_item:
                for itm in inv.keys():
                    if parts[1].lower() in itm.lower():
                        matched_item = itm
                        break
            
            if not matched_item:
                return await message.channel.send("❌ الغرض المطلوب غير موجود في ممتلكاتك!", delete_after=5)
            
            owned_qty = inv[matched_item]
            prices = update_and_get_market_prices(guild_id)
            unit_price = prices.get(matched_item, 50)
            
            sell_qty = 1
            if last_arg in ["كامل", "الكل", "كل"]:
                sell_qty = owned_qty
            elif last_arg in ["نص", "نصف"]:
                sell_qty = max(1, owned_qty // 2)
            else:
                try:
                    sell_qty = int(last_arg)
                except ValueError:
                    # لو كتب أمر بيع الغرض مباشرة بدون تحديد كمية (يفترض 1)
                    sell_qty = 1
            
            if sell_qty > owned_qty or sell_qty <= 0:
                return await message.channel.send(f"❌ الكمية غير صحيحة. لديك في الممتلكات: `{owned_qty}` فقط.", delete_after=5)
            
            success = remove_from_inventory(guild_id, user_id, matched_item, sell_qty)
            if not success:
                return await message.channel.send("❌ حدث خطأ أثناء إتمام عملية البيع.", delete_after=5)
            
            # سعر البيع يعتمد على سعر السوق الحالي (مثلاً 80% من قيمة الشراء الحالية)
            total_earned = int(unit_price * 0.8 * sell_qty)
            if total_earned < 1: 
                total_earned = sell_qty * 10
                
            new_tot = add_points(guild_id, user_id, total_earned)
            await message.channel.send(f"💸 تم بيع `{sell_qty}` من **{matched_item}** بنجاح واسترداد **{total_earned}** نقطة! الرصيد الحالي: **{new_tot}** نقطة.")
            return

        # أمر عرض قائمة الألعاب الفخمة
        if text in ["العاب", "ألعاب", "/العاب", "الالعاب"]:
            embed = discord.Embed(
                title="✨ قَائِمَة أَعَالِي الأَلْعَابِ وَالتَّحَدِّيَاتِ ✨",
                description="مرحباً بك في عالم الحماس! اختر لعبتك المفضلة عبر كتابة أحد الأوامر التالية في الشات:\n\n"
                            "🎡 `عجلة` - عجلة الحظ الكبرى\n"
                            "🎲 `نرد` - تحدي النرد الحماسي\n"
                            "📦 `صناديق` - فتح الصناديق السرية\n"
                            "✂️ `مقص` - حجر ورقة مقص\n"
                            "🔢 `تخمين` - تحدي تخمين الأرقام\n"
                            "🔮 `حظك` - اكتشف حظك اليومي\n"
                            "⚡ `تحدي السرعة` - اختبار سرعة البديهة\n"
                            "🧮 `حساب` - لعبة الحساب السريع\n"
                            "💎 `كنز` - مغامرة الكنز المفقود\n"
                            "⚽ `بلنتي` - ركلة جزاء حاسمة\n"
                            "🏀 `سلة` - بطولة كرة السلة\n"
                            "🎣 `صيد` - رحلة صيد السمك\n"
                            "🏎️ `سيارات` - سباق السيارات المثير\n"
                            "⛏️ `تعدين` - منجم الذهب والألماس\n"
                            "⚔️ `مبارزة` - ساحة الشرف والمبارزة\n"
                            "🎳 `بولينج` - بطولة البولينج الكبرى\n"
                            "✈️ `طائرة` - معارك الطيران الحربي\n"
                            "🚢 `سفينة` - رحلة عبور العواصف\n"
                            "🏹 `سهم` - مهارة الرماية والسهام\n"
                            "🚀 `فضاء` - رحلة غزو الفضاء\n"
                            "🔐 `قبو` - فك ألغاز القبو السري\n"
                            "🃏 `بوكر` - طاولة سحب الورق\n"
                            "🏺 `فخار` - ورشة صناعة الفخار\n"
                            "🧗‍♂️ `تسلق` - مغامرة تسلق القمم\n"
                            "🧙‍♂️ `سحر` - إتقان التعويذات السحرية\n"
                            "🌋 `بركان` - الهروب الأخير من الحمم\n\n"
                            "💡 *ملاحظة: اكتب اسم اللعبة مباشرة في الشات لبدء اللعب!*",
                color=discord.Color.from_rgb(212, 175, 55) # لون ذهبي فخم
            )
            embed.set_footer(text="🌟 استمتع بقضاء أوقات ممتعة واربح النقاط!", icon_url=message.author.display_avatar.url)
            await message.channel.send(embed=embed)
            return

        # 1. عجلة الحظ
        if text == "عجلة":
            if not self.can_play(guild_id, user_id, "wheel", message): return
            await message.channel.send(embed=discord.Embed(title="🎡 عجلة الحظ الكبرى", description=f"يا {message.author.mention}, اضغط للتدوير:", color=discord.Color.gold()), view=WheelView(guild_id, user_id))
        
        # 2. النرد
        elif text in ["نرد", "زهر"]:
            if not self.can_play(guild_id, user_id, "dice", message): return
            await message.channel.send(embed=discord.Embed(title="🎲 تحدي النرد", description=f"يا {message.author.mention}, اضغط للرمي:", color=discord.Color.blue()), view=DiceView(guild_id, user_id))
        
        # 3. الصناديق
        elif text == "صناديق":
            if not self.can_play(guild_id, user_id, "boxes", message): return
            await message.channel.send(embed=discord.Embed(title="📦 فتح الصناديق", description=f"يا {message.author.mention}, اختر صندوقاً:", color=discord.Color.purple()), view=BoxesView(guild_id, user_id))
        
        # 4. مقص
        elif text in ["مقص", "حجر ورقة مقص"]:
            if not self.can_play(guild_id, user_id, "rps", message): return
            await message.channel.send(embed=discord.Embed(title="✂️ حجر ورقة مقص", description=f"يا {message.author.mention}, اختر سلاحك:", color=discord.Color.teal()), view=RpsView(guild_id, user_id))
        
        # 5. تخمين
        elif text == "تخمين":
            if not self.can_play(guild_id, user_id, "guess", message): return
            await message.channel.send(embed=discord.Embed(title="🔢 تخمين الرقم (من 1 إلى 5)", description=f"يا {message.author.mention}, خمن الرقم:", color=discord.Color.dark_blue()), view=GuessView(guild_id, user_id))
        
        # 6. حظك
        elif text == "حظك":
            if not self.can_play(guild_id, user_id, "luck", message): return
            await message.channel.send(embed=discord.Embed(title="🔮 حظك اليوم", description=f"يا {message.author.mention}, اكتشف حظك:", color=discord.Color.magenta()), view=LuckView(guild_id, user_id))
        
        # 7. تحدي السرعة
        elif text == "تحدي السرعة":
            if not self.can_play(guild_id, user_id, "speed", message): return
            await message.channel.send(embed=discord.Embed(title="⚡ تحدي السرعة", description=f"يا {message.author.mention}, اضغط الآن:", color=discord.Color.red()), view=SpeedView(guild_id, user_id))
        
        # 8. حساب
        elif text == "حساب":
            if not self.can_play(guild_id, user_id, "math", message): return
            n1, n2 = random.randint(1, 20), random.randint(1, 20)
            res = n1 + n2
            is_true = random.choice([True, False])
            fake_res = res if is_true else res + random.choice([-2, 2, 3])
            await message.channel.send(embed=discord.Embed(title="🧮 لعبة الحساب السريع", description=f"يا {message.author.mention}, هل المعادلة صحيحة؟\n**{n1} + {n2} = {fake_res}**", color=discord.Color.orange()), view=MathView(guild_id, user_id, is_true))
        
        # 9. كنز
        elif text == "كنز":
            if not self.can_play(guild_id, user_id, "treasure", message): return
            await message.channel.send(embed=discord.Embed(title="💎 الكنز المفقود", description=f"يا {message.author.mention}, ابدأ الحفر:", color=discord.Color.gold()), view=TreasureView(guild_id, user_id))
        
        # 10. بلنتي
        elif text == "بلنتي":
            if not self.can_play(guild_id, user_id, "penalty", message): return
            await message.channel.send(embed=discord.Embed(title="⚽ ركلة جزاء", description=f"يا {message.author.mention}, اختر زاوية التسديد:", color=discord.Color.green()), view=PenaltyView(guild_id, user_id))
        
        # 11. سلة
        elif text == "سلة":
            if not self.can_play(guild_id, user_id, "basketball", message): return
            await message.channel.send(embed=discord.Embed(title="🏀 كرة السلة", description=f"يا {message.author.mention}, صوب السلة:", color=discord.Color.orange()), view=BasketballView(guild_id, user_id))
        
        # 12. صيد
        elif text == "صيد":
            if not self.can_play(guild_id, user_id, "fishing", message): return
            await message.channel.send(embed=discord.Embed(title="🎣 صيد السمك", description=f"يا {message.author.mention}, ارمِ الصنارة:", color=discord.Color.blue()), view=FishingView(guild_id, user_id))
        
        # 13. سيارات
        elif text == "سيارات":
            if not self.can_play(guild_id, user_id, "racing", message): return
            await message.channel.send(embed=discord.Embed(title="🏎️ سباق السيارات", description=f"يا {message.author.mention}, انطلق بالسباق:", color=discord.Color.dark_red()), view=RacingView(guild_id, user_id))
        
        # 14. تعدين
        elif text == "تعدين":
            if not self.can_play(guild_id, user_id, "mining", message): return
            await message.channel.send(embed=discord.Embed(title="⛏️ التعدين", description=f"يا {message.author.mention}, ابدأ التنقيب:", color=discord.Color.dark_gray()), view=MiningView(guild_id, user_id))
        
        # 15. مبارزة
        elif text == "مبارزة":
            if not self.can_play(guild_id, user_id, "duel", message): return
            await message.channel.send(embed=discord.Embed(title="⚔️ ساحة المبارزة", description=f"يا {message.author.mention}, ادخل المعركة:", color=discord.Color.blurple()), view=DuelView(guild_id, user_id))

        # 16. بولينج
        elif text == "بولينج":
            if not self.can_play(guild_id, user_id, "bowling", message): return
            await message.channel.send(embed=discord.Embed(title="🎳 البولينج", description=f"يا {message.author.mention}, ارمِ الكرة:", color=discord.Color.dark_purple()), view=BowlingView(guild_id, user_id))

        # 17. طائرة
        elif text == "طائرة":
            if not self.can_play(guild_id, user_id, "plane", message): return
            await message.channel.send(embed=discord.Embed(title="✈️ الطيران الحربي", description=f"يا {message.author.mention}, اختر المناورة:", color=discord.Color.blue()), view=PlaneView(guild_id, user_id))

        # 18. سفينة
        elif text == "سفينة":
            if not self.can_play(guild_id, user_id, "ship", message): return
            await message.channel.send(embed=discord.Embed(title="🚢 رحلة بحرية", description=f"يا {message.author.mention}, واجه العاصفة:", color=discord.Color.teal()), view=ShipView(guild_id, user_id))

        # 19. سهم
        elif text == "سهم":
            if not self.can_play(guild_id, user_id, "archery", message): return
            await message.channel.send(embed=discord.Embed(title="🏹 الرماية بالسهام", description=f"يا {message.author.mention}, أطلق السهم:", color=discord.Color.gold()), view=ArcheryView(guild_id, user_id))

        # 20. فضاء
        elif text == "فضاء":
            if not self.can_play(guild_id, user_id, "space", message): return
            await message.channel.send(embed=discord.Embed(title="🚀 مغامرة الفضاء", description=f"يا {message.author.mention}, اختر المسار الفضائي:", color=discord.Color.dark_theme), view=SpaceView(guild_id, user_id))

        # 21. قبو
        elif text == "قبو":
            if not self.can_play(guild_id, user_id, "vault", message): return
            await message.channel.send(embed=discord.Embed(title="🔐 فتح القبو السري", description=f"يا {message.author.mention}, اختر الرمز السري:", color=discord.Color.dark_green()), view=VaultView(guild_id, user_id))

        # 22. بوكر
        elif text == "بوكر":
            if not self.can_play(guild_id, user_id, "poker", message): return
            await message.channel.send(embed=discord.Embed(title="🃏 سحب الورق", description=f"يا {message.author.mention}, اسحب بطاقة الحظ:", color=discord.Color.dark_red()), view=PokerView(guild_id, user_id))

        # 23. فخار
        elif text == "فخار":
            if not self.can_play(guild_id, user_id, "pottery", message): return
            await message.channel.send(embed=discord.Embed(title="🏺 صناعة الفخار", description=f"يا {message.author.mention}, شكل التحفة الفنية:", color=discord.Color.orange()), view=PotteryView(guild_id, user_id))

        # 24. جبل
        elif text == "تسلق":
            if not self.can_play(guild_id, user_id, "climb", message): return
            await message.channel.send(embed=discord.Embed(title="🧗‍♂️ تسلق الجبال", description=f"يا {message.author.mention}, اصعد القمة:", color=discord.Color.default()), view=ClimbView(guild_id, user_id))

        # 25. ساحر
        elif text == "سحر":
            if not self.can_play(guild_id, user_id, "magic", message): return
            await message.channel.send(embed=discord.Embed(title="🧙‍♂️ التعويذة السحرية", description=f"يا {message.author.mention}, اختر العصا السحرية:", color=discord.Color.purple()), view=MagicView(guild_id, user_id))

        # 26. بركان
        elif text == "بركان":
            if not self.can_play(guild_id, user_id, "volcano", message): return
            await message.channel.send(embed=discord.Embed(title="🌋 الهروب من البركان", description=f"يا {message.author.mention}, اختر طريق الهروب:", color=discord.Color.red()), view=VolcanoView(guild_id, user_id))

    def can_play(self, guild_id, user_id, game_key, message):
        can, rem = check_cooldown(guild_id, user_id, game_key)
        if not can:
            self.bot.loop.create_task(message.channel.send(f"⏳ يا {message.author.mention}, انتظر **{rem}** قبل اللعب مجدداً!", delete_after=5))
            return False
        set_cooldown(guild_id, user_id, game_key)
        return True


# --- تعريف الأزرار والـ Views للألعاب الـ 26 ---

class WheelView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🎡 تدوير العجلة", style=discord.ButtonStyle.green)
    async def spin(self, i: discord.Interaction, b: discord.ui.Button):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليست لك!", ephemeral=True)
        won = random.choice([10, 25, 50, 100, 200, 0, 500])
        tot = add_points(self.g, self.u, won) if won > 0 else get_user_data(self.g, self.u)
        desc = f"🎉 مبروك ربحت **{won}** نقطة! الرصيد: **{tot}**" if won > 0 else "❌ خسارة، العجلة وقفت على الصفر."
        await i.response.edit_message(embed=discord.Embed(title="🎡 عجلة الحظ", description=desc, color=discord.Color.gold()), view=None)

class DiceView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🎲 ارمِ النرد", style=discord.ButtonStyle.blurple)
    async def roll(self, i: discord.Interaction, b: discord.ui.Button):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        u_val, b_val = random.randint(1, 6), random.randint(1, 6)
        desc = f"رقمك: {u_val} | رقم البوت: {b_val}\n"
        if u_val > b_val:
            tot = add_points(self.g, self.u, 40)
            desc += f"🏆 فزت وربحت **40** نقطة! (الرصيد: {tot})"
        elif u_val < b_val: desc += "❌ خسرت أمام البوت!"
        else:
            tot = add_points(self.g, self.u, 10)
            desc += f"🤝 تعادل! منحت **10** نقاط."
        await i.response.edit_message(embed=discord.Embed(title="🎲 تحدي النرد", description=desc, color=discord.Color.blue()), view=None)

class BoxesView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id; self.w = random.randint(1, 3)
    @discord.ui.button(label="📦 صندوق 1", style=discord.ButtonStyle.secondary)
    async def b1(self, i: discord.Interaction, b: discord.ui.Button): await self.proc(i, 1)
    @discord.ui.button(label="📦 صندوق 2", style=discord.ButtonStyle.secondary)
    async def b2(self, i: discord.Interaction, b: discord.ui.Button): await self.proc(i, 2)
    @discord.ui.button(label="📦 صندوق 3", style=discord.ButtonStyle.secondary)
    async def b3(self, i: discord.Interaction, b: discord.ui.Button): await self.proc(i, 3)
    async def proc(self, i, choice):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        if choice == self.w:
            tot = add_points(self.g, self.u, 50)
            desc = f"🎉 مبروك! اخترت الصحيح وربحت **50** نقطة! (الرصيد: {tot})"
        else: desc = f"❌ حظ أوفر! الصحيح كان رقم {self.w}."
        await i.response.edit_message(embed=discord.Embed(title="📦 فتح الصناديق", description=desc, color=discord.Color.purple()), view=None)

class RpsView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🪨 حجر", style=discord.ButtonStyle.primary)
    async def rock(self, i, b): await self.play(i, "حجر")
    @discord.ui.button(label="📄 ورقة", style=discord.ButtonStyle.primary)
    async def paper(self, i, b): await self.play(i, "ورقة")
    @discord.ui.button(label="✂️ مقص", style=discord.ButtonStyle.primary)
    async def sc(self, i, b): await self.play(i, "مقص")
    async def play(self, i, choice):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        bot_ch = random.choice(["حجر", "ورقة", "مقص"])
        desc = f"اختيارك: {choice} | البوت: {bot_ch}\n"
        if choice == bot_ch: desc += "🤝 تعادل!"
        elif (choice=="حجر" and bot_ch=="مقص") or (choice=="ورقة" and bot_ch=="حجر") or (choice=="مقص" and bot_ch=="ورقة"):
            tot = add_points(self.g, self.u, 30)
            desc += f"🏆 فزت وربحت **30** نقطة! (الرصيد: {tot})"
        else: desc += "❌ خسرت أمام البوت!"
        await i.response.edit_message(embed=discord.Embed(title="✂️ حجر ورقة مقص", description=desc, color=discord.Color.teal()), view=None)

class GuessView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id; self.t = random.randint(1, 5)
    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
    async def n1(self, i, b): await self.chk(i, 1)
    @discord.ui.button(label="2", style=discord.ButtonStyle.blurple)
    async def n2(self, i, b): await self.chk(i, 2)
    @discord.ui.button(label="3", style=discord.ButtonStyle.blurple)
    async def n3(self, i, b): await self.chk(i, 3)
    @discord.ui.button(label="4", style=discord.ButtonStyle.blurple)
    async def n4(self, i, b): await self.chk(i, 4)
    @discord.ui.button(label="5", style=discord.ButtonStyle.blurple)
    async def n5(self, i, b): await self.chk(i, 5)
    async def chk(self, i, num):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        if num == self.t:
            tot = add_points(self.g, self.u, 40)
            desc = f"🎉 ممتاز! الرقم {self.t}، وربحت **40** نقطة! (الرصيد: {tot})"
        else: desc = f"❌ خطأ! الرقم الصحيح كان {self.t}."
        await i.response.edit_message(embed=discord.Embed(title="🔢 تخمين الرقم", description=desc, color=discord.Color.dark_blue()), view=None)

class LuckView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🔮 اكشف حظك", style=discord.ButtonStyle.green)
    async def lck(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        pr = random.choice([15, 30, 60, 0, 100])
        tot = add_points(self.g, self.u, pr) if pr > 0 else get_user_data(self.g, self.u)
        desc = f"✨ حظك رائع! ربحت **{pr}** نقطة! (الرصيد: {tot})" if pr > 0 else "🌧️ حظك اليوم عاصف ولم تفز بشيء."
        await i.response.edit_message(embed=discord.Embed(title="🔮 حظك اليوم", description=desc, color=discord.Color.magenta()), view=None)

class SpeedView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="⚡ اضغط بأقصى سرعة!", style=discord.ButtonStyle.red)
    async def spd(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        tot = add_points(self.g, self.u, 35)
        await i.response.edit_message(embed=discord.Embed(title="⚡ تحدي السرعة", description=f"🚀 أسرع البرق! منحت **35** نقطة! (الرصيد: {tot})", color=discord.Color.red()), view=None)

class MathView(discord.ui.View):
    def __init__(self, g_id, u_id, ans): super().__init__(timeout=60); self.g, self.u = g_id, u_id; self.ans = ans
    @discord.ui.button(label="✅ صحيح", style=discord.ButtonStyle.green)
    async def y(self, i, b): await self.chk(i, True)
    @discord.ui.button(label="❌ خطأ", style=discord.ButtonStyle.red)
    async def n(self, i, b): await self.chk(i, False)
    async def chk(self, i, val):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        if val == self.ans:
            tot = add_points(self.g, self.u, 45)
            desc = f"🎉 إجابتك ذكية! ربحت **45** نقطة! (الرصيد: {tot})"
        else: desc = "❌ إجابة غير دقيقة."
        await i.response.edit_message(embed=discord.Embed(title="🧮 لعبة الحساب", description=desc, color=discord.Color.orange()), view=None)

class TreasureView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="💎 حفر للكنز", style=discord.ButtonStyle.green)
    async def dig(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        rew = random.choice([50, 100, 0, 150])
        tot = add_points(self.g, self.u, rew) if rew > 0 else get_user_data(self.g, self.u)
        desc = f"🏴‍☠️ وجدت كنزاً يحتوي على **{rew}** نقطة! (الرصيد: {tot})" if rew > 0 else "⛏️ لم تجد سوى الغبار."
        await i.response.edit_message(embed=discord.Embed(title="💎 الكنز المفقود", description=desc, color=discord.Color.gold()), view=None)

class PenaltyView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="⚽ يمين", style=discord.ButtonStyle.blurple)
    async def r(self, i, b): await self.kick(i, "يمين")
    @discord.ui.button(label="⚽ يسار", style=discord.ButtonStyle.blurple)
    async def l(self, i, b): await self.kick(i, "يسار")
    @discord.ui.button(label="⚽ منتصف", style=discord.ButtonStyle.blurple)
    async def m(self, i, b): await self.kick(i, "منتصف")
    async def kick(self, i, dir):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        gk = random.choice(["يمين", "يسار", "منتصف"])
        if dir != gk:
            tot = add_points(self.g, self.u, 40)
            desc = f"⚽ **هدف ساحق!** الحارس طار للاتجاه الخاطئ ({gk}). ربحت **40** نقطة! (الرصيد: {tot})"
        else: desc = "🧤 تصدى الحارس ببراعة!"
        await i.response.edit_message(embed=discord.Embed(title="⚽ ركلة جزاء", description=desc, color=discord.Color.green()), view=None)

class BasketballView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🏀 رامية ثلاثية", style=discord.ButtonStyle.green)
    async def shoot(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        sc = random.choice([True, False, True])
        tot = add_points(self.g, self.u, 35) if sc else get_user_data(self.g, self.u)
        desc = f"🎯 سلة تاريخية! ربحت **35** نقطة! (الرصيد: {tot})" if sc else "❌ اصطدمت الكرة بالحافة."
        await i.response.edit_message(embed=discord.Embed(title="🏀 كرة السلة", description=desc, color=discord.Color.orange()), view=None)

class FishingView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🎣 رمي الصنارة", style=discord.ButtonStyle.primary)
    async def fish(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        c = random.choice([20, 50, 0, 80])
        tot = add_points(self.g, self.u, c) if c > 0 else get_user_data(self.g, self.u)
        desc = f"🐟 اصطدت سمكة وربحت **{c}** نقطة! (الرصيد: {tot})" if c > 0 else "🌊 لم تسحب سوى الأعشاب."
        await i.response.edit_message(embed=discord.Embed(title="🎣 صيد السمك", description=desc, color=discord.Color.blue()), view=None)

class RacingView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🏎️ ضغط وقود", style=discord.ButtonStyle.red)
    async def race(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        win = random.choice([True, False])
        tot = add_points(self.g, self.u, 45) if win else get_user_data(self.g, self.u)
        desc = f"🏆 قطعت خط النهاية أولاً! ربحت **45** نقطة! (الرصيد: {tot})" if win else "💥 تعطلت سيارتك."
        await i.response.edit_message(embed=discord.Embed(title="🏎️ سباق السيارات", description=desc, color=discord.Color.dark_red()), view=None)

class MiningView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="⛏️ تعدين ذهب", style=discord.ButtonStyle.secondary)
    async def mine(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        gold = random.choice([30, 60, 90, 0])
        tot = add_points(self.g, self.u, gold) if gold > 0 else get_user_data(self.g, self.u)
        desc = f"🪙 استخرجت ذهباً بقيمة **{gold}** نقطة! (الرصيد: {tot})" if gold > 0 else "🪨 حفرت في صخور صلبة."
        await i.response.edit_message(embed=discord.Embed(title="⛏️ التعدين", description=desc, color=discord.Color.dark_gray()), view=None)

class DuelView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="⚔️ هجوم بالساحة", style=discord.ButtonStyle.red)
    async def duel(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        win = random.choice([True, False])
        tot = add_points(self.g, self.u, 60) if win else get_user_data(self.g, self.u)
        desc = f"🛡️ انتصرت على خصمك الشرس! ربحت **60** نقطة! (الرصيد: {tot})" if win else "🩸 هُزمت في الساحة."
        await i.response.edit_message(embed=discord.Embed(title="⚔️ ساحة المبارزة", description=desc, color=discord.Color.blurple()), view=None)

class BowlingView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🎳 رمي الكرة", style=discord.ButtonStyle.blurple)
    async def bowl(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        pts = random.choice([0, 20, 50, 80])
        tot = add_points(self.g, self.u, pts) if pts > 0 else get_user_data(self.g, self.u)
        desc = f"🎯 ضربة قوية وأسقطت القوارير! ربحت **{pts}** نقطة! (الرصيد: {tot})" if pts > 0 else "❌ ذهبت الكرة في القناة الجانبية."
        await i.response.edit_message(embed=discord.Embed(title="🎳 البولينج", description=desc, color=discord.Color.dark_purple()), view=None)

class PlaneView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="✈️ مناورة لليسار", style=discord.ButtonStyle.primary)
    async def l(self, i, b): await self.p(i)
    @discord.ui.button(label="✈️ مناورة لليمين", style=discord.ButtonStyle.primary)
    async def r(self, i, b): await self.p(i)
    async def p(self, i):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        win = random.choice([True, False])
        tot = add_points(self.g, self.u, 40) if win else get_user_data(self.g, self.u)
        desc = f"🚀 تجنبت الصواريخ باحتراف وربحت **40** نقطة! (الرصيد: {tot})" if win else "💥 أصابك الصواريخ الحربية."
        await i.response.edit_message(embed=discord.Embed(title="✈️ الطيران الحربي", description=desc, color=discord.Color.blue()), view=None)

class ShipView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🚢 مواجهة العاصفة", style=discord.ButtonStyle.green)
    async def s(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        win = random.choice([True, False])
        tot = add_points(self.g, self.u, 50) if win else get_user_data(self.g, self.u)
        desc = f"⚓ عبرت الأمواج العاتية وربحت **50** نقطة! (الرصيد: {tot})" if win else "🌊 تضررت سفينتك بالعاصفة."
        await i.response.edit_message(embed=discord.Embed(title="🚢 رحلة بحرية", description=desc, color=discord.Color.teal()), view=None)

class ArcheryView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🏹 إطلاق السهم", style=discord.ButtonStyle.blurple)
    async def a(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        hit = random.choice([10, 30, 70, 0])
        tot = add_points(self.g, self.u, hit) if hit > 0 else get_user_data(self.g, self.u)
        desc = f"🎯 أصبت الهدف بدقة وربحت **{hit}** نقطة! (الرصيد: {tot})" if hit > 0 else "❌ أخطأت الهدف تماماً."
        await i.response.edit_message(embed=discord.Embed(title="🏹 الرماية", description=desc, color=discord.Color.gold()), view=None)

class SpaceView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🚀 هبوط على الكوكب", style=discord.ButtonStyle.secondary)
    async def sp(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        rew = random.choice([40, 90, 0])
        tot = add_points(self.g, self.u, rew) if rew > 0 else get_user_data(self.g, self.u)
        desc = f"👽 اكتشفت كنزاً فضائياً بـ **{rew}** نقطة! (الرصيد: {tot})" if rew > 0 else "☄️ واجهتك نيازك مدمرة."
        await i.response.edit_message(embed=discord.Embed(title="🚀 الفضاء", description=desc, color=discord.Color.dark_theme), view=None)

class VaultView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id; self.k = random.randint(1, 4)
    @discord.ui.button(label="🔐 زر 1", style=discord.ButtonStyle.secondary)
    async def v1(self, i, b): await self.c(i, 1)
    @discord.ui.button(label="🔐 زر 2", style=discord.ButtonStyle.secondary)
    async def v2(self, i, b): await self.c(i, 2)
    @discord.ui.button(label="🔐 زر 3", style=discord.ButtonStyle.secondary)
    async def v3(self, i, b): await self.c(i, 3)
    @discord.ui.button(label="🔐 زر 4", style=discord.ButtonStyle.secondary)
    async def v4(self, i, b): await self.c(i, 4)
    async def c(self, i, num):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        if num == self.k:
            tot = add_points(self.g, self.u, 100)
            desc = f"🔓 فتحت القبو بنجاح وربحت **100** نقطة! (الرصيد: {tot})"
        else: desc = f"🔒 الزر خاطئ، القبو أغلق!"
        await i.response.edit_message(embed=discord.Embed(title="🔐 القبو السري", description=desc, color=discord.Color.dark_green()), view=None)

class PokerView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🃏 سحب بطاقة", style=discord.ButtonStyle.red)
    async def pk(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        pts = random.choice([15, 45, 85, 0])
        tot = add_points(self.g, self.u, pts) if pts > 0 else get_user_data(self.g, self.u)
        desc = f"🃏 سحبت ورقة رابحة بقيمة **{pts}** نقطة! (الرصيد: {tot})" if pts > 0 else "❌ ورقة خاسرة."
        await i.response.edit_message(embed=discord.Embed(title="🃏 البطاقات", description=desc, color=discord.Color.dark_red()), view=None)

class PotteryView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🏺 تشكيل الطين", style=discord.ButtonStyle.blurple)
    async def pt(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        win = random.choice([True, False])
        tot = add_points(self.g, self.u, 30) if win else get_user_data(self.g, self.u)
        desc = f"✨ صنعت تحفة فنية وربحت **30** نقطة! (الرصيد: {tot})" if win else "💥 تحطمت التحفة بين يديك."
        await i.response.edit_message(embed=discord.Embed(title="🏺 الفخار", description=desc, color=discord.Color.orange()), view=None)

class ClimbView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🧗‍♂️ تسلق الصخرة", style=discord.ButtonStyle.green)
    async def cl(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        win = random.choice([True, False])
        tot = add_points(self.g, self.u, 50) if win else get_user_data(self.g, self.u)
        desc = f"🏔️ وصلت قمة الجبل وربحت **50** نقطة! (الرصيد: {tot})" if win else "🧗 تزلجت وسقطت نحو البداية."
        await i.response.edit_message(embed=discord.Embed(title="🧗‍♂️ التسلق", description=desc, color=discord.Color.default()), view=None)

class MagicView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🧙‍♂️ تلويح بالعصا", style=discord.ButtonStyle.secondary)
    async def mg(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        pts = random.choice([25, 75, 0])
        tot = add_points(self.g, self.u, pts) if pts > 0 else get_user_data(self.g, self.u)
        desc = f"✨ نجحت التعويذة السحرية بـ **{pts}** نقطة! (الرصيد: {tot})" if pts > 0 else "💨 فشلت التعويذة وتحولت لدخان."
        await i.response.edit_message(embed=discord.Embed(title="🧙‍♂️ السحر", description=desc, color=discord.Color.purple()), view=None)

class VolcanoView(discord.ui.View):
    def __init__(self, g_id, u_id): super().__init__(timeout=60); self.g, self.u = g_id, u_id
    @discord.ui.button(label="🌋 ركض بسرعة للنجاة", style=discord.ButtonStyle.red)
    async def vl(self, i, b):
        if str(i.user.id) != str(self.u): return await i.response.send_message("❌ ليس لك!", ephemeral=True)
        win = random.choice([True, False])
        tot = add_points(self.g, self.u, 60) if win else get_user_data(self.g, self.u)
        desc = f"🏃 هربت من الحمم البركانية وربحت **60** نقطة! (الرصيد: {tot})" if win else "🔥 حاصرتك الحمم البركانية."
        await i.response.edit_message(embed=discord.Embed(title="🌋 البركان", description=desc, color=discord.Color.red()), view=None)


async def setup(bot):
    await bot.add_cog(GamesCog(bot))
