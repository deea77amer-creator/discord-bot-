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

# دول التداول (أجنبية) مع رموزها وتصميم مشابه للصور
TRADING_COUNTRIES = [
    {"name": "USDT", "emoji": "🟢", "desc": "1"},
    {"name": "SOL", "emoji": "🟣", "desc": "2"},
    {"name": "BNB", "emoji": "🟡", "desc": "3"},
    {"name": "XRP", "emoji": "⚪", "desc": "4"},
    {"name": "BTC", "emoji": "🟠", "desc": "7"},
    {"name": "ETH", "emoji": "🔷", "desc": "8"}
]

# دول الاستثمار (عربية) مع رموز وتصميم مشابه
INVESTMENT_COUNTRIES = [
    {"name": "السعودية", "emoji": "🇸🇦", "desc": "استثمار الخليج"},
    {"name": "الإمارات", "emoji": "🇦🇪", "desc": "دبي الم المالية"},
    {"name": "مصر", "emoji": "🇪🇬", "desc": "سوق المحروسة"},
    {"name": "المغرب", "emoji": "🇲🇦", "desc": "استثمار الشمال"},
    {"name": "الكويت", "emoji": "🇰🇼", "desc": "الصندوق الكويتي"},
    {"name": "قطر", "emoji": "🇶🇦", "desc": "الدوحة للاستثمار"}
]

class CountrySelect(discord.ui.Select):
    def __init__(self, countries):
        options = [
            discord.SelectOption(label=c["name"], description=c["desc"], emoji=c["emoji"])
            for c in countries
        ]
        super().__init__(placeholder="اختر العملة أو الدولة...", min_values=1, max_values=1, options=options)
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

        # 1. نظام التداول (دول أجنبية)
        if text.startswith("تداول") or text.startswith("!تداول"):
            parts = message.content.strip().split()
            current_pts = get_user_points(guild_id, user_id)

            # معالجة "تداول كامل" أو عدم إدخال رقم
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

            # التحقق من الـ Cooldown فقط عند بدء عملية صحيحة
            rem = self.check_cooldown(user_id, "trading")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** قبل القيام بعملية تداول أخرى!", delete_after=5)

            view = MarketView(TRADING_COUNTRIES)
            embed = discord.Embed(
                title="📈 نافذة سوق التداول الأجنبي",
                description=f"المبلغ: `{amount}`\n\nاختر العملة أو الدولة من القائمة أدناه:",
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
            
            # تفعيل الـ Cooldown بعد نجاح الخطوة واختيار الدولة
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

            # التحقق من الـ Cooldown فقط عند بدء عملية صحيحة
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
            
            # تفعيل الـ Cooldown بعد نجاح الاختيار
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
