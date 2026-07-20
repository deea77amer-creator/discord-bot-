import discord
from discord.ext import commands

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content.strip() == "اوامر":
            embed = discord.Embed(
                title="📜 قائمة أوامر البوت الشاملة",
                description="مرحباً بك! إليك جميع أوامر الألعاب والإدارة المتاحة:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🎮 الألعاب المتاحة",
                value="`عجلة`, `نرد`, `صناديق`, `مقص`, `تخمين`, `حظك`, `تحدي السرعة`, `حساب`, `كنز`, `بلنتي`, `سلة`, `صيد`, `سيارات`, `تعدين`, `مبارزة`",
                inline=False
            )
            embed.add_field(
                name="📌 أوامر الحضور والنقاط",
                value="`دخول`, `خروج`, `سجل`, `نقاطي`, `توب`",
                inline=False
            )
            embed.set_footer(text="تم تطوير البوت خصيصاً لك")
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BotCommands(bot))
