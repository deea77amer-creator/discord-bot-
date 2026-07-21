import discord
from discord.ext import commands
import os
from pymongo import MongoClient
from datetime import datetime

# --- الاتصال بقاعدة البيانات السحابية MongoDB الموحدة ---
MONGO_URL = os.getenv("MONGO_URL")
db = None
users_collection = None
auth_logs_collection = None
user_status_collection = None

if MONGO_URL:
    try:
        client = MongoClient(MONGO_URL)
        db = client["discord_bot_db"]
        users_collection = db["users"]
        auth_logs_collection = db["auth_logs"]
        user_status_collection = db["user_status"]
    except Exception as e:
        print(f"Error connecting to MongoDB in auth_cog.py: {e}")

def init_auth_db():
    # تم إبقاء هذه الدالة لتتوافق مع هيكلة كودك الأصلي بدون حذفها
    pass

init_auth_db()

def get_user_data(guild_id, user_id):
    if users_collection is None:
        return 0
    query = {"guild_id": str(guild_id), "user_id": str(user_id)}
    doc = users_collection.find_one(query)
    if not doc:
        users_collection.insert_one({
            "guild_id": str(guild_id),
            "user_id": str(user_id),
            "points": 0
        })
        return 0
    return doc.get("points", 0)

def add_points(guild_id, user_id, amount):
    if users_collection is None:
        return 0
    current = get_user_data(guild_id, user_id)
    new_points = current + amount
    query = {"guild_id": str(guild_id), "user_id": str(user_id)}
    users_collection.update_one(
        query,
        {"$set": {"points": new_points}},
        upsert=True
    )
    return new_points

def get_user_status(guild_id, user_id):
    if user_status_collection is None:
        return None
    query = {"guild_id": str(guild_id), "user_id": str(user_id)}
    doc = user_status_collection.find_one(query)
    if doc:
        return doc.get("last_action")
    return None

def update_user_status(guild_id, user_id, action):
    if user_status_collection is not None:
        # تحديث آخر حركة للمستخدم في MongoDB
        user_status_collection.update_one(
            {"guild_id": str(guild_id), "user_id": str(user_id)},
            {"$set": {"last_action": action}},
            upsert=True
        )
    
    if auth_logs_collection is not None:
        # تسجيل الحركة في السجلات السحابية
        now_str = datetime.now().isoformat()
        auth_logs_collection.insert_one({
            "guild_id": str(guild_id),
            "user_id": str(user_id),
            "action": action,
            "timestamp": now_str
        })

def get_user_stats(guild_id, user_id):
    stats = {"دخول": 0, "خروج": 0}
    if auth_logs_collection is None:
        return stats
    
    query = {"guild_id": str(guild_id), "user_id": str(user_id)}
    logs = auth_logs_collection.find(query)
    for log in logs:
        action = log.get("action")
        if action in stats:
            stats[action] += 1
            
    return stats

class AuthCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.LOGIN_CHANNEL_ID = 1528779670911320174
        self.LOGOUT_CHANNEL_ID = 1528604200710308011

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        text = message.content.strip().lower()
        guild_id = message.guild.id
        user_id = message.author.id
        channel_id = message.channel.id

        last_act = get_user_status(guild_id, user_id)

        if text in ["دخول", "/دخول"]:
            if channel_id != self.LOGIN_CHANNEL_ID:
                try:
                    await message.delete()
                except:
                    pass
                return

            if last_act == "دخول":
                try:
                    await message.delete()
                except:
                    pass
                return await message.channel.send(f"❌ يا {message.author.mention}, لقد قمت بتسجيل **الدخول** مسبقاً ولا يمكنك تكراره حتى تسجل الخروج!", delete_after=5)

            update_user_status(guild_id, user_id, "دخول")
            new_pts = add_points(guild_id, user_id, 5) # مكافأة 5 نقاط عند تسجيل الدخول
            await message.channel.send(f"✅ يا {message.author.mention}, تم تسجيل **الدخول** بنجاح! (رصيد النقاط: {new_pts} نقطة).")
            return

        if text in ["خروج", "/خروج"]:
            if channel_id != self.LOGOUT_CHANNEL_ID:
                try:
                    await message.delete()
                except:
                    pass
                return

            if last_act == "خروج" or last_act is None:
                try:
                    await message.delete()
                except:
                    pass
                return await message.channel.send(f"❌ يا {message.author.mention}, أنت لم تقم بتسجيل الدخول أساساً لتسجل الخروج!", delete_after=5)

            update_user_status(guild_id, user_id, "خروج")
            current_pts = get_user_data(guild_id, user_id)
            await message.channel.send(f"🚪 يا {message.author.mention}, تم تسجيل **الخروج** بنجاح. (رصيد النقاط: {current_pts} نقطة).")
            return

        if text in ["سجل", "/سجل", "نقاطي"]:
            # السماح بأمر السجل والنقاط فقط في قناة الدخول أو قناة الخروج
            if channel_id not in [self.LOGIN_CHANNEL_ID, self.LOGOUT_CHANNEL_ID]:
                try:
                    await message.delete()
                except:
                    pass
                return

            stats = get_user_stats(guild_id, user_id)
            current_pts = get_user_data(guild_id, user_id)
            embed = discord.Embed(
                title=f"📊 سِجِلات الحُضُور ونِقَاط لـ {message.author.display_name}",
                color=discord.Color.blue()
            )
            embed.add_field(name="📥 مرات الدخول", value=f"`{stats['دخول']}` مرة", inline=True)
            embed.add_field(name="📤 مرات الخروج", value=f"`{stats['خروج']}` مرة", inline=True)
            embed.add_field(name="⭐ رصيد النقاط", value=f"`{current_pts}` نقطة", inline=False)
            embed.set_footer(text="💡 يتم حفظ النقاط بشكل دائم ومشاركته مع الألعاب.")
            await message.channel.send(embed=embed)
            return

async def setup(bot):
    await bot.add_cog(AuthCog(bot))
