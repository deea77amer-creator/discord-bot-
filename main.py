import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ البوت شغال وجاهز باسم: {bot.user}")

@bot.command()
async def هلا(ctx):
    await ctx.send(f"أهلاً بك يا {ctx.author.mention}! البوت يعمل بنجاح من الجوال.")

# تشغيل البوت باستخدام التوكن المخفي
token = os.environ.get("DISCORD_TOKEN")
bot.run(token)
