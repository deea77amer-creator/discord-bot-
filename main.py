import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# إعداد خادم ويب وهمي لإبقاء البوت مستيقظاً على موقع Render المجاني
app = Flask('')

@app.route('/')
def home():
    return "البوت يعمل بنجاح في الخلفية!"

def run_web():
    # Render يطلب تشغيل السيرفر على المنفذ 10000 تلقائياً
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# إعدادات البوت والبادئة الأوامر
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # الصلاحية التي فعلناها في موقع المطورين
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ البوت شغال وجاهز باسم: {bot.user}")

@bot.command()
async def هلا(ctx):
    await ctx.send(f"أهلاً بك يا {ctx.author.mention}! البوت يعمل بنجاح الآن.")

# تشغيل خادم الويب أولاً ثم البوت
keep_alive()

token = os.environ.get("DISCORD_TOKEN")
bot.run(token)
