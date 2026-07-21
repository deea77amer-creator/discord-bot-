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

# جدول المنتجات في المتجر (تم توحيدها لتتوافق مع نظام المزاد والأسعار)
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

# أداة تفاعلية لأمر الشراء الجديد
class ShopPurchaseView(discord.ui.View):
    def __init__(self, author_id, guild_id):
        super().__init__(timeout=20.0)
        self.value = None
        self.author_id = author_id
        self.guild_id = guild_id

        for k, item in SHOP_ITEMS.items():
            btn = discord.ui.Button(label=f"{k}. {item['name']} ({item['price']} نقطة)", style=discord.ButtonStyle.success, custom_id=f"shop_{k}")
            btn.callback = self.create_callback(k)
            self.add_item(btn)

    def create_callback(self, item_key):
        async def button_callback(interaction: discord.Interaction):
            try:
                if interaction.user.id != self.author_id:
                    return await interaction.response.send_message("❌ هذه القائمة ليست لك!", ephemeral=True)
                self.value = item_key
                if not interaction.response.is_done():
                    await interaction.response.defer()
                self.stop()
            except Exception as e:
                print(f"Error in ShopPurchaseView callback: {e}")
        return button_callback

    async def on_timeout(self):
        self.stop()

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

    @commands.command(name="نقاط", aliases=["رصيدي", "البنك"])
    async def points_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        pts = await get_user_points(ctx.guild.id, target.id)
        await ctx.send(f"👤 العضو: {target.mention}\n💰 رصيده الحالي: `{pts}` نقطة")

    @commands.command(name="العاب", aliases=["الالعاب"])
    async def games_cmd(self, ctx):
        embed = discord.Embed(
            title="🎮 الألعاب والأنظمة التفاعلية (26 لعبة باللغة العربية)",
            description="كل لعبة تفاعلية تتطلب خيارات وأزرار حماسية لكل لعبة وقت انتظار دقيقتين:",
            color=discord.Color.gold()
        )
        part1 = "\n".join([f"{i+1}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[:13])])
        part2 = "\n".join([f"{i+14}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[13:])])
        
        embed.add_field(name="📋 الألعاب (1 - 13)", value=part1, inline=True)
        embed.add_field(name="📋 الألعاب (14 - 26)", value=part2, inline=True)
        embed.set_footer(text="اكتب اسم اللعبة للبدء فوراً!")
        await ctx.send(embed=embed)

    @commands.command(name="اسعار", aliases=["الاسعار"])
    async def prices_cmd(self, ctx):
        embed = discord.Embed(title="🛒 قائمة أسعار المزاد ومتجر السيرفر", color=discord.Color.green())
        for k, v in SHOP_ITEMS.items():
            embed.add_field(name=f"{k}. {v['name']}", value=f"السعر في المزاد: **{v['price']}** نقطة\nالوصف: {v['desc']}", inline=False)
        embed.set_footer(text="لشراء غرض اكتب: شراء واختار من الأزرار التفاعلية")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        # التأكد من معالجة الأوامر البرمجية العادية أيضاً من خلال البوت
        await self.bot.process_commands(message)

        text = message.content.strip().lower()
        guild_id = message.guild.id
        user_id = message.author.id
        channel_id = message.channel.id

        if channel_id != self.target_channel_id:
            return

        # 1. قائمة الأوامر العامة
        if text in ["اوامر", "!اوامر", "/اوامر"]:
            embed = discord.Embed(
                title="📜 قائمة الأوامر والألعاب التفاعلية",
                description="مرحباً بك! إليك دليل الاستخدام والأوامر المتاحة:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🎲 الألعاب والمتجر",
                value="• `العاب` — لعرض قائمة الـ 26 لعبة.\n"
                      "• `اسعار` أو `مزاد` — لعرض أسعار الأغراض.\n"
                      "• `شراء` — لفتح قائمة المزاد التفاعلية والشراء بالأزرار.\n"
                      "• `بيع` — لبيع أغراضك واسترداد النقاط (مثال: بيع سيف الأساطير).\n"
                      "• `رصيد @الشخص` — لمعرفة رصيد أي عضو.\n"
                      "• `تحويل @الشخص المبلغ` — لتحويل نقاط لعضو آخر.\n"
                      "• `توب` — لعرض قائمة أفضل 10 لاعبين في السيرفر.\n"
                      "• `ممتلكات` أو `حقيبتي` — لعرض محتويات حقيبتك.",
                inline=False
            )
            embed.set_footer(text="جميع الأوامر تعمل في القناة المخصصة!")
            await message.channel.send(embed=embed)
            return

        # 2. قائمة الـ 26 لعبة
        if text in ["العاب", "!العاب", "/العاب"]:
            embed = discord.Embed(
                title="🎮 الألعاب والأنظمة التفاعلية (26 لعبة باللغة العربية)",
                description="كل لعبة تفاعلية تتطلب خيارات وأزرار حماسية لكل لعبة وقت انتظار دقيقتين:",
                color=discord.Color.gold()
            )
            part1 = "\n".join([f"{i+1}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[:13])])
            part2 = "\n".join([f"{i+14}️⃣ **{g['name']}**: `{g['cmd']}`" for i, g in enumerate(GAMES_LIST[13:])])
            
            embed.add_field(name="📋 الألعاب (1 - 13)", value=part1, inline=True)
            embed.add_field(name="📋 الألعاب (14 - 26)", value=part2, inline=True)
            embed.set_footer(text="اكتب اسم اللعبة للبدء فوراً!")
            await message.channel.send(embed=embed)
            return

        # 3. نظام الأسعار والمزاد
        if text in ["اسعار", "!اسعار", "مزاد", "!مزاد"]:
            embed = discord.Embed(title="🛒 قائمة أسعار المزاد ومتجر السيرفر", color=discord.Color.green())
            for k, v in SHOP_ITEMS.items():
                embed.add_field(name=f"{k}. {v['name']}", value=f"السعر في المزاد: **{v['price']}** نقطة\nالوصف: {v['desc']}", inline=False)
            embed.set_footer(text="لشراء غرض اكتب: شراء واختار من الأزرار التفاعلية")
            await message.channel.send(embed=embed)
            return

        # 4. نظام الشراء التفاعلي الجديد (أمر شراء يفتح أزرار لاختيار ما تريد وشراؤه)
        if text in ["شراء", "!شراء", "/شراء"]:
            view = ShopPurchaseView(user_id, guild_id)
            embed = discord.Embed(
                title="🛍️ قائمة المزاد والشراء التفاعلي",
                description=f"يا {message.author.mention}! اختر الغرض الذي ترغب في شرائه من الأزرار أدناه:",
                color=discord.Color.blue()
            )
            for k, item in SHOP_ITEMS.items():
                embed.add_field(name=f"{item['name']}", value=f"السعر: `{item['price']}` نقطة", inline=True)
            
            msg = await message.channel.send(embed=embed, view=view)
            await view.wait()

            if view.value is None:
                try: await msg.delete()
                except: pass
                return await message.channel.send("⌛ انتهى الوقت ولم تقم باختيار أي غرض للشراء!")

            item_key = view.value
            item = SHOP_ITEMS[item_key]
            current_pts = await get_user_points(guild_id, user_id)

            if current_pts < item["price"]:
                try: await msg.delete()
                except: pass
                return await message.channel.send(f"❌ لا توجد نقاط كافية لديك! رصيدك `{current_pts}` وتحتاج إلى `{item['price']}` نقطة.", delete_after=5)

            await add_points(guild_id, user_id, -item["price"])
            await inventory_collection.insert_one({"guild_id": str(guild_id), "user_id": str(user_id), "item_name": item["name"]})
            
            success_text = f"✅ مبروك يا {message.author.mention}! تم الشراء من المزاد بنجاح وأضفت **{item['name']}** إلى حقيبتك مقابل `{item['price']}` نقطة!"
            try: await msg.edit(content=success_text, embed=None, view=None)
            except: await message.channel.send(success_text)
            return

        # 5. نظام الممتلكات / الحقيبة
        if text in ["ممتلكات", "حقيبتي", "!حقيبتي"]:
            cursor = inventory_collection.find({"guild_id": str(guild_id), "user_id": str(user_id)})
            items = await cursor.to_list(length=100)
            
            pts = await get_user_points(guild_id, user_id)
            embed = discord.Embed(title=f"🎒 حقيبة الممتلكات لـ {message.author.name}", color=discord.Color.purple())
            embed.add_field(name="💰 رصيد النقاط", value=f"`{pts}` نقطة", inline=False)
            
            if items:
                items_list = "\n".join([f"• {item['item_name']}" for item in items])
                embed.add_field(name="📦 الأغراض والممتلكات", value=items_list, inline=False)
            else:
                embed.add_field(name="📦 الأغراض والممتلكات", value="حقيبتك فارغة حالياً! استخدم `مزاد` ثم `شراء`.", inline=False)
            return await message.channel.send(embed=embed)

        # 6. نظام البيع (استرداد النقاط)
        if text.startswith("بيع ") or text.startswith("!بيع "):
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

        # 7. نظام عرض رصيد الآخرين (مثال: رصيد @الشخص)
        if text.startswith("رصيد ") or text.startswith("!رصيد "):
            if message.mentions:
                target_user = message.mentions[0]
                pts = await get_user_points(guild_id, target_user.id)
                return await message.channel.send(f"👤 العضو: {target_user.mention}\n💰 رصيده الحالي: `{pts}` نقطة")
            else:
                pts = await get_user_points(guild_id, user_id)
                return await message.channel.send(f"👤 العضو: {message.author.mention}\n💰 رصيدك الحالي: `{pts}` نقطة")

        # 8. نظام تحويل النقاط (مثال: تحويل @الشخص 100)
        if text.startswith("تحويل ") or text.startswith("!تحويل "):
            parts = message.content.strip().split()
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

        # 9. أمر التوب (أفضل 10 لاعبين في السيرفر) بالعربي بالكامل
        if text in ["توب", "!توب", "/توب"]:
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

        # 10. أمر إضافة أو خصم النقاط (خاص بصاحب السيرفر أو المسؤولين Administrator فقط)
        if text.startswith("نقاط") or text.startswith("!نقاط") or text.startswith("/نقاط"):
            # التحقق من صلاحية Administrator أو أن المستخدم هو مالك السيرفر
            if not message.author.guild_permissions.administrator and message.author != message.guild.owner:
                return await message.channel.send("❌ عذراً، هذا الأمر خاص بصاحب السيرفر والمشرفين (Administrator) فقط!", delete_after=5)
            
            parts = message.content.strip().split()
            if len(parts) < 2:
                return await message.channel.send("❌ الاستخدام الصحيح: `نقاط @الشخص المبلغ` أو `نقاط [ID] المبلغ`", delete_after=5)
            
            target_user = None
            amount_str = parts[-1]
            
            # محاولة جلب العضو من المنشن أو الـ ID أو الاسم
            if message.mentions:
                target_user = message.mentions[0]
            else:
                target_identifier = parts[1].strip()
                if target_identifier.isdigit():
                    target_user = message.guild.get_member(int(target_identifier))
                else:
                    possible_name = target_identifier.replace("@", "").lower()
                    for member in message.guild.members:
                        if possible_name in member.name.lower() or (member.nick and possible_name in member.nick.lower()):
                            target_user = member
                            break
            
            if not target_user:
                return await message.channel.send("❌ لم يتم العثور على العضو المطلوب. تأكد من المنشن أو الـ ID الصحيح.", delete_after=5)
            
            try:
                amount = int(amount_str)
            except ValueError:
                return await message.channel.send("❌ يرجى التأكد من كتابة رقم صحيح للمبلغ (سواء للإضافة أو الخصم مثل: 50 أو -50).", delete_after=5)
            
            new_tot = await add_points(guild_id, target_user.id, amount)
            action_word = "إضافة" if amount >= 0 else "خصم"
            await message.channel.send(f"✅ تم {action_word} **{abs(amount)}** نقطة بنجاح لـ {target_user.mention}!\nرصيده الحالي: `{new_tot}` نقطة.")
            return

        # 11. حل مشكلة أمر النرد بـ منشن ومبلغ (مثال: نرد @شخص 50)
        if text.startswith("نرد "):
            parts = message.content.strip().split()
            if message.mentions:
                target_user = message.mentions[0]
                if target_user.id == user_id:
                    return await message.channel.send("❌ لا يمكنك تحدي نفسك في النرد!", delete_after=5)
                
                amount = 50
                for p in parts:
                    if p.isdigit():
                        amount = int(p)
                        break
                
                rem = self.check_cooldown(user_id, "نرد_تحدي")
                if rem > 0:
                    mins, secs = divmod(rem, 60)
                    return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** لتحدي النرد مرة أخرى!", delete_after=5)

                user_pts = await get_user_points(guild_id, user_id)
                target_pts = await get_user_points(guild_id, target_user.id)

                if user_pts < amount or target_pts < amount:
                    return await message.channel.send(f"❌ أحد الطرفين لا يملك نقاط كافية لرهان بقيمة `{amount}` نقطة!", delete_after=5)

                await message.channel.send(f"🎲 {target_user.mention}, لقد تحداك {message.author.mention} في لعبة النرد برهان **{amount} نقطة**!\nاكتب `قبول` في الشات خلال 15 ثانية للموافقة:")
                def check_accept(m):
                    return m.author.id == target_user.id and m.channel.id == channel_id and m.content.strip() == "قبول"
                try:
                    await self.bot.wait_for("message", timeout=15.0, check=check_accept)
                    r1 = random.randint(1, 6)
                    r2 = random.randint(1, 6)
                    
                    if r1 > r2:
                        await add_points(guild_id, target_user.id, -amount)
                        new_p = await add_points(guild_id, user_id, amount)
                        await message.channel.send(f"🏆 النرد أسفر عن: ({message.author.name}: `{r1}` VS {target_user.name}: `{r2}`).\nفاز {message.author.mention} وربح `{amount}` نقطة! رصيده الجديد: `{new_p}`")
                    elif r2 > r1:
                        await add_points(guild_id, user_id, -amount)
                        new_p = await add_points(guild_id, target_user.id, amount)
                        await message.channel.send(f"🏆 النرد أسفر عن: ({message.author.name}: `{r1}` VS {target_user.name}: `{r2}`).\nفاز {target_user.mention} وربح `{amount}` نقطة! رصيده الجديد: `{new_p}`")
                    else:
                        await message.channel.send(f"🤝 تعادل في النرد (`{r1}` مقابل `{r2}`)! لم يتم خصم أو إضافة نقاط.")
                except asyncio.TimeoutError:
                    await message.channel.send(f"⌛ انتهى الوقت ولم يقبل {target_user.mention} التحدي.")
                return

        # 12. حل مشكلة أمر التحدي المباشر بين لاعبين
        if text.startswith("تحدي "):
            if message.mentions:
                target_user = message.mentions[0]
                if target_user.id == user_id:
                    return await message.channel.send("❌ لا يمكنك تحدي نفسك!", delete_after=5)

                rem = self.check_cooldown(user_id, "مبارزة")
                if rem > 0:
                    mins, secs = divmod(rem, 60)
                    return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** للمبارزة مرة أخرى!", delete_after=5)

                await message.channel.send(f"⚔️ {target_user.mention}, أرسل لك {message.author.mention} تحدياً مباشراً!\nاكتب `موافقة` خلال 15 ثانية لدخول المعركة:")
                def check_duel(m):
                    return m.author.id == target_user.id and m.channel.id == channel_id and m.content.strip() == "موافقة"
                try:
                    await self.bot.wait_for("message", timeout=15.0, check=check_duel)
                    winner = random.choice([message.author, target_user])
                    loser = target_user if winner == message.author else message.author
                    
                    await add_points(guild_id, loser.id, -30)
                    new_win_pts = await add_points(guild_id, winner.id, 50)
                    
                    await message.channel.send(f"🔥 اشتعلت المعركة بين المحاربين!\n👑 البطل الفائز: {winner.mention} وحصل على **+50 نقطة** (رصيده: {new_win_pts})\n💀 الخاسر: {loser.mention} وخسر **-30 نقطة**.")
                except asyncio.TimeoutError:
                    await message.channel.send(f"⌛ انتهى الوقت ولم يستجب {target_user.mention} للتحدي.")
                return

        # --- الألعاب التفاعلية المصممة خصيصاً (بدون أسئلة عامة مكررة) ---

        # 1. لعبة صيد الكنز (البحث عن الكنز)
        if text == "كنز" or text == "صيد":
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

        # 2. لعبة النرد السريع (اختيار عالي ومنخفض)
        if text == "نرد":
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

        # 3. عجلة الحظ والأبواب (فتح صناديق وأبواب)
        elif text in ["حظ", "روليت"]:
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

        # 4. حجرة ورقة مقص (لعبة تعتمد على الحظ والمهارة)
        elif text in ["مقص", "حجر ورقة مقص"]:
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

        # 5. الألعاب التفاعلية الأخرى المتنوعة (تخطي الأسئلة المكررة وتصميم ألعاب فريدة مثل سرعة الضغط، هروب الوحش، متاهة، قنبلة مؤقتة، إلخ)
        elif text in [g["cmd"] for g in GAMES_LIST]:
            game_obj = next(g for g in GAMES_LIST if g["cmd"] == text)
            game_name = game_obj["name"]
            
            rem = self.check_cooldown(user_id, text)
            if rem > 0:
                mins, secs = divmod(rem, 60)
                return await message.channel.send(f"⏳ انتظر **{mins} دقيقة و {secs} ثانية** للعب ({game_name}) مرة أخرى!", delete_after=5)

            # تخصيص ألعاب فريدة ومختلفة كلياً عن نظام الأسئلة التقليدية
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

            scenario = unique_game_scenarios.get(text, {
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
