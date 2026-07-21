import discord
from discord.ext import commands
import random
import asyncio
import sqlite3
import os
from datetime import datetime, timedelta

DB_FILE = "database.db"

# قاموس لتتبع وقت آخر تداول واستثمار لكل مستخدم (Cooldown: دقيقتين)
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

# دول التداول (أجنبية)
TRADING_COUNTRIES = ["فرنسا", "أمريكا", "ألمانيا", "بريطانيا", "اليابان", "إيطاليا"]

# دول الاستثمار (عربية)
INVESTMENT_COUNTRIES = ["السعودية", "الإمارات", "مصر", "المغرب", "الكويت", "قطر", "الأردن", "البحرين"]

class MarketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_id = 1528917497246515221

    def check_cooldown(self, user_id, action_type):
        now = datetime.now()
        key = (user_id, action_type)
        if key in market_cooldowns:
            expire_time = market_cooldowns[key]
            if now < expire_time:
                remaining = int((expire_time - now).total_seconds())
                return remaining
        market_cooldowns[key] = now + timedelta(minutes=2)
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

        # 1. نظام التداول (دول أجنبية) - مثال: تداول 1000
        if text.startswith("تداول") or text.startswith("!تداول"):
            rem = self.check_cooldown(user_id, "trading")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** قبل القيام بعملية تداول أخرى!", delete_after=5)

            parts = message.content.strip().split()
            if len(parts) < 2 or not parts[1].isdigit():
                return await message.channel.send("❌ الاستخدام الصحيح: `تداول [المبلغ]` (مثال: `تداول 1000`)", delete_after=5)
            
            amount = int(parts[1])
            if amount <= 0:
                return await message.channel.send("❌ يرجى إدخال مبلغ صحيح أكبر من الصفر.", delete_after=5)

            current_pts = get_user_points(guild_id, user_id)
            if current_pts < amount:
                return await message.channel.send(f"❌ نقاطك غير كافية! رصيدك الحالي `{current_pts}` نقطة.", delete_after=5)

            countries_str = " ، ".join([f"**{c}**" for c in TRADING_COUNTRIES])
            embed = discord.Embed(
                title="📈 نافذة سوق التداول الأجنبي",
                description=f"مبلغ التداول: `{amount}` نقطة.\n\nاختر إحدى الدول الأجنبية التالية واكتب اسمها في الشات خلال 15 ثانية:\n{countries_str}",
                color=discord.Color.orange()
            )
            await message.channel.send(embed=embed)

            def check(m):
                return m.author.id == user_id and m.channel.id == channel_id and m.content.strip() in TRADING_COUNTRIES

            try:
                user_msg = await self.bot.wait_for("message", timeout=15.0, check=check)
                chosen_country = user_msg.content.strip()
                
                # حساب النتيجة (ربح أو خسارة عشوائية مع نسبة نجاح)
                is_win = random.choice([True, False, True]) # حظ محتمل
                if is_win:
                    percentage = random.randint(15, 85)
                    profit = int(amount * (percentage / 100))
                    new_total = add_points(guild_id, user_id, profit)
                    res_embed = discord.Embed(
                        title=f"🟢 نتيجة التداول في ({chosen_country})",
                        description=f"🎉 **مبروك! نجحت صفقة التداول الأجنبي.**\n📊 نسبة النجاح: `+{percentage}%`\n💰 الربح المحقق: `+{profit}` نقطة\n💼 رصيدك الجديد: `{new_total}` نقطة",
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
                await message.channel.send(embed=res_embed)
            except asyncio.TimeoutError:
                await message.channel.send(f"⌛ انتهى الوقت ولم تقم باختيار الدولة الأجنبية المناسبة للتداول!")
            return

        # 2. نظام الاستثمار (دول عربية) - مثال: استثمار 1000
        if text.startswith("استثمار") or text.startswith("!استثمار"):
            rem = self.check_cooldown(user_id, "investment")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** قبل القيام بعملية استثمار أخرى!", delete_after=5)

            parts = message.content.strip().split()
            if len(parts) < 2 or not parts[1].isdigit():
                return await message.channel.send("❌ الاستخدام الصحيح: `استثمار [المبلغ]` (مثال: `استثمار 1000`)", delete_after=5)
            
            amount = int(parts[1])
            if amount <= 0:
                return await message.channel.send("❌ يرجى إدخال مبلغ صحيح أكبر من الصفر.", delete_after=5)

            current_pts = get_user_points(guild_id, user_id)
            if current_pts < amount:
                return await message.channel.send(f"❌ نقاطك غير كافية للاستثمار! رصيدك الحالي `{current_pts}` نقطة.", delete_after=5)

            countries_str = " ، ".join([f"**{c}**" for c in INVESTMENT_COUNTRIES])
            embed = discord.Embed(
                title="🏢 نافذة صندوق الاستثمار العربي",
                description=f"مبلغ الاستثمار: `{amount}` نقطة.\n\nاختر الدولة العربية المناسبة واكتب اسمها في الشات خلال 15 ثانية:\n{countries_str}",
                color=discord.Color.gold()
            )
            await message.channel.send(embed=embed)

            def check(m):
                return m.author.id == user_id and m.channel.id == channel_id and m.content.strip() in INVESTMENT_COUNTRIES

            try:
                user_msg = await self.bot.wait_for("message", timeout=15.0, check=check)
                chosen_country = user_msg.content.strip()
                
                # حساب النتيجة للاستثمار (دول عربية)
                is_win = random.choice([True, True, False]) # فرصة جيدة للأرباح
                if is_win:
                    percentage = random.randint(20, 100)
                    profit = int(amount * (percentage / 100))
                    new_total = add_points(guild_id, user_id, profit)
                    res_embed = discord.Embed(
                        title=f"🟢 نتيجة الاستثمار في ({chosen_country})",
                        description=f"🌟 **ألف مبروك! أثمر المشروع الاستثماري العربي بنجاح.**\n📊 نسبة العائد والنجاح: `+{percentage}%`\n💰 العوائد النقدية: `+{profit}` نقطة\n💼 رصيدك الجديد: `{new_total}` نقطة",
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
                await message.channel.send(embed=res_embed)
            except asyncio.TimeoutError:
                await message.channel.send(f"⌛ انتهى الوقت ولم تقم باختيار الدولة العربية للاستثمار!")
            return

async def setup(bot):
    await bot.add_cog(MarketCog(bot))
