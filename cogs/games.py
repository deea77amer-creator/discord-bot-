import discord
from discord.ext import commands
import random
import asyncio
import os
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

# رابط الاتصال بقاعدة بيانات MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["discord_bot_db"]
users_collection = db["users"]
inventory_collection = db["inventory"]

# تتبع وقت الانتظار (Cooldown)
user_cooldowns = {}

# مؤقت وقت تحديث قائمة الأسعار (يتحدث تلقائياً بناءً على الوقت الفعلي)
LAST_SHOP_UPDATE = datetime.now()

async def get_user_points(guild_id, user_id):
    doc = await users_collection.find_one({"guild_id": str(guild_id), "user_id": str(user_id)})
    return doc["points"] if doc else 0

async def add_points(guild_id, user_id, amount):
    g_id = str(guild_id)
    u_id = str(user_id)
    doc = await users_collection.find_one({"guild_id": g_id, "user_id": u_id})
    
    if not doc:
        new_pts = max(0, amount)
        await users_collection.insert_one({"guild_id": g_id, "user_id": u_id, "points": new_pts})
    else:
        new_pts = max(0, doc["points"] + amount)
        await users_collection.update_one(
            {"guild_id": g_id, "user_id": u_id},
            {"$set": {"points": new_pts}}
        )
    return new_pts

