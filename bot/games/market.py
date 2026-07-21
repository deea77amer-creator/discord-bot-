import discord
from discord.ext import commands
import random
import asyncio
import os
from datetime import datetime, timedelta
from pymongo import MongoClient

# --- الاتصال بقاعدة البيانات السحابية MongoDB الموحدة ---
MONGO_URL = os.getenv("MONGO_URL")
db = None
users_collection = None

if MONGO_URL:
    try:
        client = MongoClient(MONGO_URL)
        db = client["discord_bot_db"]
        users_collection = db["users"]
    except Exception as e:
        print(f"Error connecting to MongoDB in games.py: {e}")

# قاموس لتتبع وقت آخر تداول واستثمار وباقي الأوامر لكل مستخدم (Cooldown: دقيقتين)
market_cooldowns = {}

# قائمة الأسعار الجديدة والمستقلة تماماً (أصناف جديدة كلياً)
DYNAMIC_ASSETS = [
    {"name": "سيف الأساطير", "emoji": "⚔️", "price": 1500, "desc": "سيف حربي أسطوري يزيد هيبتك"},
    {"name": "درع التيتانيوم", "emoji": "🛡️", "price": 2800, "desc": "درع حصين يصد أقوى الضربات"},
    {"name": "جرعة الإكسير الذهبي", "emoji": "🧪", "price": 850, "desc": "جرعة نادرة تمنحك طاقة مضاعفة"},
    {"name": "خنجر الظل الخفي", "emoji": "🗡️", "price": 1200, "desc": "سلاح سريع للضربات المباغتة"},
    {"name": "تفاحة الطاقة السحرية", "emoji": "🍎", "price": 300, "desc": "تنعش طاقتك وتمنحك حيوية فورية"},
    {"name": "عباءة التخفي الكبرى", "emoji": "🧥", "price": 4500, "desc": "تعطيك حماية مطلقة وهيبة ملكية"}
]
last_price_update = datetime.now()

def update_dynamic_prices():
    global last_price_update
    if datetime.now() - last_price_update > timedelta(minutes=3):
        for asset in DYNAMIC_ASSETS:
            change_percent = random.uniform(-0.15, 0.20)
            asset["price"] = max(100, int(asset["price"] * (1 + change_percent)))
        last_price_update = datetime.now()

def get_user_points(guild_id, user_id):
    if users_collection is None:
        return 0
    query = {"guild_id": str(guild_id), "user_id": str(user_id)}
    doc = users_collection.find_one(query)
    if doc:
        return doc.get("points", 0)
    return 0

def add_points(guild_id, user_id, amount):
    if users_collection is None:
        return 0
    query = {"guild_id": str(guild_id), "user_id": str(user_id)}
    doc = users_collection.find_one(query)
    
    if not doc:
        new_pts = max(0, amount)
        users_collection.insert_one({
            "guild_id": str(guild_id),
            "user_id": str(user_id),
            "points": new_pts,
            "joins": 0,
            "leaves": 0,
            "checkins_count": 0,
            "manual_leaves_count": 0,
            "last_checkin": "",
            "last_leave": ""
        })
        return new_pts
    else:
        current_pts = doc.get("points", 0)
        new_pts = max(0, current_pts + amount)
        users_collection.update_one(query, {"$set": {"points": new_pts}})
        return new_pts

TRADING_COUNTRIES = [
    {"name": "أمريكا", "emoji": "🇺🇸", "desc": "سوق وول ستريت"},
    {"name": "بريطانيا", "emoji": "🇬🇧", "desc": "بورصة لندن"},
    {"name": "ألمانيا", "emoji": "🇩🇪", "desc": "السوق الأوروبي"},
    {"name": "اليابان", "emoji": "🇯🇵", "desc": "بورصة طوكيو"},
    {"name": "فرنسا", "emoji": "🇫🇷", "desc": "اسواق باريس"},
    {"name": "إيطاليا", "emoji": "🇮🇹", "desc": "البورصة الإيطالية"}
]

