import discord
from discord.ext import commands
import json

class ChannelStorageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # تم تثبيت الآيدي الذي أرسلته هنا
        self.storage_channel_id = 1528829118681059498
        self.config_data = {}
        self.bot.loop.create_task(self.async_load_data())

    async def async_load_data(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(self.storage_channel_id)
        if not channel:
            return

        try:
            async for message in channel.history(limit=10):
                if message.author == self.bot.user and message.content.startswith("{"):
                    self.config_data = json.loads(message.content)
                    break
        except Exception as e:
            print(f"خطأ أثناء استرجاع البيانات من القناة: {e}")

    async def save_data_to_discord(self):
        channel = self.bot.get_channel(self.storage_channel_id)
        if not channel:
            return

        content = json.dumps(self.config_data, ensure_ascii=False)

        try:
            async for message in channel.history(limit=10):
                if message.author == self.bot.user and message.content.startswith("{"):
                    await message.edit(content=content)
                    return
            
            await channel.send(content)
        except Exception as e:
            print(f"خطأ أثناء حفظ البيانات في القناة: {e}")

    @commands.command(name="تحديد")
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx, channel_type: str, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        key = channel_type.lower()
        self.config_data[key] = channel.id
        await self.save_data_to_discord()

        await ctx.send(f"✅ تم حفظ وتحديد قناة ({channel_type}) بنجاح وحفظها تلقائياً في قناة الديسكورد: {channel.mention}")

    @commands.command(name="قنواتي")
    @commands.has_permissions(administrator=True)
    async def show_all_channels(self, ctx):
        if not self.config_data:
            await ctx.send("❌ لم يتم حفظ أي قناة حتى الآن.")
            return

        embed = discord.Embed(
            title="📌 القنوات المحفوظة في النظام",
            color=discord.Color.green()
        )
        
        for key, ch_id in self.config_data.items():
            ch = self.bot.get_channel(ch_id)
            ch_mention = ch.mention if ch else f"قناة محذوفة (ID: {ch_id})"
            embed.add_field(name=f"• النوع: {key}", value=ch_mention, inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ChannelStorageCog(bot))
