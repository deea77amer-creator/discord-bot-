import discord
from discord.ext import commands
import random
import asyncio
import sqlite3
import os
from datetime import datetime, timedelta

DB_FILE = "database.db"

# قاموس لتتبع وقت آخر تداول واستثمار لكل مستخدم (Cooldown: دقيقتين عند النجاح فقط)
market_cooldowns = {}

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

# دول التداول (أجنبية) بأسماء حقيقية وواضحة
TRADING_COUNTRIES = [
    {"name": "أمريكا", "emoji": "🇺🇸", "desc": "سوق وول ستريت"},
    {"name": "بريطانيا", "emoji": "🇬🇧", "desc": "بورصة لندن"},
    {"name": "ألمانيا", "emoji": "🇩🇪", "desc": "السوق الأوروبي"},
    {"name": "اليابان", "emoji": "🇯🇵", "desc": "بورصة طوكيو"},
    {"name": "فرنسا", "emoji": "🇫🇷", "desc": "اسواق باريس"},
    {"name": "إيطاليا", "emoji": "🇮🇹", "desc": "البورصة الإيطالية"}
]

# دول الاستثمار (عربية) بأسماء حقيقية وواضحة
INVESTMENT_COUNTRIES = [
    {"name": "السعودية", "emoji": "🇸🇦", "desc": "السوق السعودي (تداول)"},
    {"name": "الإمارات", "emoji": "🇦🇪", "desc": "دبي المالي"},
    {"name": "مصر", "emoji": "🇪🇬", "desc": "بورصة مصر"},
    {"name": "الكويت", "emoji": "🇰🇼", "desc": "البورصة الكويتية"},
    {"name": "قطر", "emoji": "🇶🇦", "desc": "بورصة قطر"},
    {"name": "المغرب", "emoji": "🇲🇦", "desc": "سوق الدار البيضاء"}
]

# قائمة الأصول والممتلكات العشوائية للشراء والبيع والتحويل بالعدد
ASSETS_LIST = [
    {"name": "فيلا فاخرة", "emoji": "🏰", "price": 5000},
    {"name": "عمارة تجارية", "emoji": "🏢", "price": 12000},
    {"name": "سيارة فارهة", "emoji": "🏎️", "price": 2500},
    {"name": "شركة تقنية", "emoji": "💻", "price": 20000},
    {"name": "متجر إلكتروني", "emoji": "🛒", "price": 1000}
]

class CountrySelect(discord.ui.Select):
    def __init__(self, countries):
        options = [
            discord.SelectOption(label=c["name"], description=c["desc"], emoji=c["emoji"])
            for c in countries
        ]
        super().__init__(placeholder="اختر الدولة...", min_values=1, max_values=1, options=options)
        self.selected_value = None

    async def callback(self, interaction: discord.Interaction):
        self.selected_value = self.values[0]
        await interaction.response.defer()
        self.view.stop()

class AssetSelect(discord.ui.Select):
    def __init__(self, assets):
        options = [
            discord.SelectOption(label=f"{a['name']} (السعر: {a['price']} نقطة)", description=f"شراء أو تحويل بالعدد", emoji=a["emoji"])
            for a in assets
        ]
        super().__init__(placeholder="اختر الممتلك أو الأصل...", min_values=1, max_values=1, options=options)
        self.selected_value = None

    async def callback(self, interaction: discord.Interaction):
        self.selected_value = self.values[0]
        await interaction.response.defer()
        self.view.stop()

class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="إلغاء")

    async def callback(self, interaction: discord.Interaction):
        self.view.cancelled = True
        await interaction.response.send_message("❌ تم إلغاء العملية.", ephemeral=True)
        self.view.stop()

class MarketView(discord.ui.View):
    def __init__(self, countries):
        super().__init__(timeout=15.0)
        self.select = CountrySelect(countries)
        self.add_item(self.select)
        self.add_item(CancelButton())
        self.cancelled = False

    async def on_timeout(self):
        self.stop()

