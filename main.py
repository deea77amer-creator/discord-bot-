import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from pymongo import MongoClient

# --- إعداد سيرفر الـ Flask الوهمي لمنع Port Timeout ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="", intents=intents)

    async def setup_hook(self):
        # تحميل الملفات تلقائياً من مجلد cogs إن وجد
        if os.path.exists('./cogs'):
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    cog_name = f'cogs.{filename[:-3]}'
                    try:
                        await self.load_extension(cog_name)
                        print(f"تم تحميل الملف بنجاح: {filename}")
                    except commands.errors.ExtensionAlreadyLoaded:
                        pass
        # تحميل ملف games مباشرة
        try:
            await self.load_extension('games')
            print("تم تحميل ملف games بنجاح")
        except Exception as e:
            print(f"فشل تحميل ملف games: {e}")

    async def on_ready(self):
        print(f"البوت جاهز ومتصل بقاعدة البيانات السحابية MongoDB باسم: {self.user}")

bot = MyBot()

# --- الاتصال بقاعدة البيانات السحابية MongoDB ---
MONGO_URL = os.getenv("MONGO_URL")
db = None
users_collection = None
config_collection = None

if MONGO_URL:
    try:
        client = MongoClient(MONGO_URL)
        db = client["discord_bot_db"]
        users_collection = db["users"]
        config_collection = db["config"]
        print("Connected to MongoDB successfully!")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
else:
    print("Warning: MONGO_URL is not set!")

def get_user_data(guild_id, user_id):
    if users_collection is None:
        return {"joins": 0, "leaves": 0, "points": 0, "checkins_count": 0, "manual_leaves_count": 0, "last_checkin": "", "last_leave": ""}
    
    query = {"guild_id": str(guild_id), "user_id": str(user_id)}
    data = users_collection.find_one(query)
    
    if not data:
        default_data = {
            "guild_id": str(guild_id),
            "user_id": str(user_id),
            "joins": 0, "leaves": 0, "points": 0,
            "checkins_count": 0, "manual_leaves_count": 0,
            "last_checkin": "", "last_leave": ""
        }
        users_collection.insert_one(default_data)
        return default_data
    return data

def update_user_data(guild_id, user_id, **kwargs):
    if users_collection is None:
        return
    get_user_data(guild_id, user_id)
    query = {"guild_id": str(guild_id), "user_id": str(user_id)}
    users_collection.update_one(query, {"$set": kwargs})

def get_config(guild_id):
    if config_collection is None:
        return {}
    config = config_collection.find_one({"guild_id": str(guild_id)})
    if config:
        return {
            "welcome_channel": config.get("welcome_channel"),
            "leave_channel": config.get("leave_channel"),
            "games_channel": config.get("games_channel"),
            "records_channel": config.get("records_channel"),
            "top_channel": config.get("top_channel")
        }
    return {}

def save_config_key(guild_id, key, value):
    if config_collection is None:
        return
    config_collection.update_one(
        {"guild_id": str(guild_id)},
        {"$set": {key: value}},
        upsert=True
    )

@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    data = get_user_data(guild_id, user_id)
    new_joins = data.get("joins", 0) + 1
    update_user_data(guild_id, user_id, joins=new_joins)

    config = get_config(guild_id)
    if config.get("welcome_channel"):
        channel = member.guild.get_channel(config["welcome_channel"])
        if channel:
            embed = discord.Embed(title="✨ | وعاد النور إلى السيرفر!", description=f"أهلاً ومرحباً بك يا {member.mention}\n• عدد مرات دخولك: **{new_joins}**", color=discord.Color.gold())
            await channel.send(content=f"حياك الله {member.mention} 🚀", embed=embed)

@bot.event
async def on_member_remove(member):
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    data = get_user_data(guild_id, user_id)
    new_leaves = data.get("leaves", 0) + 1
    update_user_data(guild_id, user_id, leaves=new_leaves)

    config = get_config(guild_id)
    if config.get("leave_channel"):
        channel = member.guild.get_channel(config["leave_channel"])
        if channel:
            embed = discord.Embed(title="👋 | طير غادرنا!", description=f"العضو **{member.name}** طلع.\n• إجمالي مرات خروجه: **{new_leaves}**", color=discord.Color.red())
            await channel.send(embed=embed)

@bot.command(name="تحديد_الترحيب")
@commands.has_permissions(administrator=True)
async def set_welcome(ctx):
    save_config_key(ctx.guild.id, "welcome_channel", ctx.channel.id)
    await ctx.send("✅ تم تعيين قناة **الترحيب** بنجاح!")

@bot.command(name="تحديد_الخروج")
@commands.has_permissions(administrator=True)
async def set_leave(ctx):
    save_config_key(ctx.guild.id, "leave_channel", ctx.channel.id)
    await ctx.send("✅ تم تعيين قناة **الخروج** بنجاح!")

@bot.command(name="تحديد_الألعاب")
@commands.has_permissions(administrator=True)
async def set_games(ctx):
    save_config_key(ctx.guild.id, "games_channel", ctx.channel.id)
    await ctx.send("✅ تم تعيين قناة **الألعاب** بنجاح!")

@bot.command(name="تحديد_السجلات")
@commands.has_permissions(administrator=True)
async def set_records(ctx):
    save_config_key(ctx.guild.id, "records_channel", ctx.channel.id)
    await ctx.send("✅ تم تعيين قناة **السجلات** بنجاح!")

@bot.command(name="تحديد_التوب")
@commands.has_permissions(administrator=True)
async def set_top(ctx):
    save_config_key(ctx.guild.id, "top_channel", ctx.channel.id)
    await ctx.send("✅ تم تعيين قناة **التوب** بنجاح!")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    text = message.content.strip()
    text_lower = text.lower()
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)
    config = get_config(guild_id)

    if text_lower == "نقاطي":
        data = get_user_data(guild_id, user_id)
        await message.channel.send(f"💰 رصيدك الحالي يا {message.author.mention}: **{data.get('points', 0)}** نقطة.")

    elif text_lower in ["tوب", "!top", "top"]:
        if config.get("top_channel") and message.channel.id != config["top_channel"]:
            await message.delete()
            return

        if users_collection is not None:
            top_users_cursor = users_collection.find({"guild_id": guild_id}).sort("points", -1).limit(10)
            top_users = [(doc.get("user_id"), doc.get("points", 0)) for doc in top_users_cursor]
        else:
            top_users = []

        embed = discord.Embed(title="🏆 قائمة لوحة الشرف (Top 10)", description="أكثر الأعضاء جمعاً للنقاط في السيرفر:", color=discord.Color.gold())
        
        if not top_users:
            embed.description = "لا توجد أي بيانات مسجلة حتى الآن."
        else:
            description_lines = []
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            for index, (u_id, pts) in enumerate(top_users):
                member = message.guild.get_member(int(u_id))
                name = member.display_name if member else f"مغادر ({u_id})"
                medal = medals[index] if index < len(medals) else f"•"
                description_lines.append(f"{medal} **{name}** — `{pts}` نقطة")
            embed.description = "\n".join(description_lines)

        await message.channel.send(embed=embed)

    # الأهم: هذا السطر هو الذي يجبر البوت على إرسال الرسائل لملفات الـ Cogs لتشغيل الألعاب
    await bot.process_commands(message)

if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("خطأ: التوكن غير موجود!")