# جدول المنتجات في المتجر
SHOP_ITEMS = {
    "1": {"name": "سيف الأساطير", "price": 150, "desc": "سيف حربي قوي لزيادة هيبتك"},
    "2": {"name": "درع الماس", "price": 250, "desc": "درع واقي من الضربات القوية"},
    "3": {"name": "جرعة حظ ذهبية", "price": 100, "desc": "تزيد حظك في الألعاب"},
    "4": {"name": "خنجر الظل", "price": 200, "desc": "خنجر خفي وسريع للضربات المفاجئة"},
    "5": {"name": "تَفَاحَةُ الطَّاقَةِ", "price": 50, "desc": "تمنحك انتعاشاً سريعاً ونقاط إضافية"},
    "6": {"name": "عباءة الاختفاء", "price": 350, "desc": "تعطيك حماية كاملة وهيبة أسطورية"}
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

class GameChoiceView(discord.ui.View):
    def __init__(self, options, author_id):
        super().__init__(timeout=15.0)
        self.value = None
        self.author_id = author_id

        for i, opt in enumerate(options):
            btn = discord.ui.Button(label=opt, style=discord.ButtonStyle.primary, custom_id=f"opt_{i}")
            btn.callback = self.create_callback(opt)
            self.add_item(btn)

    def create_callback(self, opt_text):
        async def button_callback(interaction: discord.Interaction):
            try:
                if interaction.user.id != self.author_id:
                    return await interaction.response.send_message("❌ هذه اللعبة ليست لك!", ephemeral=True)
                self.value = opt_text
                if not interaction.response.is_done():
                    await interaction.response.defer()
                self.stop()
            except Exception as e:
                print(f"Error in GameChoiceView callback: {e}")
        return button_callback

    async def on_timeout(self):
        self.stop()

class DuelAcceptView(discord.ui.View):
    def __init__(self, target_user_id):
        super().__init__(timeout=15.0)
        self.value = None
        self.target_user_id = target_user_id

        accept_btn = discord.ui.Button(label="قبول ✅", style=discord.ButtonStyle.success, custom_id="duel_accept")
        accept_btn.callback = self.accept_callback
        self.add_item(accept_btn)

        reject_btn = discord.ui.Button(label="رفض ❌", style=discord.ButtonStyle.danger, custom_id="duel_reject")
        reject_btn.callback = self.reject_callback
        self.add_item(reject_btn)

    async def accept_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.target_user_id:
            return await interaction.response.send_message("❌ هذا التحدي ليس موجهة لك!", ephemeral=True)
        self.value = "accept"
        if not interaction.response.is_done():
            await interaction.response.defer()
        self.stop()

    async def reject_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.target_user_id:
            return await interaction.response.send_message("❌ هذا التحدي ليس موجهة لك!", ephemeral=True)
        self.value = "reject"
        if not interaction.response.is_done():
            await interaction.response.defer()
        self.stop()

    async def on_timeout(self):
        self.stop()

class ShopPurchaseView(discord.ui.View):
    def __init__(self, author_id, guild_id):
        super().__init__(timeout=30.0)
        self.selected_item = None
        self.selected_quantity = 1
        self.author_id = author_id
        self.guild_id = guild_id
        self.is_finished = False

        for k, item in SHOP_ITEMS.items():
            btn = discord.ui.Button(label=f"{k}. {item['name']} ({item['price']}p)", style=discord.ButtonStyle.secondary, custom_id=f"shop_{k}")
            btn.callback = self.create_item_callback(k)
            self.add_item(btn)

        for q in [1, 2, 3, 5]:
            q_btn = discord.ui.Button(label=f"كمية: {q}", style=discord.ButtonStyle.primary, custom_id=f"qty_{q}")
            q_btn.callback = self.create_qty_callback(q)
            self.add_item(q_btn)

        confirm_btn = discord.ui.Button(label="تأكيد الشراء ✅", style=discord.ButtonStyle.success, custom_id="shop_confirm", row=4)
        confirm_btn.callback = self.confirm_callback
        self.add_item(confirm_btn)

    def create_item_callback(self, item_key):
        async def button_callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                return await interaction.response.send_message("❌ هذه القائمة ليست لك!", ephemeral=True)
            self.selected_item = item_key
            item_name = SHOP_ITEMS[item_key]["name"]
            await interaction.response.send_message(f"📌 تم اختيار المنتج: **{item_name}** (الكمية الحالية: {self.selected_quantity}). اضغط الآن على زر **تأكيد الشراء ✅**", ephemeral=True)
        return button_callback

    def create_qty_callback(self, qty):
        async def button_callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id:
                return await interaction.response.send_message("❌ هذه القائمة ليست لك!", ephemeral=True)
            self.selected_quantity = qty
            await interaction.response.send_message(f"🔢 تم تحديد الكمية: **{qty}**.", ephemeral=True)
        return button_callback

    async def confirm_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ هذه القائمة ليست لك!", ephemeral=True)
        if not self.selected_item:
            return await interaction.response.send_message("❌ يرجى اختيار منتج أولاً بالنقر على زره الخاص قبل التأكيد!", ephemeral=True)
        
        self.is_finished = True
        if not interaction.response.is_done():
            await interaction.response.defer()
        self.stop()

    async def on_timeout(self):
        self.stop()

class InteractiveGamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_id = 1528588181371490344
        self.processed_messages = set()

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

        if message.id in self.processed_messages:
            return
        self.processed_messages.add(message.id)
        if len(self.processed_messages) > 1000:
            self.processed_messages.pop()

        text = message.content.strip().lower()
        guild_id = message.guild.id
        user_id = message.author.id
        channel_id = message.channel.id

        if channel_id != self.target_channel_id:
            return

        parts = message.content.strip().split()
        if not parts:
            return
        
        first_word = parts[0].lower().replace("!", "").replace("/", "")

        # 1. قائمة الأوامر العامة
        if first_word in ["اوامر"]:
            embed = discord.Embed(
                title="📜 قائمة الأوامر والألعاب التفاعلية",
                description="مرحباً بك! إليك دليل الاستخدام والأوامر المتاحة:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🎲 الألعاب والمتجر",
                value="• `العاب` — لعرض قائمة الـ 26 لعبة.\n"
                      "• `اسعار` أو `مزاد` — لعرض أسعار الأغراض مع مؤقت التحديث التلقائي.\n"
                      "• `شراء` — لفتح قائمة المزاد التفاعلية لاختيار المنتج والكمية وتأكيد الشراء.\n"
                      "• `بيع` — لبيع أغراضك واسترداد النقاط.\n"
                      "• `رصيد` (أو `رصيد @الشخص`) — لمعرفة رصيد النقاط بكل السيرفر.\n"
                      "• `تحويل @الشخص المبلغ` — لتحويل نقاط لعضو آخر.\n"
                      "• `توب` — لعرض قائمة أفضل 10 لاعبين في السيرفر.\n"
                      "• `ممتلكات` أو `حقيبتي` — لعرض محتويات حقيبتك.\n"
                      "• `اعطاء @الشخص المبلغ` — (خاص بصاحب السيرفر) لإضافة أو خصم النقاط.\n"
                      "• *ملاحظة:* يمكنك كتابة أي لعبة ثم منشن لصديق (مثال: `نرد @فلان`) لدعوته لتحدي ثنائي بأزرار قبول ورفض!",
                inline=False
            )
            embed.set_footer(text="جميع الأوامر تعمل في القناة المخصصة!")
            await message.channel.send(embed=embed)
            return

        # 2. قائمة الـ 26 لعبة
        if first_word in ["العاب"]:
            embed = discord.Embed(
                title="🎮 الألعاب والأنظمة التفاعلية (26 لعبة باللغة العربية)",
                description="كل لعبة تفاعلية تتطلب خيارات وأزرار حماسية لكل لعبة وقت انتظار دقيقتين:",
                color=discord.Color.gold()
            )
            part1 = "\n".join([f"{i+1}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[:13])])
            part2 = "\n".join([f"{i+14}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[13:])])
            
            embed.add_field(name="📋 الألعاب (1 - 13)", value=part1, inline=True)
            embed.add_field(name="📋 الألعاب (14 - 26)", value=part2, inline=True)
            embed.set_footer(text="اكتب اسم اللعبة للبدء فوراً! (أو اكتب اسم اللعبة مع منشن صديق للتحدي)")
            await message.channel.send(embed=embed)
            return

        # 3. نظام الأسعار والمزاد (تحديث تلقائي عشوائي للأسعار مع المؤقت)
        if first_word in ["اسعار", "مزاد"]:
            global LAST_SHOP_UPDATE
            LAST_SHOP_UPDATE = datetime.now()
            for k in SHOP_ITEMS:
                SHOP_ITEMS[k]["price"] = random.randint(40, 350)

            time_str = LAST_SHOP_UPDATE.strftime("%Y-%m-%d %H:%M")
            embed = discord.Embed(
                title="🛒 قائمة أسعار المزاد ومتجر السيرفر", 
                description=f"⏱️ **آخر تحديث تلقائي للأسعار:** `{time_str}`",
                color=discord.Color.green()
            )
            for k, v in SHOP_ITEMS.items():
                embed.add_field(name=f"{k}. {v['name']}", value=f"السعر في المزاد: **{v['price']}** نقطة\nالوصف: {v['desc']}", inline=False)
            embed.set_footer(text="لشراء غرض اكتب: شراء واختار المنتج والكمية بالأزرار")
            await message.channel.send(embed=embed)
            return

        # 4. نظام الشراء التفاعلي الجديد
        if first_word in ["شراء"]:
            view = ShopPurchaseView(user_id, guild_id)
            embed = discord.Embed(
                title="🛍️ قائمة المزاد والشراء التفاعلي",
                description=f"يا {message.author.mention}! اختر المنتج أولاً، ثم حدد الكمية، ثم اضغط على زر **تأكيد الشراء ✅**:",
                color=discord.Color.blue()
            )
            for k, item in SHOP_ITEMS.items():
                embed.add_field(name=f"{k}. {item['name']}", value=f"السعر: `{item['price']}` نقطة", inline=True)
            
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if not view.is_finished or view.selected_item is None:
                try: await msg.delete()
                except: pass
                return await message.channel.send("⌛ انتهى الوقت أو لم تقم بتأكيد عملية الشراء!")

            item_key = view.selected_item
            quantity = view.selected_quantity
            item = SHOP_ITEMS[item_key]
            total_price = item["price"] * quantity
            current_pts = await get_user_points(guild_id, user_id)

            if current_pts < total_price:
                try: await msg.delete()
                except: pass
                return await message.channel.send(f"❌ لا توجد نقاط كافية لديك! رصيدك `{current_pts}` وتحتاج إلى `{total_price}` نقطة (`{item['price']}` × {quantity}).", delete_after=5)

            await add_points(guild_id, user_id, -total_price)
            
            for _ in range(quantity):
                await inventory_collection.insert_one({"guild_id": str(guild_id), "user_id": str(user_id), "item_name": item["name"]})
            
            success_text = f"✅ مبروك يا {message.author.mention}! تم الشراء من المزاد بنجاح وأضفت **{quantity}x {item['name']}** إلى حقيبتك مقابل إجمالي `{total_price}` نقطة!"
            try: await msg.edit(content=success_text, embed=None, view=None)
            except: await message.channel.send(success_text)
            return

        # 5. نظام الممتلكات / الحقيبة
        if first_word in ["ممتلكات", "حقيبتي"]:
            cursor = inventory_collection.find({"guild_id": str(guild_id), "user_id": str(user_id)})
            items = await cursor.to_list(length=100)
            
            pts = await get_user_points(guild_id, user_id)
            embed = discord.Embed(title=f"🎒 حقيبة الممتلكات لـ {message.author.name}", color=discord.Color.purple())
            embed.add_field(name="💰 رصيد النقاط", value=f"`{pts}` نقطة", inline=False)
            
            if items:
                item_counts = {}
                for item in items:
                    name = item['item_name']
                    item_counts[name] = item_counts.get(name, 0) + 1
                
                items_list = "\n".join([f"• {name} (العدد: {count})" for name, count in item_counts.items()])
                embed.add_field(name="📦 الأغراض والممتلكات", value=items_list, inline=False)
            else:
                embed.add_field(name="📦 الأغراض والممتلكات", value="حقيبتك فارغة حالياً! استخدم `مزاد` ثم `شراء`.", inline=False)
            return await message.channel.send(embed=embed)

        # 6. نظام البيع (استرداد النقاط)
        if first_word in ["بيع"] and len(parts) > 1:
            item_to_sell = message.content.replace("بيع", "").replace("!", "").strip()
            if not item_to_sell:
                return await message.channel.send("❌ يرجى كتابة اسم الغرض الذي تريد بيعه (مثال: بيع سيف الأساطير)", delete_after=5)
            
            item_doc = await inventory_collection.find_one({"guild_id": str(guild_id), "user_id": str(user_id), "item_name": {"$regex": item_to_sell, "$options": "i"}})
            
            if not item_doc:
                return await message.channel.send(f"❌ ليس لديك غرض بهذا الاسم في حقيبتك!", delete_after=5)
            
            await inventory_collection.delete_one({"_id": item_doc["_id"]})
            
            refund = 75
            new_pts = await add_points(guild_id, user_id, refund)
            return await message.channel.send(f"✅ تم بيع الغرض بنجاح واسترداد **{refund} نقطة**! رصيدك الحالي: `{new_pts}`")

        # 7. نظام عرض الرصيد الموحد
        if first_word in ["رصيد"]:
            if message.mentions:
                target_user = message.mentions[0]
                pts = await get_user_points(guild_id, target_user.id)
                return await message.channel.send(f"👤 العضو: {target_user.mention}\n💰 رصيده الحالي: `{pts}` نقطة")
            else:
                pts = await get_user_points(guild_id, user_id)
                return await message.channel.send(f"👤 العضو: {message.author.mention}\n💰 رصيدك الحالي: `{pts}` نقطة")

        # 8. نظام تحويل النقاط
        if first_word in ["تحويل"]:
            if len(parts) < 3 or not message.mentions:
                return await message.channel.send("❌ الاستخدام الصحيح: `تحويل @الشخص المبلغ`", delete_after=5)
            
            target_user = message.mentions[0]
            if target_user.id == user_id:
                return await message.channel.send("❌ لا يمكنك تحويل النقاط لنفسك!", delete_after=5)
            
            try:
                amount = int(parts[2])
            except ValueError:
                return await message.channel.send("❌ يرجى كتابة رقم صحيح للمبلغ المراد تحويله.", delete_after=5)
            
            if amount <= 0:
                return await message.channel.send("❌ لا يمكنك تحويل مبلغ سالب أو صفر!", delete_after=5)
            
            sender_pts = await get_user_points(guild_id, user_id)
            if sender_pts < amount:
                return await message.channel.send(f"❌ رصيدك غير كافٍ! رصيدك الحالي `{sender_pts}` نقطة.", delete_after=5)
            
            new_sender_pts = await add_points(guild_id, user_id, -amount)
            new_target_pts = await add_points(guild_id, target_user.id, amount)
            
            return await message.channel.send(f"💸 تم تحويل **{amount}** نقطة بنجاح إلى {target_user.mention}!\n💰 رصيدك الجديد: `{new_sender_pts}` نقطة.")

        # 9. أمر التوب
        if first_word in ["توب"]:
            cursor = users_collection.find({"guild_id": str(guild_id)}).sort("points", -1).limit(10)
            top_users = await cursor.to_list(length=10)
            
            if not top_users:
                return await message.channel.send("📊 لا توجد أي بيانات مسجلة للأعضاء حتى الآن!", delete_after=5)
            
            embed = discord.Embed(
                title="🏆 لوحة المتصدرين (التوب) في السيرفر",
                description="أفضل 10 لاعبين من حيث جمع النقاط:",
                color=discord.Color.gold()
            )
            
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            desc_list = []
            for i, doc in enumerate(top_users):
                u_id = int(doc["user_id"])
                pts = doc["points"]
                user_obj = message.guild.get_member(u_id)
                name = user_obj.mention if user_obj else f"مستخدم مغادر ({u_id})"
                medal = medals[i] if i < len(medals) else f"{i+1}."
                desc_list.append(f"{medal} {name} — **{pts}** نقطة")
            
            embed.add_field(name="✨ قائمة الأبطال", value="\n".join(desc_list), inline=False)
            embed.set_footer(text=f"طلب بواسطة: {message.author.name}")
            return await message.channel.send(embed=embed)

        # 10. أمر الإعطاء الخاص بصاحب السيرفر
        if first_word == "اعطاء":
            if message.author != message.guild.owner:
                return await message.channel.send("❌ عذراً، هذا الأمر خاص بصاحب السيرفر فقط!", delete_after=5)
            
            if len(parts) < 3 or not message.mentions:
                return await message.channel.send("❌ الاستخدام الصحيح لصاحب السيرفر: `اعطاء @الشخص المبلغ`", delete_after=5)
            
            target_user = message.mentions[0]
            try:
                amount = int(parts[2])
            except ValueError:
                return await message.channel.send("❌ يرجى كتابة مبلغ صحيح بالأرقام.", delete_after=5)

            new_tot = await add_points(guild_id, target_user.id, amount)
            action_word = "إضافة" if amount >= 0 else "خصم"
            await message.channel.send(f"✅ تم {action_word} **{abs(amount)}** نقطة بنجاح لـ {target_user.mention}!\nرصيده الحالي: `{new_tot}` نقطة.")
            return

        # 11. دعم نظام التحدي الثنائي
        matched_game = next((g for g in GAMES_LIST if g["cmd"] == first_word), None)
        if matched_game and message.mentions:
            target_user = message.mentions[0]
            if target_user.id == user_id:
                return await message.channel.send("❌ لا يمكنك تحدي نفسك!", delete_after=5)
            if target_user.bot:
                return await message.channel.send("❌ لا يمكنك تحدي بوت!", delete_after=5)

            game_name = matched_game["name"]
            view = DuelAcceptView(target_user.id)
            embed = discord.Embed(
                title=f"⚔️ تحدي ثنائي: {game_name}",
                description=f"يا {target_user.mention}! أرسل لك {message.author.mention} تحدياً في لعبة **({game_name})**.\nاضغط على الزر أدناه للقبول أو الرفض خلال 15 ثانية:",
                color=discord.Color.orange()
            )
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.value is None or view.value == "reject":
                try: await msg.delete()
                except: pass
                status_msg = "رفض التحدي" if view.value == "reject" else "انتهى الوقت ولم يستجب"
                return await message.channel.send(f"⌛ {target_user.mention} {status_msg}!")

            try: await msg.delete()
            except: pass

            duel_options = ["الخيار الأول (صحيح 🟢)", "الخيار الثاني (خاطئ ❌)", "الخيار الثالث (خاطئ ❌)"]
            random.shuffle(duel_options)
            correct_opt = duel_options[0]

            game_view = GameChoiceView(duel_options, target_user.id)
            game_embed = discord.Embed(
                title=f"🎮 معركة ثنائية: {game_name}",
                description=f"دورك يا {target_user.mention}! اختر الإجابة الصحيحة للتحدي المقدم من {message.author.mention}:",
                color=discord.Color.blurple()
            )
            game_msg = await message.channel.send(embed=game_embed, view=game_view)
            await game_view.wait()

            if game_view.value is None:
                try: await game_msg.delete()
                except: pass
                await add_points(guild_id, target_user.id, -20)
                await add_points(guild_id, user_id, 40)
                return await message.channel.send(f"⌛ انتهى الوقت ولم يختار {target_user.mention}!\n👑 الفائز بالافتراض: {message.author.mention} وحصل على **+40 نقطة**\n💀 الخاسر: {target_user.mention} وخسر **-20 نقطة**.")

            chosen_answer = game_view.value
            correct_answer = duel_options[0] 

            if chosen_answer == correct_answer:
                win_pts = await add_points(guild_id, target_user.id, 40)
                await add_points(guild_id, user_id, -20)
                result_msg = f"🏆 فاز {target_user.mention} بالتحدي واختار الإجابة الصحيحة!\n حصل على **+40 نقطة** (رصيده: `{win_pts}`)\n وخسر المحدي {message.author.mention} **-20 نقطة**."
            else:
                win_pts = await add_points(guild_id, user_id, 40)
                await add_points(guild_id, target_user.id, -20)
                result_msg = f"💀 خسر {target_user.mention} التحدي باختياره الخاطئ!\n تذهب النقاط للبادئ {message.author.mention} ليحصل على **+40 نقطة** (رصيده: `{win_pts}`)\n وخسر {target_user.mention} **-20 نقطة**."

            try: await game_msg.edit(content=result_msg, embed=None, view=None)
            except: await message.channel.send(result_msg)
            return

        # --- الألعاب التفاعلية الفردية العادية ---

        if first_word in ["كنز", "صيد"]:
            rem = self.check_cooldown(user_id, "صيد")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** لرحلة الصيد القادمة!", delete_after=5)

            options = ["🐟 سمكة صغيرة", "🦈 قرش متوحش", "🪙 صندوق كنز ذهبي", "👢 حذاء قديم"]
            view = GameChoiceView(options, user_id)
            embed = discord.Embed(
                title="🎣 رحلة صيد الكنوز البحرية",
                description=f"يا {message.author.mention}! ألقيت صنارة الصيد في البحر العميق... اختر أين تبحث أو ماذا تصطاد بالأزرار أدناه:",
                color=discord.Color.blue()
            )
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.value is None:
                try: await msg.delete()
                except: pass
                return await message.channel.send(f"⌛ انتهى الوقت ولم تقم بالصيد يا {message.author.mention}!")

            chosen = view.value
            if "سمكة صغيرة" in chosen:
                reward = random.choice([20, 35, 40])
                pts = await add_points(guild_id, user_id, reward)
                res_desc = f" لقد اصطدت **سمكة صغيرة لذيذة**! ربحت **+{reward} نقطة** (رصيدك: {pts})"
            elif "قرش متوحش" in chosen:
                reward = random.choice([70, 100, 120])
                pts = await add_points(guild_id, user_id, reward)
                res_desc = f" هجم عليك قرش شرس لكنك سيطرت عليه وصطدته! كنز كبير ربحت **+{reward} نقطة** (رصيدك: {pts})"
            elif "صندوق كنز ذهبي" in chosen:
                reward = random.choice([150, 200, 250])
                pts = await add_points(guild_id, user_id, reward)
                res_desc = f" يا له من حظ أسطوري! وجدت **صندوق كنز ذهبي** مغطى بالمجوهرات! ربحت **+{reward} نقطة** (رصيدك: {pts})"
            else:
                loss = 15
                pts = await add_points(guild_id, user_id, -loss)
                res_desc = f" للأسف... اصطدت **حذاءً قديماً متهالكاً** وضاعت تعبك (-{loss} نقطة، رصيدك: {pts})"

            try: await msg.edit(content=f"🎣 **نتيجة الصيد:**{res_desc}", embed=None, view=None)
            except: await message.channel.send(f"🎣 **نتيجة الصيد:**{res_desc}")
            return

        if first_word in ["نرد"]:
            rem = self.check_cooldown(user_id, "نرد")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** لرمي النرد مرة أخرى!", delete_after=5)

            options = ["عالي (4-6)", "منخفض (1-3)"]
            view = GameChoiceView(options, user_id)
            embed = discord.Embed(title="🎲 تحدي النرد السريع", description=f"يا {message.author.mention}! اختر توقعك لرمية النرد بالأزرار أدناه:", color=discord.Color.dark_magenta())
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.value is None:
                try: await msg.delete()
                except: pass
                return await message.channel.send("⌛ انتهى الوقت ولم تقم بالاختيار!")

            roll = random.randint(1, 6)
            is_high = roll >= 4
            user_choice_high = "عالي" in view.value
            user_won = (user_choice_high and is_high) or (not user_choice_high and not is_high)

            if user_won:
                pts = await add_points(guild_id, user_id, 50)
                result_text = f"🎉 طلع النرد (`{roll}`). توقعك كان صحيحاً تماماً! **ربحت 50 نقطة** (رصيدك: {pts})"
            else:
                result_text = f"❌ طلع النرد (`{roll}`). توقعك كان خاطئاً، حظاً أوفر في المرة القادمة!"

            try: await msg.edit(content=result_text, embed=None, view=None)
            except: await message.channel.send(result_text)
            return

        if first_word in ["حظ", "روليت"]:
            rem = self.check_cooldown(user_id, "حظ")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** لتدوير عجلة الحظ مرة أخرى!", delete_after=5)

            options = ["الباب الأول 🚪", "الباب الثاني 🚪", "الباب الثالث 🚪"]
            view = GameChoiceView(options, user_id)
            embed = discord.Embed(title="🎰 عجلة الحظ والأبواب السرية", description=f"يا {message.author.mention}! أمامك 3 أبواب مغلقة، اختر باباً لتكتشف ما خلفه بالأزرار أدناه:", color=discord.Color.orange())
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.value is None:
                try: await msg.delete()
                except: pass
                return await message.channel.send("⌛ انتهى الوقت ولم تختر الباب المناسب!")

            reward = random.choice([60, 120, -30, 180, 0, 90])
            pts = await add_points(guild_id, user_id, reward)
            if reward > 0:
                res_text = f"✨ فتحت {view.value} ووجدت خلفه كنزاً بقيمة **+{reward} نقطة**! رصيدك: `{pts}`"
            elif reward < 0:
                res_text = f"💥 اصطدمت بفخ خلف {view.value} وخسرت **{reward} نقطة**! رصيدك: `{pts}`"
            else:
                res_text = f"💨 {view.value} كان فارغاً وخاوياً على عروشه! لم تربح ولم تخسر."

            try: await msg.edit(content=res_text, embed=None, view=None)
            except: await message.channel.send(res_text)
            return

        if first_word in ["مقص"]:
            rem = self.check_cooldown(user_id, "مقص")
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** للعب مرة أخرى!", delete_after=5)

            options = ["حجر 🪨", "ورقة 📄", "مقص ✂️"]
            view = GameChoiceView(options, user_id)
            embed = discord.Embed(title="✂️ تحدي حجرة ورقة مقص الكلاسيكي", description=f"يا {message.author.mention}! اختر سلاحك بالأزرار أدناه لمواجهة البوت:", color=discord.Color.red())
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.value is None:
                try: await msg.delete()
                except: pass
                return await message.channel.send("⌛ انتهى الوقت ولم تختر خيارك!")

            choice = "حجر" if "حجر" in view.value else ("ورقة" if "ورقة" in view.value else "مقص")
            bot_choice = random.choice(["حجر", "ورقة", "مقص"])

            if choice == bot_choice:
                res_text = f"🤝 اختيارك ({choice}) والبوت اختر ({bot_choice}) -> **تعادل تماماً!**"
            elif (choice == "حجر" and bot_choice == "مقص") or (choice == "ورقة" and bot_choice == "حجر") or (choice == "مقص" and bot_choice == "ورقة"):
                pts = await add_points(guild_id, user_id, 60)
                res_text = f"🎉 اختيارك ({choice}) والبوت اختر ({bot_choice}) -> **فزت بجدارة وربحت 60 نقطة!** (رصيدك: {pts})"
            else:
                res_text = f"❌ اختيارك ({choice}) والبوت اختر ({bot_choice}) -> **للأسف خسرت أمام ذكاء البوت!**"

            try: await msg.edit(content=res_text, embed=None, view=None)
            except: await message.channel.send(res_text)
            return

        if matched_game:
            game_obj = matched_game
            game_name = game_obj["name"]
            
            rem = self.check_cooldown(user_id, first_word)
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** للعب ({game_name}) مرة أخرى!", delete_after=5)

            unique_game_scenarios = {
                "تخمين": {
                    "title": "🔐 لعبة تخمين الرقم السري",
                    "desc": "أمامك خزانة مغلقة بأرقام سرية... اختر الرقم الصحيح لفتحها:",
                    "options": ["الرقم 3", "الرقم 7", "الرقم 12", "الرقم 9"],
                    "ans": "الرقم 7"
                },
                "حساب": {
                    "title": "⚡ اختبار سرعة البديهة والرياضيات",
                    "desc": "احسب بسرعة: كم ناتج (12 + 8 × 2) ؟",
                    "options": ["28", "40", "20", "32"],
                    "ans": "28"
                },
                "عاصمة": {
                    "title": "🗺️ رحلة استكشاف العواصم الكبرى",
                    "desc": "اختر العاصمة الصحيحة لدولة اليابان:",
                    "options": ["طوكيو", "سول", "بكين", "بانكوك"],
                    "ans": "طوكيو"
                },
                "معنى": {
                    "title": "📖 تحدي المفردات واللغة العربية",
                    "desc": "ما هو مرادف كلمة (أسد) الشهيرة في اللغة؟",
                    "options": ["هيثم", "غضنفر", "أهيف", "حطيئة"],
                    "ans": "غضنفر"
                },
                "شفرة": {
                    "title": "🕵️‍♂️ غرفة فك الشفرات والرموز",
                    "desc": "رتب الحروف المبعثرة (ة - ق - ص - ق) لتكون كلمة صحيحة:",
                    "options": ["قصة", "قصب", "صقر", "قصر"],
                    "ans": "قصة"
                },
                "خطأ": {
                    "title": "👁️ اكتشاف الكلمة الشاذة",
                    "desc": "أي من هذه العناصر يعتبر شاذ ولا ينتمي للمجموعة؟",
                    "options": ["تفاح", "موز", "حديد", "برتقال"],
                    "ans": "حديد"
                },
                "ذاكرة": {
                    "title": "🧠 تحدي الذاكرة وقوة الحفظ",
                    "desc": "تذكر الرمز الذي ظهر لك سابقاً واختاره:",
                    "options": ["⭐ نجمة ذهبية", "🔷 معين أزرق", "🔴 دائرة حمراء", "⬛ مربع أسود"],
                    "ans": "⭐ نجمة ذهبية"
                },
                "ترتيب": {
                    "title": "🔄 تحدي ترتيب الحروف المبعثرة",
                    "desc": "رتب الحروف (ر - ك - ص - ت) لتشكيل كلمة صحيحة:",
                    "options": ["سكر", "قصر", "صتر", "كرست"],
                    "ans": "سكر"
                },
                "مقولة": {
                    "title": "📜 حكمة الأقوال المشهورة",
                    "desc": "أكمل المثل الشعبي الشهير: (الباب اللي يجيك منه ريح...)",
                    "options": ["سده واستريح", "افتحه واستقبل", "ابنيه ولا تبالي", "راقب الريح"],
                    "ans": "سده واستريح"
                },
                "لون": {
                    "title": "🎨 تحدي الألوان والخدع البصرية",
                    "desc": "ما هو اللون الناتج عن خلط اللونين (الأزرق والأصفر)؟",
                    "options": ["أخضر", "بنفسجي", "برتقالي", "بني"],
                    "ans": "أخضر"
                },
                "سباق": {
                    "title": "🏎️ سباق السيارات السريع",
                    "desc": "اختر مسار القيادة الأسرع لتتخطى المنعطف الخطير:",
                    "options": ["المسار الأيمن الضيق", "المسار الأوسط المنحني", "المسار الأيسر المستقيم", "طريق الجبل الوعر"],
                    "ans": "المسار الأيسر المستقيم"
                },
                "أسطورة": {
                    "title": "⚔️ حرب الأساطير والملاحم الفردية",
                    "desc": "اختر ضربتك القاضية لمواجهة الوحش الأسطوري:",
                    "options": ["ضربة السيف السريعة", "درع الصد الحصين", "رمية الرمح النارية", "تعويذة الاختفاء"],
                    "ans": "ضربة السيف السريعة"
                },
                "قلعة": {
                    "title": "🏰 بناء الحصن والقلعة الدفاعية",
                    "desc": "أي الموارد تبدأ بجمعها أولاً لبناء سور القلعة؟",
                    "options": ["الصخور الصلبة", "الأخشاب الخفيفة", "الرمال الناعمة", "المياه العذبة"],
                    "ans": "الصخور الصلبة"
                },
                "بوصة": {
                    "title": "⏱️ معركة التكتيك السريع",
                    "desc": "اتخذ قراراً تكتيكياً حاسماً في أجزاء من الثانية:",
                    "options": ["هجوم شامل خاطف", "دفاع وتمركز حصين", "انسحاب استراتيجي", "كمين مباغت"],
                    "ans": "هجوم شامل خاطف"
                },
                "فضاء": {
                    "title": "🚀 رحلة استكشاف الفضاء والمخاطر",
                    "desc": "أي الكواكب أقرب إلى الشمس في مجموعتنا الشمسية؟",
                    "options": ["عطارد", "المريخ", "الزهرة", "المشتري"],
                    "ans": "عطارد"
                },
                "روليت كبرى": {
                    "title": "🎰 روليت الحظ الكبرى والمضاعفة",
                    "desc": "اختر صندوق المجوهرات المخفي لمضاعفة نقاطك:",
                    "options": ["الصندوق الياقوتي الأحمر", "الصندوق الزمردي الأخضر", "صندوق الماس الخالص", "الصندوق الفضي"],
                    "ans": "صندوق الماس الخالص"
                },
                "سؤال": {
                    "title": "💡 تحدي الذكاء والثقافة العامة",
                    "desc": "ما هو أسرع حيوان بري في العالم؟",
                    "options": ["الفهد (الشيتا)", "الأسد", "الغزال", "الحصان"],
                    "ans": "الفهد (الشيتا)"
                },
                "سرعة": {
                    "title": "⚡ تحدي السرعة واتخاذ القرار",
                    "desc": "اضغط على الزر الأسرع لتفادي الفخ المنصوب:",
                    "options": ["القفز للأمام", "الانحناء للأسفل", "الركض لليسار", "التثبت مكاني"],
                    "ans": "القفز للأمام"
                },
                "سلسلة": {
                    "title": "🔗 سلسلة الكلمات المترابطة",
                    "desc": "أكمل سلسلة الكلمات بحرف البداية الصحيح:",
                    "options": ["تفاح - هواء - أمل", "كتاب - باب - بيت", "قلم - مسطرة - دفتر", "ماء - أرض - سماء"],
                    "ans": "كتاب - باب - بيت"
                },
                "كنز خفي": {
                    "title": "🗺️ تجميع الألغاز والكنز الخفي",
                    "desc": "أين تقع إشارة الإكس (X) على خريطة الكنز الممزقة؟",
                    "options": ["تحت شجرة النخيل العتيقة", "بجانب الصخرة السوداء", "خلف الشلال الكبير", "داخل كهف الموتى"],
                    "ans": "خلف الشلال الكبير"
                },
                "حرب": {
                    "title": "🔥 حرب الكلمات المشتعلة والجماعية",
                    "desc": "اختر خطة الهجوم المناسبة لاجتياح المعسكر:",
                    "options": ["اقتحام البوابة الرئيسية", "التسلل عبر الأنفاق", "قصف الحصان من بعيد", "فرض حصار شامل"],
                    "ans": "التسلل عبر الأنفاق"
                }
            }

            scenario = unique_game_scenarios.get(first_word, {
                "title": f"🎮 لعبة تفاعلية: {game_name}",
                "desc": f"اجتاز تحدي {game_name} بنجاح عبر اختيار الإجابة الصحيحة:",
                "options": ["الخيار الأول", "الخيار الثاني", "الخيار الثالث", "الخيار الرابع"],
                "ans": "الخيار الأول"
            })

            shuffled_opts = scenario["options"].copy()
            random.shuffle(shuffled_opts)

            view = GameChoiceView(shuffled_opts, user_id)
            embed = discord.Embed(
                title=scenario["title"],
                description=f"يا {message.author.mention}! {scenario['desc']}",
                color=discord.Color.teal()
            )
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.value is None:
                try: await msg.delete()
                except: pass
                return await message.channel.send(f"⌛ انتهى الوقت المخصص لتحدي {game_name} ولم تقم بالإجابة!")

            if view.value == scenario["ans"]:
                reward = random.randint(40, 90)
                total = await add_points(guild_id, user_id, reward)
                res_text = f"🏆 إجابة خارقة وصحيحة يا {message.author.mention}! اجتزت تحدي **{game_name}** بنجاح وربحت **+{reward} نقطة**! رصيدك الحالي: `{total}`"
            else:
                res_text = f"❌ إجابة خاطئة! الإجابة الصحيحة كانت: **{scenario['ans']}**. حظاً أوفر في المرات القادمة!"

            try: await msg.edit(content=res_text, embed=None, view=None)
            except: await message.channel.send(res_text)
            return

async def setup(bot):
    await bot.add_cog(InteractiveGamesCog(bot))