INVESTMENT_COUNTRIES = [
    {"name": "السعودية", "emoji": "🇸🇦", "desc": "السوق السعودي (تداول)"},
    {"name": "الإمارات", "emoji": "🇦🇪", "desc": "دبي المالي"},
    {"name": "مصر", "emoji": "🇪🇬", "desc": "بورصة مصر"},
    {"name": "الكويت", "emoji": "🇰🇼", "desc": "البورصة الكويتية"},
    {"name": "قطر", "emoji": "🇶🇦", "desc": "بورصة قطر"},
    {"name": "المغرب", "emoji": "🇲🇦", "desc": "سوق الدار البيضاء"}
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
        update_dynamic_prices()
        options = [
            discord.SelectOption(label=f"{a['name']}", description=f"السعر: {a['price']} نقطة | {a['desc']}", emoji=a["emoji"])
            for a in assets
        ]
        super().__init__(placeholder="اختر المنتج من المتجر...", min_values=1, max_values=1, options=options)
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

        if channel_id != self.target_channel_id:
            return

        # 0. أمر اعطاء النقاط
        if text.startswith("اعطاء") or text.startswith("!اعطاء") or text.startswith("/اعطاء"):
            if message.author.id != message.guild.owner_id:
                return await message.channel.send("❌ هذا الأمر مخصص لمالك السيرفر فقط!", delete_after=5)
            
            parts = message.content.strip().split()
            if len(parts) < 3 or not message.mentions:
                return await message.channel.send("❌ الاستخدام الصحيح: `اعطاء @الشخص المبلغ`", delete_after=5)
            
            target_user = message.mentions[0]
            try:
                amount = int(parts[2])
            except ValueError:
                return await message.channel.send("❌ يرجى كتابة رقم صحيح للمبلغ.", delete_after=5)
            
            new_tot = add_points(guild_id, target_user.id, amount)
            return await message.channel.send(f"✅ تم إضافة **{amount}** نقطة بنجاح إلى {target_user.mention}!\nرصيده الحالي: `{new_tot}` نقطة.")

        # 1. نظام الرصيد الموحد
        if text.startswith("رصيد") or text.startswith("!رصيد"):
            target = message.mentions[0] if message.mentions else message.author
            pts = get_user_points(guild_id, target.id)
            return await message.channel.send(f"👤 العضو: {target.mention}\n💰 رصيدك الحالي: `{pts}` نقطة")

        # 2. نظام الاسعار
        if text.startswith("اسعار") or text.startswith("!اسعار") or text.startswith("أسعار"):
            update_dynamic_prices()
            rem_seconds = 180 - int((datetime.now() - last_price_update).total_seconds())
            mins, secs = divmod(max(0, rem_seconds), 60)
            
            desc = f"⏰ سيتم تحديث الأسعار بعد : `{mins:02d}:{secs:02d}`\n\n"
            for asset in DYNAMIC_ASSETS:
                trend = random.choice(["📈 صاعد", "📉 هابط"])
                desc += f"{asset['emoji']} **{asset['name']}** ⟵ `{asset['price']:,}` نقطة ({trend})\n   └ *{asset['desc']}*\n\n"
            
            embed = discord.Embed(title="🛒 قائمة أسعار المتجر والمقتنيات الأسطورية", description=desc, color=discord.Color.dark_theme())
            return await message.channel.send(embed=embed)

        # 3. نظام الوقت
        if text.startswith("وقت") or text.startswith("!وقت"):
            commands_list = ["استثمار", "تداول", "شراء", "بيع"]
            
            desc = ""
            for cmd in commands_list:
                act_key = "investment" if cmd == "استثمار" else ("trading" if cmd == "تداول" else cmd)
                rem = self.check_cooldown(user_id, act_key)
                if rem > 0:
                    mins, secs = divmod(rem, 60)
                    desc += f"• **{cmd}**: 🔴 متبقي `{mins} دقيقة و {secs} ثانية`\n"
                else:
                    desc += f"• **{cmd}**: 🟢 متاح الآن للاستخدام\n"
            
            embed = discord.Embed(title="⏳ حالة الأوامر والوقت (Cooldowns)", description=desc, color=discord.Color.blurple())
            return await message.channel.send(embed=embed)

        # 4. نظام الشراء التفاعلي بالأزرار
        if text.startswith("شراء") or text.startswith("!شراء"):
            update_dynamic_prices()
            parts = message.content.strip().split()
            count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1

            view = AssetView(DYNAMIC_ASSETS)
            embed = discord.Embed(title="🛒 متجر الشراء التفاعلي", description=f"الكمية المحددة: **{count}**\nاختر المنتج الذي تريد شراءه من القائمة أدناه:", color=discord.Color.blue())
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.cancelled or not view.select.selected_value:
                try: await msg.delete()
                except: pass
                return

            chosen_asset_name = view.select.selected_value
            asset_obj = next((a for a in DYNAMIC_ASSETS if a["name"] == chosen_asset_name), None)
            if not asset_obj:
                return await message.channel.send("❌ المنتج غير موجود.", delete_after=5)

            total_cost = asset_obj["price"] * count
            current_pts = get_user_points(guild_id, user_id)

            if current_pts < total_cost:
                return await message.channel.send(f"❌ نقاطك غير كافية لشراء هذا المنتج! رصيدك: `{current_pts}` | التكلفة المطلوبة: `{total_cost:,}`", delete_after=5)

            new_total = add_points(guild_id, user_id, -total_cost)
            success_msg = f"🎉 مبروك يا {message.author.mention}! اشتريت `{count}` من `{chosen_asset_name}` بنجاح مقابل `{total_cost:,}` نقطة!\n💼 رصيدك المتبقي: `{new_total:,}` نقطة."
            try: await msg.edit(content=success_msg, embed=None, view=None)
            except: await message.channel.send(success_msg)
            return

        # 5. نظام البيع التفاعلي بالأزرار
        if text.startswith("بيع") or text.startswith("!بيع"):
            update_dynamic_prices()
            parts = message.content.strip().split()
            count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1

            view = AssetView(DYNAMIC_ASSETS)
            embed = discord.Embed(title="💰 سوق البيع التفاعلي", description=f"الكمية المحددة: **{count}**\nاختر المنتج المراد بيعه من القائمة أدناه (يتم استرداد 80% من القيمة):", color=discord.Color.orange())
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.cancelled or not view.select.selected_value:
                try: await msg.delete()
                except: pass
                return

            chosen_asset_name = view.select.selected_value
            asset_obj = next((a for a in DYNAMIC_ASSETS if a["name"] == chosen_asset_name), None)
            if not asset_obj:
                return await message.channel.send("❌ المنتج غير موجود.", delete_after=5)

            total_gain = int((asset_obj["price"] * count) * 0.8)
            new_total = add_points(guild_id, user_id, total_gain)
            success_msg = f"✅ تم بيع `{count}` من `{chosen_asset_name}` بنجاح واسترداد `{total_gain:,}` نقطة!\n💼 رصيدك الحالي: `{new_total:,}` نقطة."
            try: await msg.edit(content=success_msg, embed=None, view=None)
            except: await message.channel.send(success_msg)
            return

        # 6. نظام تحويل النقاط
        if text.startswith("تحويل") or text.startswith("!تحويل"):
            if not message.mentions:
                return await message.channel.send("❌ يرجى منشن الشخص المراد التحويل له والمبلغ (مثال: `تحويل @user 100`)", delete_after=5)
            
            target_user = message.mentions[0]
            if target_user.id == user_id:
                return await message.channel.send("❌ لا يمكنك التحويل لنفسك!", delete_after=5)

            parts = message.content.strip().split()
            amount = 0
            for p in reversed(parts):
                if p.isdigit():
                    amount = int(p)
                    break

            if amount <= 0:
                return await message.channel.send("❌ يرجى تحديد مبلغ صحيح للتحويل.", delete_after=5)

            current_pts = get_user_points(guild_id, user_id)
            if current_pts < amount:
                return await message.channel.send("❌ ليس لديك نقاط كافية لإتمام التحويل.", delete_after=5)

            add_points(guild_id, user_id, -amount)
            new_target_pts = add_points(guild_id, target_user.id, amount)
            
            return await message.channel.send(f"✨ تم تحويل `{amount:,}` نقطة بنجاح إلى العضو {target_user.mention}!")

        # 7. نظام التداول
        if text.startswith("تداول") or text.startswith("!تداول"):
            parts = message.content.strip().split()
            current_pts = get_user_points(guild_id, user_id)

            if len(parts) < 2:
                return await message.channel.send("❌ الاستخدام: `تداول [المبلغ]` أو `تداول كامل` أو `تداول نص`", delete_after=5)
            
            if parts[1] == "كامل":
                amount = current_pts
            elif parts[1] == "نص":
                amount = current_pts // 2
            elif parts[1].isdigit():
                amount = int(parts[1])
            else:
                return await message.channel.send("❌ صيغة المبلغ غير صحيحة.", delete_after=5)

            if amount <= 0 or current_pts < amount:
                return await message.channel.send("❌ رصيدك غير كافٍ للتداول بهذه القيمة.", delete_after=5)

            rem = self.check_cooldown(user_id, "trading")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** للتداول مرة أخرى!", delete_after=5)

            view = MarketView(TRADING_COUNTRIES)
            embed = discord.Embed(title="📈 نافذة سوق التداول الأجنبي", description=f"المبلغ: `{amount}`\nاختر الدولة:", color=discord.Color.orange())
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.cancelled or not view.select.selected_value:
                try: await msg.delete()
                except: pass
                return

            chosen_country = view.select.selected_value
            self.set_cooldown(user_id, "trading")

            is_win = random.choice([True, False, True])
            if is_win:
                profit = int(amount * (random.randint(15, 85) / 100))
                new_total = add_points(guild_id, user_id, profit)
                res_embed = discord.Embed(title=f"🟢 تداول ناجح في ({chosen_country})", description=f"💰 ربحت: `+{profit:,}` نقطة\n💼 رصيدك: `{new_total:,}` نقطة", color=discord.Color.green())
            else:
                loss = int(amount * (random.randint(10, 60) / 100))
                new_total = add_points(guild_id, user_id, -loss)
                res_embed = discord.Embed(title=f"🔴 خسارة في ({chosen_country})", description=f"💸 خسرت: `-{loss:,}` نقطة\n💼 رصيدك: `{new_total:,}` نقطة", color=discord.Color.red())
            
            try: await msg.edit(embed=res_embed, view=None)
            except: await message.channel.send(embed=res_embed)
            return

        # 8. نظام الاستثمار
        if text.startswith("استثمار") or text.startswith("!استثمار"):
            parts = message.content.strip().split()
            current_pts = get_user_points(guild_id, user_id)

            if len(parts) < 2:
                return await message.channel.send("❌ الاستخدام: `استثمار [المبلغ]` أو `استثمار كامل` أو `استثمار نص`", delete_after=5)
            
            if parts[1] == "كامل":
                amount = current_pts
            elif parts[1] == "نص":
                amount = current_pts // 2
            elif parts[1].isdigit():
                amount = int(parts[1])
            else:
                return await message.channel.send("❌ صيغة المبلغ غير صحيحة.", delete_after=5)

            if amount <= 0 or current_pts < amount:
                return await message.channel.send("❌ رصيدك غير كافٍ للاستثمار بهذه القيمة.", delete_after=5)

            rem = self.check_cooldown(user_id, "investment")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** للاستثمار مرة أخرى!", delete_after=5)

            view = MarketView(INVESTMENT_COUNTRIES)
            embed = discord.Embed(title="🏢 صندوق الاستثمار العربي", description=f"المبلغ: `{amount}`\nاختر الدولة:", color=discord.Color.gold())
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.cancelled or not view.select.selected_value:
                try: await msg.delete()
                except: pass
                return

            chosen_country = view.select.selected_value
            self.set_cooldown(user_id, "investment")

            is_win = random.choice([True, True, False])
            if is_win:
                profit = int(amount * (random.randint(20, 100) / 100))
                new_total = add_points(guild_id, user_id, profit)
                res_embed = discord.Embed(title=f"🟢 استثمار ناجح في ({chosen_country})", description=f"💰 العوائد: `+{profit:,}` نقطة\n💼 رصيدك: `{new_total:,}` نقطة", color=discord.Color.green())
            else:
                loss = int(amount * (random.randint(10, 50) / 100))
                new_total = add_points(guild_id, user_id, -loss)
                res_embed = discord.Embed(title=f"🔴 تراجع استثماري في ({chosen_country})", description=f"💸 الخسارة: `-{loss:,}` نقطة\n💼 رصيدك: `{new_total:,}` نقطة", color=discord.Color.red())
            
            try: await msg.edit(embed=res_embed, view=None)
            except: await message.channel.send(embed=res_embed)
            return

async def setup(bot):
    await bot.add_cog(MarketCog(bot))
