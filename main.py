import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from pymongo import MongoClient

# استيراد الأوامر التي أعددناها سابقاً
from bot.commands import setup_commands

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
        # تفعيل وتشغيل الأوامر الخارجية التي أرسلتها
        await setup_commands(self)
        print("تم تفعيل وتثبيت جميع الأوامر الخارجية بنجاح!")

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

        # تحميل الملفات من مجلد الألعاب bot/games تلقائياً
        games_paths = ['./bot/games', './games']
        loaded_games = False
        for path in games_paths:
            if os.path.exists(path):
                for filename in os.listdir(path):
                    if filename.endswith('.py'):
                        prefix = path.replace('./', '').replace('/', '.')
                        cog_name = f"{prefix}.{filename[:-3]}"
                        try:
                            await self.load_extension(cog_name)
                            print(f"تم تحميل ملف الألعاب/السوق بنجاح: {filename}")
                            loaded_games = True
                        except Exception as e:
                            print(f"فشل تحميل {filename}: {e}")
                if loaded_games:
                    break

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
        return {"guild_id": str(guild_id), "user_id": str(user_id), "joins": 0, "leaves": 0, "points": 0, "checkins_count": 0, "manual_leaves_count": 0, "last_checkin": "", "last_leave": ""}
    
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
    users_collection.update_one(query, {"$set": kwargs}, upsert=True)

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

# --- أمر نقاطي ---
@bot.command(name="نقاطي")
async def my_points(ctx):
    if not ctx.guild:
        return
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    data = get_user_data(guild_id, user_id)
    await ctx.send(f"💰 رصيدك الحالي يا {ctx.author.mention}: **{data.get('points', 0)}** نقطة.")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    
    # معالجة الأوامر والملفات الخارجية
    await bot.process_commands(message)

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        keep_alive()  # تشغيل سيرفر الـ Flask أولاً في الخلفية
        bot.run(token) # تشغيل البوت
    else:
        print("خطأ: التوكن غير موجود!")
