import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from pymongo import MongoClient

# إعداد خلفية ويب لمنع انقطاع البوت
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# الاتصال بقاعدة البيانات السحابية MongoDB
MONGO_URL = os.getenv("MONGO_URL")
db = None
users_collection = None

if MONGO_URL:
    try:
        client = MongoClient(MONGO_URL)
        db = client["discord_bot_db"]
        users_collection = db["users"]
        print("Connected to MongoDB successfully!")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
else:
    print("Warning: MONGO_URL is not set!")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # نظام نقاط تفاعلي بسيط كمثال
    if users_collection is not None:
        user_id = str(message.author.id)
        # تحديث أو إضافة نقاط عند التفاعل
        users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"points": 1}, "$set": {"name": message.author.name}},
            upsert=True
        )

    await bot.process_commands(message)

# أمر نقاطي
@bot.command(name="نقاطي")
async def my_points(ctx):
    if users_collection is None:
        await ctx.send("قاعدة البيانات غير متصلة حالياً.")
        return
    
    user_id = str(ctx.author.id)
    user_data = users_collection.find_one({"user_id": user_id})
    points = user_data.get("points", 0) if user_data else 0
    await ctx.send(f"{ctx.author.mention}, رصيدك الحالي هو: **{points}** نقطة.")

# أمر الترتيب أو top
@bot.command(name="top", aliases=["توب"])
async def leaderboard(ctx):
    if users_collection is None:
        await ctx.send("قاعدة البيانات غير متصلة حالياً.")
        return

    top_users = list(users_collection.find().sort("points", -1).limit(10))
    
    if not top_users:
        await ctx.send("لا توجد بيانات مسجلة حتى الآن.")
        return

    desc = ""
    for index, user in enumerate(top_users, start=1):
        name = user.get("name", "مستخدم")
        points = user.get("points", 0)
        desc += f"**{index}.** {name} — **{points}** نقطة\n"

    embed = discord.Embed(title="🏆 قائمة الترتيب الأفضل (Top 10)", description=desc, color=discord.Color.gold())
    await ctx.send(embed=embed)

keep_alive()
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN is missing!")
