import discord
from discord.ext import commands

class DiscordStorageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # تخزين مؤقت في الذاكرة عشان البوت يقرأها مباشرة بعد التحديد
        self.memory_channels = {}

    @commands.command(name="تحديد")
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx, channel_type: str, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        key = channel_type.lower()
        self.memory_channels[key] = channel.id

        # نرسل رسالة تأكيد وفيها نثبت البيانات داخل الشات
        await ctx.send(f"✅ تم تحديد وحفظ قناة **{channel_type}** بنجاح: {channel.mention}\n*(تم الحفظ في ذاكرة البوت النشطة)*")

    @commands.command(name="قنواتي")
    @commands.has_permissions(administrator=True)
    async def show_all_channels(self, ctx):
        if not self.memory_channels:
            await ctx.send("❌ لم يتم تحديد أي قناة في الجلسة الحالية.")
            return

        embed = discord.Embed(
            title="📌 القنوات المحددة حالياً",
            color=discord.Color.green()
        )
        for key, ch_id in self.memory_channels.items():
            ch = self.bot.get_channel(ch_id)
            ch_mention = ch.mention if ch else f"مفقود (ID: {ch_id})"
            embed.add_field(name=f"• {key}", value=ch_mention, inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DiscordStorageCog(bot))
