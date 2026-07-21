import discord
from discord.ext import commands
import os
from pymongo import MongoClient

# --- الاتصال بقاعدة البيانات السحابية MongoDB الموحدة ---
MONGO_URL = os.getenv("MONGO_URL")
db = None
config_collection = None

if MONGO_URL:
    try:
        client = MongoClient(MONGO_URL)
        db = client["discord_bot_db"]
        config_collection = db["config"]
    except Exception as e:
        print(f"Error connecting to MongoDB in channel_storage.py: {e}")

class ChannelStorageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # تم الاحتفاظ بمتغير الآيدي لتجنب حذف أي شيء من كودك الأصلي
        self.storage_channel_id = 1528829118681059498

    def get_config_data(self, guild_id):
        if config_collection is None:
            return {}
        config = config_collection.find_one({"guild_id": str(guild_id)})
        if config:
            # استخراج جميع الإعدادات المحفوظة للسيرفر عدا مفتاح الآيدي الخاص بقاعدة البيانات
            data = dict(config)
            data.pop("_id", None)
            data.pop("guild_id", None)
            return data
        return {}

    def save_config_data(self, guild_id, key, value):
        if config_collection is None:
            return
        config_collection.update_one(
            {"guild_id": str(guild_id)},
            {"$set": {key: value}},
            upsert=True
        )

    @commands.command(name="تحديد")
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx, channel_type: str, channel: discord.TextChannel = None):
        if not ctx.guild:
            return
            
        if channel is None:
            channel = ctx.channel

        key = channel_type.lower()
        save_config_data_guild = ctx.guild.id
        
        # حفظ القناة مباشرة في MongoDB السحابي لضمان الأمان وعدم الضياع
        self.save_config_data(save_config_data_guild, key, channel.id)

        await ctx.send(f"✅ تم حفظ وتحديد قناة ({channel_type}) بنجاح وحفظها تلقائياً في قاعدة البيانات: {channel.mention}")

    @commands.command(name="قنواتي")
    @commands.has_permissions(administrator=True)
    async def show_all_channels(self, ctx):
        if not ctx.guild:
            return
            
        config_data = self.get_config_data(ctx.guild.id)

        if not config_data:
            await ctx.send("❌ لم يتم حفظ أي قناة حتى الآن.")
            return

        embed = discord.Embed(
            title="📌 القنوات المحفوظة في النظام",
            color=discord.Color.green()
        )
        
        for key, ch_id in config_data.items():
            if ch_id:
                ch = self.bot.get_channel(int(ch_id))
                ch_mention = ch.mention if ch else f"قناة محذوفة (ID: {ch_id})"
                embed.add_field(name=f"• النوع: {key}", value=ch_mention, inline=False)

        if len(embed.fields) == 0:
            await ctx.send("❌ لم يتم حفظ أي قناة حتى الآن.")
            return

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ChannelStorageCog(bot))