class AssetView(discord.ui.View):
    def __init__(self, assets):
        super().__init__(timeout=15.0)
        self.select = AssetSelect(assets)
        self.add_item(self.select)
        self.add_item(CancelButton())
        self.cancelled = False

    async def on_timeout(self):
        self.stop()

class MarketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_id = 1528917497246515221

    def set_cooldown(self, user_id, action_type):
        market_cooldowns[(user_id, action_type)] = datetime.now() + timedelta(minutes=2)

    def check_cooldown(self, user_id, action_type):
        now = datetime.now()
        key = (user_id, action_type)
        if key in market_cooldowns:
            expire_time = market_cooldowns[key]
            if now < expire_time:
                remaining = int((expire_time - now).total_seconds())
                return remaining
        return 0

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        text = message.content.strip().lower()
        guild_id = message.guild.id
        user_id = message.author.id
        channel_id = message.channel.id

        # التحقق من أن الأوامر تعمل فقط في القناة المحددة حصراً
        if channel_id != self.target_channel_id:
            return

        # 3. نظام شراء الممتلكات بالعدد (مثال: شراء 18 فيلا فاخرة أو شراء عشوائي)
        if text.startswith("شراء") or text.startswith("!شراء"):
            parts = message.content.strip().split()
            if len(parts) < 3 or not parts[1].isdigit():
                return await message.channel.send("❌ الاستخدام الصحيح: `شراء [العدد]` (مثال: `شراء 18`)", delete_after=5)
            
            count = int(parts[1])
            if count <= 0:
                return await message.channel.send("❌ يرجى إدخال عدد صحيح أكبر من الصفر.", delete_after=5)

            view = AssetView(ASSETS_LIST)
            embed = discord.Embed(
                title="🛒 متجر الممتلكات والأصول",
                description=f"العدد المطلوب شراؤه: `{count}`\nاختر الأصل أو الممتلك من القائمة أدناه:",
                color=discord.Color.blue()
            )
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.cancelled or not view.select.selected_value:
                try:
                    await msg.delete()
                except:
                    pass
                return

            chosen_text = view.select.selected_value
            # استخراج اسم الأصل فقط بدون السعر
            chosen_asset = chosen_text.split(" (السعر:")[0]
            
            # إيجاد سعر الأصل الواحد
            asset_obj = next((a for a in ASSETS_LIST if a["name"] in chosen_asset), None)
            if not asset_obj:
                return await message.channel.send("❌ حدث خطأ في اختيار الأصل.", delete_after=5)

            total_cost = asset_obj["price"] * count
            current_pts = get_user_points(guild_id, user_id)

            if current_pts < total_cost:
                return await message.channel.send(f"❌ نقاطك غير كافية لشراء هذا العدد! التكلفة الإجمالية: `{total_cost}` نقطة، ورصيدك: `{current_pts}` نقطة.", delete_after=5)

            new_total = add_points(guild_id, user_id, -total_cost)
            success_embed = discord.Embed(
                title="✅ تم الشراء بنجاح",
                description=ف f"🛍️ لقد قمت بشراء **{count}** من ({chosen_asset}) بنجاح!\n💰 التكلفة الإجمالية: `-{total_cost}` نقطة\n💼 رصيدك الحالي: `{new_total}` نقطة",
                color=discord.Color.green()
            )
            try:
                await msg.edit(embed=success_embed, view=None)
            except:
                await message.channel.send(embed=success_embed)
            return

        # 4. نظام تحويل الممتلكات (مثال: تحويل ممتلكات @الشخص العدد)
        if text.startswith("تحويل ممتلكات") or text.startswith("!تحويل ممتلكات"):
            if not message.mentions:
                return await message.channel.send("❌ يرجى منشن الشخص المراد التحويل له (مثال: `تحويل ممتلكات @user 5`)", delete_after=5)
            
            target_user = message.mentions[0]
            if target_user.id == user_id:
                return await message.channel.send("❌ لا يمكنك تحويل ممتلكات لنفسك!", delete_after=5)

            parts = message.content.strip().split()
            # البحث عن الرقم الأخير في الأمر ليمثل العدد
            count = 0
            for p in reversed(parts):
                if p.isdigit():
                    count = int(p)
                    break

            if count <= 0:
                return await message.channel.send("❌ يرجى تحديد العدد الصحيح للممتلكات المراد تحويلها (مثال: `تحويل ممتلكات @user 3`)", delete_after=5)

            view = AssetView(ASSETS_LIST)
            embed = discord.Embed(
                title="🎁 قائمة تحويل الممتلكات",
                description=f"المستلم: {target_user.mention}\nالعدد المراد تحويله: `{count}`\nاختر نوع الممتلك من القائمة أدناه للتحويل:",
                color=discord.Color.purple()
            )
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.cancelled or not view.select.selected_value:
                try:
                    await msg.delete()
                except:
                    pass
                return

            chosen_text = view.select.selected_value
            chosen_asset = chosen_text.split(" (السعر:")[0]

            transfer_embed = discord.Embed(
                title="✨ تمت عملية تحويل الممتلكات",
                description=f"📦 تم تحويل **{count}** من ({chosen_asset}) بنجاح إلى العضو {target_user.mention}!",
                color=discord.Color.gold()
            )
            try:
                await msg.edit(embed=transfer_embed, view=None)
            except:
                await message.channel.send(embed=transfer_embed)
            return

        # 1. نظام التداول (دول أجنبية)
        if text.startswith("تداول") or text.startswith("!تداول"):
            parts = message.content.strip().split()
            current_pts = get_user_points(guild_id, user_id)

            if len(parts) < 2:
                return await message.channel.send("❌ الاستخدام الصحيح: `تداول [المبلغ]` أو `تداول كامل`", delete_after=5)
            
            if parts[1] == "كامل":
                amount = current_pts
            elif parts[1].isdigit():
                amount = int(parts[1])
            else:
                return await message.channel.send("❌ يرجى كتابة مبلغ صحيح أو كلمة `كامل`.", delete_after=5)

            if amount <= 0:
                return await message.channel.send("❌ ليس لديك نقاط كافية أو رصيدك صفر للتداول.", delete_after=5)

            if current_pts < amount:
                return await message.channel.send(f"❌ نقاطك غير كافية! رصيدك الحالي `{current_pts}` نقطة.", delete_after=5)

            rem = self.check_cooldown(user_id, "trading")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** قبل القيام بعملية تداول أخرى!", delete_after=5)

            view = MarketView(TRADING_COUNTRIES)
            embed = discord.Embed(
                title="📈 نافذة سوق التداول الأجنبي",
                description=f"المبلغ: `{amount}`\n\nاختر الدولة أو السوق من القائمة أدناه:",
                color=discord.Color.orange()
            )
            msg = await message.channel.send(embed=embed, view=view)

            await view.wait()

            if view.cancelled or not view.select.selected_value:
                try:
                    await msg.delete()
                except:
                    pass
                return

            chosen_country = view.select.selected_value
            self.set_cooldown(user_id, "trading")

            is_win = random.choice([True, False, True])
            if is_win:
                percentage = random.randint(15, 85)
                profit = int(amount * (percentage / 100))
                new_total = add_points(guild_id, user_id, profit)
                res_embed = discord.Embed(
                    title=f"🟢 نتيجة التداول في ({chosen_country})",
                    description=f"🎉 **مبروك! نجحت صفقة التداول.**\n📊 نسبة النجاح: `+{percentage}%`\n💰 الربح المحقق: `+{profit}` نقطة\n💼 رصيدك الجديد: `{new_total}` نقطة",
                    color=discord.Color.green()
                )
            else:
                percentage = random.randint(10, 60)
                loss = int(amount * (percentage / 100))
                new_total = add_points(guild_id, user_id, -loss)
                res_embed = discord.Embed(
                    title=f"🔴 نتيجة التداول في ({chosen_country})",
                    description=f"📉 **للأسف! هبطت السوق وخسرت الصفقة.**\n📊 نسبة الخسارة: `-{percentage}%`\n💸 الخسارة: `-{loss}` نقطة\n💼 رصيدك الجديد: `{new_total}` نقطة",
                    color=discord.Color.red()
                )
            try:
                await msg.edit(embed=res_embed, view=None)
            except:
                await message.channel.send(embed=res_embed)
            return

        # 2. نظام الاستثمار (دول عربية)
        if text.startswith("استثمار") or text.startswith("!استثمار"):
            parts = message.content.strip().split()
            current_pts = get_user_points(guild_id, user_id)

            if len(parts) < 2:
                return await message.channel.send("❌ الاستخدام الصحيح: `استثمار [المبلغ]` أو `استثمار كامل`", delete_after=5)
            
            if parts[1] == "كامل":
                amount = current_pts
            elif parts[1].isdigit():
                amount = int(parts[1])
            else:
                return await message.channel.send("❌ يرجى كتابة مبلغ صحيح أو كلمة `كامل`.", delete_after=5)

            if amount <= 0:
                return await message.channel.send("❌ ليس لديك نقاط كافية أو رصيدك صفر للاستثمار.", delete_after=5)

            if current_pts < amount:
                return await message.channel.send(f"❌ نقاطك غير كافية للاستثمار! رصيدك الحالي `{current_pts}` نقطة.", delete_after=5)

            rem = self.check_cooldown(user_id, "investment")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** قبل القيام بعملية استثمار أخرى!", delete_after=5)

            view = MarketView(INVESTMENT_COUNTRIES)
            embed = discord.Embed(
                title="🏢 نافذة صندوق الاستثمار العربي",
                description=f"المبلغ: `{amount}`\n\nاختر الدولة العربية من القائمة أدناه:",
                color=discord.Color.gold()
            )
            msg = await message.channel.send(embed=embed, view=view)

            await view.wait()

            if view.cancelled or not view.select.selected_value:
                try:
                    await msg.delete()
                except:
                    pass
                return

            chosen_country = view.select.selected_value
            self.set_cooldown(user_id, "investment")

            is_win = random.choice([True, True, False])
            if is_win:
                percentage = random.randint(20, 100)
                profit = int(amount * (percentage / 100))
                new_total = add_points(guild_id, user_id, profit)
                res_embed = discord.Embed(
                    title=f"🟢 نتيجة الاستثمار في ({chosen_country})",
                    description=f"🌟 **ألف مبروك! أثمر المشروع الاستثماري بنجاح.**\n📊 نسبة العائد والنجاح: `+{percentage}%`\n💰 العوائد النقدية: `+{profit}` نقطة\n💼 رصيدك الجديد: `{new_total}` نقطة",
                    color=discord.Color.green()
                )
            else:
                percentage = random.randint(10, 50)
                loss = int(amount * (percentage / 100))
                new_total = add_points(guild_id, user_id, -loss)
                res_embed = discord.Embed(
                    title=f"🔴 نتيجة الاستثمار في ({chosen_country})",
                    description=f"📉 **تراجع طفيف في أرباح المشروع.**\n📊 نسبة الهبوط: `-{percentage}%`\n💸 قيمة الخسارة: `-{loss}` نقطة\n💼 رصيدك الجديد: `{new_total}` نقطة",
                    color=discord.Color.red()
                )
            try:
                await msg.edit(embed=res_embed, view=None)
            except:
                await message.channel.send(embed=res_embed)
            return

async def setup(bot):
    await bot.add_cog(MarketCog(bot))
