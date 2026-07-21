import discord
from discord.ext import commands
import os
from pymongo import MongoClient
import asyncio

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
        print(f"Error connecting to MongoDB in top.py: {e}")

class TopCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # يمكنك تعديل رقم قناة التوب هنا أو جعله ديناميكياً
        self.top_channel_id = 1528917497246515221

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        text = message.content.strip().lower()
        guild_id = str(message.guild.id)

        if text == "توب" or text == "!توب":
            # التحقق من أن الأمر مكتوب في القناة المخصصة
            if message.channel.id != self.top_channel_id:
                await message.delete()
                warn = await message.channel.send(f"❌ عذراً {message.author.mention}, هذا الأمر مخصص فقط في قناة التوب المحددة!", delete_after=4)
                return

            if users_collection is None:
                return await message.channel.send("❌ قاعدة البيانات غير متصلة حالياً.")

            # جلب كل مستخدمي السيرفر وترتيبهم تنازلياً حسب النقاط
            cursor = users_collection.find({"guild_id": guild_id, "points": {"$gt": 0}}).sort("points", -1).limit(10)
            top_users = list(cursor)

            if not top_users:
                return await message.channel.send("📊 لا توجد بيانات نقاط مسجلة حتى الآن في هذا السيرفر!")

            desc = ""
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

            for index, doc in enumerate(top_users):
                uid = doc.get("user_id")
                pts = doc.get("points", 0)
                member = message.guild.get_member(int(uid))
                name = member.mention if member else f"مستخدم مغادر ({uid})"
                medal = medals[index] if index < len(medals) else f"**{index+1}.**"
                desc += f"{medal} {name} ⟵ **{pts:,}** نقطة\n"

            embed = discord.Embed(
                title="🏆 | لوحة الشرف وأكثر الأعضاء تفاعلاً",
                description=desc,
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"طلب بواسطة: {message.author.display_name}")
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TopCommand(bot))
