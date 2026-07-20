import discord
from discord.ext import commands
import asyncio

class PointsLoggerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_name = "bot-points-storage"

    async def get_or_create_log_channel(self, guild: discord.guild.Guild):
        # البحث عن القناة المخصصة لحفظ النقاط في السيرفر
        channel = discord.utils.get(guild.text_channels, name=self.log_channel_name)
        if not channel:
            # إنشاء القناة وجعلها مخفية أو صعبة الوصول لحمايتها من العبث
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
            }
            channel = await guild.create_text_channel(
                self.log_channel_name, 
                overwrites=overwrites, 
                topic="نظام حفظ نقاط وأرصدة الألعاب السحابي - لا تقم بحذف الرسائل هنا أبداً."
            )
        return channel

    async def fetch_user_points(self, guild: discord.guild.Id, user_id: int) -> int:
        guild_obj = self.bot.get_guild(guild)
        if not guild_obj:
            return 0
        
        channel = await self.get_or_create_log_channel(guild_obj)
        async for message in channel.history(limit=200):
            if message.author == self.bot.user and f"USER:{user_id}" in message.content:
                try:
                    # استخراج النقاط من محتوى رسالة السجل
                    parts = message.content.split("|")
                    for p in parts:
                        if "POINTS:" in p:
                            return int(p.split(":")[1].strip())
                except:
                    pass
        return 0

    async def update_user_points(self, guild: discord.guild.Id, user_id: int, new_points: int):
        guild_obj = self.bot.get_guild(guild)
        if not guild_obj:
            return
        
        channel = await self.get_or_create_log_channel(guild_obj)
        target_message = None
        
        # البحث عن رسالة المستخدم القديمة لتحديثها
        async for message in channel.history(limit=200):
            if message.author == self.bot.user and f"USER:{user_id}" in message.content:
                target_message = message
                break
        
        content = f"USER:{user_id} | POINTS:{new_points}"
        
        if target_message:
            await target_message.edit(content=content)
        else:
            await channel.send(content)

async def setup(bot):
    await bot.add_cog(PointsLoggerCog(bot))
